import { setupContextPrompt, summarizePrompt } from "../../utils/prompts";

const openAIChatCompletion = "https://api.openai.com/v1/chat/completions";

export default async function handler(req, res) {
  const { context } = JSON.parse(req.body);

  const requestBody = {
    model: "gpt-3.5-turbo",
    messages: [
      {
        role: "assistant",
        content: setupContextPrompt(context),
      },
      {
        role: "user",
        content: summarizePrompt(),
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
