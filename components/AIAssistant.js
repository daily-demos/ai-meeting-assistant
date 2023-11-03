import { useDailyEvent, useTranscription } from "@daily-co/daily-react";
import classNames from "classnames";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactTimeago from "react-timeago";

const summarizeChunkSize = 10;

const getStructuredContext = (items) =>
  items
    .map((item) =>
      item.is_summary
        ? `[summary] ${item.text}`
        : `[${item.user_name}|${item.timestamp}] ${item.text}`,
    )
    .join("\n");

export const AIAssistant = () => {
  /**
   * Holds conversation context. Initially it will hold raw transcriptions, as returned from Deepgram.
   * Over time multiple entries will be merged into summaries.
   */
  const [context, setContext] = useState([]);
  /**
   * Holds messages from chatting with LLM.
   */
  const [chatHistory, setChatHistory] = useState([]);

  const inputRef = useRef(null);

  /**
   * In case a user has no username, we'll reference them as "Speaker 1", "Speaker 2", etc.
   * This array holds session ids for all participants that have been transcribed.
   * This way we can easily get the speaker number with speakerMap.current.indexOf(sessionId).
   * The first null element makes sure we don't have "Speaker 0".
   */
  const speakers = useRef([null]);
  const { isTranscribing, startTranscription, stopTranscription } =
    useTranscription({
      onTranscriptionAppData: useCallback((ev) => {
        if (!ev.data.is_final) return;
        if (!speakers.current.includes(ev.data.session_id))
          speakers.current.push(ev.data.session_id);
        setContext((prev) => [
          ...prev,
          {
            text: ev.data.text,
            timestamp: ev.data.timestamp,
            user_name:
              ev.data.user_name ||
              `Speaker ${speakers.current.indexOf(ev.data.session_id)}`,
            is_summary: false,
          },
        ]);
      }),
    });

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
    const response = await fetch("/api/ask-ai", {
      method: "POST",
      body: JSON.stringify({
        context: getStructuredContext(context),
        query,
      }),
    });
    const body = await response.json();
    if (response.ok) {
      setChatHistory((prev) => [
        ...prev,
        {
          ...body.choices[0].message,
          date: new Date(),
        },
      ]);
    }
  };

  const isSummarizing = useRef(false);
  const summarize = useCallback(async (ctx) => {
    isSummarizing.current = true;

    try {
      const response = await fetch("/api/summarize", {
        method: "POST",
        body: JSON.stringify({
          context: getStructuredContext(ctx),
        }),
      });

      const body = await response.json();

      if (response.ok) {
        setContext((prev) => {
          const newPrev = prev.slice();
          newPrev.splice(0, summarizeChunkSize, {
            text: body.choices[0].message.content,
            is_summary: true,
          });
          return newPrev;
        });
      }
    } finally {
      isSummarizing.current = false;
    }
  }, []);

  useEffect(() => {
    if (context.length < summarizeChunkSize || isSummarizing.current) return;
    summarize(context);
  }, [context, summarize]);

  useDailyEvent(
    "left-meeting",
    useCallback(() => {
      stopTranscription();
    }, [context, stopTranscription]),
  );

  const chatRef = useRef(null);

  useEffect(() => {
    chatRef.current?.scrollTo({
      top: chatRef.current?.scrollHeight,
      behavior: "smooth",
    });
  }, [chatHistory]);

  return (
    <div
      className={classNames("ai-assistant", {
        active: isTranscribing,
      })}
    >
      <div className="actions">
        {isTranscribing ? (
          <button onClick={() => stopTranscription()}>
            ⏹️ Stop transcription
          </button>
        ) : (
          <button onClick={() => startTranscription()}>
            ⏺️ Start transcription
          </button>
        )}
        {chatHistory.length > 0 && (
          <button onClick={() => setChatHistory([])}>💨 Clear chat</button>
        )}
        {context.length > 0 && (
          <button onClick={() => setContext([])}>
            ⚠️ Clear context ({context.length})
          </button>
        )}
      </div>
      {(isTranscribing || chatHistory.length > 0 || context.length > 0) && (
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
      )}
      <style jsx>{`
        .ai-assistant {
          align-self: stretch;
          flex-grow: 1;
          width: 40%;

          align-items: center;
          display: flex;
          flex-direction: column;
          gap: 8px;
          justify-content: center;
        }
        .ai-assistant.active {
          align-items: stretch;
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
