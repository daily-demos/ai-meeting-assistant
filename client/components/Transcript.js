import React, {
  Fragment,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { fetchTranscript } from "../utils/api";
import { GlobalStyles } from "./GlobalStyles";
import { useTranscription } from "@daily-co/daily-react";

const REFRESH_INTERVAL = 30000;

export const Transcript = ({ roomUrl }) => {
  const unhandledLines = useRef(0);
  const [transcript, setTranscript] = useState("");

  const isScrolledDown = useRef(true);
  const transcriptRef = useRef(null);

  useTranscription({
    onTranscriptionAppData: useCallback(() => {
      unhandledLines.current++;
    }, []),
  });

  useEffect(() => {
    const handleUnhandledTranscript = async () => {
      if (unhandledLines.current === 0) return;
      try {
        unhandledLines.current = 0;
        const response = await fetchTranscript(roomUrl);
        isScrolledDown.current =
          transcriptRef.current.scrollTop >=
          transcriptRef.current.scrollHeight -
            transcriptRef.current.clientHeight;
        setTranscript(response);
      } catch {
        // Failed to fetch transcript
      }
    };
    const interval = setInterval(handleUnhandledTranscript, REFRESH_INTERVAL);
    return () => {
      clearInterval(interval);
    };
  }, [roomUrl]);

  useEffect(() => {
    if (!isScrolledDown.current) return;
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current?.scrollHeight,
      behavior: "smooth",
    });
  }, [transcript]);

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
      <GlobalStyles />
      <style jsx>{`
        .transcript {
          max-height: 100%;
          overflow-x: hidden;
          overflow-y: auto;
          padding: 8px;
        }
      `}</style>
    </div>
  );
};
