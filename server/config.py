"""Module providing primary configuration variables, such as
third-party API keys."""
from __future__ import annotations
import argparse

import os
from os.path import join, dirname, abspath

from dotenv import load_dotenv


class BotConfig:
    _openai_api_key: str = None
    _openai_model_name: str = None
    _log_dir_path: str = None
    _daily_room_url: str = None
    _daily_meeting_token: str = None

    def __init__(self,
                 openai_api_key: str,
                 openai_model_name: str,
                 daily_room_url: str = None,
                 daily_meeting_token: str = None,
                 log_dir_path: str = None):
        self._openai_api_key = openai_api_key
        self._openai_model_name = openai_model_name
        self._log_dir_path = log_dir_path
        self._daily_room_url = daily_room_url
        self._daily_meeting_token = daily_meeting_token

    @property
    def openai_model_name(self) -> str:
        return self._openai_model_name

    @property
    def openai_api_key(self) -> str:
        return self._openai_api_key

    @property
    def log_dir_path(self) -> str:
        return self._log_dir_path

    @property
    def daily_room_url(self) -> str:
        return self._daily_room_url

    @property
    def daily_meeting_token(self) -> str:
        return self._daily_meeting_token

    def get_log_file_path(self, room_name: str) -> str | None:
        """Returns the log file for the given room name"""
        if not self.log_dir_path:
            return None
        return os.path.join(self.log_dir_path, f"{room_name}.log")

    def ensure_dirs(self):
        """Creates required file directories if they do not already exist."""
        if self.log_dir_path:
            ensure_dir(self.log_dir_path)


def ensure_dir(dir_path: str):
    """Creates directory at the given path if it does not already exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def get_headless_config() -> BotConfig:
    dotenv_path = join(dirname(dirname(abspath(__file__))), '.env')
    load_dotenv(dotenv_path)

    parser = argparse.ArgumentParser(description='Start a session.')
    parser.add_argument(
        '--room_url',
        type=str,
        default=os.environ.get('ROOM_URL'),
        help='URL of the room')
    parser.add_argument(
        '--oai_api_key',
        type=str,
        default=os.environ.get('OPENAI_API_KEY'),
        help='OpenAI API key')
    parser.add_argument(
        '--oai_model_name',
        type=str,
        default=os.environ.get('OPENAI_MODEL_NAME'),
        help='OpenAI API URL')
    parser.add_argument(
        '--daily_meeting_token',
        type=str,
        default=None,
        help='Daily meetng token')
    parser.add_argument(
        '--log_dir_name',
        type=str,
        default=None,
        help='Log dir name')
    args = parser.parse_args()

    ldn = args.log_dir_name
    ldp = None
    if ldn:
        ldp = os.path.abspath(ldn)
    return BotConfig(args.oai_api_key, args.oai_model_name,
                     args.room_url, args.daily_meeting_token, ldp)
