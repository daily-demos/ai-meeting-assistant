# Daily AI Meeting Assistant Demo

This demo shows how to build and run an AI meeting assistant based on Daily's transcription API alongside an embedded Prebuilt call.

## Demo

➡️ [Deployed demo]()

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

1. Navigate to the client directory: `cd client`
1. Install dependencies with `yarn install`
1. Start the dev server with `yarn dev`

Open the displayed localhost port in your browser.
