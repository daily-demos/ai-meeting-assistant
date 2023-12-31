"""Module which keeps track of all ongoing sessions and provides
querying functionality to HTTP requesters."""
import threading

import polling2
from daily import Daily
from server.call.errors import SessionNotFoundException
from server.config import Config
from server.call.session import Session


class Operator():
    _config: Config
    _sessions: list[Session]
    _is_shutting_down: bool
    _lock: threading.Lock

    def __init__(self, config: Config):
        self._config = config
        self._is_shutting_down = False
        self._lock = threading.Lock()
        self._sessions = []
        Daily.init()

        t = threading.Thread(target=self.cleanup)
        t.start()

    def create_session(self, room_duration_mins: int = None,
                       room_url: str = None) -> str:
        """Creates a session, which includes creating a Daily room."""

        # If an active session for given room URL already exists,
        # don't create a new one
        if room_url:
            with self._lock:
                for s in self._sessions:
                    if s.room_url == room_url and not s.is_destroyed:
                        print("found session:", s.room_url)
                        return s.room_url

        # Create a new session
        session = Session(self._config, room_duration_mins, room_url)
        with self._lock:
            self._sessions.append(session)
        return session.room_url

    async def query_assistant(self, room_url: str, custom_query=None) -> str:
        """Queries the assistant for the provided room URL."""
        self._lock.acquire()
        for s in self._sessions:
            if s.room_url == room_url and not s.is_destroyed:
                self._lock.release()
                return await s.query_assistant(custom_query=custom_query)

        self._lock.release()
        raise SessionNotFoundException(room_url)

    def shutdown(self):
        """Shuts down all active sessions"""
        with self._lock:
            for session in self._sessions:
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
        with self._lock:
            if self._is_shutting_down and len(self._sessions) == 0:
                Daily.deinit()
                return True

            # Check each session to see if it's been destroyed.
            for session in self._sessions:
                if session.is_destroyed:
                    print("Removing destroyed session:", session.room_url)
                    self._sessions.remove(session)
            return False
