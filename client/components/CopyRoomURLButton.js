import { useState } from "react";
import { CopyIcon } from "./icons/CopyIcon";
import { DoneIcon } from "./icons/DoneIcon";

export const CopyRoomURLButton = ({ url }) => {
  const [copied, setCopied] = useState(false);
  const handleCopyURL = () => {
    if (copy(url)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  return (
    <button disabled={copied} onClick={handleCopyURL}>
      {copied ? (
        <>
          <DoneIcon size={16} />
          <span>Copied</span>
        </>
      ) : (
        <>
          <CopyIcon size={16} />
          <span>Copy room URL</span>
        </>
      )}
    </button>
  );
};
