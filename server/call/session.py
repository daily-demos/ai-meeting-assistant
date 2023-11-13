import asyncio
import dataclasses
import json
import threading
import time
from asyncio import Future
from typing import Callable, Protocol

import polling2
import requests
from daily import Daily, EventHandler, CallClient
from server.config import Config
from server.llm.openai_summarizer import OpenAISummarizer
from server.llm.summarizer import Summarizer


@dataclasses.dataclass
class Room:
    url: str = None
    token: str = None
    name: str = None


@dataclasses.dataclass
class Participant:
    session_id: str = None
    user_name: str = None

class OnShutdown(Protocol):
    def __call__(self, id: str, room_url: str) -> None: ...


class Session(EventHandler):
    _config: Config
    _daily: Daily
    _task: Future
    _room: Room
    _id: str
    _on_shutdown: Callable[[str, str], None]
    _summarizer: Summarizer

    def __init__(self, config: Config, on_shutdown: OnShutdown):
        print("Initializing session")
        super().__init__()
        self._config = config
        self._on_shutdown = on_shutdown
        self._summarizer = OpenAISummarizer(config.openai_api_key)
        self.init()

    @property
    def room_url(self) -> str:
        return self._room.url

    @property
    def id(self) -> str:
        return self._id

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def init(self) -> str:
        room = self.create_room()
        self._room = room
        loop = asyncio.get_event_loop()
        self._call_client = CallClient(event_handler=self)
        print("pre-loop thread count", threading.active_count())
        task = loop.run_in_executor(None, self.start_session)
        print("post-loop thread count", threading.active_count())
        self._task = task
        return room.url

    def start_session(self):
        # Start polling for participant count, only move on
        # when there is at least once participant in the room.
        print("Session starting polling for participation")
        polling2.poll(target=self.get_participant_count, check_success=lambda count: count > 0, step=0.5, timeout=300)
        print("Session detected at least one participant - joining")
        # There is at least one participant in the room - join with the bot
        call_client = CallClient(event_handler=self)
        print("Session created call client")
        self._call_client = call_client
        room = self._room
        print("Session joining room")
        call_client.join(room.url, room.token, completion=self.on_joined_meeting)
        print("Joined call? Returning")

    def get_participant_count(self) -> int:
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

    def create_room(self) -> Room:
        api_key = self._config.daily_api_key
        api_url = self._config.daily_api_url

        url = f'{api_url}/rooms'
        headers = {'Authorization': f'Bearer {api_key}'}

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

    def generate_summary(self):
        return self._summarizer.summarize()

    def on_joined_meeting(self, join_data, error):
        print("Session joined meeting:", join_data, error)
        if error:
            raise Exception("failed to join meeting", error)
        self._id = join_data["participants"]["local"]["id"]
        self._call_client.start_transcription()
        self._call_client.set_user_name("Daily AI Assistant")
        self.set_session_data(self._room.name, self._id)

    def on_transcription_message(self, message):
        print("transcription message", message)
        user_name = message["user_name"]
        text = message["text"]
        self._summarizer.register_new_context(f"{user_name} said '{text}'")


    def on_app_message(self,
                       message,
                       sender):
        print("app-message")

    def on_participant_left(self,
                            participant,
                            reason):

        count = self._call_client.participant_counts()['present']
        print("Session handling participant left. Participant count: ", count)
        if count == 1:
            self.shutdown()

    def set_session_data(self, room_name: str, bot_id: str):
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
        print(f"Session {self._id} shutting down. Active threads:", threading.active_count())
        self._call_client.leave()
        print(f"Session {self._id} invoked leave")
        if self._on_shutdown:
            print(f"Session {self._id} invoking shutdown callback, active threads:", threading.active_count())
            self._on_shutdown(self._id, self._room.url)
