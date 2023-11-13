"""Module providing primary input and output configuration paths."""
import os

INDEX_DIR_ENV = 'INDEX_DIR'
TRANSCRIPTS_DIR_ENV = 'TRANSCRIPTS_DIR'
UPLOAD_DIR_ENV = 'UPLOAD_DIR'
RECORDINGS_DIR_ENV = 'RECORDINGS_DIR'


class Config:
    """Class representing third-party API keys and other settings."""
    _daily_api_key: str = None
    _daily_api_url: str = None
    _openai_api_key: str = None
    _room_duration_mins: int = None
    _transcript_dir_path: str = None

    def __init__(self, daily_api_key=os.getenv("DAILY_API_KEY"),
                 daily_api_url=os.getenv("DAILY_API_URL"),
                 openai_api_key=os.getenv("OPENAI_API_KEY"),
                 room_duration_mins=os.getenv("ROOM_DURATION_MINUTES"),
                 transcript_dir_path=None,
                 ):
        self._daily_api_key = daily_api_key
        self._openai_api_key = openai_api_key

        if not daily_api_url:
            daily_api_url = 'https://api.daily.co/v1'
        self._daily_api_url = daily_api_url

        if not room_duration_mins:
            room_duration_mins = 15
        self._room_duration_mins = int(room_duration_mins)

        if not transcript_dir_path:
            self._transcript_dir_path = os.path.abspath(
                deduce_dir_name("INDEX_DIR"))

    def ensure_dirs(self):
        """Creates required file directories if they do not already exist."""
        ensure_dir(self._transcript_dir_path)

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
    def room_duration_mins(self) -> str:
        return self._room_duration_mins

    @property
    def transcript_dir_path(self) -> str:
        """Returns transcript directory path."""
        return self._transcript_dir_path

    def get_transcript_file_path(self, file_name: str) -> str:
        """Returns the destination file path of the transcript file"""
        return os.path.join(self.transcript_dir_path, f"{file_name}.txt")


def ensure_dir(dir_path: str):
    """Creates directory at the given path if it does not already exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def deduce_dir_name(env_name: str):
    d = os.getenv(env_name)
    if not d:
        d = env_name
    return d
