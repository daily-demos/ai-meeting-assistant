import CCDisabledIcon from "../public/cc-disabled.svg";
import CCIcon from "../public/cc.svg";
import RobotIcon from "../public/robot.svg";

const getIconPath = (icon) => {
  return location.protocol + "//" + location.host + icon.src;
};

export const getEnableCCButton = () => ({
  iconPath: getIconPath(CCDisabledIcon),
  label: "Caption",
  tooltip: "Enable closed caption",
});

export const getDisableCCButton = () => ({
  iconPath: getIconPath(CCIcon),
  label: "Caption",
  tooltip: "Disable closed caption",
});

export const getOpenRobotButton = () => ({
  iconPath: getIconPath(RobotIcon),
  label: "AI Assistant",
  tooltip: "Open AI Assistant",
});

export const getCloseRobotButton = () => ({
  iconPath: getIconPath(RobotIcon),
  label: "AI Assistant",
  tooltip: "Close AI Assistant",
});
