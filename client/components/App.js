import DailyIframe from "@daily-co/daily-js";
import { DailyProvider } from "@daily-co/daily-react";
import { useEffect, useRef, useState } from "react";
import copy from "copy-to-clipboard";
import { ClosedCaptions, disableCCId } from "./ClosedCaptions";
import { RobotButtonEffects, robotBtnId } from "./RobotButtonEffects";
import {
  getDisableCCButton,
  getOpenRobotButton,
} from "../utils/custom-buttons";

export default function App() {
  const [url, setUrl] = useState("");
  const [daily, setDaily] = useState(null);
  const [isJoining, setIsJoining] = useState(false);
  const wrapperRef = useRef(null);

  const handleJoinClick = async () => {
    setIsJoining(true);
    const response = await fetch("/api/create-session", {
      method: "POST",
    });
    const body = await response.json();
    if (body.url) {
      setUrl(body.url);
    }
    setIsJoining(false);
  };

  const handleSubmit = (ev) => {
    ev.preventDefault();
    setUrl(ev.target.elements.url.value);
  };

  useEffect(
    function initAppEffect() {
      if (!url) return;
      const initFrame = async () => {
        if (DailyIframe.getCallInstance()) {
          await DailyIframe.getCallInstance().destroy();
        }
        const frame = DailyIframe.createFrame(wrapperRef.current, {
          showLeaveButton: true,
          showUserNameChangeUI: true,
          url: url,
          customIntegrations: {
            assistant: {
              label: "AI Assistant",
              location: "sidebar",
              src:
                location.protocol +
                "//" +
                location.host +
                "/assistant?room_url=" +
                url,
            },
          },
          customTrayButtons: {
            [robotBtnId]: getOpenRobotButton(),
            [disableCCId]: getDisableCCButton(),
          },
        });
        setDaily(frame);
        await frame.join();

        frame.once("left-meeting", () => {
          frame.destroy();
          setDaily(null);
          setUrl("");
        });
      };
      initFrame();
    },
    [url],
  );

  const [copied, setCopied] = useState(false);
  const handleCopyURL = () => {
    if (copy(url)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  return (
    <DailyProvider callObject={daily}>
      <div className="App">
        <h1>Daily AI Meeting Assistant Demo</h1>
        {url ? (
          <>
            <div className="actions">
              <button disabled={copied} onClick={handleCopyURL}>
                {copied ? "✅ Copied" : "📋 Copy room URL"}
              </button>
            </div>
          </>
        ) : (
          <>
            <p>Join the call and the AI Assistant bot joins automatically.</p>
            <p>
              Once there's enough context, you can ask the AI for a summary or
              other information, based on the spoken words.
            </p>
            <div>
              <button disabled={isJoining} onClick={handleJoinClick}>
                Join a call
              </button>
            </div>
            <div>or enter room URL</div>
            <div>
              <form onSubmit={handleSubmit}>
                <input type="url" name="url" required />
                <button type="submit">Join</button>
              </form>
            </div>
          </>
        )}
        <div className="container">
          <div className="call">
            <div id="frame" ref={wrapperRef} />
            <ClosedCaptions />
            <RobotButtonEffects />
          </div>
        </div>
      </div>
      <style jsx global>{`
        *,
        *::before,
        *::after {
          box-sizing: border-box;
        }

        :root {
          --bg: #fff;
          --border: #2b3f56;
          --text: #121a24;
          --highlight: #1bebb9;
          --highlight50: #d1fbf1;

          height: 100%;
          margin: 0;
          padding: 0;
          width: 100%;
        }

        body {
          background: var(--bg);
          color: var(--text);
          font-family:
            -apple-system,
            BlinkMacSystemFont,
            Segoe UI,
            Roboto,
            Oxygen,
            Ubuntu,
            Cantarell,
            Fira Sans,
            Droid Sans,
            Helvetica Neue,
            sans-serif;
          height: 100%;
          width: 100%;
          margin: 0;
          padding: 0;
        }

        #__next {
          height: 100%;
        }

        button {
          background: var(--highlight);
          border: none;
          border-radius: 4px;
          color: var(--text);
          cursor: pointer;
          outline: 0 solid var(--highlight50);
          padding: 4px 8px;
        }
        button:not([disabled]):hover,
        button:not([disabled]):focus-visible {
          outline-width: 2px;
        }
        button[disabled] {
          cursor: default;
          opacity: 0.5;
        }

        input {
          background: var(--bg);
          border: 1px solid var(--border);
          border-radius: 4px;
          color: var(--text);
          outline: 0 solid var(--highlight50);
          padding: 4px 8px;
        }
        input:focus-visible {
          outline-width: 2px;
        }
      `}</style>
      <style jsx>{`
        .App {
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
        }
        .call {
          align-items: center;
          display: flex;
          flex-direction: column;
          flex: 1 1 auto;
          gap: 8px;
          height: 100%;
          justify-content: center;
          position: relative;
          width: 60%;
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
