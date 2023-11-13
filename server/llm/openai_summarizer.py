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


    def __init__(self, api_key: str, model_name: str="gpt-3.5-turbo"):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )

        system_msg = ChatCompletionSystemMessageParam(content="You are a helpful meeting summarization assistant. Your job"
                                                           "is to take meeting transcripts and produce useful "
                                                           "summaries.", role="system")
        self._context.append(system_msg)

    def register_new_context(self, new_text: str):
        user_msg = ChatCompletionUserMessageParam(content=new_text, role="user")
        self._context.append(user_msg)

    def summarize(self) -> str:
        res = self._client.chat.completions.create(
            model=self._model_name,
            messages=self._context,
            temperature=0,
            max_tokens=1024
        )
        return res.model_dump_json()
