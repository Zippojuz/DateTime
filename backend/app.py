"""Flask application entry point.

The backend is server-authoritative (see PLAN.md -> Architecture Decisions):
all game state and rules live here; the React frontend is a thin view.

Milestone 0 exposes only a health check. Game routes land in Milestone 1.
"""

from flask import Flask, jsonify
from flask_cors import CORS

import config
from db import init_db


def create_app():
    app = Flask(__name__)
    CORS(app, origins=[config.FRONTEND_ORIGIN])

    init_db()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", game="nexus-city", api="v0")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=config.PORT)
