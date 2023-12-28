"""Module that defines an OpenAI assistant."""
import asyncio
from collections import deque
import logging
import threading

from openai import OpenAI
from openai.types.beta import Assistant
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from server.llm.assistant import Assistant, NoContextError

class StrContext:
    ctx: str = None
    lock: threading.Lock = None

    def __init__(self):
        self.ctx = ""
        self.lock = threading.Lock()
        
class OpenAIAssistant(Assistant):
    """Class that implements assistant features using the OpenAI API"""
    _client: OpenAI = None
    _oai_assistant_id: int = None
    _oai_summary_thread_id: int = None
    _model_name: str = None
    _logger: logging.Logger = None

    # For now, just store context in memory.
    _raw_context: deque([ChatCompletionMessageParam]) = None
    _clean_transcript: StrContext = None
    _clean_transcript_running: bool = False
    _summary_context: str = None

    # Process 20 context items at a time.
    _transcript_batch_size: int = 25


    _default_transcript_prompt = ChatCompletionSystemMessageParam(content="""
        Using the exact transcript provided in the previous messages, convert it into a cleaned-up, paragraphed format. It is crucial that you strictly adhere to the content of the provided transcript without adding or modifying any of the original dialogue. Your tasks are to:

        1. Correct punctuation and spelling mistakes.
        2. Merge broken sentences into complete ones.
        3. Remove timestamps and transcript types.
        4. Clearly indicate the speaker's name at the beginning of their dialogue.

        Do not add any new content or dialogue that was not present in the original transcript. The focus is on cleaning and reformatting the existing content for clarity and readability.
        """,
        role="system")
    
    _default_prompt = """
         Primary Instruction:
         Based on the provided meeting transcripts, please create a concise summary. Your summary should include:

            1. Key discussion points.
            2. Decisions made.
            3. Action items assigned.

        Keep the summary within six sentences, ensuring it captures the essence of the conversation. Structure it in clear, digestible parts for easy understanding. Rely solely on information from the transcript; do not infer or add information not explicitly mentioned. Exclude any square brackets, tags, or timestamps from the summary. Always summarize the provided transcript context as a whole from scratch, without referring to previous summaries.
        """

    def __init__(self, api_key: str, model_name: str = None,
                 logger: logging.Logger = None):
        if not api_key:
            raise Exception("OpenAI API key not provided, but required.")

        self._raw_context = deque()
        self._summary_context = ""
        self._clean_transcript = StrContext()
        self._logger = logger
        if not model_name:
            model_name = "gpt-3.5-turbo"
        self._model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
        )
        self._oai_assistant_id = self._client.beta.assistants.create(description="Daily meeting summary assistant",
        instructions=self._default_prompt,
        model=model_name).id

    def destroy(self):
        self._client.beta.threads.delete(self._oai_summary_thread_id)
        self._client.beta.assistants.delete(self._oai_assistant_id)

    def register_new_context(self, new_text: str, metadata: list[str] = None):
        """Registers new context (usually a transcription line)."""
        content = self._compile_ctx_content(new_text, metadata)
        user_msg = ChatCompletionUserMessageParam(content=content, role="user")
        self._raw_context.append(user_msg)

    def get_clean_transcript(self) -> str:
        return self._clean_transcript.ctx

    async def cleanup_transcript(self) -> str:
        if self._clean_transcript_running:
            raise Exception("Clean transcript process already running")
        
        self._clean_transcript_running = True

        if len(self._raw_context) == 0:
            self._clean_transcript_running = False
            raise NoContextError()
        
        
        to_fetch = self._transcript_batch_size
        to_process = []
        ctx = self._raw_context
        while to_fetch > 0 and ctx:
            next_line = ctx.popleft()
            to_process.append(next_line)
            to_fetch -= 1
            if to_fetch == 0 and "." not in next_line:
                to_fetch += 1
                print("SEARCHING FOR END OF SENTENCE")


        messages = to_process + [self._default_transcript_prompt]
        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None, self._make_openai_request, messages)
            res = await future
            ct = self._clean_transcript
            ct.ctx += res

            if not self._oai_summary_thread_id:
                print("CREATING OAI SUMMARY THREAD")
                thread = self._client.beta.threads.create()
                self._oai_summary_thread_id = thread.id
            print("CREATING OAI MESSAGE")
            self._client.beta.threads.messages.create(self._oai_summary_thread_id, content=res, role="user")
            self._clean_transcript_running = False
        except Exception as e:
            print("CLEAN_TRANSCRIPT() failed:", e, sep="\n")
            # Re-insert failed items into the queue
            for item in reversed(to_process):
                self._raw_context.appendleft(item)
            self._clean_transcript_running = False
            raise Exception(f"Failed to query OpenAI: {e}") from e

    async def query(self, custom_query: str = None) -> str:
        """Submits a query to OpenAI with the stored context if one is provided.
        If a query is not provided, uses the default."""
        if not self._oai_summary_thread_id:
            raise NoContextError()

        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                None, self._make_openai_thread_request, self._oai_summary_thread_id)
            res = await future
            return res
        except Exception as e:
            raise Exception(f"Failed to query OpenAI thread: {e}") from e

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

    def _make_openai_thread_request(
            self, thread_id: list) -> str:
        """Makes a chat completion request to OpenAI and returns the response."""
    
        run = self._client.beta.threads.runs.create(
                assistant_id=self._oai_assistant_id,
                thread_id=thread_id,
            )
        while run.status !="completed":
            run = self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        
        messages = self._client.beta.threads.messages.list(
            thread_id=thread_id,
        )

        msg_data = messages.data[0]
        answer = msg_data.content[0].text.value
        return answer
