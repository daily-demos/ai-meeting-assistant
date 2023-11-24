import TranscriptIcon from "../public/article.svg";
import TranscriptIconDark from "../public/article-dark.svg";
import CCDisabledIcon from "../public/cc-disabled.svg";
import CCDisabledIconDark from "../public/cc-disabled-dark.svg";
import CCIcon from "../public/cc.svg";
import CCIconDark from "../public/cc-dark.svg";
import RobotIcon from "../public/robot.svg";
import RobotIconDark from "../public/robot-dark.svg";

const getIconPath = (icon) => {
  return location.protocol + "//" + location.host + icon.src;
};

export const getEnableCCButton = () => ({
  iconPath: getIconPath(CCDisabledIcon),
  iconPathDarkMode: getIconPath(CCDisabledIconDark),
  label: "Caption",
  tooltip: "Enable closed caption",
});

export const getDisableCCButton = () => ({
  iconPath: getIconPath(CCIcon),
  iconPathDarkMode: getIconPath(CCIconDark),
  label: "Caption",
  tooltip: "Disable closed caption",
});

export const getOpenRobotButton = () => ({
  iconPath: getIconPath(RobotIcon),
  iconPathDarkMode: getIconPath(RobotIconDark),
  label: "AI Assistant",
  tooltip: "Open AI Assistant",
});

export const getCloseRobotButton = () => ({
  iconPath: getIconPath(RobotIcon),
  iconPathDarkMode: getIconPath(RobotIconDark),
  label: "AI Assistant",
  tooltip: "Close AI Assistant",
});

export const getOpenTranscriptButton = () => ({
  iconPath: getIconPath(TranscriptIcon),
  iconPathDarkMode: getIconPath(TranscriptIconDark),
  label: "Transcript",
  tooltip: "Open Transcript",
});

export const getCloseTranscriptButton = () => ({
  iconPath: getIconPath(TranscriptIcon),
  iconPathDarkMode: getIconPath(TranscriptIconDark),
  label: "Transcript",
  tooltip: "Close Transcript",
});
