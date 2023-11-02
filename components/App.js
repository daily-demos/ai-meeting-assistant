import DailyIframe from "@daily-co/daily-js";
import { DailyAudio, DailyProvider } from "@daily-co/daily-react";
import { useRef, useState } from "react";
import { AIAssistant } from "./AIAssistant";

export default function App() {
  const [url, setUrl] = useState("");
  const [daily, setDaily] = useState(null);
  const wrapperRef = useRef(null);

  const handleJoinClick = async () => {
    const response = await fetch("/api/create-room", {
      method: "POST",
    });
    const body = await response.json();
    if (body.url) {
      setUrl(body.url);
      if (DailyIframe.getCallInstance()) {
        await DailyIframe.getCallInstance().destroy();
      }
      const frame = DailyIframe.createFrame(wrapperRef.current, {
        showLeaveButton: true,
        showUserNameChangeUI: true,
        url: body.url,
      });
      setDaily(frame);
      await frame.join();
    }
  };

  const handleLeaveClick = async () => {
    await daily.stopTranscription();
    await daily.destroy();
    setDaily(null);
    setUrl("");
  };

  return (
    <DailyProvider callObject={daily}>
      <div className="App">
        <h1>Daily AI Meeting Assistant Demo</h1>
        <p>
          Enter your username, join the call and start speaking. The call is
          automatically transcribed.
        </p>
        <p>
          Once there's enough context, you can ask the AI for a summary or other
          information, based on the spoken words.
        </p>
        <div className="container">
          <div className="call">
            {url ? (
              <>
                <strong>{url}</strong>
                <button onClick={handleLeaveClick}>Leave</button>
              </>
            ) : (
              <button onClick={handleJoinClick}>Join a call</button>
            )}
            <div id="frame" ref={wrapperRef} />
          </div>
          {url && <AIAssistant />}
        </div>
      </div>
      <DailyAudio />
      <style jsx global>{`
        *,
        *::before,
        *::after {
          box-sizing: border-box;
        }

        :root {
          --bg: #121a24;
          --border: #2b3f56;
          --text: #fff;
          --highlight: #feaa2c;

          height: 100%;
          margin: 0;
          padding: 0;
          width: 100%;
        }

        body {
          background: var(--bg);
          color: var(--text);
          height: 100%;
          width: 100%;
          margin: 0;
          padding: 0;
        }

        #__next {
          height: 100%;
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
          justify-content: center;
          width: 60%;
          height: 100%;
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
