"""Module providing primary configuration variables, such as
third-party API keys."""
from __future__ import annotations

import os


class DailyAPIData:
    """Class representing a Daily API key and its associated
    domain and environment."""
    _domain: str
    _env: str
    _key: str

    def __init__(self, domain: str, env: str, key: str):
        self._domain = domain
        self._env = env
        self._key = key

    def get_api_url(self) -> str:
        """Returns the API URL for this environment."""
        if not self._env:
            # If env was not provided, assume production
            return f"https://api.daily.co/v1/"
        return f"https://api.{self._env}.daily.co/v1/"

    @property
    def key(self) -> str:
        return self._key


class Config:
    """Class representing third-party API keys and other settings."""
    _default_daily_api_key: str = None
    _default_daily_api_url: str = None
    _openai_api_key: str = None
    _openai_model_name: str = None
    _room_duration_mins: int = None
    _log_dir_path: str = None
    _daily_api_keys: dict[str, DailyAPIData] = None

    def __init__(self, daily_api_key=os.getenv("DAILY_API_KEY"),
                 daily_api_url=os.getenv("DAILY_API_URL"),
                 openai_api_key=os.getenv("OPENAI_API_KEY"),
                 openai_model_name=os.getenv("OPENAI_MODEL_NAME"),
                 room_duration_mins=os.getenv("ROOM_DURATION_MINUTES"),
                 log_dir_name: str = None
                 ):
        self._default_daily_api_key = daily_api_key
        self._openai_api_key = openai_api_key
        self._openai_model_name = openai_model_name

        if not daily_api_url:
            daily_api_url = 'https://api.daily.co/v1'
        self._default_daily_api_url = daily_api_url

        if not room_duration_mins:
            room_duration_mins = 15
        self._room_duration_mins = int(room_duration_mins)

        if log_dir_name:
            self._log_dir_path = os.path.abspath(log_dir_name)

    def load_daily_api_keys(self):
        """Loads all Daily API keys from environment variables"""""
        self._daily_api_keys = {}
        items = os.environ.items()
        key_prefix = "DAILY_API_KEY_"
        for key, value in items:
            if key.startswith(key_prefix):
                domain_and_env = key.split(key_prefix)[1].lower()
                parts = domain_and_env.split("_")

                domain_name: str = parts[0]
                env_name: str = None

                # If there are two parts, the second is the environment name
                if len(parts) == 2:
                    env_name = parts[1]
                api_key = DailyAPIData(domain_name, env_name, value)
                self._daily_api_keys[domain_name] = api_key

    def get_daily_api_data(self, domain_name: str) -> DailyAPIData | None:
        """Returns the Daily API data for the given domain name if it exists"""
        if self._daily_api_keys is None:
            self.load_daily_api_keys()
        dn = domain_name.lower()
        return self._daily_api_keys.get(dn)

    @property
    def default_daily_api_key(self) -> str:
        """Returns the configured Daily API key"""
        return self._default_daily_api_key

    @property
    def default_daily_api_url(self) -> str:
        """Returns the configured Daily API URL"""
        return self._default_daily_api_url

    @property
    def openai_api_key(self) -> str:
        """Returns the configured OpenAI API key"""
        return self._openai_api_key

    @property
    def openai_model_name(self) -> str:
        """Returns the configured OpenAI model name"""
        return self._openai_model_name

    @property
    def room_duration_mins(self) -> int:
        """Returns how long each room should be alive for, in minutes"""
        return self._room_duration_mins

    @property
    def log_dir_path(self) -> str | None:
        """Returns the configured log directory"""
        return self._log_dir_path

    def get_log_file_path(self, room_name: str) -> str | None:
        """Returns the log file for the given room name"""
        if not self._log_dir_path:
            return None
        return os.path.join(self.log_dir_path, f"{room_name}.log")

    def ensure_dirs(self):
        """Creates required file directories if they do not already exist."""
        if self._log_dir_path:
            ensure_dir(self._log_dir_path)


def ensure_dir(dir_path: str):
    """Creates directory at the given path if it does not already exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
