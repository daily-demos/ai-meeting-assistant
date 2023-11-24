export const API_HOST = process.env.API_HOST ?? "http://127.0.0.1:5000";

const buildPrompt = (question) =>
  `AI adopts role of a positive, helpful, and concise meeting assistant. The meeting transcript is provided as structured user messages. Given the transcript, answer the following question: \`${question}\`. Answer without square brackets, tags, or timestamps.`;

export const fetchSummary = async (roomUrl) => {
  const response = await fetch(`/api/summary?room_url=${roomUrl}`, {
    headers: {
      "Content-type": "application/json",
    },
  });

  if (response.ok) {
    const body = await response.json();
    return body.summary;
  }

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
  const response = await fetch("/api/query", {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      room_url: roomUrl,
      query: cleanupTranscriptPrompt,
    }),
  });

  if (response.ok) {
    const body = await response.json();
    return body.response;
  }

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

  if (response.ok) {
    const body = await response.json();
    return body.response;
  }

  throw new Error();
};
