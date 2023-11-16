import classNames from "classnames";
import React, { useEffect, useRef, useState } from "react";
import ReactTimeago from "react-timeago";

const buildPrompt = (question) =>
  `AI adopts role of meeting assistant. Always respond helpful, positive, concise and in clear text. Wrap every response with 🤖. Given the transcript, answer: ${question}`;

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

export const AIAssistant = ({ roomUrl }) => {
  /**
   * Holds messages from chatting with the bot.
   */
  const [chatHistory, setChatHistory] = useState([]);

  const [isPrompting, setIsPrompting] = useState(false);

  // const inputRef = useRef(null);

  const handleAskAISubmit = async (ev) => {
    ev.preventDefault();
    // const query = inputRef.current.value.trim();
    // if (!query) return;
    // inputRef.current.value = "";
    // setChatHistory((prev) => [
    //   ...prev,
    //   {
    //     role: "user",
    //     content: query,
    //     date: new Date(),
    //   },
    // ]);
    try {
      setIsPrompting(true);
      const summary = await fetchSummary(roomUrl);
      console.log(summary);
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: summary,
          date: new Date(),
        },
      ]);
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
    } finally {
      setIsPrompting(false);
    }
  };

  const chatRef = useRef(null);

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
        <form className="input" onSubmit={handleAskAISubmit}>
          {/* <input
            ref={inputRef}
            type="text"
            placeholder="Ask AI"
            maxLength={256}
            required
          /> */}
          <button disabled={isPrompting} type="submit">
            {isPrompting ? "Loading…" : "Get summary"}
          </button>
        </form>
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
          font-weight: 600;
          outline: 0 solid var(--highlight50);
          padding: 4px 8px;
          width: 100%;
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
        .ai-assistant > button {
          align-self: center;
        }
        .actions {
          display: flex;
          gap: 4px;
          justify-content: center;
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
        .input {
          display: flex;
          gap: 4px;
        }
        .input input {
          flex-grow: 1;
        }
      `}</style>
    </div>
  );
};
