"""Module which keeps track of all ongoing sessions and provides
querying functionality to HTTP requesters."""
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

    def create_session(self, room_duration_mins: int = None) -> str:
        """Creates a session, which includes creating a Daily room."""
        session = Session(self._config, self.clear_session, room_duration_mins)
        self._sessions.append(session)
        return session.room_url

    def query_assistant(self, room_url: str) -> str:
        """Queries the assistant for the provided room URL."""
        for s in self._sessions:
            if s.room_url == room_url:
                return s.query_assistant()
        raise Exception(
            f"Requested room URL {room_url} not found in active sessions")

    def clear_session(self, id: str, room_url: str):
        """Removes the session from the list of active sessions."""
        print("previous session count:", len(self._sessions),
              "active threads:", threading.active_count())
        for s in self._sessions:
            if s.id == id and s.room_url == room_url:
                self._sessions.remove(s)
                break
        print("current session count:", len(self._sessions),
              "active threads:", threading.active_count())

    def shutdown(self):
        """Shuts down all active sessions and deinitializes Daily."""
        print(
            "Shutting down operator. Thread count before:",
            threading.active_count())
        for session in self._sessions:
            session.shutdown()
        # TODO: Should make sure this waits until all bots have left.
        Daily.deinit()
        print(
            "Shutting down operator. Thread count after:",
            threading.active_count())
