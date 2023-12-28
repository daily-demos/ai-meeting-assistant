"""Module defining an assistant base class, which new assistants can implement"""
from abc import ABC, abstractmethod


class NoContextError(Exception):
    """Raised when a query is made but no context is available"""
    def __init__(self):
        m = "No context available."
        super().__init__(m)


class Assistant(ABC):
    """Abstract class defining methods that should be implemented by any assistant"""

    @abstractmethod
    def register_new_context(self, new_text: str,
                             name: list[str] = None) -> str:
        """Registers new context (usually a transcription line)."""

    @abstractmethod
    async def query(self, custom_query: str) -> str:
        """Runs a query against the assistant and returns the answer."""

    @abstractmethod
    def get_clean_transcript(self) -> str:
        """Returns latest clean transcript."""

    @abstractmethod
    async def cleanup_transcript(self) -> str:
        """Cleans up transcript from raw context."""

    @abstractmethod
    def destroy(self) -> str:
        """Destroys the assistant."""