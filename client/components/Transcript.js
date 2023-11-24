import React, { Fragment, useEffect, useRef, useState } from "react";
import { fetchTranscript } from "../utils/api";
import { GlobalStyles } from "./GlobalStyles";

const REFRESH_INTERVAL = 30000;

export const Transcript = ({ roomUrl }) => {
  const [transcript, setTranscript] = useState("");

  const isScrolledDown = useRef(true);
  const transcriptRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetchTranscript(roomUrl);
        isScrolledDown.current =
          transcriptRef.current.scrollTop >=
          transcriptRef.current.scrollHeight -
            transcriptRef.current.clientHeight;
        setTranscript(response);
      } catch {
        // Failed to fetch transcript
      }
    }, REFRESH_INTERVAL);
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
          overflow-x: hidden;
          overflow-y: auto;
          padding: 8px;
        }
      `}</style>
    </div>
  );
};
