"""Class representing a single meeting happening within a Daily room.
This is responsible for all Daily operations."""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import sys
import threading
import time
from asyncio import Future
from datetime import datetime
from logging import Logger

import polling2
import requests
from daily import EventHandler, CallClient

from server.config import Config
from server.llm.openai_assistant import OpenAIAssistant
from server.llm.assistant import Assistant


@dataclasses.dataclass
class Room:
    """Class representing a Daily video call room"""
    url: str = None
    token: str = None
    name: str = None


@dataclasses.dataclass
class Participant:
    """Class representing a Daily participant"""
    session_id: str = None
    user_name: str = None


@dataclasses.dataclass
class Summary:
    """Class representing a Daily meeting summary"""
    content: str
    retrieved_at: time.time()


class Session(EventHandler):
    """Class representing a single meeting happening within a Daily room."""

    _config: Config
    _assistant: Assistant
    _summary: Summary | None

    # Daily-related properties
    _id: str
    _call_client: CallClient
    _room: Room

    # Shutdown-related properties
    _is_destroyed: bool = False
    _shutdown_timer: threading.Timer | None = None

    def __init__(self, config: Config,
                 room_duration_mins: int = None):
        super().__init__()
        self._config = config
        self._summary = None
        self.init(room_duration_mins)
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

    def init(self, room_duration_mins: int = None) -> str:
        """Creates a Daily room and uses it to start a session"""
        room = self.create_room(room_duration_mins)
        self._room = room
        task = threading.Thread(target=self.start_session)
        task.start()
        return room.url

    def start_session(self):
        """Waits for at least one person to join the associated Daily room,
        then joins, starts transcription, and begins registering context."""
        try:
            polling2.poll(
                target=self.get_participant_count,
                check_success=lambda count: count > 0,
                step=3,
                timeout=300)
        except polling2.TimeoutException as e:
            self._logger.error("Timed out waiting for participants to join")
            return
        self._logger.info(
            "Session detected at least one participant - joining")
        call_client = CallClient(event_handler=self)
        self._call_client = call_client
        room = self._room
        call_client.join(
            room.url,
            room.token,
            completion=self.on_joined_meeting)

    def get_participant_count(self) -> int:
        """Gets the current number of participants in the room
        using Daily's REST API"""
        api_key = self._config.daily_api_key
        api_url = self._config.daily_api_url

        url = f'{api_url}/rooms/{self._room.name}/presence'
        headers = {'Authorization': f'Bearer {api_key}'}

        res = requests.get(url, headers=headers)

        if not res.ok:
            raise Exception(
                f'Failed to get room presence {res.status_code}'
            )

        presence = res.json()
        return presence['total_count']

    def create_room(self, room_duration_mins: int = None) -> Room:
        """Creates a Daily room on the configured domain."""
        api_key = self._config.daily_api_key
        api_url = self._config.daily_api_url

        url = f'{api_url}/rooms'
        headers = {'Authorization': f'Bearer {api_key}'}

        duration = room_duration_mins
        # Fall back on configured default if needed
        if not duration:
            duration = self._config.room_duration_mins

        exp = time.time() + duration * 60

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
            raise Exception(
                f'Failed to create room {res.status_code}'
            )

        room_data = res.json()
        url = room_data['url']
        name = room_data['name']
        token = self.get_meeting_token(name, exp)
        return Room(url, token, name)

    def get_meeting_token(self, room_name: str, token_expiry: float = None):
        """Retrieves an owner meeting token for the given Daily room."""
        api_url = self._config.daily_api_url
        api_key = self._config.daily_api_key

        # 1-hour default expiry
        if not token_expiry:
            token_expiry = time.time() + 3600

        url = f'{api_url}/meeting-tokens'
        headers = {'Authorization': f'Bearer {api_key}'}

        res = requests.post(url,
                            headers=headers,
                            json={'properties': {'room_name': room_name, 'is_owner': True, 'exp': token_expiry}})

        if not res.ok:
            raise Exception(
                f'Failed to create meeting token {res.status_code}'
            )

        meeting_token = res.json()['token']
        return meeting_token

    def query_assistant(self, recipient_session_id: str = None,
                        custom_query: str = None) -> [str | Future]:
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
            answer = self._assistant.query(custom_query)

            # If there was no custom query provided, save this as cached
            # summary.
            if want_cached_summary:
                self._logger.info("Saving general summary")
                self._summary = Summary(
                    content=answer, retrieved_at=time.time())

        # If no recipient is provided, this was probably an HTTP request through the operator
        # Just return the answer string in that case.
        if not recipient_session_id:
            return answer

        # If a recipient is provided, ths was likely a request through Daily's app message events.
        # Send the answer as an event as well.
        self._call_client.send_app_message({
            "kind": "assist",
            "data": answer
        }, participant=recipient_session_id, completion=self.on_app_message_sent)

    def on_app_message_sent(self, _, error: str = None):
        """Callback invoked when an app message is sent."""
        if error:
            self._logger.error("Failed to send app message: %s", error)

    def on_left_meeting(self, _, error: str = None):
        if error:
            self._logger.error(
                "Encountered error while leaving meeting: %s", error)
        self._is_destroyed = True

    def on_joined_meeting(self, join_data, error):
        """Callback invoked when the bot has joined the Daily room."""
        if error:
            raise Exception("failed to join meeting", error)
        self._id = join_data["participants"]["local"]["id"]
        self._call_client.start_transcription()
        self._call_client.set_user_name("Daily AI Assistant")
        self.set_session_data(self._room.name, self._id)

    def on_transcription_message(self, message):
        """Callback invoked when a transcription message is received."""
        user_name = message["user_name"]
        text = message["text"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        metadata = [user_name, 'voice', timestamp]
        self._assistant.register_new_context(text, metadata)

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
        # Should probably be limited only to owners
        if bool(data.get("broadcast")):
            recipient = "*"
        self.query_assistant(recipient, query)

    def on_participant_joined(self, participant):
        # As soon as someone joins, stop shutdown process
        if self._shutdown_timer:
            self._logger.info("Participant joined - cancelling shutdown.")
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

    def on_participant_left(self,
                            participant,
                            reason):
        """Callback invoked when a participant leaves the Daily room."""
        count = self._call_client.participant_counts()['present']
        self._logger.info(
            "Session handling participant left. Participant count: %s", count)
        if count == 1:
            self._shutdown_timer = threading.Timer(60.0, self.shutdown)
            self._shutdown_timer.start()

    def set_session_data(self, room_name: str, bot_id: str):
        """Sets the bot session ID in the Daily room's session data."""
        api_key = self._config.daily_api_key
        api_url = self._config.daily_api_url

        url = f'{api_url}/rooms/{room_name}/set-session-data'
        headers = {'Authorization': f'Bearer {api_key}'}
        session_data = {
            "data": {
                "bot_session_id": bot_id
            },
            "mergeStrategy": "shallow-merge"
        }
        body = json.dumps(session_data)

        res = requests.post(url, headers=headers, data=body)
        if not res.ok:
            raise Exception(
                f'Failed to set bot ID in session data. Response code: {res.status_code}, body: {res.json()}'
            )

    def shutdown(self):
        """Shuts down the session, leaving the Daily room, invoking the shutdown callback,
        and cancelling any pending Futures"""
        self._logger.info(
            f"Session {self._id} shutting down. Active threads: %s",
            threading.active_count())

        self._call_client.leave(self.on_left_meeting)

    def create_logger(self, name) -> Logger:
        # Create a logger
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
