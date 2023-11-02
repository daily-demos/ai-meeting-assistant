const openAIChatCompletion = "https://api.openai.com/v1/chat/completions";

export default async function handler(req, res) {
  const { context, query } = JSON.parse(req.body);

  const requestBody = {
    model: "gpt-3.5-turbo",
    messages: [
      {
        role: "assistant",
        content: `AI adopts role of virtual meeting assistant and handles meeting transcript to provide meaningful and concise assistance for meeting participants. Always answer short and polite.\nBelow is the context of the meeting thus far:\n\n\`\`\`${context}\`\`\``,
      },
      {
        role: "user",
        content: query,
      },
    ],
  };
  try {
    const response = await fetch(openAIChatCompletion, {
      headers: {
        "Content-type": "application/json",
        Authorization: `Bearer ${process.env.OPENAI_API_TOKEN}`,
      },
      method: "POST",
      body: JSON.stringify(requestBody),
    });
    const body = await response.json();
    if (response.ok) {
      res.status(200).json(body);
    } else {
      res.status(500).json({ error: "Error when querying AI", details: body });
    }
  } catch (e) {
    res.status(500).json({ error: e });
  }
}
