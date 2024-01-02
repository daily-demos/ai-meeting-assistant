import classNames from "classnames";
import React, { useEffect, useRef, useState, useCallback } from "react";
import ReactTimeago from "react-timeago";
import { fetchQuery } from "../utils/api";
import { GlobalStyles } from "./GlobalStyles";
import { DeleteIcon } from "./icons/DeleteIcon";
import { VolumeOnIcon } from "./icons/VolumeOnIcon";
import { VolumeOffIcon } from "./icons/VolumeOffIcon";
import { SummaryIcon } from "./icons/SummaryIcon";
import {
  useDaily,
  useDailyEvent,
} from "@daily-co/daily-react";

const responseErrorText =
  "Uh oh! While I tried to get a response for you, an error occurred! Please try again.";
const summaryErrorText =
  "Uh oh! While I tried to get a summary for you, an error occurred! Please try again.";

const createUserMessage = (message) => ({
  role: "user",
  content: message,
  date: new Date(),
});

const createAssistantMessage = (message) => ({
  role: "assistant",
  content: message,
  date: new Date(),
});

export const AIAssistant = ({ roomUrl }) => {
  const daily = useDaily();
  const [summary, setSummary] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);

  const [isPrompting, setIsPrompting] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [playSounds, setPlaySounds] = useState(false);

  const inputRef = useRef(null);
  const chatRef = useRef(null);

  const audioMsgRef = useRef(null);
  const audioErrorRef = useRef(null);

  useDailyEvent(
    "app-message",
    useCallback((ev) => {
      const data = ev?.data;
      if (data?.kind === "ai-summary") {
        setSummary(data.data);
        setIsSummarizing(false);
        return;
      }
      if (data?.kind === "ai-query") {
        setChatHistory((prev) => [...prev, createAssistantMessage(data.data)]);
        setIsPrompting(false);
        return;
      }
    }, []),
  );

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
    setChatHistory((prev) => [...prev, createUserMessage(query)]);
    try {
      setIsPrompting(true);
      daily.sendAppMessage({
        "kind": "assist",
        "task": "query",
        "query": query,
      }, "*")
      playAudioMsg();
    } catch {
      setChatHistory((prev) => [
        ...prev,
        createAssistantMessage(responseErrorText),
      ]);
      playAudioError();
    } 
  };

  const handleSummaryClick = async () => {
    try {
      setIsSummarizing(true);
      daily.sendAppMessage({
        "kind": "assist",
        "task": "summary",
      }, "*")
      playAudioMsg();
    } catch {
      setSummary(summaryErrorText);
      playAudioError();
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
        <button
          className="summary-btn"
          disabled={isSummarizing}
          type="button"
          onClick={handleSummaryClick}
        >
          <SummaryIcon size={16} />
          <span>{summary ? "Refresh summary" : "Get summary"}</span>
        </button>
        <div className="summary">
          {!!summary && <div className="message answer">{summary}</div>}
        </div>
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
        .wrapper {
          padding: 8px;

          flex-grow: 1;
          min-height: 0;

          display: flex;
          flex-direction: column;
        }
        .summary-btn {
          align-self: flex-start;
          width: auto;
        }
        .summary {
          border-bottom: 1px solid var(--border);
          flex: 1 1 50%;
          overflow-y: auto;
          padding: 8px 0;
        }
        .stream {
          flex: 1 1 50%;
          overflow-y: auto;
          padding: 8px 0;
        }
        .actions {
          display: flex;
          gap: 4px;
          justify-content: space-between;
          margin-top: 8px;
        }
        .actions button img {
          display: block;
        }
        .message {
          border-radius: 4px;
          padding: 8px;
          text-align: left;
          width: auto;
        }
        .message.question {
          border: 1px solid var(--border);
          margin-left: 2rem;
        }
        .message.answer {
          background: var(--highlight50);
          color: #000;
          margin-right: 2rem;
          white-space: pre-wrap;
        }
        .message :global(time) {
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
        .input button {
          flex-shrink: 1;
          width: auto;
        }
      `}</style>
    </div>
  );
};
