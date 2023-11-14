import { useAppMessage } from "@daily-co/daily-react";
import classNames from "classnames";
import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactTimeago from "react-timeago";

const buildPrompt = (question) =>
  `AI adopts role of meeting assistant. Always respond helpful, positive, concise and in clear text. Wrap every response with 🤖. Given the transcript, answer: ${question}`;

export const AIAssistant = () => {
  /**
   * Holds messages from chatting with the bot.
   */
  const [chatHistory, setChatHistory] = useState([]);

  const inputRef = useRef(null);
  const sendAppMessage = useAppMessage({
    onAppMessage: useCallback((ev) => {
      if (ev.data.kind === "assist" && "data" in ev.data) {
        setChatHistory((h) => [
          ...h,
          {
            role: "assistant",
            date: new Date(),
            content: ev.data.data,
          },
        ]);
      }
    }, []),
  });

  const handleAskAISubmit = async (ev) => {
    ev.preventDefault();
    const query = inputRef.current.value.trim();
    // if (!query) return;
    inputRef.current.value = "";
    setChatHistory((prev) => [
      ...prev,
      {
        role: "user",
        content: query,
        date: new Date(),
      },
    ]);
    sendAppMessage(
      {
        kind: "assist",
        query: buildPrompt(query),
      },
      "*",
    );
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
      <div className="actions">
        {chatHistory.length > 0 && (
          <button onClick={() => setChatHistory([])}>💨 Clear chat</button>
        )}
      </div>
      <div className="wrapper">
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
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask AI"
            maxLength={256}
          />
          <button type="submit">Submit</button>
        </form>
      </div>
      <style jsx>{`
        .ai-assistant {
          align-self: stretch;
          flex-grow: 1;
          width: 40%;

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
          border: 1px solid var(--border);
          border-radius: 4px;
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
