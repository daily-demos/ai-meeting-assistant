import threading
import time
import numpy
from openai.types.embedding import Embedding
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionUserMessageParam
import textwrap
import tiktoken
from dailyai.services.open_ai_services import OpenAILLMService



class MemoryStore:
    _service: OpenAILLMService
    _embeddings: list[Embedding]
    _params: list[ChatCompletionMessageParam]
    _embedding_model = "text-embedding-ada-002"
    _lock: threading.Lock

    def __init__(self, service: OpenAILLMService):
        self._lock = threading.Lock()
        self._service = service
        self._embeddings = []
        self._params = []

    async def add(self, params: list[ChatCompletionMessageParam]):
        """Stores messages and embeddings for context generation."""
        new_params = []
        for param in params:
            content = param.get("content")
            prefix = f'[Timestamp {time.time()}]: '

            chunks = chunk(content, prefix=prefix, target_chunk_size=500)
            for c in chunks:
                np = {'role': param.get('role'), 'content': c}
                new_params.append(np)

        input: list[str] = []
        for doc in new_params:
            input.append(str(doc))
        embeddings = await self._service.client.embeddings.create(
            input=input,
            model=self._embedding_model
        )
        with self._lock:
            self._params.extend(new_params)
            self._embeddings.extend(embeddings.data)

            if len(self._params) != len(self._embeddings):
                raise Exception(
                    "Something went wrong, params and embeddings are not the same length.")

    async def gather_context(self, input: ChatCompletionUserMessageParam,
                       max_tokens: int = 120000) -> list[ChatCompletionMessageParam]:
        """Queries store for most contextually relevant params."""
        with self._lock:
            if self._params == []:
                return []

            embeddings = await self._service.client.embeddings.create(
                input=str(input),
                model=self._embedding_model
            )
            input_embedding = embeddings.data[0].embedding

            sims: list[tuple[float, int]] = []
            for i, embedding in enumerate(self._embeddings):
                sim = self._cosine_similarity(
                    input_embedding, embedding.embedding)
                sims.append((sim, i))

            sims.sort(key=lambda x: x[0], reverse=True)
            idxs = [x[1] for x in sims]

            remaining_tokens = max_tokens
            relevant_docs = []
            for i in idxs:
                doc = self._params[i]
                tokens_used = count_tokens(doc.get('content'))
                if remaining_tokens - tokens_used < 0:
                    print("Token limit reached")
                    break
                remaining_tokens -= tokens_used
                relevant_docs.append(doc)
            return relevant_docs
    
    def destroy(self):
        """Destroys all stored messages and embeddings."""
        with self._lock:
            self._embeddings = []
            self._params = []

    def _cosine_similarity(self, a, b):
        return numpy.dot(a, b) / (numpy.linalg.norm(a) * numpy.linalg.norm(b))


def count_tokens(input: str, model_name="gpt-4-1106-preview") -> int:
    """Count token usage for given input string."""
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(input))


def chunk(input: str, target_chunk_size=500, prefix: str = "",
          model_name="gpt-4-1106-preview") -> list[str]:
    """Chunk given input string."""
    prefix_token_count = count_tokens(prefix, model_name=model_name)
    part_spec = f'[Part x/y]'
    part_spec_token_count = count_tokens(part_spec, model_name=model_name)

    chunks = textwrap.wrap(
        input,
        target_chunk_size -
        prefix_token_count -
        part_spec_token_count)
    num_chunks = len(chunks)
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if num_chunks > 1:
            chunk = f'{prefix}[Part {i+1}/{len(chunks)}]: {chunk}'
        else:
            chunk = f'{prefix}{chunk}'
        final_chunks.append(chunk)
    return final_chunks
