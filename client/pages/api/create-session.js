const createSessionBackend = `http://127.0.0.1:5000/session`;

export default async function handler(req, res) {
  const response = await fetch(createSessionBackend, {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
  });

  if (!response.ok) {
    res.status(500).json({
      error: "Error when creating session",
      details: await response.json(),
    });
    return;
  }
  const body = await response.json();

  if (response.ok) {
    res.status(200).json({ url: body.room_url });
  } else {
    res.status(500).json({ error: "Error when creating room", details: body });
  }
}
