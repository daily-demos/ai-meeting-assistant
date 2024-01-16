"""Module that defines an OpenAI assistant."""
import asyncio
from collections import deque
import logging

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.assistant import Assistant, NoContextError
from server.store.memory import MemoryStore


def probe_api_key(api_key: str) -> bool:
    """Probes the OpenAI API with the provided key to ensure it is valid."""
    try:
        client = OpenAI(api_key=api_key)
        client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                ChatCompletionUserMessageParam(
                    content="This is a test",
                    role="user")],
        )
        return True
    except Exception as e:
        print(f"Failed to probe OpenAI API key: {e}")
        return False


class OpenAIAssistant(Assistant):
    """Class that implements assistant features using the OpenAI API"""
    _client: OpenAI = None

    _model_name: str = None
    _logger: logging.Logger = None

    # For now, just store context in memory.
    _raw_context: deque([ChatCompletionMessageParam]) = None
    _clean_transcript: str = None
    _clean_transcript_running: bool = False
    _summary_context: str = None

    # Process 20 context items at a time.
    _transcript_batch_size: int = 25

    _store: MemoryStore = None
    _default_transcript_prompt = ChatCompletionSystemMessageParam(content="""
        Using the exact transcript provided in the previous messages, convert it into a cleaned-up, paragraphed format. It is crucial that you strictly adhere to the content of the provided transcript without adding or modifying any of the original dialogue. Your tasks are to:

        1. Include speaker's name at the beginning of each dialogue
        2. Correct punctuation and spelling mistakes.
        3. Merge broken sentences into complete ones.
        4. Remove timestamps and transcript types.

        Do not add any new content or dialogue that was not present in the original transcript. The focus is on cleaning and reformatting the existing content for clarity and readability.
        """, role="system")

    _default_prompt = """
         Based on the above meeting transcript context, please create a concise summary.
         Assume the role of a professional note taker for business meetings.
         Your summary should include 3 separate sections:

            1. Key discussion points written as bullet points
            2. Decisions made written as bullet points
            3. Action items assigned written as bullet points

        Keep the summary within 12 sentences, ensuring it captures the 3 sections of the conversation. 
        Structure it in clear, digestible paragraphs for easy understanding. 
        Rely solely on information from the transcript; do not infer or add information not explicitly mentioned. 
        Exclude any square brackets, tags, or timestamps from the summary.
        """

    def __init__(self, api_key: str, model_name: str = None,
                 logger: logging.Logger = None):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")

        self._raw_context = deque()
        self._summary_context = ""
        self._clean_transcript = ""
        self._logger = logger
        if not model_name:
            model_name = "gpt-4-1106-preview"
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )
        self._store = MemoryStore(self._client)

    def destroy(self):
        """Destroys the assistant and relevant resources"""
        self._store.destroy()

    def register_new_context(self, new_text: str, metadata: list[str] = None):
        """Registers new context (usually a transcription line)."""
        content = self._compile_ctx_content(new_text, metadata)
        user_msg = ChatCompletionUserMessageParam(content=content, role="user")
        self._raw_context.append(user_msg)

    def get_clean_transcript(self) -> str:
        """Returns latest clean transcript."""
        return self._clean_transcript

    async def cleanup_transcript(self) -> str:
        """Cleans up transcript from raw context."""
        if self._clean_transcript_running:
            raise Exception("Clean transcript process already running")

        # Set this bool to ensure only one cleanup process
        # is running at a time.
        self._clean_transcript_running = True

        if len(self._raw_context) == 0:
            self._clean_transcript_running = False
            raise NoContextError()

        # How many transcript lines to process
        to_fetch = self._transcript_batch_size

        to_process = []
        ctx = self._raw_context

        # Fetch the next batch of transcript lines
        while to_fetch > 0 and ctx:
            next_line = ctx.popleft()
            to_process.append(next_line)
            # If we're at the end of the batch size but did not
            # get what appears to be a full sentence, just keep going.
            if to_fetch == 1 and "." not in next_line.content:
                continue
            to_fetch -= 1

        messages = to_process + [self._default_transcript_prompt]
        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None, self._make_openai_request, messages)
            res = await future
            self._clean_transcript += f"\n\n{res}"
            self._store.add(
                [ChatCompletionUserMessageParam(role="user", content=res)])
            self._clean_transcript_running = False
        except Exception as e:
            # Re-insert failed items into the queue,
            # to make sure they do not get lost on next attempt.
            for item in reversed(to_process):
                self._raw_context.appendleft(item)
            self._clean_transcript_running = False
            raise Exception(f"Failed to query OpenAI: {e}") from e

    async def query(self, custom_query: str = None) -> str:
        """Submits a query to OpenAI with the stored context if one is provided.
        If a query is not provided, uses the default."""

        if not self._clean_transcript:
            raise NoContextError()

        input_param: ChatCompletionUserMessageParam = None
        search_param: ChatCompletionUserMessageParam = None
        ctx = []
        if custom_query:
            search_param = ChatCompletionUserMessageParam(
                content=custom_query, role="user")
            input_param = search_param
            ctx = self._store.gather_context(input_param, 4096)
            if not ctx:
                raise NoContextError()

        else:
            ctx = [ChatCompletionUserMessageParam(
                content=self._clean_transcript, role="user")]
            input_param =ChatCompletionUserMessageParam(
                content=self._default_prompt, role="system")
            
        final_ctx = ctx + [input_param]
        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None, self._make_openai_request, final_ctx)
            res = await future
            if not custom_query:
                self._store.add(
                    [ChatCompletionUserMessageParam(role="assistant", content=res)])
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
        )

        for choice in res.choices:
            reason = choice.finish_reason
            if reason == "stop" or reason == "length":
                answer = choice.message.content
                return answer
        raise Exception(
            "No usable choice found in OpenAI response: %s",
            res.choices)
