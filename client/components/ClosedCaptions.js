import {
  useDaily,
  useDailyEvent,
  useTranscription,
} from "@daily-co/daily-react";
import classNames from "classnames";
import { useCallback, useEffect, useRef, useState } from "react";

import { getDisableCCButton, getEnableCCButton } from "../utils/custom-buttons";

export const enableCCId = "enable-cc";
export const disableCCId = "disable-cc";

const captionTime = 5000;

export const ClosedCaptions = ({ style = {} }) => {
  const daily = useDaily();
  const [enabled, setEnabled] = useState(true);
  const [hasSidebar, setHasSidebar] = useState(false);

  useDailyEvent(
    "custom-button-click",
    useCallback((ev) => {
      switch (ev.button_id) {
        case disableCCId:
          setEnabled(false);
          break;
        case enableCCId:
          setEnabled(true);
          break;
      }
    }, []),
  );

  useEffect(() => {
    if (!daily || daily.isDestroyed()) return;
    const buttons = daily.customTrayButtons();
    delete buttons[enableCCId];
    delete buttons[disableCCId];
    if (enabled) {
      buttons[disableCCId] = getDisableCCButton();
    } else {
      buttons[enableCCId] = getEnableCCButton();
    }
    daily.updateCustomTrayButtons(buttons);
  }, [enabled]);

  const audioRef = useRef(null);
  const containerRef = useRef(null);

  const addCaptionLine = (text) => {
    if (!containerRef.current) return;
    const div = document.createElement("div");
    div.className = "cc-line";
    div.innerText = text;
    containerRef.current.appendChild(div);
    setTimeout(() => {
      div.remove();
      // Remove slightly earlier to avoid element go back to initial CSS state
    }, captionTime - 50);
  };

  const { isTranscribing } = useTranscription({
    onTranscriptionStarted: useCallback(() => {
      if (!audioRef.current) return;
      audioRef.current.play();
    }, []),
    onTranscriptionAppData: useCallback((ev) => {
      addCaptionLine(ev.data.text);
    }, []),
  });

  useDailyEvent(
    "sidebar-view-changed",
    useCallback((ev) => {
      setHasSidebar(ev.view !== null);
    }, []),
  );

  useDailyEvent(
    "left-meeting",
    useCallback(() => {
      if (!containerRef.current) return;
      containerRef.current.innerText = "";
    }, []),
  );

  return (
    <div
      className={classNames("closed-captions", {
        sidebar: hasSidebar,
      })}
      style={style}
    >
      <audio ref={audioRef} src="/transcription-started.mp3" playsInline />
      {isTranscribing && enabled && (
        <div ref={containerRef} className="text"></div>
      )}
      <style jsx>{`
        .closed-captions {
          bottom: 100px;
          font-size: 14px;
          left: 50%;
          line-height: 24px;
          pointer-events: none;
          position: absolute;
          transform: translateX(-50%);
          max-width: 100%;
        }
        .closed-captions.sidebar {
          left: calc(50% - 160px);
          max-width: calc(100% - 320px);
        }
        .closed-captions:empty {
          opacity: 0;
        }
        .text {
          align-items: center;
          display: flex;
          flex-direction: column;
        }
        .closed-captions :global(.cc-line) {
          animation-name: show-cc;
          animation-duration: ${captionTime / 1000}s;
          animation-play-state: running;
          animation-timing-function: ease-in-out;
          animation-iteration-count: 1;
          background: rgba(0, 0, 0, 0.5);
          color: #fff;
          display: block;
          padding: 4px;
          width: auto;
        }
        @keyframes show-cc {
          0% {
            opacity: 0;
            transform: translateY(25%);
          }
          10% {
            opacity: 1;
            transform: translateY(0);
          }
          90% {
            opacity: 1;
            transform: translateY(0);
          }
          100% {
            opacity: 0;
            transform: translateY(-25%);
          }
        }
      `}</style>
    </div>
  );
};
