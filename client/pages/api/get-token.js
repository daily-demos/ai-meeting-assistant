import { API_HOST } from "../../utils/api";

export default async function handler(req, res) {


  if (!apiKey) { 
    res.status(500).json({
      error: "Missing Daily API Key",
    });
    return;
  }

  const { roomName } = req.query;
  if (!roomName) {
    res.status(400).json({
      error: "Missing room name query parameter",
    });
    return;
  }

  // 5-minute default expiry
  const tokenExpiry = Math.floor(Date.now() / 1000) + 300;

  const url = `${API_HOST}/meeting-tokens`;

  const response = await fetch(url, {
      method: 'POST',
      headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          'properties': {
              'room_name': roomName,
              'is_owner': true,
              'exp': tokenExpiry,
          }
      })
  });

  if (!response.ok) {
      const err = await response.text();
      throw new Error(`Failed to get meeting token: ${err}`);
  }
  const data = await response.json();

  const meetingToken = data['token'];
  res.status(200).json({ meetingToken: meetingToken });
}


