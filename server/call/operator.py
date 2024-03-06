"""Module which keeps track of all ongoing sessions and provides
querying functionality to HTTP requesters."""
import threading

import polling2
from server.config import BotConfig
from server.call.session import Session


class Operator():
    _sessions: list[Session]
    _is_shutting_down: bool
    _lock: threading.Lock

    def __init__(self):
        self._is_shutting_down = False
        self._lock = threading.Lock()
        self._sessions = []

        self._thread = threading.Thread(target=self.cleanup)
        self._thread.start()

    def create_session(self, bot_config: BotConfig) -> Session:
        """Creates a session, which includes creating a Daily room."""

        # If an active session for given room URL already exists,
        # don't create a new one
        with self._lock:
            for s in self._sessions:
                if s.room_url == bot_config.daily_room_url and not s.is_destroyed:
                    print("found session:", s.room_url)
                    return None

        # Create a new session
        session = Session(bot_config)
        with self._lock:
            self._sessions.append(session)
        return session

    def shutdown(self):
        """Shuts down all active sessions"""
        self._is_shutting_down = True
        with self._lock:
            for session in self._sessions:
                session.shutdown()
        self._thread.join()

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
                return True

            # Check each session to see if it's been destroyed.
            for session in self._sessions:
                if session.is_destroyed:
                    print("Removing destroyed session:", session.room_url)
                    self._sessions.remove(session)
            return False
