"""Module which keeps track of all ongoing sessions and provides
querying functionality to HTTP requesters."""
import threading

from daily import Daily
from server.config import Config
from server.call.session import Session


class Operator():
    _config: Config
    _sessions: list[Session] = []
    _is_shutting_down: bool

    def __init__(self, config: Config):
        self._config = config
        self._is_shutting_down = False
        Daily.init()

    def create_session(self, room_duration_mins: int = None) -> str:
        """Creates a session, which includes creating a Daily room."""
        session = Session(self._config, self.clear_session, room_duration_mins)
        self._sessions.append(session)
        print("CREATED SESSION. ALL THREADS:", threading.active_count())
        for thread in threading.enumerate():
            print(thread.name, thread.is_alive())

        return session.room_url

    def query_assistant(self, room_url: str, custom_query=None) -> str:
        """Queries the assistant for the provided room URL."""
        for s in self._sessions:
            if s.room_url == room_url:
                return s.query_assistant(custom_query=custom_query)
        raise Exception(
            f"Requested room URL {room_url} not found in active sessions")

    def clear_session(self, id: str, room_url: str):
        """Removes the session from the list of active sessions."""
        for s in self._sessions:
            if s.id == id and s.room_url == room_url:
                self._sessions.remove(s)
                break

        # If the operator is shutting down and this was the last
        # session removed, deinitialize Daily
        if self._is_shutting_down and len(self._sessions) is None:
            Daily.deinit()

        print("KILLED SESSION. ALL THREADS:", threading.active_count())
        for thread in threading.enumerate():
            print(thread.name, thread.is_alive(), thread.ident)

    def shutdown(self):
        """Shuts down all active sessions and deinitializes Daily."""

        self._is_shutting_down = True
        for idx, session in self._sessions:
            session.shutdown()

        if len(self._sessions) == 0:
            Daily.deinit()

