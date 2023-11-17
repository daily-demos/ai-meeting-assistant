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
import { GlobalStyles } from "./GlobalStyles";
import { DoneIcon } from "./icons/DoneIcon";
import { CopyIcon } from "./icons/CopyIcon";

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
                {copied ? (
                  <>
                    <DoneIcon size={16} />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <CopyIcon size={16} />
                    <span>Copy room URL</span>
                  </>
                )}
              </button>
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
            <button disabled={isJoining} onClick={handleJoinClick}>
              Create room and join
            </button>
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
