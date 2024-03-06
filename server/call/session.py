"""Class representing a single meeting happening within a Daily room.
This is responsible for all Daily operations."""
from __future__ import annotations
import asyncio
import atexit

import dataclasses
import json
import logging
import os.path
import sys
import threading
import time
from threading import Thread
from asyncio import Future
from datetime import datetime
from logging import Handler, Logger
from typing import Mapping, Any
from urllib.parse import urlparse

from daily import Daily, EventHandler, CallClient

from server.config import BotConfig, get_headless_config
from server.llm.openai_assistant import OpenAIAssistant
from server.llm.assistant import Assistant, NoContextError


@dataclasses.dataclass
class Room:
    """Class representing a Daily video call room"""
    url: str = None
    token: str = None
    name: str = None


@dataclasses.dataclass
class Summary:
    """Class representing a Daily meeting summary"""
    content: str
    retrieved_at: time.time()


class Session(EventHandler):
    """Class representing a single meeting happening within a Daily room."""

    _config: BotConfig
    _assistant: Assistant
    _summary: Summary | None
    _session_thread: Thread
    _transcript_thread: Thread

    # Logging
    _logger: Logger
    _log_handler: Handler

    # Daily-related properties
    _id: str | None
    _call_client: CallClient | None
    _room: Room

    # Shutdown-related properties
    _is_destroyed: bool
    _is_shutting_down: bool
    _shutdown_timer: threading.Timer | None = None

    def __init__(self, config: BotConfig):
        super().__init__()
        self._is_destroyed = False
        self._is_shutting_down = False
        self._config = config
        self._summary = None
        self._id = None

        self._room = self._get_room_config(self._config.daily_room_url)
        self._logger = logging.getLogger(self._room.name)
        self._log_handler = self.create_log_handler(self._logger)

        # Create Daily client and tell it to ignore incoming audio and video
        # since we don't use that.
        self._call_client = CallClient(event_handler=self)
        self._call_client.update_subscription_profiles({
            "base": {
                "camera": "unsubscribed",
                "microphone": "unsubscribed"
            }
        })

        self._assistant = OpenAIAssistant(
            config.openai_api_key,
            config.openai_model_name,
            self._logger)

        self._session_thread = threading.Thread(target=self._run)
        self._transcript_thread = threading.Thread(
            target=self._start_transcript_polling, daemon=True)
        self._logger.info("Initialized session %s", self._room.name)

    def start(self):
        # Start running the thread
        self._session_thread.start()

    @property
    def room_url(self) -> str:
        return self._room.url

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_destroyed(self) -> bool:
        return self._is_destroyed

    def _get_room_config(self, room_url: str = None) -> Room:
        """Creates a Daily room and uses it to start a session"""
        parsed_url = urlparse(room_url)
        room_name = os.path.basename(parsed_url.path)
        token = self._config.daily_meeting_token
        room = Room(url=room_url, name=room_name, token=token)
        return room

    def _run(self):
        """Waits for at least one person to join the associated Daily room,
        then joins, starts transcription, and begins registering context."""
        room = self._room
        self._logger.info("Joining Daily room %s", room.url)
        self._call_client.join(
            room.url,
            room.token,
            completion=self.on_joined_meeting)
        while not self._is_shutting_down:
            time.sleep(1)

    async def _generate_clean_transcript(self) -> bool:
        """Generates a clean transcript from the raw context."""
        if self._is_shutting_down:
            return False
        try:
            await self._assistant.cleanup_transcript()
        except Exception as e:
            self._logger.warning(
                "Failed to generate clean transcript: %s", e)
        return True

    async def _query_assistant(self, custom_query: str = None) -> Future[str]:
        """Queries the configured assistant with either the given query, or the
        configured assistant's default"""

        want_cached_summary = not bool(custom_query)
        answer = None

        # If we want a generic summary, and we have a cached one that's less than 15 seconds old,
        # just return that.
        if want_cached_summary and self._summary:
            seconds_since_generation = time.time() - self._summary.retrieved_at
            if seconds_since_generation < 15:
                self._logger.info("Returning cached summary")
                answer = self._summary.content

        # If we don't have a cached summary, or it's too old, query the
        # assistant.
        if not answer:
            self._logger.info("Querying assistant")
            try:
                answer = await self._assistant.query(custom_query)
                # If there was no custom query provided, save this as cached
                # summary.
                if want_cached_summary:
                    self._logger.info("Saving general summary")
                    self._summary = Summary(
                        content=answer, retrieved_at=time.time())
            except NoContextError:
                answer = (
                    "I don't have any context saved yet. Please speak to add some context or "
                    "confirm that transcription is enabled.")
            except Exception as e:
                self._logger.error(
                    "Failed to query assistant: %s", e)
                answer = (
                    "Something went wrong while generating the summary. Please check the server logs.")

        return answer

    def on_app_message_sent(self, error: str = None):
        """Callback invoked when an app message is sent."""
        if error:
            self._logger.error("Failed to send app message: %s", error)

    def on_app_message(self,
                       message: str,
                       sender: str):
        """Callback invoked when a Daily app message is received."""
        # TODO message appears to be a dict when our docs say str.
        # For now dumping it to a JSON string and parsing it back out,
        # until designed behavior is clarified.
        jsonMsg = json.dumps(message)
        data = json.loads(jsonMsg)
        kind = data.get("kind")
        if kind != "assist":
            return

        query = data.get("query")

        recipient = sender

        # If this is a broadcast, set recipient to all participants
        if bool(data.get("broadcast")):
            recipient = None

        task = data.get("task")

        answer: str = None
        error: str = None
        try:
            if task == "summary" or task == "query":
                answer = asyncio.run(self._query_assistant(query))
            elif task == "transcript":
                answer = self._assistant.get_clean_transcript()
        except Exception as e:
            self._logger.error("Failed to query assistant: %s", e)
            error = "Sorry! I ran into an error. Please try again."

        msg_data = {
            "kind": f"ai-{task}",
        }

        if answer:
            msg_data["data"] = answer

        if error:
            msg_data["error"] = error
        self._call_client.send_app_message(
            msg_data,
            participant=recipient,
            completion=self.on_app_message_sent)

    def on_left_meeting(self, error: str = None):
        """Cancels any ongoing shutdown timer and marks this session as destroyed"""
        if error:
            self._logger.error(
                "Encountered error while leaving meeting: %s", error)

        # There's a chance of a shutdown timer being ongoing at the time the bot
        # is kicked or leaves for other reasons. Clean up the shutdown timer if
        # that is the case.
        if self._shutdown_timer:
            self._logger.info(
                "Participant left meeting - cancelling shutdown.")
            self.cancel_shutdown_timer()

        self._logger.info("Left meeting %s", self._room.url)

    def on_joined_meeting(self, join_data, error):
        """Callback invoked when the bot has joined the Daily room."""
        if error:
            raise Exception("failed to join meeting", error)
        self._logger.info("Bot joined meeting %s", self._room.url)
        self._id = join_data["participants"]["local"]["id"]

        self._call_client.set_user_name("Daily AI Assistant")

        # Check whether the bot is actually the only one in the call, in which case
        # the shutdown timer should start. The shutdown will be cancelled if
        # daily-python detects someone new joining.
        self.maybe_start_shutdown()

    def on_error(self, message):
        """Callback invoked when an error is received."""
        self._logger.error("Received meeting error: %s", message)

    async def _poll_async_func(self, async_func, interval):
        while True:
            if not await async_func():
                return
            await asyncio.sleep(interval)

    def _start_transcript_polling(self):
        """Starts an asyncio event loop and schedules generate_clean_transcript to run every 15 seconds."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self._poll_async_func(
                self._generate_clean_transcript, 15))

    def on_transcription_started(self, status):
        self._logger.info("Transcription started: %s", status)
        self._transcript_thread.start()

    def on_transcription_stopped(self, stopped_by: str, stopped_by_error: str):
        self._logger.info(
            "Transcription stopped: %s (%s)",
            stopped_by,
            stopped_by_error)

    def on_transcription_error(self, message):
        """Callback invoked when a transcription error is received."""
        self._logger.error("Received transcription error: %s", message)

    def on_transcription_message(self, message):
        """Callback invoked when a transcription message is received."""
        try:
            participant_id = message["participantId"]
            participant = self._call_client.participants()[participant_id]
            participant_user_name = participant["info"]["userName"]
            user_name = f'Name: {participant_user_name}'
        except Exception as e:
            self._logger.error("Failed to get speaker's name: %s", e)
            user_name = "Name: Unknown"
        text = message["text"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        metadata = [user_name, 'voice', f"Sent at {timestamp}"]
        self._assistant.register_new_context(text, metadata)

    def on_participant_joined(self, participant):
        # As soon as someone joins, stop shutdown process if one is in progress
        if self._shutdown_timer:
            self._logger.info("Participant joined - cancelling shutdown.")
            self.cancel_shutdown_timer()

    def on_participant_left(self,
                            participant,
                            reason):
        """Callback invoked when a participant leaves the Daily room."""
        self.maybe_start_shutdown()

    def on_call_state_updated(self, state: Mapping[str, Any]) -> None:
        """Invoked when the Daily call state has changed"""
        self._logger.info(
            "Call state updated for session %s: %s",
            self._room.url,
            state)
        if state == "left" and not self._is_shutting_down:
            self._logger.info("Call state left, destroying immediately")
            self.on_left_meeting(None)

    def maybe_start_shutdown(self) -> bool:
        """Checks if the session should be shut down, and if so, starts the shutdown process."""
        count = self._call_client.participant_counts()['present']
        self._logger.info(
            "Participant count: %s", count)

        # If there is at least one present participant, do nothing.
        if count > 1:
            return False

        self._logger.info("Starting shutdown timer")

        # If there are no present participants left, wait 1 minute and
        # start shutdown.
        if not self._shutdown_timer:
            self._shutdown_timer = threading.Timer(60.0, self.shutdown)
            self._shutdown_timer.start()
        return True

    def shutdown(self):
        """Shuts down the session, leaving the Daily room, invoking the shutdown callback,
        and cancelling any pending Futures"""
        self._is_shutting_down = True

        self._logger.info(
            f"Session {self._id} shutting down. Active threads: %s",
            threading.active_count())

        self.cancel_shutdown_timer()
        self._call_client.leave(self.on_left_meeting)
        self._call_client.release()

        self._session_thread.join()
        try:
            self._transcript_thread.join()
        except Exception as e:
            self._logger.warning("Failed to join transcript thread: %s", e)

        self._assistant.destroy()

        self._logger.info(
            f"Session {self._id} completely shut down. Active threads: %s",
            threading.active_count())

        self._logger.removeHandler(self._log_handler)

        self._is_destroyed = True

    def cancel_shutdown_timer(self):
        """Cancels the live shutdown timer"""
        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

    def create_log_handler(self, logger) -> Handler:
        """Creates a logger for this session"""
        formatter = logging.Formatter(
            '%(asctime)s -[%(threadName)s-%(thread)s] - %(levelname)s - %(message)s')

        log_file_path = self._config.get_log_file_path(self._room.name)
        if log_file_path:
            handler = logging.FileHandler(log_file_path)
        else:
            handler = logging.StreamHandler(sys.stdout)

        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)

        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        return handler


def bot_cleanup(session: Session):
    session.shutdown()
    while not session.is_destroyed:
        print("Waiting for bot to leave the call")
        time.sleep(1)


def main():
    config = get_headless_config()

    Daily.init()

    session = Session(config)
    atexit.register(bot_cleanup, session)
    session.start()

    Daily.deinit()


if __name__ == "__main__":
    main()
