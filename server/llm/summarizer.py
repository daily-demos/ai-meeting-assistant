"""Module defining a transcriber base class, which new summarizers can implement"""
from abc import ABC, abstractmethod


class Summarizer(ABC):
    """Abstract class defining methods that should be implemented by any summarizer"""
    @abstractmethod
    def register_new_context(self, new_text: str) -> str:
        """Returns a transcription string"""

    @abstractmethod
    def query(self, custom_query: str) -> str:
        """Returns a transcription string"""
