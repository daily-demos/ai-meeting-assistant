"""Module providing primary configuration variables, such as
third-party API keys."""
import os


class Config:
    """Class representing third-party API keys and other settings."""
    _daily_api_key: str = None
    _daily_api_url: str = None
    _openai_api_key: str = None
    _room_duration_mins: int = None

    def __init__(self, daily_api_key=os.getenv("DAILY_API_KEY"),
                 daily_api_url=os.getenv("DAILY_API_URL"),
                 openai_api_key=os.getenv("OPENAI_API_KEY"),
                 room_duration_mins=os.getenv("ROOM_DURATION_MINUTES"),
                 ):
        self._daily_api_key = daily_api_key
        self._openai_api_key = openai_api_key

        if not daily_api_url:
            daily_api_url = 'https://api.daily.co/v1'
        self._daily_api_url = daily_api_url

        if not room_duration_mins:
            room_duration_mins = 15
        self._room_duration_mins = int(room_duration_mins)

    @property
    def daily_api_key(self) -> str:
        return self._daily_api_key

    @property
    def daily_api_url(self) -> str:
        return self._daily_api_url

    @property
    def openai_api_key(self) -> str:
        return self._openai_api_key

    @property
    def room_duration_mins(self) -> int:
        return self._room_duration_mins
