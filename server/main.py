"""This module defines all the routes for the Daily AI assistant server."""
import json
import sys
import traceback

from quart_cors import cors
from quart import Quart, jsonify, Response, request

from server.config import Config
from server.call.operator import Operator

app = Quart(__name__)

print("Running AI assistant server")

# Note that this is not a secure CORS configuration for production.
cors(app, allow_origin="*", allow_headers=["content-type"])
config = Config()
operator = Operator(config)


@app.after_serving
async def shutdown():
    """Stop all background tasks and cancel Futures"""
    operator.shutdown()
    for task in app.background_tasks:
        task.cancel()


@app.route('/session', methods=['POST'])
async def create_session():
    """Creates a session, which includes creating a Daily room
    and returning its URL to the caller."""
    try:
        raw = await request.get_data()
        data = json.loads(raw or 'null')
        room_duration_mins = None
        if data:
            requested_duration_mins = data["room_duration_mins"]
            if requested_duration_mins:
                room_duration_mins = int(requested_duration_mins)

        room_url = operator.create_session(room_duration_mins)

        return jsonify({
            "room_url": room_url
        }), 200
    except Exception as e:
        return process_error('failed to create session', 500, e)


@app.route('/summary', methods=['GET'])
async def summary():
    """Creates and returns a summary of the meeting at the provided room URL."""
    room_url = request.args.get("room_url")
    if not room_url:
        return process_error('room_url query parameter must be provided', 400)
    try:
        summary = operator.query_assistant(room_url)
        print("summary")
        return jsonify({
            "summary": summary
        }), 200
    except Exception as e:
        return process_error('failed to generate meeting summary', 500, e)


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
