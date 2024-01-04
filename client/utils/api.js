export const API_HOST = process.env.API_HOST ?? "http://127.0.0.1:5000";
export const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
export const DAILY_API_KEY = process.env.DAILY_API_KEY;

const buildPrompt = (question) =>
  `AI adopts role of a positive, helpful, and concise meeting assistant. The meeting transcript is provided as structured user messages. Given the transcript, answer the following question: \`${question}\`. Answer without square brackets, tags, or timestamps.`;

export const fetchSummary = async (roomUrl) => {
  const response = await fetch(`/api/summary?room_url=${roomUrl}`, {
    headers: {
      "Content-type": "application/json",
    },
  });

  const body = await response.json();
  if (response.ok) {
    return body.summary;
  }
  console.error("Failed to fetch summary: ", body);
  throw new Error();
};

const cleanupTranscriptPrompt = `
Using the exact transcript provided in the previous messages, convert it into a cleaned-up, paragraphed format. It is crucial that you strictly adhere to the content of the provided transcript without adding or modifying any of the original dialogue. Your tasks are to:

1. Correct punctuation and spelling mistakes.
2. Merge broken sentences into complete ones.
3. Remove timestamps and transcript types.
4. Clearly indicate the speaker's name at the beginning of their dialogue.

Do not add any new content or dialogue that was not present in the original transcript. The focus is on cleaning and reformatting the existing content for clarity and readability.
`;

export const fetchTranscript = async (roomUrl) => {
  const response = await fetch(`/api/transcript?room_url=${roomUrl}`, {
    headers: {
      "Content-type": "application/json",
    },
  });

  const body = await response.json();
  if (response.ok) {
    return body.transcript;
  }
  console.error("Failed to fetch transcript: ", body);
  throw new Error();
};

export const fetchQuery = async (roomUrl, query) => {
  const response = await fetch("/api/query", {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      room_url: roomUrl,
      query: buildPrompt(query),
    }),
  });

  const body = await response.json();
  if (response.ok) {
    return body.response;
  }
  console.error("Failed to fetch query: ", body);
  throw new Error()
};
