import classNames from "classnames";
import React, { useEffect, useRef, useState } from "react";
import ReactTimeago from "react-timeago";
import { fetchQuery, fetchSummary } from "../utils/api";
import { GlobalStyles } from "./GlobalStyles";
import { DeleteIcon } from "./icons/DeleteIcon";
import { VolumeOnIcon } from "./icons/VolumeOnIcon";
import { VolumeOffIcon } from "./icons/VolumeOffIcon";

export const AIAssistant = ({ roomUrl }) => {
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
            <button onClick={() => setChatHistory([])}>
              <DeleteIcon size={16} />
              <span>Clear chat</span>
            </button>
          )}
          <button
            onClick={() => setPlaySounds((p) => !p)}
            title={playSounds ? "Disable sounds" : "Enable sounds"}
          >
            {playSounds ? (
              <VolumeOnIcon size={16} />
            ) : (
              <VolumeOffIcon size={16} />
            )}
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
              <ReactTimeago
                date={msg.date}
                formatter={(
                  value,
                  unit,
                  suffix,
                  epochMilliseconds,
                  nextFormatter,
                ) => {
                  if (unit === "second") {
                    return value < 30 ? `a moment ago` : `about a minute ago`;
                  }
                  return nextFormatter(value, unit, suffix, epochMilliseconds);
                }}
              />
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
      <GlobalStyles />
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
          background: var(--highlight50);
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
