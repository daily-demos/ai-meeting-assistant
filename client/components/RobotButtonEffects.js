import {
  useDaily,
  useDailyEvent,
  useMeetingState,
} from "@daily-co/daily-react";
import { useCallback } from "react";
import {
  getCloseRobotButton,
  getOpenRobotButton,
} from "../utils/custom-buttons";

export const robotBtnId = "robot";

export const RobotButtonEffects = () => {
  const daily = useDaily();
  const meetingState = useMeetingState();

  useDailyEvent(
    "sidebar-view-changed",
    useCallback((ev) => {
      if (meetingState !== "joined-meeting") return;
      const buttons = daily.customTrayButtons();
      switch (ev.view) {
        case "assistant":
          buttons[robotBtnId] = getCloseRobotButton();
          break;
        default:
          buttons[robotBtnId] = getOpenRobotButton();
          break;
      }
      daily.updateCustomTrayButtons(buttons);
    }),
  );

  useDailyEvent(
    "custom-button-click",
    useCallback(async (ev) => {
      if (ev.button_id === robotBtnId) {
        const view = await daily.getSidebarView();
        if (view === "assistant") {
          daily.setSidebarView(null);
        } else {
          daily.setSidebarView("assistant");
        }
      }
    }),
  );
};
