"""This module defines all the routes for the filler-word removal server."""
import sys
import traceback

from quart_cors import cors
from quart import Quart, jsonify, Response, request

from config import Config
from call.operator import Operator

app = Quart(__name__)


# Note that this is not a secure CORS configuration for production.
cors(app, allow_origin="*", allow_headers=["content-type"])
config = Config()
config.ensure_dirs()
operator = Operator(config)

@app.after_serving
async def shutdown():
    """Stop all background tasks and threads"""
    operator.shutdown()
    for task in app.background_tasks:
        task.cancel()

@app.route('/session', methods=['POST'])
async def create_session():
    """Queries the loaded index"""

    try:
        room_url = operator.create_session()

        return jsonify({
            "room_url": room_url
        }), 200
    except Exception as e:
        return process_error('failed to create session', 500, e)

@app.route('/summarize', methods=['GET'])
async def summarize():
    """Queries the loaded index"""
    room_url = request.args.get("room_url")
    if not room_url:
        return process_error('room_url query parameter must be provided', 400)
    try:
        summary = operator.generate_summary(room_url)
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


app.run()

if __name__ == '__main__':
    app.run(debug=True)
