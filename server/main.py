"""This module defines all the routes for the Daily AI assistant server."""
import json
import sys
import traceback
from os.path import join, dirname, abspath

from quart.cli import load_dotenv
from quart_cors import cors
from quart import Quart, jsonify, Response, request
from server.call.errors import DailyPermissionException, SessionNotFoundException

from server.config import Config
from server.call.operator import Operator

dotenv_path = join(dirname(dirname(abspath(__file__))), '.env')
load_dotenv(dotenv_path)
app = Quart(__name__)

print("Running AI assistant server")

# Note that this is not a secure CORS configuration for production.
cors(app, allow_origin="*", allow_headers=["content-type"])
config = Config()
config.ensure_dirs()
operator = Operator(config)


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

    err_msg = "Failed to create session"

    try:
        raw = await request.get_data()
        data = json.loads(raw or 'null')
        room_duration_mins = None
        room_url = None
        if data:
            requested_duration_mins = data.get("room_duration_mins")
            if requested_duration_mins:
                room_duration_mins = int(requested_duration_mins)
            provided_room_url = data.get("room_url")
            if provided_room_url:
                room_url = provided_room_url

        room_url = operator.create_session(room_duration_mins, room_url)

        return jsonify({
            "room_url": room_url
        }), 200

    except DailyPermissionException as e:
        return process_error(err_msg, 401, e)
    except Exception as e:
        return process_error(err_msg, 500, e)


@app.route('/summary', methods=['GET'])
async def summary():
    """Creates and returns a summary of the meeting at the provided room URL."""
    room_url = request.args.get("room_url")
    if not room_url:
        return process_error('room_url query parameter must be provided', 400)
    try:
        got_summary = await operator.query_assistant(room_url)
        return jsonify({
            "summary": got_summary
        }), 200
    except SessionNotFoundException as e:
        return process_error(
            'Requested session not found. Has it been destroyed?', 400, e)
    except Exception as e:
        return process_error('failed to generate meeting summary', 500, e)


@app.route('/query', methods=['POST'])
async def query():
    """Runs a query against the session using the provided query string."""

    raw = await request.get_data()
    try:
        data = json.loads(raw or 'null')
    except Exception as e:
        return process_error(
            "Confirm that request body is in valid JSON format", 400, e)

    room_url = None
    requested_query = None
    if data:
        room_url = data.get("room_url")
        requested_query = data.get("query")

    # Both room URl and query are required for this endpoint
    if not room_url or not requested_query:
        return process_error(
            "Request body must contain a 'room_url' and 'query'", 400)

    try:
        res = await operator.query_assistant(room_url, requested_query)
        return jsonify({
            "response": res
        }), 200
    except SessionNotFoundException as e:
        return process_error(
            'Requested session not found. Has it been destroyed?', 400, e)
    except Exception as e:
        return process_error('Failed to query session', 500, e)


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
