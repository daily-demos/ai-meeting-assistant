import {
  useDaily,
  useDailyEvent,
  useMeetingState,
} from "@daily-co/daily-react";
import { useCallback } from "react";
import {
  getCloseRobotButton,
  getCloseTranscriptButton,
  getOpenRobotButton,
  getOpenTranscriptButton,
} from "../utils/custom-buttons";

export const assistantId = "assistant";
export const transcriptId = "transcript";

export const CustomButtonEffects = () => {
  const daily = useDaily();
  const meetingState = useMeetingState();

  useDailyEvent(
    "sidebar-view-changed",
    useCallback((ev) => {
      if (meetingState !== "joined-meeting") return;
      const buttons = daily.customTrayButtons();
      switch (ev.view) {
        case assistantId:
          buttons[assistantId] = getCloseRobotButton();
          buttons[transcriptId] = getOpenTranscriptButton();
          break;
        case transcriptId:
          buttons[assistantId] = getOpenRobotButton();
          buttons[transcriptId] = getCloseTranscriptButton();
          break;
        default:
          buttons[assistantId] = getOpenRobotButton();
          buttons[transcriptId] = getOpenTranscriptButton();
          break;
      }
      daily.updateCustomTrayButtons(buttons);
    }),
  );

  useDailyEvent(
    "custom-button-click",
    useCallback(async (ev) => {
      const view = await daily.getSidebarView();
      switch (ev.button_id) {
        case assistantId:
          daily.setSidebarView(view === assistantId ? null : assistantId);
          break;
        case transcriptId:
          daily.setSidebarView(view === transcriptId ? null : transcriptId);
          break;
      }
    }),
  );
};
