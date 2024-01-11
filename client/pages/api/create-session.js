import { API_HOST , DAILY_API_KEY, OPENAI_API_KEY } from "../../utils/api";

const createSessionBackend = `${API_HOST}/session`;

const dailyAPIKeyErr = "Invalid Daily API key";

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
  let ownerToken, botToken;
  try {
    ownerToken = await getMeetingToken(room_url, daily_api_key, true);
    if (want_bot_token) {
      botToken = await getMeetingToken(room_url, daily_api_key, false);
    }
  } catch (err) {
    if (err.message === dailyAPIKeyErr) {
      res.status(400).json({
        error: dailyAPIKeyErr,
      });
      return;
    }
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
    if (response.status === 401) {
      res.status(401).json({
        error: body,
      });
    }
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
  const roomName = getRoomName(roomURL);

  const tokenProperties = {
    'properties': {
        'room_name': roomName,
        'is_owner': isOwner,
        'exp': tokenExpiry,
    }
  }

  if (isOwner) {
    tokenProperties.properties['auto_start_transcription'] = true;
  }

  const response = await fetch(url, {
      method: 'POST',
      headers: {
          Authorization: `Bearer ${dailyKey}`,
          'Content-Type': 'application/json',
      },
      body: JSON.stringify(tokenProperties)
   });
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error(dailyAPIKeyErr)
    }

    const err = await response.text();
    throw new Error(`Failed to get meeting token: ${err}`);
  }
  const data = await response.json(); 
  const meetingToken = data.token;
  return meetingToken;
 }

/**
 * Returns the URL of the Daily API based on the room URL
 * @param {string} roomURL 
 * @returns 
 */
function getDailyAPIURL(roomURL) {
  const url = new URL(roomURL);
  const host = url.host;
  const hostParts = host.split('.');

  let subdomain = "";
  if (hostParts.length > 3) {
    subdomain = `${hostParts[1]}.`
  }
  return `https://${subdomain}api.daily.co/v1`
} 

/**
 * Returns the room name using the room URL
 * @param {string} roomURL 
 * @returns 
 */
function getRoomName(roomURL) {
  const url = new URL(roomURL);
  return url.pathname.split("/")[1];
} 
