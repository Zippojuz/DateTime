"""Flask application entry point.

The backend is server-authoritative (see PLAN.md -> Architecture Decisions):
all game state and rules live here; the React frontend is a thin view.
"""

import config
from db import init_db
from flask import Flask, jsonify, request
from flask_cors import CORS
from game import data, dialogue, save, social, world
from game.actions import ACTIONS, apply_action
from game.errors import GameError
from game.npc import NPC
from game.player import DEFAULT_SPECIES, IDENTITY_FIELDS


def _day_index(clock):
    """Absolute in-game day number, used to gate one conversation per day."""
    return (clock.week - 1) * 7 + clock.day


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

    # --- Characters, availability, and dialogue (Milestone 2) ---

    @app.get("/api/characters")
    def characters():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, _player, clock = models
        day = _day_index(clock)
        rels = social.all_relationships(save_id)
        result = []
        for cid, npc in NPC.load_all().items():
            rel = rels.get(cid, {})
            result.append(
                {
                    **npc.to_dict(),
                    "availability": world.availability(npc, clock),
                    "affection": rel.get("affection", 0),
                    "talked_today": rel.get("last_talked_day") == day,
                }
            )
        return jsonify(result)

    @app.post("/api/dialogue/start")
    def dialogue_start():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            npc = NPC.load(body.get("npc_id"))
        except KeyError:
            return jsonify(error="No such character."), 404

        avail = world.availability(npc, clock)
        if not avail["available"]:
            return jsonify(error=f"{npc.name} isn't available right now."), 400
        if social.has_talked_today(save_id, npc.id, _day_index(clock)):
            return jsonify(error=f"You've already spent real time with {npc.name} today."), 400

        tree = dialogue.tree_for_npc(npc.id)
        if tree is None:
            return jsonify(error=f"{npc.name} has nothing to say yet."), 404

        # Gate at start so an abandoned conversation still counts for the day.
        social.mark_talked(save_id, npc.id, _day_index(clock))
        return jsonify(
            {
                "npc_id": npc.id,
                "npc_name": npc.name,
                "dialogue_id": tree["id"],
                "tier": avail["tier"],
                "affection": social.get_affection(save_id, npc.id),
                "node": dialogue.node_view(tree, tree["start"], player),
            }
        )

    @app.post("/api/dialogue/choose")
    def dialogue_choose():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            npc = NPC.load(body.get("npc_id"))
        except KeyError:
            return jsonify(error="No such character."), 404

        tree = dialogue.tree_for_npc(npc.id)
        if tree is None:
            return jsonify(error="No dialogue in progress."), 404

        # Clock is paused during dialogue, so the arrival tier is stable.
        tier = world.availability(npc, clock)["tier"]
        try:
            next_id, base_affection = dialogue.resolve_choice(
                tree, body.get("node_id"), body.get("choice_index"), player
            )
        except GameError as err:
            return jsonify(error=str(err)), 400

        gained = round(base_affection * world.TIER_MULTIPLIER.get(tier, 0))
        if gained:
            social.add_affection(save_id, npc.id, gained)

        payload = {
            "ended": next_id is None,
            "gained": gained,
            "affection": social.get_affection(save_id, npc.id),
        }
        if next_id is not None:
            payload["node"] = dialogue.node_view(tree, next_id, player)
        return jsonify(payload)

    return app


# Exposed for tests / reference.
STARTING_SPECIES = DEFAULT_SPECIES

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host=config.HOST, port=config.PORT)
