const postQueryBackend = `http://daily-ai-assistant-wip4.eba-khngcrah.us-east-2.elasticbeanstalk.com/query`;

export default async function handler(req, res) {
  const response = await fetch(postQueryBackend, {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: JSON.stringify(req.body),
  });

  if (!response.ok) {
    res.status(500).json({
      error: "Error when getting response",
      details: await response.json(),
    });
    return;
  }
  const body = await response.json();

  let botResponse = body.response;

  if (!botResponse.startsWith("🤖")) botResponse = `🤖 ${botResponse}`;

  res.status(200).json({ response: botResponse });
}
