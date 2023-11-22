const createSessionBackend = `${process.env.API_HOST}/session`;

export default async function handler(req, res) {
  const response = await fetch(createSessionBackend, {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: req.body,
  });

  const body = await response.json();

  if (!response.ok) {
    res.status(500).json({
      error: "Error when creating session",
      details: body,
    });
    return;
  }
  res.status(200).json({ url: body.room_url });
}
