"""Class representing a single meeting happening within a Daily room.
This is responsible for all Daily operations."""
from __future__ import annotations

import asyncio
import dataclasses
import json
import threading
import time
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Protocol

import polling2
import requests
from daily import Daily, EventHandler, CallClient
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


class OnShutdown(Protocol):
    """Class that defines the signature of a callback invoked when a session is destroyed"""

    def __call__(self, id: str, room_url: str) -> None: ...


class Session(EventHandler):
    """Class representing a single meeting happening within a Daily room."""
    _call_client: CallClient
    _config: Config
    _daily: Daily
    _executor: ThreadPoolExecutor
    _room: Room
    _id: str
    _on_shutdown: Callable[[str, str], None]
    _assistant: Assistant

    def __init__(self, config: Config, on_shutdown: OnShutdown,
                 room_duration_mins: int = None):
        print("Initializing session")
        super().__init__()
        self._config = config
        self._on_shutdown = on_shutdown
        self._assistant = OpenAIAssistant(config.openai_api_key)
        self._executor = ThreadPoolExecutor(max_workers=5)
        self.init(room_duration_mins)

    @property
    def room_url(self) -> str:
        return self._room.url

    @property
    def id(self) -> str:
        return self._id

    def init(self, room_duration_mins: int = None) -> str:
        """Creates a Daily room and uses it to start a session"""
        room = self.create_room(room_duration_mins)
        self._room = room
        loop = asyncio.get_event_loop()
        self._call_client = CallClient(event_handler=self)
        print("pre-loop thread count", threading.active_count())
        task = loop.run_in_executor(self._executor, self.start_session)
        print("post-loop thread count", threading.active_count())
        self._task = task
        return room.url

    def start_session(self):
        """Waits for at least one person to join the associated Daily room,
        then joins, starts transcription, and begins registering context."""
        print("Session starting polling for participation")
        polling2.poll(
            target=self.get_participant_count,
            check_success=lambda count: count > 0,
            step=0.5,
            timeout=300)
        print("Session detected at least one participant - joining")
        # There is at least one participant in the room - join with the bot
        call_client = CallClient(event_handler=self)
        print("Session created call client")
        self._call_client = call_client
        room = self._room
        print("Session joining room")
        call_client.join(
            room.url,
            room.token,
            completion=self.on_joined_meeting)
        print("Joined call? Returning")

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
        answer = self._assistant.query(custom_query)

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

    def on_app_message_sent(self, error: str = None):
        """Callback invoked when an app message is sent."""
        if error:
            print("Failed to send message", error)

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
        print("transcription message", message)
        user_name = message["user_name"]
        text = message["text"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        metadata = [user_name, 'voice', timestamp]
        self._assistant.register_new_context(text, metadata)

    def on_app_message(self,
                       message: str,
                       sender: str):
        """Callback invoked when a Daily app message is received."""
        msg = json.loads(message)
        kind = msg["kind"]
        if not kind or kind != "assist":
            return

        query = msg["query"]
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            self._executor,
            self.query_assistant,
            sender,
            query)

    def on_participant_left(self,
                            participant,
                            reason):
        """Callback invoked when a participant leaves the Daily room."""
        count = self._call_client.participant_counts()['present']
        print("Session handling participant left. Participant count: ", count)
        if count == 1:
            # Should probably wait a few minutes here in case someone rejoins
            self.shutdown()

    def set_session_data(self, room_name: str, bot_id: str):
        """Sets the bot session ID in the Daily room's session data."""
        print("Session setting bot id in session data: ", bot_id)
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
        print("Session body:", body)

        res = requests.post(url, headers=headers, data=body)
        if not res.ok:
            raise Exception(
                f'Failed to set bot ID in session data. Response code: {res.status_code}, body: {res.json()}'
            )

    def shutdown(self):
        """Shuts down the session, leaving the Daily room, invoking the shutdown callback,
        and cancelling any pending Futures"""
        print(
            f"Session {self._id} shutting down. Active threads:",
            threading.active_count())
        self._call_client.leave()
        print(f"Session {self._id} invoked leave")
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self._on_shutdown:
            print(
                f"Session {self._id} invoking shutdown callback, active threads:",
                threading.active_count())
            self._on_shutdown(self._id, self._room.url)
