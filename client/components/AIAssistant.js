import classNames from "classnames";
import React, { useEffect, useRef, useState, useCallback } from "react";
import ReactTimeago from "react-timeago";
import { GlobalStyles } from "./GlobalStyles";
import { VolumeOnIcon } from "./icons/VolumeOnIcon";
import { VolumeOffIcon } from "./icons/VolumeOffIcon";
import { SummaryIcon } from "./icons/SummaryIcon";
import { useDaily, useDailyEvent } from "@daily-co/daily-react";

const responseErrorText =
  "Uh oh! While I tried to get a response for you, an error occurred! Please try again.";
const timeoutErrorText = "Ruh roh! We didn't get a response in time!";

const createUserMessage = (message) => ({
  role: "user",
  content: message,
  date: new Date(),
  is_summary: false,
});

const createAssistantMessage = (message, is_summary = false) => ({
  role: "assistant",
  content: message,
  date: new Date(),
  is_summary,
});

export const AIAssistant = () => {
  const daily = useDaily();
  const [chatHistory, setChatHistory] = useState([]);

  const [isPrompting, setIsPrompting] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [playSounds, setPlaySounds] = useState(false);

  const inputRef = useRef(null);
  const chatRef = useRef(null);

  const audioMsgRef = useRef(null);
  const audioErrorRef = useRef(null);

  /**
   * Reset summary button state after 60 seconds, in case no summary was sent from server.
   */
  useEffect(() => {
    if (!isSummarizing) return;
    const timeout = setTimeout(() => {
      setIsSummarizing(false);
      setChatHistory((prev) => [
        ...prev,
        createAssistantMessage(timeoutErrorText),
      ]);
    }, 60000);
    return () => {
      clearTimeout(timeout);
    };
  }, [isSummarizing]);

  /**
   * Reset query button state after 60 seconds, in case no summary was sent from server.
   */
  useEffect(() => {
    if (!isPrompting) return;
    const timeout = setTimeout(() => {
      setIsPrompting(false);
      setChatHistory((prev) => [
        ...prev,
        createAssistantMessage(timeoutErrorText),
      ]);
    }, 60000);
    return () => {
      clearTimeout(timeout);
    };
  }, [isPrompting]);

  useDailyEvent(
    "app-message",
    useCallback((ev) => {
      const data = ev?.data;
      if (!data) return;
      const kind = data.kind;
      const err = data.error;
      if (err) {
        playAudioError();
      }
      const msg = err ?? data.data;
      if (kind === "ai-summary") {
        setChatHistory((prev) => {
          const summaries = prev.filter(
            (m) => m.role === "assistant" && m.is_summary,
          );
          const lastSummary = summaries?.[summaries.length - 1];
          if (!lastSummary) {
            return [...prev, createAssistantMessage(msg, true)];
          }
          if (lastSummary.content === msg) {
            /**
             * Last summary had the same content, so we can simply update the timestamp.
             */
            lastSummary.date = new Date();
          } else {
            /**
             * New summary is different, so we can just append it at the end.
             */
            return [...prev, createAssistantMessage(msg, true)];
          }
          /**
           * Find index of last summary.
           */
          const idx = prev.findIndex(
            (m) =>
              m.role === "assistant" &&
              m.is_summary &&
              m.content === lastSummary.content,
          );
          delete prev[idx];
          return [...prev.filter(Boolean), lastSummary];
        });
        setIsSummarizing(false);
        playAudioMsg();
        return;
      }
      if (kind === "ai-query") {
        setChatHistory((prev) => [...prev, createAssistantMessage(msg)]);
        setIsPrompting(false);
        playAudioMsg();
        return;
      }
    }, []),
  );

  const hasRequestedInitialSummary = useRef(false);
  useDailyEvent(
    "network-connection",
    useCallback((ev) => {
      if (ev.type === "signaling" && ev.event === "connected") {
        if (hasRequestedInitialSummary.current) return;
        hasRequestedInitialSummary.current = true;
        setTimeout(handleSummaryClick, 100)
      }
    }, [daily]),
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
      daily.sendAppMessage(
        {
          kind: "assist",
          task: "query",
          query: query,
        },
        "*",
      );
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
      daily.sendAppMessage(
        {
          kind: "assist",
          task: "summary",
          broadcast: true,
        },
        "*",
      );
    } catch {
      setChatHistory((prev) => [
        ...prev,
        createAssistantMessage(responseErrorText),
      ]);
      playAudioError();
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
                summary: msg.is_summary,
              })}
            >
              <div>
                <strong>{msg.role === "user" ? "You" : "Assistant"}</strong>{" "}
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
                    return nextFormatter(
                      value,
                      unit,
                      suffix,
                      epochMilliseconds,
                    );
                  }}
                />
              </div>
              <div>{msg.content}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex" }}>
          <button
            className="summary-btn"
            disabled={isSummarizing}
            type="button"
            onClick={handleSummaryClick}
          >
            <SummaryIcon size={16} />
            <span>Get summary</span>
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
        .wrapper {
          padding: 8px;

          flex-grow: 1;
          min-height: 0;

          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .summary-btn {
          align-self: flex-start;
          background: var(--summary);
          width: auto;
        }
        .summary-btn:not([disabled]):hover,
        .summary-btn:not([disabled]):focus-visible {
          outline-color: var(--summary50);
        }
        .stream {
          flex: 1 1 50%;
          overflow-y: auto;
        }
        .actions {
          display: flex;
          gap: 4px;
          justify-content: space-between;
        }
        .actions button img {
          display: block;
        }
        .message {
          border-radius: 4px;
          display: flex;
          flex-direction: column;
          gap: 4px;
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
        .message.summary {
          background: var(--summary50);
          border: none;
        }
        .message :global(time) {
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
