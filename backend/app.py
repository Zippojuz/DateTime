"""Flask application entry point.

The backend is server-authoritative (see PLAN.md -> Architecture Decisions):
all game state and rules live here; the React frontend is a thin view.
"""

import config
from db import init_db
from flask import Flask, jsonify, request
from flask_cors import CORS
from game import data, save
from game.actions import ACTIONS, apply_action
from game.errors import GameError
from game.player import DEFAULT_SPECIES, IDENTITY_FIELDS


def create_app():
    app = Flask(__name__)
    CORS(app, origins=[config.FRONTEND_ORIGIN])

    init_db()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", game="nexus-city", api="v0")

    # --- Content (read-only reference data the frontend renders generically) ---

    @app.get("/api/attributes")
    def attributes():
        return jsonify(data.attributes())

    @app.get("/api/actions")
    def actions():
        return jsonify(ACTIONS)

    # --- Game state ---

    @app.post("/api/game/new")
    def new_game():
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            return jsonify(error="Name is required."), 400
        identity = {field: (body.get(field) or "").strip() for field in IDENTITY_FIELDS}
        identity["name"] = name
        if not identity["pronouns"]:
            identity["pronouns"] = "they/them"
        return jsonify(save.create_new_game(identity)), 201

    @app.get("/api/game/state")
    def game_state():
        state = save.get_state()
        if state is None:
            return jsonify(error="No game in progress."), 404
        return jsonify(state)

    @app.post("/api/action")
    def action():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            apply_action(player, clock, body.get("action"), body.get("attribute"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify(save.state_dict(player, clock))

    @app.post("/api/player/transform")
    def transform():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            player.transform(body.get("changes") or {})
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify(save.state_dict(player, clock))

    return app


# Exposed for tests / reference.
STARTING_SPECIES = DEFAULT_SPECIES

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host=config.HOST, port=config.PORT)
