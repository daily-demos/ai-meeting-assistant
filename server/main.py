"""This module defines all the routes for the Daily AI assistant server."""
import json
import sys
import threading
import traceback
from os.path import join, dirname, abspath

from quart.cli import load_dotenv
from quart_cors import cors
from quart import Quart, jsonify, Response, request

from server.config import BotConfig
from server.call.operator import Operator
from server.llm.openai_assistant import probe_api_key

dotenv_path = join(dirname(dirname(abspath(__file__))), '.env')
load_dotenv(dotenv_path)
app = Quart(__name__)

print("Running AI assistant server")

# Note that this is not a secure CORS configuration for production.
cors(app, allow_origin="*", allow_headers=["content-type"])
operator = Operator()


@app.after_serving
async def shutdown():
    """Stop all background tasks and cancel Futures"""
    operator.shutdown()
    for task in app.background_tasks:
        task.cancel()


@app.route('/', methods=['GET'])
async def index():
    """Just an empty index file"""
    return {}, 200


@app.route('/session', methods=['POST'])
async def create_session():
    """Creates a session, which includes creating a Daily room
    and returning its URL to the caller."""

    err_msg = "Room URL and OpenAI API key must be provided"

    raw = await request.get_data()
    data = json.loads(raw or 'null')

    if not data:
        return process_error(err_msg, 400)

    # Room URL and OpenAI API Key are required parameters
    room_url = data.get("room_url")
    openai_api_key = data.get("openai_api_key")
    if not room_url or not openai_api_key:
        return process_error(err_msg, 400)

    if await probe_api_key(openai_api_key) is False:
        return process_error("Invalid OpenAI API key", 401)

    openai_model_name = data.get("openai_model_name")
    meeting_token = data.get("meeting_token")

    c = BotConfig(openai_api_key, openai_model_name, room_url, meeting_token)
    session = operator.create_session(c)
    if session:
        app.add_background_task(session.start)
    return jsonify({
        "room_url": room_url
    }), 200


def process_error(msg: str, code=500, error: Exception = None,
                  ) -> tuple[Response, int]:
    """Prints provided error and returns appropriately-formatted response."""
    if error:
        traceback.print_exc()
        print(msg, error, file=sys.stderr)
    response = {'error': msg}
    return jsonify(response), code


if __name__ == '__main__':
    app.run(debug=True)
