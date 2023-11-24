import { API_HOST } from "../../utils/api";

const postQueryBackend = `${API_HOST}/query`;

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

  res.status(200).json({ response: body.response });
}
