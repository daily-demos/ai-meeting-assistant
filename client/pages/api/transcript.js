import { API_HOST } from "../../utils/api";

const getTranscriptBackend = `${API_HOST}/transcript`;

export default async function handler(req, res) {
  const roomUrl = req.query.room_url;

  const backend = new URL(getTranscriptBackend);
  backend.searchParams.set("room_url", roomUrl);

  const response = await fetch(backend.toString(), {
    headers: {
      "Content-type": "application/json",
    },
    method: "GET",
  });

  if (!response.ok) {
    res.status(500).json({
      error: "Error when getting transcript",
      details: await response.json(),
    });
    return;
  }
  const body = await response.json();

  res.status(200).json({ transcript: body.transcript });
}
