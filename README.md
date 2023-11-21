# Daily AI Meeting Assistant Demo

This demo shows how to build and run an AI meeting assistant based on Daily's transcription API alongside an embedded Prebuilt call.

**Note that the client code in this repository is still a work in progress. A final version of the client will be merged shortly.**

## How it works

The server component uses [Daily's REST API](https://docs.daily.co/reference/rest-api) and [Daily's Python SDK](https://docs.daily.co/reference/daily-python) to create rooms and join them with 
a bot assistant. The assistant joins with an [owner meeting token](https://docs.daily.co/reference/rest-api/meeting-tokens) and begins transcription. 
The server component configures an AI _assistant_ (in this case powered by OpenAI) for each session.
Each incoming transcription line is stored. When the session is queried via an [`"app-message"` event](https://docs.daily.co/reference/daily-js/events/participant-events#app-message) 
or an HTTP endpoint, the server component uses the stored transcription lines to generate a response from the OpenAI assistant.

## Getting started

### Running the server

In the root of the repository on your local machine, run the following commands:

1. `python3 -m venv venv`
1. `source venv/bin/activate`

In the virtual environment, run the following to install requirements and run the server:

1. Copy the `.env.example` file to `.env` and add your API tokens for Daily and OpenAI
1. `pip install -r server/requirements.txt`
1. `quart --app server/main.py --debug run`

### Running the client

In another terminal window, run the following:

1. Navigate to the client directory: `cd client`
1. Install dependencies with `yarn install`
1. Start the dev server with `yarn dev`

Open the displayed localhost port in your browser.

## Production considerations

### Security
Currently, HTTP endpoints used to query a session are not secured. Anybody with a room URL associated with an ongoing
session can query the session. In a production environment, consider adding your own authenticatio layer or using
[Daily's meeting tokens](https://docs.daily.co/reference/rest-api/meeting-tokens) to secure the endpoints.

### Storage layer
All transcription lines are currently stored in memory. In a production environment, consider using a more scalable
storage solution.