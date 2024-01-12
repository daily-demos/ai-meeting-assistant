import DailyIframe from "@daily-co/daily-js";
import { DailyProvider } from "@daily-co/daily-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ClosedCaptions, disableCCId } from "./ClosedCaptions";
import {
  CustomButtonEffects,
  assistantId,
  transcriptId,
} from "./CustomButtonEffects";
import {
  getDisableCCButton,
  getOpenRobotButton,
  getOpenTranscriptButton,
} from "../utils/custom-buttons";
import { GlobalStyles } from "./GlobalStyles";
import { useRouter } from "next/router";
import { AIAssistant } from "./AIAssistant";
import { Transcript } from "./Transcript";
import { CopyContentButton } from "./CopyContentButton";

export default function App() {
  const { query } = useRouter();
  const [url, setUrl] = useState("");
  const [meetingToken, setMeetingToken] = useState("");
  const [daily, setDaily] = useState(null);
  const [isJoining, setIsJoining] = useState(false);
  const [aiView, setAiView] = useState(null);
  const wrapperRef = useRef(null);

  const joinRoom = useCallback(async (url, dailyKey, oaiKey, wantBotToken) => {
    setIsJoining(true);
    if (url && dailyKey && oaiKey) {
      const response = await fetch("/api/create-session", {
        method: "POST",
        body: JSON.stringify({
          room_url: url,
          daily_api_key: dailyKey,
          want_bot_token: wantBotToken,
          openai_api_key: oaiKey,
        }),
      });
      const body = await response.json();
      if (response.ok) {
        setMeetingToken(body.token);
        setUrl(url);
      } else {
        console.error("failed to create session:", body);
      }
    } else if (url) {
      setUrl(url);
    } else {
      console.error("URL must be provided");
    }
    setIsJoining(false);
  }, []);

  useEffect(() => {
    if (query.url && typeof query.url === "string") {
      joinRoom(query.url);
    }
  }, [query]);

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const eles = ev.target.elements;
    const roomUrl = eles.url?.value;
    const dailyKey = eles.dailyKey?.value;
    const oaiKey = eles.oaiKey?.value;
    joinRoom(roomUrl, dailyKey, oaiKey);
  };

  useEffect(
    function initAppEffect() {
      if (!url) return;

      const handleCustomButtonClick = (ev) => {
        switch (ev.button_id) {
          case assistantId:
            setAiView((v) => (v === assistantId ? null : assistantId));
            break;
          case transcriptId:
            setAiView((v) => (v === transcriptId ? null : transcriptId));
            break;
        }
      };

      const initFrame = async () => {
        if (DailyIframe.getCallInstance()) {
          await DailyIframe.getCallInstance().destroy();
        }

        const opts = {
          showLeaveButton: true,
          showUserNameChangeUI: true,
          url,
          customTrayButtons: {
            [assistantId]: getOpenRobotButton(),
            [transcriptId]: getOpenTranscriptButton(),
            [disableCCId]: getDisableCCButton(),
          },
        };

        if (meetingToken) {
          opts.token = meetingToken;
        }
        const frame = DailyIframe.createFrame(wrapperRef.current, opts);
        setDaily(frame);

        frame.on("custom-button-click", handleCustomButtonClick);

        frame.once("left-meeting", () => {
          frame.off("custom-button-click", handleCustomButtonClick);
          frame.destroy();
          setDaily(null);
          setUrl("");
          setAiView(null);
        });

        await frame.join();
      };
      initFrame();
    },
    [url],
  );

  const setInviteUrl = (roomURL) => {
    const inviteUrl = new URL(window.location.href);
    inviteUrl.searchParams.set("url", roomURL);
    return inviteUrl.toString();
  };

  return (
    <DailyProvider callObject={daily}>
      <div className="App">
        {url ? (
          <>
            <div className="actions">
              <CopyContentButton
                content={setInviteUrl(url)}
                label="Copy room URL"
              />
            </div>
            <div className="container">
              <div className="call">
                <div
                  className="ai-view"
                  style={{ display: aiView ? "" : "none" }}
                >
                  <div
                    style={{
                      display: aiView === assistantId ? "" : "none",
                      height: "100%",
                    }}
                  >
                    <AIAssistant roomUrl={url} />
                  </div>
                  <div
                    style={{
                      display: aiView === transcriptId ? "" : "none",
                      height: "100%",
                    }}
                  >
                    <Transcript roomUrl={url} />
                  </div>
                </div>
                <div id="frame" ref={wrapperRef} />
                <ClosedCaptions
                  style={{
                    left: aiView ? `calc(50% + 150px)` : "50%",
                    maxWidth: aiView ? `calc(100% - 300px)` : "100%",
                  }}
                />
                <CustomButtonEffects />
              </div>
            </div>
          </>
        ) : (
          <>
            <h1>Daily AI Meeting Assistant Demo</h1>
            <p>
              Join the call and the AI Assistant bot joins and starts
              transcription automatically.
            </p>
            <p>
              Once there's enough context, you can ask the AI for a summary or
              other information, based on the spoken words.
            </p>
            <div>
              <form onSubmit={handleSubmit} style={{ flexDirection: "column" }}>
                <input
                  readOnly={isJoining}
                  type="url"
                  name="url"
                  placeholder="Room URL (optional)"
                />
                <input
                  readOnly={isJoining}
                  type="password"
                  name="dailyKey"
                  placeholder="Daily API key"
                />
                <input
                  readOnly={isJoining}
                  type="password"
                  name="oaiKey"
                  placeholder="OpenAI API key"
                />
                <span>
                  <label htmlFor="wantBotToken">Give bot a meeting token</label>
                  <input
                    readOnly={isJoining}
                    type="checkbox"
                    name="wantBotToken"
                  />
                </span>
                <button disabled={isJoining} type="submit">
                  Join
                </button>
              </form>
            </div>
          </>
        )}
      </div>
      <GlobalStyles />
      <style jsx>{`
        .App {
          align-items: center;
          display: flex;
          flex-direction: column;
          font-family: sans-serif;
          gap: 8px;
          height: 100%;
          overflow: hidden;
          position: relative;
          text-align: center;
          width: 100%;
        }
        h1 {
          font-size: 1.25rem;
          margin: 0.5rem 0;
        }
        form {
          display: flex;
          gap: 8px;
          justify-content: center;
        }
        .actions {
          display: flex;
          gap: 4px;
          justify-content: center;
        }
        .container {
          align-items: center;
          display: flex;
          flex-grow: 1;
          gap: 8px;
          justify-content: center;
          min-height: 0;
          position: relative;
          width: 100%;
        }
        .call {
          align-items: center;
          border: 1px solid var(--border);
          display: flex;
          flex-direction: row;
          flex: 1 1 auto;
          height: 100%;
          justify-content: center;
          position: relative;
          width: 100%;
        }
        .ai-view {
          border-right: 1px solid var(--border);
          height: 100%;
          text-align: initial;
          width: 320px;
        }
        #frame {
          align-self: stretch;
          flex-grow: 2;
        }
        #frame iframe {
          display: block;
        }
      `}</style>
    </DailyProvider>
  );
}
