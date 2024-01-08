import { useState } from "react";
import { CopyIcon } from "./icons/CopyIcon";
import { DoneIcon } from "./icons/DoneIcon";

export const SaveFileButton = ({ content, filePrefix }) => {
  const [saved, setSaved] = useState(false);
  const handleSaveToFile = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = getDownloadFileName(filePrefix);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setSaved(true);
    setTimeout(() => setSaved(false), 3000);

  };

  const getDownloadFileName = (filePrefix) => {
    const date = new Date();
    const dateStr = date.toLocaleDateString();
    return `${filePrefix}-${dateStr}.txt`;
  }

  return (
    <button disabled={saved} onClick={handleSaveToFile} style={{margin: "2px"}}>
      {saved ? (
        <>
          <DoneIcon size={16} />
          <span>Saved</span>
        </>
      ) : (
        <>
          <CopyIcon size={16} />
          <span>Save</span>
        </>
      )}
    </button>
  );
};
