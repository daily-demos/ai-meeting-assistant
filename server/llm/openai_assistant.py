"""Module that defines an OpenAI assistant."""
import asyncio
import logging
import threading

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.assistant import Assistant, NoContextError


class OpenAIAssistant(Assistant):
    """Class that implements assistant features using the OpenAI API"""
    _client: OpenAI = None
    _model_name: str = None
    _logger: logging.Logger = None
    _lock: threading.Lock

    # For now, just store context in memory.
    _context: list[ChatCompletionMessageParam] = None
    _default_prompt = ChatCompletionSystemMessageParam(
        content="""
         Based on the provided meeting transcript, please create a concise summary. Your summary should include:

            1. Key discussion points.
            2. Decisions made.
            3. Action items assigned.

        Keep the summary within six sentences, ensuring it captures the essence of the conversation. Structure it in clear, digestible parts for easy understanding. Rely solely on information from the transcript; do not infer or add information not explicitly mentioned. Exclude any square brackets, tags, or timestamps from the summary.
        """,
        role="system")

    def __init__(self, api_key: str, model_name: str = None,
                 logger: logging.Logger = None):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")

        self._lock = threading.Lock()
        self._context = []
        self._logger = logger
        if not model_name:
            model_name = "gpt-3.5-turbo"
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )

    def register_new_context(self, new_text: str, metadata: list[str] = None):
        """Registers new context (usually a transcription line)."""
        content = self._compile_ctx_content(new_text, metadata)
        user_msg = ChatCompletionUserMessageParam(content=content, role="user")
        with self._lock:
            self._context.append(user_msg)

    async def query(self, custom_query: str = None) -> str:
        """Submits a query to OpenAI with the stored context if one is provided.
        If a query is not provided, uses the default."""
        with self._lock:
            if len(self._context) == 0:
                raise NoContextError()

        query = self._default_prompt

        if custom_query:
            query = ChatCompletionSystemMessageParam(
                content=custom_query, role="system")

        with self._lock:
            messages = self._context + [query]

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None, self._make_openai_request, messages)
            res = await future
            return res
        except Exception as e:
            raise Exception(f"Failed to query OpenAI: {e}") from e

    def _compile_ctx_content(self, new_text: str,
                             metadata: list[str] = None) -> str:
        """Compiles context content from the provided text and metadata."""
        content = ""
        if metadata:
            content += f"[{' | '.join(metadata)}] "
        content += new_text
        return content

    def _make_openai_request(
            self, messages: list[ChatCompletionMessageParam]) -> str:
        """Makes a chat completion request to OpenAI and returns the response."""
        res = self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=0,
        )
        for choice in res.choices:
            reason = choice.finish_reason
            if reason == "stop" or reason == "length":
                answer = choice.message.content
                return answer
        raise Exception(
            "No usable choice found in OpenAI response: %s",
            res.choices)
