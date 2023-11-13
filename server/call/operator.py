import threading

from daily import Daily
from server.config import Config
from server.call.session import Session


class Operator():
    _config: Config
    _sessions: list[Session] = []

    def __init__(self, config: Config):
        self._config = config
        Daily.init()
        print("active threads on operator init:", threading.active_count())

    def create_session(self) -> str:
        session = Session(self._config, self.clear_session)
        self._sessions.append(session)
        return session.room_url

    def generate_summary(self, room_url: str) -> str:
        for s in self._sessions:
            if s.room_url == room_url:
                return s.generate_summary()
        raise Exception(f"Requested room URL {room_url} not found in active sessions")
    def clear_session(self, id: str, room_url: str):
        print("previous session count:", len(self._sessions), "active threads:", threading.active_count())
        for s in self._sessions:
            if s.id == id and s.room_url == room_url:
                self._sessions.remove(s)
                break
        print("current session count:", len(self._sessions), "active threads:", threading.active_count())

    def shutdown(self):
        print("Shutting down operator. Thread count before:", threading.active_count())
        for session in self._sessions:
            session.shutdown()
        Daily.deinit()
        print("Shutting down operator. Thread count after:", threading.active_count())
