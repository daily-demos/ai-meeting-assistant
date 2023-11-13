/**
 * This prompt sets up the context for the OpenAI chat completion.
 * The context should contain the structured transcript, optionally with a leading summary of previous parts of the conversation.
 * Make sure to include timestamps, usernames and the actual transcript.
 * It's possible to add non-verbal events, like emoji reactions, screen sharing, etc.
 */
export const setupContextPrompt = (context) =>
  `AI adopts role of virtual meeting assistant and handles meeting transcript to provide meaningful and concise assistance for meeting participants. Always answer short and polite.\nBelow is the context of the meeting thus far:\n\n\`\`\`${context}\`\`\``;

/**
 * This prompt instructs the LLM to write or extend a summary based on the latest transcript.
 * Because the transcript contains square brackets for structuring the content, LLM is instructed to skip square brackets in its own output.
 */
export const summarizePrompt = () =>
  "Write a summary incl. key topics and action items for each participant. Extend existing summary based on the latest transcript. No square brackets in output.";
