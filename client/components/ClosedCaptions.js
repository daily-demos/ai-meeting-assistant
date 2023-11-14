import { useDailyEvent, useTranscription } from "@daily-co/daily-react";
import classNames from "classnames";
import { useCallback, useState } from "react";

export const ClosedCaptions = () => {
  const [captions, setCaptions] = useState([]);

  const [hasSidebar, setHasSidebar] = useState(false);

  const { isTranscribing } = useTranscription({
    onTranscriptionAppData: useCallback((ev) => {
      setCaptions((c) => [...c, ev.data.text]);
      setTimeout(() => {
        setCaptions((c) => c.slice(1));
      }, 5000);
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
      setCaptions([]);
    }, []),
  );

  if (!isTranscribing) return null;

  return (
    <div
      className={classNames("closed-captions", {
        sidebar: hasSidebar,
      })}
    >
      <span className="text">
        {captions.map((text, i) => (
          <>
            {i > 0 && <br />}
            <span>{text}</span>
          </>
        ))}
      </span>
      <style jsx>{`
        .closed-captions {
          background: rgba(0, 0, 0, 0.5);
          bottom: 100px;
          color: #fff;
          display: inline;
          font-size: 20px;
          left: 50%;
          line-height: 24px;
          padding: 4px;
          pointer-events: none;
          position: absolute;
          transform: translateX(-50%);
          max-width: 100%;
        }
        .closed-captions.sidebar {
          left: calc(50% - 160px);
          max-width: calc(100% - 320px);
        }
      `}</style>
    </div>
  );
};
