"""Module defining an assistant base class, which new assistants can implement"""
from abc import ABC, abstractmethod


class NoContextError(Exception):
    """Raised when a query is made but no context is available"""
    pass


class Assistant(ABC):
    """Abstract class defining methods that should be implemented by any assistant"""

    @abstractmethod
    def register_new_context(self, new_text: str,
                             name: list[str] = None) -> str:
        """Registers new context (usually a transcription line)."""

    @abstractmethod
    async def query(self, custom_query: str) -> str:
        """Runs a query against the assistant and returns the answer."""
