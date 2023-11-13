# Daily AI Meeting Assistant Demo

This demo shows how to build and run an AI meeting assistant based on Daily's transcription API alongside an embedded Prebuilt call.

## Technical concept

At the core the [AIAssistant component](client/components/AIAssistant.js) subscribes to [transcription events](https://docs.daily.co/reference/daily-js/events/transcription-events) to build the conversational context of the meeting.

Once N transcription lines have been collected, they'll be automatically summarized with the help of OpenAI's gpt-3.5-turbo model and replaced with the summary.
In the meantime transcription lines are continuously collected and added to the context. When N transcription lines are collected again, the original summary will be extended with the information gathered from the last N transcription lines.

With this approach it's possible to handle meetings independent of their duration while keeping token usage for OpenAI's API low.

## Demo

➡️ [Deployed demo]()

## Getting started

- Copy the `.env.example` file to `.env.local` and add your API tokens for Daily, Deepgram and OpenAI
- Install dependencies with `yarn install`
- Start the dev server with `yarn dev`
