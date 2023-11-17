const buildPrompt = (question) =>
  `AI adopts role of meeting assistant. Answer questions based on transcript. Always respond helpful, positive, concise and in clear text. No questions. User asks: ${question}`;

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
