import { API_HOST , DAILY_API_KEY, OPENAI_API_KEY } from "../../utils/api";

const createSessionBackend = `${API_HOST}/session`;

export default async function handler(req, res) {
  const reqBody = JSON.parse(req.body);
  let { room_url, daily_api_key, openai_api_key, want_bot_token } = reqBody;
  if (!daily_api_key) {
    daily_api_key = DAILY_API_KEY;
  }
  if (!openai_api_key) {
    openai_api_key = OPENAI_API_KEY;
  } 
  if (!daily_api_key && !openai_api_key) {
    res.status(400).json({
      error: "No Daily or OpenAI API keys provided",
    });
    return;
  }
  const ownerToken = await getMeetingToken(room_url, daily_api_key, true);
  let botToken;
  if (want_bot_token) {
    botToken = await getMeetingToken(room_url, daily_api_key, false);
  }

  const response = await fetch(createSessionBackend, {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      room_url: room_url,
      meeting_token: botToken,
      openai_api_key: openai_api_key,
    }),
  });
  if (!response.ok) {
    const body = await response.text();
    res.status(500).json({
      error: "Error when creating session",
      details: body,
    });
    return;
  }
  res.status(200).json({ token: ownerToken });
}

async function getMeetingToken(roomURL, dailyKey, isOwner) {
  // 5-minute default expiry
  const tokenExpiry = Math.floor(Date.now() / 1000) + 300;

  const url = `${getDailyAPIURL(roomURL)}/meeting-tokens`;
  console.log("Ulr.", url)
  const roomName = getRoomName(roomURL);
  const response = await fetch(url, {
      method: 'POST',
      headers: {
          Authorization: `Bearer ${dailyKey}`,
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          'properties': {
              'room_name': roomName,
              'is_owner': isOwner,
              'exp': tokenExpiry,
          }
      })
   });
 
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to get meeting token: ${err}`);
  }
  const data = await response.json(); 
  const meetingToken = data.token;
  return meetingToken;
 }
 

function getDailyAPIURL(roomURL) {
  const url = new URL(roomURL);
  const host = url.host;
  const hostParts = host.split('.');

  if (hostParts.length > 2) {
    return `https://${hostParts[1]}.daily.co/api/v1`;
  }
  return "https://api.daily.co/v1"
} 

function getRoomName(roomURL) {
  const url = new URL(roomURL);
  return url.pathname.split("/")[1];
} 
