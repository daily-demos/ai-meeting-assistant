import copy from "copy-to-clipboard";
import { useState } from "react";
import { CopyIcon } from "./icons/CopyIcon";
import { DoneIcon } from "./icons/DoneIcon";

export const CopyContentButton = ({ content, label }) => {
  const [copied, setCopied] = useState(false);

  if (!label) {
    label = "Copy"
  }
  const handleCopyContent = () => {
    if (copy(content)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  return (
    <button disabled={copied} onClick={handleCopyContent} style={{margin: "2px"}}>
      {copied ? (
        <>
          <DoneIcon size={16} />
          <span>Copied</span>
        </>
      ) : (
        <>
          <CopyIcon size={16} />
          <span>{label}</span>
        </>
      )}
    </button>
  );
};
