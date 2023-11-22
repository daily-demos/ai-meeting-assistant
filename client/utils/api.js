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
