"""Module that defines an OpenAI assistant."""
import dataclasses
import logging
from typing import Literal

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.assistant import Assistant


class OpenAIAssistant(Assistant):
    """Class that implements assistant features using the OpenAI API"""
    _client: OpenAI = None
    _model_name: str = None
    _logger: logging.Logger = None
    # For now, just store context in memory.
    _context: list[ChatCompletionMessageParam] = None
    _default_prompt = ChatCompletionSystemMessageParam(
        content="You are a helpful meeting summarization assistant. Your job"
                "is to take meeting transcripts and produce useful summaries."
                "You will not include square brackets in the output,"
                "nor will you include any content that you found within the square"
                "brackets EXCEPT for providing context for who is speaking by "
                "using the listed speaker's name.", role="system")

    def __init__(self, api_key: str, model_name: str = None, logger: logging.Logger = None):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")

        self._context = []
        self._logger = logger
        if not model_name:
            model_name = "gpt-3.5-turbo"
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )
        logger.info("Instantiated AI assistant %s", self._context)

    def register_new_context(self, new_text: str, metadata: list[str] = None):
        """Registers new context (usually a transcription line)."""
        self._logger.info("Registering new context %s %s %s", metadata, new_text, len(self._context))
        content = self._compile_ctx_content(new_text, metadata)
        user_msg = ChatCompletionUserMessageParam(content=content, role="user")
        self._context.append(user_msg)

    def query(self, custom_query: str = None) -> str:
        """Submits a query to OpenAI with the stored context if one is provided.
        If a query is not provided, uses the default."""
        if len(self._context) == 0:
            return ("Sorry! I don't have any context saved yet. "
                    "Please try speaking to add some context and confirm that "
                    "transcription is enabled.")

        query = self._default_prompt

        if custom_query:
            query = ChatCompletionSystemMessageParam(
                content=custom_query, role="system")
        messages = [query] + self._context
        self._logger.info("Querying %s", messages)

        try:
            res = self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=0,
                #    max_tokens=1024
            )
            for choice in res.choices:
                if choice.finish_reason == "stop":
                    answer = choice.message.content
                    return answer
            raise Exception("No usable choice found in OpenAI response")
        except Exception as e:
            raise Exception(f"Failed to query OpenAI: {e}") from e

    def _compile_ctx_content(self, new_text: str,
                             metadata: list[str] = None) -> str:
        content = ""
        if metadata:
            content += f"[{' | '.join(metadata)}] "
        content += new_text
        return content
