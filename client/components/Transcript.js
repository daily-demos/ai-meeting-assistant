import React, {
  Fragment,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { GlobalStyles } from "./GlobalStyles";
import { useTranscription } from "@daily-co/daily-react";
import {
  useDaily,
  useDailyEvent,
} from "@daily-co/daily-react";
import { CopyContentButton } from "./CopyContentButton";
import { SaveFileButton } from "./SaveContentButton";

const REFRESH_INTERVAL = 30000;

export const Transcript = ({ roomUrl }) => {
  const daily = useDaily();
  const unhandledLines = useRef(0);
  const [transcript, setTranscript] = useState("");

  const [transcriptHeight, setTranscriptHeight] = useState(0);
  const transcriptRef = useRef(null);

  useDailyEvent(
    "app-message",
    useCallback((ev) => {
      const data = ev?.data;
      if (data?.kind !== "ai-transcript") return;
      setTranscript(data.data);
    }, []),
  );

  useTranscription({
    onTranscriptionAppData: useCallback(() => {
      unhandledLines.current++;
    }, []),
  });

  const requestTranscript = () => {
    unhandledLines.current = 0;
    daily.sendAppMessage({
      "kind": "assist",
      "task": "transcript",
    }, "*");
  };
  useEffect(() => {
    daily?.on("transcription-error", (ev) => {
      console.error("Transcription failed. Attempting to restart", ev)
      const lp = daily.participants().local;
      if (lp.owner) {
        daily.startTranscription();
      }
    })
    // Wait for a single participant joined event
    // to request transcript the first time local user joins.
    // Using this instead of joined-meeting to account for
    // app-message availability fluctuations between join times.
    daily?.once("participant-joined", () => {
      requestTranscript()
    })
    
    const handleUnhandledTranscript = async () => {
      if (unhandledLines.current === 0) return;
      requestTranscript();
    };
    const interval = setInterval(handleUnhandledTranscript, REFRESH_INTERVAL);
    return () => {
      clearInterval(interval);
    };
  }, [daily]);

  useLayoutEffect(() => {
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        setTranscriptHeight(entry.target.scrollHeight);
      }
    });
  
    if (transcriptRef.current) {
      observer.observe(transcriptRef.current);
    }
  
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current?.scrollHeight,
      behavior: "smooth",
    });
  }, [transcriptHeight]);

  return (
    <div className="transcript" ref={transcriptRef}>
      <h3>Transcript</h3>
      {transcript
        ? transcript.split("\n").map((line, i) => (
            <Fragment key={`transcript-${i}`}>
              {i > 0 && <br />}
              {line}
            </Fragment>
          ))
        : "No transcript available."}
      <p style={{
        display: "flex",
        flexDirection: "row",
      }}>
        <CopyContentButton content={transcript} />
        <SaveFileButton content={transcript} filePrefix="transcript" />
      </p>
      <GlobalStyles />
      <style jsx>{`
        .transcript {
          max-height: 100%;
          overflow-x: hidden;
          overflow-y: scroll;
          padding: 8px;
        }
      `}</style>
    </div>
  );
};
