import requests

class HeadlessNotPermittedException(Exception):
    def __init__(self, action: str):
        super().__init__(
            f"Cannot {action} in headless mode.")



class SessionNotFoundException(Exception):
    def __init__(self, session_id: str):
        super().__init__(
            f"Requested session ID {session_id} not found in active sessions")


class DailyPermissionException(Exception):
    def __init__(self, msg: str):
        m = "Daily API denied permission to perform this action."
        super().__init__(f"{m}: {msg}")


def handle_daily_error_res(res: requests.Response, err_msg: str = None):
    """Raises relevant exception to a Daily API error response."""
    code = res.status_code
    if code == 401:
        raise DailyPermissionException(err_msg)
    raise Exception(
        f'{err_msg}. Response code: {code}, body: {res.json()}'
    )
