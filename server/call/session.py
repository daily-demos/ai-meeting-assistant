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
from asyncio import Future
from datetime import datetime
from logging import Logger
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

    # Daily-related properties
    _id: str | None
    _call_client: CallClient | None
    _room: Room

    # Shutdown-related properties
    _is_destroyed: bool
    _shutdown_timer: threading.Timer | None = None

    def __init__(self, config: BotConfig):
        super().__init__()
        self._is_destroyed = False
        self._config = config
        self._summary = None
        self._id = None
        self._room = self._get_room_config(self._config.daily_room_url)
        self._logger = self.create_logger(self._room.name)
        self._assistant = OpenAIAssistant(
            config.openai_api_key,
            config.openai_model_name,
            self._logger)
        self._logger.info("Initialized session %s", self._room.name)

    def start(self):
        # Start session on new thread
        task = threading.Thread(target=self._run)
        task.start()
        while not self.is_destroyed:
            time.sleep(1)

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
        call_client = CallClient(event_handler=self)
        self._call_client = call_client
        room = self._room
        self._logger.info("Joining Daily room %s", room.url)
        call_client.join(
            room.url,
            room.token,
            completion=self.on_joined_meeting)

    async def _generate_clean_transcript(self) -> bool:
        """Generates a clean transcript from the raw context."""
        if self._is_destroyed:
            return True
        try:
            await self._assistant.cleanup_transcript()
        except Exception as e:
            self._logger.warning(
                "Failed to generate clean transcript: %s", e)
        return False

    async def _query_assistant(self, custom_query: str = None) -> Future[str]:
        """Queries the configured assistant with either the given query, or the
        configured assistant's default"""

        want_cached_summary = not bool(custom_query)
        answer = None

        # If we want a generic summary, and we have a cached one that's less than 30 seconds old,
        # just return that.
        if want_cached_summary and self._summary:
            seconds_since_generation = time.time() - self._summary.retrieved_at
            if seconds_since_generation < 30:
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
                answer = ("Sorry! I don't have any context saved yet. Please try speaking to add some context and "
                          "confirm that transcription is enabled.")

        return answer

    def on_app_message_sent(self, _, error: str = None):
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
            recipient = "*"

        task = data.get("task")

        answer: str = None
        if task == "summary" or task == "query":
            answer = asyncio.run(self._query_assistant(query))
        elif task == "transcript":
            answer = self._assistant.get_clean_transcript()

        self._call_client.send_app_message({
            "kind": f"ai-{task}",
            "data": answer
        }, participant=recipient, completion=self.on_app_message_sent)

    def on_left_meeting(self, _, error: str = None):
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

        # Similar to above, if this session has already been destroyed for any other reason,
        # Don't do this again.
        if self._is_destroyed:
            self._logger.info("Session %s already destroyed.", self._room.url)
            return

        self._logger.info("Left meeting %s", self._room.url)
        self._assistant.destroy()
        self._is_destroyed = True

    def on_joined_meeting(self, join_data, error):
        """Callback invoked when the bot has joined the Daily room."""
        if error:
            raise Exception("failed to join meeting", error)
        self._logger.info("Bot joined meeting %s", self._room.url)
        self._id = join_data["participants"]["local"]["id"]

        # TODO (Liza): Remove this when transcription started events are invoked
        # as expected
        threading.Thread(
            target=self.start_transcript_polling,
            daemon=True).start()

        self._call_client.set_user_name("Daily AI Assistant")

        # Check whether the bot is actually the only one in the call, in which case
        # the shutdown timer should start. The shutdown will be cancelled if
        # daily-python detects someone new joining.
        self.maybe_start_shutdown()

    def on_error(self, message):
        """Callback invoked when an error is received."""
        self._logger.error("Received meeting error: %s", message)

    async def poll_async_func(self, async_func, interval):
        while True:
            await async_func()
            if self._is_destroyed:
                return
            await asyncio.sleep(interval)

    def start_transcript_polling(self):
        """Starts an asyncio event loop and schedules generate_clean_transcript to run every 30 seconds."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.poll_async_func(
                self._generate_clean_transcript, 30))

    # TODO: (Liza) Uncomment this when transcription events are properly invoked
    # if the transcription is starte before the bot joins.
    # def on_transcription_started(self, status):
    #    self._logger.info("Transcription started: %s", status)
    #    threading.Thread(target=self.start_transcript_polling, daemon=True).start()

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
        user_name = message["user_name"]
        text = message["text"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        metadata = [user_name, 'voice', timestamp]
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
        if state == "left" and not self._is_destroyed:
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
        self._shutdown_timer = threading.Timer(60.0, self.shutdown)
        self._shutdown_timer.start()
        return True

    def shutdown(self):
        """Shuts down the session, leaving the Daily room, invoking the shutdown callback,
        and cancelling any pending Futures"""
        self._logger.info(
            f"Session {self._id} shutting down. Active threads: %s",
            threading.active_count())

        self.cancel_shutdown_timer()
        self._call_client.leave(self.on_left_meeting)

    def cancel_shutdown_timer(self):
        """Cancels the live shutdown timer"""
        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

    def create_logger(self, name) -> Logger:
        """Creates a logger for this session"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s -[%(threadName)s-%(thread)s] - %(levelname)s - %(message)s')

        log_file_path = self._config.get_log_file_path(self._room.name)
        if log_file_path:
            file_handler = logging.FileHandler(
                self._config.get_log_file_path(self._room.name))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        else:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger


def bot_cleanup(session: Session):
    session.shutdown()
    while not session.is_destroyed:
        print("Waiting for bot to leave the call")
        time.sleep(1)

    Daily.deinit()


def main():
    config = get_headless_config()

    Daily.init()

    session = Session(config)
    atexit.register(bot_cleanup, session)
    session.start()


if __name__ == "__main__":
    main()
