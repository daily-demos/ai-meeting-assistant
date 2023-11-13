const dailyDomainAPI = `https://api.daily.co/v1`;
const dailyRoomAPI = `https://api.daily.co/v1/rooms`;

export default async function handler(req, res) {
  const domainConfig = {
    properties: {
      enable_transcription: `deepgram:${process.env.DEEPGRAM_API_KEY}`,
    },
  };
  const domainResponse = await fetch(dailyDomainAPI, {
    headers: {
      "Content-type": "application/json",
      Authorization: `Bearer ${process.env.DAILY_API_TOKEN}`,
    },
    method: "POST",
    body: JSON.stringify(domainConfig),
  });
  if (!domainResponse.ok) {
    res.status(500).json({
      error: "Error when configuring domain",
      details: await domainResponse.json(),
    });
    return;
  }

  const roomConfig = {
    properties: {
      // 10 minutes from now
      exp: Math.ceil(Date.now() / 1000) + 600,
      eject_at_room_exp: true,
      max_participants: 3,
      // Minimal Prebuilt config
      enable_people_ui: true,
      enable_pip_ui: true,
      enable_emoji_reactions: false,
      enable_hand_raising: false,
      enable_prejoin_ui: false,
      enable_network_ui: false,
      enable_noise_cancellation_ui: false,
      enable_breakout_rooms: false,
      enable_screenshare: false,
      enable_chat: false,
      enable_recording: false,
      enable_video_processing_ui: false,
      start_video_off: false,
      start_audio_off: false,
      permissions: {
        canAdmin: true,
      },
    },
  };
  const response = await fetch(dailyRoomAPI, {
    headers: {
      "Content-type": "application/json",
      Authorization: `Bearer ${process.env.DAILY_API_TOKEN}`,
    },
    method: "POST",
    body: JSON.stringify(roomConfig),
  });
  const body = await response.json();
  if (response.ok) {
    res.status(200).json({ url: body.url });
  } else {
    res.status(500).json({ error: "Error when creating room", details: body });
  }
}
