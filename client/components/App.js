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
import { CopyRoomURLButton } from "./CopyRoomURLButton";
import { useRouter } from "next/router";
import { AIAssistant } from "./AIAssistant";
import { Transcript } from "./Transcript";

export default function App() {
  const { query } = useRouter();
  const [url, setUrl] = useState("");
  const [daily, setDaily] = useState(null);
  const [isJoining, setIsJoining] = useState(false);
  const [aiView, setAiView] = useState(null);
  const wrapperRef = useRef(null);

  const joinRoom = useCallback(async (url) => {
    setIsJoining(true);
    const response = await fetch("/api/create-session", {
      method: "POST",
      body: JSON.stringify({
        room_url: url,
      }),
    });
    const body = await response.json();
    if (body.url) {
      setUrl(body.url);
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
    const roomUrl = ev.target.elements?.url?.value;
    joinRoom(roomUrl);
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
        const frame = DailyIframe.createFrame(wrapperRef.current, {
          showLeaveButton: true,
          showUserNameChangeUI: true,
          url,
          customTrayButtons: {
            [assistantId]: getOpenRobotButton(),
            [transcriptId]: getOpenTranscriptButton(),
            [disableCCId]: getDisableCCButton(),
          },
        });
        setDaily(frame);
        await frame.join();

        frame.on("custom-button-click", handleCustomButtonClick);

        frame.once("left-meeting", () => {
          frame.off("custom-button-click", handleCustomButtonClick);
          frame.destroy();
          setDaily(null);
          setUrl("");
          setAiView(null);
        });
      };
      initFrame();
    },
    [url],
  );

  return (
    <DailyProvider callObject={daily}>
      <div className="App">
        <h1>Daily AI Meeting Assistant Demo</h1>
        {url ? (
          <>
            <div className="actions">
              <CopyRoomURLButton url={url} />
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
            <p>
              Join the call and the AI Assistant bot joins and starts
              transcription automatically.
            </p>
            <p>
              Once there's enough context, you can ask the AI for a summary or
              other information, based on the spoken words.
            </p>
            <div>
              <form onSubmit={handleSubmit}>
                <input
                  readOnly={isJoining}
                  type="url"
                  name="url"
                  placeholder="Room URL (optional)"
                />
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
