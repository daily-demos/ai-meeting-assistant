const getSummaryBackend = `http://daily-ai-assistant-wip4.eba-khngcrah.us-east-2.elasticbeanstalk.com/summary`;

export default async function handler(req, res) {
  const roomUrl = req.query.room_url;

  const backend = new URL(getSummaryBackend);
  backend.searchParams.set("room_url", roomUrl);

  const response = await fetch(backend.toString(), {
    headers: {
      "Content-type": "application/json",
    },
    method: "GET",
  });

  if (!response.ok) {
    res.status(500).json({
      error: "Error when getting summary",
      details: await response.json(),
    });
    return;
  }
  const body = await response.json();

  let summary = body.summary;

  if (!summary.startsWith("🤖")) summary = `🤖 ${summary}`;

  res.status(200).json({ summary });
}
