class SessionNotFoundException(Exception):
    def __init__(self, session_id: str):
        # Call the base class constructor with the parameters it needs
        super().__init__(
            f"Requested session ID {session_id} not found in active sessions")
