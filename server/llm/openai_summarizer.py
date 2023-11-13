import dataclasses
from typing import Literal

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.summarizer import Summarizer

@dataclasses.dataclass
class Context:
    role: Literal["system", "user", "assistant"]
    content: str


class OpenAISummarizer(Summarizer):
    _client: OpenAI = None
    _model_name: str = None
    # For now, just store context in memory.
    _context: list[ChatCompletionMessageParam] = []
    _default_prompt = ChatCompletionSystemMessageParam(content="You are a helpful meeting summarization assistant. Your job"
                                                           "is to take meeting transcripts and produce useful "
                                                           "summaries.", role="system")


    def __init__(self, api_key: str, model_name: str="gpt-3.5-turbo"):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )

    def register_new_context(self, new_text: str):
        user_msg = ChatCompletionUserMessageParam(content=new_text, role="user")
        self._context.append(user_msg)

    def query(self, custom_query: str = None) -> str:
        query = self._default_prompt
        if custom_query:
            query = ChatCompletionSystemMessageParam(content=custom_query, role="system")
        messages = [query] + self._context
        res = self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=0,
        #    max_tokens=1024
        )
        return res.model_dump_json()
