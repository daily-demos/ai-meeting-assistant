import classNames from "classnames";
import React, { useEffect, useRef, useState } from "react";
import ReactTimeago from "react-timeago";

const buildPrompt = (question) =>
  `AI adopts role of meeting assistant. Answer questions based on transcript. Always respond helpful, positive, concise and in clear text. No questions. User asks: ${question}`;

const fetchSummary = async (roomUrl) => {
  const response = await fetch(`/api/summary?room_url=${roomUrl}`, {
    headers: {
      "Content-type": "application/json",
    },
  });

  if (response.ok) {
    const body = await response.json();
    return body.summary;
  }

  throw new Error();
};

const fetchQuery = async (roomUrl, query) => {
  const response = await fetch("/api/query", {
    headers: {
      "Content-type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      room_url: roomUrl,
      query: buildPrompt(query),
    }),
  });

  if (response.ok) {
    const body = await response.json();
    console.log(body);
    return body.response;
  }

  throw new Error();
};

export const AIAssistant = ({ roomUrl }) => {
  /**
   * Holds messages from chatting with the bot.
   */
  const [chatHistory, setChatHistory] = useState([]);

  const [isPrompting, setIsPrompting] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [playSounds, setPlaySounds] = useState(false);

  const inputRef = useRef(null);
  const chatRef = useRef(null);

  const audioMsgRef = useRef(null);
  const audioErrorRef = useRef(null);

  const playAudioMsg = () => {
    if (!audioMsgRef.current || !playSounds) return;
    audioMsgRef.current.currentTime = 0;
    audioMsgRef.current.play();
  };

  const playAudioError = () => {
    if (!audioErrorRef.current || !playSounds) return;
    audioErrorRef.current.currentTime = 0;
    audioErrorRef.current.play();
  };

  const handleAskAISubmit = async (ev) => {
    ev.preventDefault();
    const query = inputRef.current.value.trim();
    if (!query) return;
    inputRef.current.value = "";
    setChatHistory((prev) => [
      ...prev,
      {
        role: "user",
        content: query,
        date: new Date(),
      },
    ]);
    try {
      setIsPrompting(true);
      const response = await fetchQuery(roomUrl, query);
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response,
          date: new Date(),
        },
      ]);
      playAudioMsg();
    } catch {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Uh oh! While I tried to get a response for you, an error occurred! Please try again.",
          date: new Date(),
        },
      ]);
      playAudioError();
    } finally {
      setIsPrompting(false);
    }
  };

  const handleSummaryClick = async () => {
    try {
      setIsSummarizing(true);
      const response = await fetchSummary(roomUrl);
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response,
          date: new Date(),
        },
      ]);
      playAudioMsg();
    } catch {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Uh oh! While I tried to get a summary for you, an error occurred! Please try again.",
          date: new Date(),
        },
      ]);
      playAudioError();
    } finally {
      setIsSummarizing(false);
    }
  };

  useEffect(() => {
    chatRef.current?.scrollTo({
      top: chatRef.current?.scrollHeight,
      behavior: "smooth",
    });
  }, [chatHistory]);

  return (
    <div className="ai-assistant">
      <div className="wrapper">
        <div className="actions">
          {chatHistory.length > 0 && (
            <button onClick={() => setChatHistory([])}>💨 Clear chat</button>
          )}
          <button onClick={() => setPlaySounds((p) => !p)}>
            <img
              src={playSounds ? "/volume-on.svg" : "/volume-off.svg"}
              alt={playSounds ? "Disable sounds" : "Enable sounds"}
              height="16"
            />
          </button>
        </div>
        <div className="stream" ref={chatRef}>
          {chatHistory.map((msg) => (
            <div
              key={`${msg.role}${msg.date.toString()}`}
              className={classNames("message", {
                question: msg.role === "user",
                answer: msg.role === "assistant",
              })}
            >
              <ReactTimeago date={msg.date} />
              {msg.content}
            </div>
          ))}
        </div>
        <div className="quick-actions">
          <button disabled={isSummarizing} onClick={handleSummaryClick}>
            Summary
          </button>
        </div>
        <form className="input" onSubmit={handleAskAISubmit}>
          <input
            ref={inputRef}
            type="text"
            readOnly={isPrompting}
            placeholder="Ask AI"
            maxLength={256}
            required
          />
          <button disabled={isPrompting} type="submit">
            {isPrompting ? "Loading…" : "Submit"}
          </button>
        </form>
      </div>
      <audio ref={audioMsgRef} src="/ai-message.mp3" playsInline />
      <audio ref={audioErrorRef} src="/ai-error.mp3" playsInline />
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
          font-size: 14px;
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
          font-weight: 600;
          outline: 0 solid var(--highlight50);
          padding: 6px 8px;
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
          padding: 6px 8px;
        }
        input:focus-visible {
          outline-width: 2px;
        }
      `}</style>
      <style jsx>{`
        .ai-assistant {
          align-self: stretch;
          flex-grow: 1;
          height: 100%;
          width: 100%;

          align-items: stretch;
          display: flex;
          flex-direction: column;
          gap: 8px;
          justify-content: stretch;
        }
        .actions {
          display: flex;
          gap: 4px;
          justify-content: flex-end;
        }
        .actions button img {
          display: block;
        }
        .wrapper {
          padding: 8px;

          flex-grow: 1;
          min-height: 0;

          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .stream {
          flex-grow: 1;

          overflow-y: auto;
        }
        .stream .message {
          border-radius: 4px;
          padding: 8px;
          text-align: left;
          width: auto;
        }
        .stream .message.question {
          border: 1px solid var(--border);
          margin-left: 2rem;
        }
        .stream .message.answer {
          background: var(--highlight);
          color: #000;
          margin-right: 2rem;
          white-space: pre-wrap;
        }
        .stream .message :global(time) {
          display: block;
          font-style: italic;
          font-size: 0.75rem;
        }
        .stream .message + .message {
          margin-top: 4px;
        }
        .quick-actions {
          display: flex;
          gap: 4px;
          justify-content: flex-start;
        }
        .quick-actions button {
          width: auto;
        }
        .input {
          display: flex;
          gap: 4px;
        }
        .input input {
          flex-grow: 1;
        }
        .input button {
          flex-shrink: 1;
          width: auto;
        }
      `}</style>
    </div>
  );
};
