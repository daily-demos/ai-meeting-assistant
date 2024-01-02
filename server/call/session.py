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

import polling2
import requests
from daily import Daily, EventHandler, CallClient
from server.call.errors import HeadlessNotPermittedException, handle_daily_error_res

from server.config import Config, HeadlessConfig, get_headless_config
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

    _is_headless = False
    _config: Config | HeadlessConfig
    _assistant: Assistant
    _summary: Summary | None

    # Daily-related properties
    _id: str | None
    _call_client: CallClient | None
    _room: Room

    # Shutdown-related properties
    _is_destroyed: bool
    _shutdown_timer: threading.Timer | None = None

    # Daily-REST-API-related properties
    _daily_auth_headers: dict[str, str] = None
    _daily_api_url: str = None

    def __init__(self, config: Config | HeadlessConfig,
                 room_duration_mins: int = None, room_url: str = None):
        super().__init__()
        self._is_destroyed = False

        headless = isinstance(config, HeadlessConfig)

        self._is_headless = headless
        self._config = config
        self._summary = None
        self._id = None
        if not headless:
            self.set_daily_request_data(room_url)
        self.init(room_duration_mins, room_url)
        self._logger = self.create_logger(self._room.name)
        self._assistant = OpenAIAssistant(
            config.openai_api_key,
            config.openai_model_name,
            self._logger)
        self._logger.info("Initialized session %s", self._room.name)

    @property
    def room_url(self) -> str:
        return self._room.url

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_destroyed(self) -> bool:
        return self._is_destroyed

    def init(self, room_duration_mins: int = None,
             room_url: str = None) -> str:
        """Creates a Daily room and uses it to start a session"""

        room = None

        if self._is_headless:
            parsed_url = urlparse(room_url)
            room_name = os.path.basename(parsed_url.path)
            print("ROOM NAME:", room_name)
            token = self._config.daily_meeting_token
            room = Room(url=room_url, name=room_name, token=token)
            self._room = room
            return room.url
        elif room_url:
            room = self.get_room(room_url)
        else:
            room = self.create_room(room_duration_mins)

        self._room = room
        task = threading.Thread(target=self.start_session)
        task.start()
        return room.url

    def start_session(self):
        """Waits for at least one person to join the associated Daily room,
        then joins, starts transcription, and begins registering context."""
    
        if not self._is_headless:
            try:
                polling2.poll(
                    target=self.get_participant_count,
                    check_success=lambda count: count > 0,
                    step=3,
                    timeout=300)
            except polling2.TimeoutException:
                self._logger.error("Timed out waiting for participants to join")
                self._is_destroyed = True
                return
            self._logger.info(
                "Session detected at least one participant - joining")
        call_client = CallClient(event_handler=self)
        self._call_client = call_client
        room = self._room
        self._logger.info("Joining Daily room %s", room.url)
        call_client.join(
            room.url,
            room.token,
            completion=self.on_joined_meeting)

    def get_participant_count(self) -> int:
        """Gets the current number of participants in the room
        using Daily's REST API"""

        if self._is_headless:
            raise HeadlessNotPermittedException("get participant count through Daily's REST API")
        headers = self._daily_auth_headers

        url = f'{self._daily_api_url}/rooms/{self._room.name}/presence'
        res = requests.get(url, headers=headers)

        if not res.ok:
            handle_daily_error_res(res, "Failed to get participant count")

        presence = res.json()
        return presence['total_count']

    def get_room(self, room_url: str) -> Room:
        """Retrieves a Daily room on the configured domain."""        
        if self._is_headless:
            raise HeadlessNotPermittedException("retrieve a Daily room")
    
        if not room_url:
            raise Exception("Room URL must be provided to retrieve a room")
        room_name = os.path.basename(room_url)
        url = f'{self._daily_api_url}/rooms/{room_name}'
        headers = self._daily_auth_headers

        res = requests.get(url, headers=headers)

        if not res.ok:
            handle_daily_error_res(res, "Failed to get room")

        room_data = res.json()

        # We have the URL and name above, but use the values returned
        # by the API itself since that's the source of truth.
        url = room_data['url']
        name = room_data['name']

        # Using gets with exp as default value to avoid KeyError,
        # since this value  might not be set for a room.
        exp = room_data.get("config").get("exp")
        token = self.get_meeting_token(name, exp)
        return Room(url, token, name)

    def create_room(self, room_duration_mins: int = None) -> Room:
        """Creates a Daily room on the configured domain."""

        if self._is_headless:
            raise HeadlessNotPermittedException("create a Daily room")
        headers = self._daily_auth_headers

        duration = room_duration_mins
        # Fall back on configured default if needed
        if not duration:
            duration = self._config.room_duration_mins

        exp = time.time() + duration * 60

        url = f'{self._daily_api_url}/rooms'

        res = requests.post(url,
                            headers=headers,
                            json={
                                'properties': {
                                    'eject_at_room_exp': True,
                                    'enable_chat': True,
                                    'enable_emoji_reactions': True,
                                    'enable_prejoin_ui': False,
                                    'exp': exp
                                }
                            })

        if not res.ok:
            handle_daily_error_res(res, "Failed to create room")

        room_data = res.json()
        url = room_data['url']
        name = room_data['name']
        token = self.get_meeting_token(name, exp)
        return Room(url, token, name)

    def get_meeting_token(self, room_name: str, token_expiry: float = None):
        """Retrieves an owner meeting token for the given Daily room."""

        if self._is_headless:
            raise HeadlessNotPermittedException("get a Daily meeting token")
        
        # 1-hour default expiry
        if not token_expiry:
            token_expiry = time.time() + 3600

        url = f'{self._daily_api_url}/meeting-tokens'
        headers = self._daily_auth_headers

        res = requests.post(url,
                            headers=headers,
                            json={'properties':
                                  {'room_name': room_name,
                                   'is_owner': True,
                                   'exp': token_expiry,
                                   }})

        if not res.ok:
            handle_daily_error_res(res, "Failed to get meeting token")

        meeting_token = res.json()['token']
        return meeting_token
    
    async def generate_clean_transcript(self) -> bool:
        """Generates a clean transcript from the raw context."""
        if self._is_destroyed:
            return True
        try:
            await self._assistant.cleanup_transcript()
        except Exception as e:
            self._logger.warning(
                "Failed to generate clean transcript: %s", e)
        return False

    def get_clean_transcript(self) -> str:
        return self._assistant.get_clean_transcript()
    
    async def query_assistant(self, custom_query: str = None) -> Future[str]:
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
            answer = asyncio.run(self.query_assistant(query))
        elif task == "transcript":
            answer = self.get_clean_transcript()
            
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
        threading.Thread(target=self.start_transcript_polling, daemon=True).start()

        if not self._is_headless:
            self._logger.info("Starting transcription %s", self._room.url)
            self._call_client.start_transcription()
            self.set_session_data(self._room.name, self._id)
        
        self._call_client.set_user_name("Daily AI Assistant")

        # Check whether the bot is actually the only one in the call, in which case
        # the shutdown timer should start. The shutdown will be cancelled if
        # daily-python detects someone new joining.
        self.maybe_start_shutdown()

    def on_error(self, message):
        """Callback invoked when an error is received."""
        self._logger.error("Received meeting error: %s", message)


    async def poll_async_func(self, async_func, interval):
        done = False
        while not done:
            result = await async_func()
            if self._is_destroyed:
                done = True
            else:
                await asyncio.sleep(interval)

    def start_transcript_polling(self):
        """Starts an asyncio event loop and schedules generate_clean_transcript to run every 30 seconds."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.poll_async_func(self.generate_clean_transcript, 30))

    async def poll_async_func(self, async_func, interval):
        """Runs an async function at regular intervals until the session is destroyed."""
        while not self._is_destroyed:
            await async_func()
            await asyncio.sleep(interval)

    # TODO: (Liza) Uncomment this when transcription events are properly invoked
    # if the transcription is starte before the bot joins. 
    #def on_transcription_started(self, status):
    #    self._logger.info("Transcription started: %s", status)
    #    threading.Thread(target=self.start_transcript_polling, daemon=True).start()

    def on_transcription_stopped(self, stopped_by: str, stopped_by_error: str):
        self._logger.info("Transcription stopped: %s (%s)", stopped_by, stopped_by_error)

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

    def set_session_data(self, room_name: str, bot_id: str):
        """Sets the bot session ID in the Daily room's session data."""

        if self._is_headless:
            raise HeadlessNotPermittedException("set session data")
        
        self._logger.info("Setting bot ID in session data: %s (%s)", room_name, bot_id)
        url = f'{self._daily_api_url}/rooms/{room_name}/set-session-data'
        headers = self._daily_auth_headers
        session_data = {
            "data": {
                "bot_session_id": bot_id
            },
            "mergeStrategy": "shallow-merge"
        }
        body = json.dumps(session_data)

        res = requests.post(url, headers=headers, data=body)
        if not res.ok:
            handle_daily_error_res(
                res, "Failed to set bot ID in session data")

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

    def set_daily_request_data(self, room_url: str):
        """Sets the Daily auth headers for this session, using either the default
        API key or a domain-specific one if provided."""

        # Default to primary API key
        api_key = self._config.default_daily_api_key
        api_url = self._config.default_daily_api_url

        # If a room URL is provided, try to parse the subdomain
        # and use a domain-specific API key
        if room_url:
            try:
                parsed_url = urlparse(room_url)
            except Exception as e:
                raise Exception(
                    f"Failed to parse room URL {room_url}") from e
            subdomain = parsed_url.hostname.split('.')[0]
            domain_api_data = self._config.get_daily_api_data(subdomain)
            if domain_api_data:
                api_key = domain_api_data.key
                api_url = domain_api_data.get_api_url()

        headers = {'Authorization': f'Bearer {api_key}'}
        self._daily_auth_headers = headers
        self._daily_api_url = api_url

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

    session = Session(config, None, config.daily_room_url)
    atexit.register(bot_cleanup, session)
    task = threading.Thread(target=session.start_session)
    task.start()
    while not session.is_destroyed:
        time.sleep(1)

if __name__ == "__main__":
    main()