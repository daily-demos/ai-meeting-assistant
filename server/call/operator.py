"""Module which keeps track of all ongoing sessions and provides
querying functionality to HTTP requesters."""
import threading

import polling2
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

        t = threading.Thread(target=self.cleanup)
        t.start()

    def create_session(self, room_duration_mins: int = None) -> str:
        """Creates a session, which includes creating a Daily room."""
        session = Session(self._config, room_duration_mins)
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

    def shutdown(self):
        """Shuts down all active sessions"""
        for idx, session in self._sessions:
            session.shutdown()

    def cleanup(self):
        """Periodically checks for destroyed sessions and removes them from the session list"""
        polling2.poll(
            target=self.remove_destroyed_sessions,
            check_success=lambda done: done is True,
            poll_forever=True,
            step=5)

    def remove_destroyed_sessions(self) -> bool:
        """Removes destroyed sessions from the session list and deinitializes Daily
        if all sessions are gone and the operator is shutting down."""

        if self._is_shutting_down and len(self._sessions) == 0:
            Daily.deinit()
            return True

        # Check each session to see if it's been destroyed.
        for session in self._sessions:
            if session.is_destroyed:
                print(
                    "REMOVED SESSION. ALL THREADS:",
                    threading.active_count())
                for thread in threading.enumerate():
                    print(thread.name, thread.is_alive(), thread.ident)
                self._sessions.remove(session)
        return False
