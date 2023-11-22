"""Module that defines an OpenAI assistant."""
import logging

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.assistant import Assistant, NoContextError


class OpenAIAssistant(Assistant):
    """Class that implements assistant features using the OpenAI API"""
    _client: OpenAI = None
    _model_name: str = None
    _logger: logging.Logger = None
    # For now, just store context in memory.
    _context: list[ChatCompletionMessageParam] = None
    _default_prompt = ChatCompletionSystemMessageParam(
        content="AI adopts role of meeting recorder to provide short meeting summaries including discussed key "
                "items, decisions and action items. Based on the meeting transcript only, write a summary that helps "
                "document all key aspects of the conversation. Structure the answer into digestible chunks. Do not "
                "assume things that are not in the transcript. Answer without square brackets, tags, or timestamps."
                "The summary should be no more than 6 sentences long.",
                role="system")

    def __init__(self, api_key: str, model_name: str = None,
                 logger: logging.Logger = None):
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

    def register_new_context(self, new_text: str, metadata: list[str] = None):
        """Registers new context (usually a transcription line)."""
        content = self._compile_ctx_content(new_text, metadata)
        user_msg = ChatCompletionUserMessageParam(content=content, role="user")
        self._context.append(user_msg)

    def query(self, custom_query: str = None) -> str:
        """Submits a query to OpenAI with the stored context if one is provided.
        If a query is not provided, uses the default."""
        if len(self._context) == 0:
            raise NoContextError()

        query = self._default_prompt

        if custom_query:
            query = ChatCompletionSystemMessageParam(
                content=custom_query, role="system")

        messages = self._context + [query]

        try:
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
            raise Exception("No usable choice found in OpenAI response: %s", res.choices)
        except Exception as e:
            raise Exception(f"Failed to query OpenAI: {e}") from e

    def _compile_ctx_content(self, new_text: str,
                             metadata: list[str] = None) -> str:
        content = ""
        if metadata:
            content += f"[{' | '.join(metadata)}] "
        content += new_text
        return content
