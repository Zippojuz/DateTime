"""Flask application entry point.

The backend is server-authoritative (see PLAN.md -> Architecture Decisions):
all game state and rules live here; the React frontend is a thin view.
"""

import config
from db import init_db
from flask import Flask, jsonify, request
from flask_cors import CORS
from game import data, dialogue, encounters, preferences, save, social, world
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

    @app.get("/api/topics")
    def topics():
        return jsonify(data.load("topics"))

    @app.get("/api/districts")
    def districts():
        return jsonify(data.load("districts"))

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
        save_id, player, clock = models
        day = _day_index(clock)
        rels = social.all_relationships(save_id, day)
        result = []
        for cid, npc in NPC.load_all().items():
            rel = rels.get(cid, {})
            known = set(rel.get("known_npc_topics", []))
            payload = npc.to_dict()
            # Redact undiscovered preferences — you only see what you've learned.
            payload["preferences"] = {
                t: pref for t, pref in payload["preferences"].items() if t in known
            }
            avail = world.availability(npc, clock)
            result.append(
                {
                    **payload,
                    "availability": avail,
                    # Reachable only if available AND in your current district.
                    "reachable": avail["available"] and avail.get("district") == player.location,
                    "affection": rel.get("affection", 0),
                    "talked_today": rel.get("last_talked_day") == day,
                }
            )
        return jsonify(result)

    @app.post("/api/travel")
    def travel():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            world.travel(player, clock, body.get("to"), body.get("mode", "walk"))
        except GameError as err:
            return jsonify(error=str(err)), 400

        day = _day_index(clock)
        rels = social.all_relationships(save_id, day)
        met_ids = {cid for cid, rel in rels.items() if rel.get("last_talked_day", 0) > 0}
        present = {
            cid: npc.name
            for cid, npc in NPC.load_all().items()
            if (a := world.availability(npc, clock))["available"]
            and a.get("district") == player.location
        }
        encounter = encounters.roll_encounter(present, met_ids)
        if encounter and encounter.get("affection"):
            social.add_opinion(save_id, encounter["npc_id"], encounter["affection"], day)

        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "encounter": encounter})

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
        if avail.get("district") != player.location:
            districts = data.load("districts")
            where = districts.get(avail.get("district"), {}).get("name", "another district")
            return jsonify(error=f"You need to be in {where} to reach {npc.name}."), 400
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
                "affection": social.get_affection(save_id, npc.id, _day_index(clock)),
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
        day = _day_index(clock)
        try:
            next_id, choice = dialogue.resolve_choice(
                tree, body.get("node_id"), body.get("choice_index"), player
            )
        except GameError as err:
            return jsonify(error=str(err)), 400

        before = social.get_affection(save_id, npc.id, day)

        # Base affection from the choice, scaled by how late you arrived.
        base = round(choice.get("affection", 0) * world.TIER_MULTIPLIER.get(tier, 0))
        if base:
            social.add_opinion(save_id, npc.id, base, day)

        # Compatibility: the NPC learns the player's stance and reacts (asymmetric).
        topic = choice.get("express")
        if topic:
            social.reveal_player_topic(save_id, npc.id, topic)
            comp = preferences.compatibility_delta(
                preferences.sentiment_of(npc.preferences, topic),
                preferences.sentiment_of(player.preferences, topic),
            )
            if comp:
                social.add_opinion(save_id, npc.id, comp, day)

        # Discovery: the player learns the NPC's stance on a topic.
        if choice.get("reveal_npc"):
            social.discover_npc_topic(save_id, npc.id, choice["reveal_npc"])

        # An offence: amplified when the bond is weak, decays by severity.
        offense = choice.get("offense")
        if offense:
            social.record_offense(
                save_id, npc.id, offense.get("delta", 0), day, offense.get("severity", "minor")
            )

        after = social.get_affection(save_id, npc.id, day)
        payload = {"ended": next_id is None, "gained": after - before, "affection": after}
        if next_id is not None:
            payload["node"] = dialogue.node_view(tree, next_id, player)
        return jsonify(payload)

    return app


# Exposed for tests / reference.
STARTING_SPECIES = DEFAULT_SPECIES

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host=config.HOST, port=config.PORT)
