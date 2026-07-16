"""Flask application entry point.

The backend is server-authoritative (see PLAN.md -> Architecture Decisions):
all game state and rules live here; the React frontend is a thin view.
"""

import random

import config
from db import init_db
from flask import Flask, jsonify, request
from flask_cors import CORS
from game import (
    almanac,
    arena,
    bathhouse,
    combat,
    corps,
    cyberlink,
    data,
    dating,
    dialogue,
    dungeon,
    encounters,
    equipment,
    events,
    fixer,
    gifts,
    inventory,
    jobs,
    places,
    preferences,
    salvage,
    save,
    shop,
    social,
    stacks,
    teahouse,
    traits,
    world,
)
from game.actions import ACTIONS, apply_action
from game.errors import GameError
from game.npc import NPC
from game.player import DEFAULT_SPECIES, IDENTITY_FIELDS


def _day_index(clock):
    """Absolute in-game day number, used to gate one conversation per day."""
    return (clock.week - 1) * 7 + clock.day


# Growing close to Juno (the ripperdoc) unlocks identity transformation aspects
# — trust first, body work second. See dtDesignDoc.md -> Identity Philosophy.
JUNO_UNLOCKS = {15: "appearance", 25: "pronouns", 40: "body"}


def _grant_juno_unlocks(save_id, player, clock):
    """Sync transformation unlocks with Juno's affection. Returns new grants."""
    affection = social.get_affection(save_id, "juno", _day_index(clock))
    granted = []
    for threshold, aspect in JUNO_UNLOCKS.items():
        if affection >= threshold and aspect not in player.unlocked_transformations:
            player.unlocked_transformations.append(aspect)
            granted.append(aspect)
    return granted


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

    @app.get("/api/venues")
    def venues():
        return jsonify(data.load("venues"))

    @app.get("/api/species")
    def species():
        # Suggestions for character creation — never a gate. Free text is
        # always accepted (see dtDesignDoc.md -> Identity Philosophy).
        return jsonify(data.load("species"))

    @app.get("/api/link/tones")
    def link_tones():
        return jsonify(cyberlink.tones())

    @app.get("/api/protocols")
    def protocols():
        return jsonify(data.load("protocols"))

    @app.get("/api/statuses")
    def statuses():
        return jsonify(data.load("statuses"))

    @app.get("/api/corps")
    def corps_view():
        models = save.load_models()
        week = models[2].week if models else 1
        return jsonify(corps.view(week))

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
        species = (body.get("species") or "").strip() or None
        # Trait: explicit (custom species pick any, or "" for none), otherwise
        # inferred from the species name when it matches the registry.
        if "trait" in body:
            trait = (body.get("trait") or "").strip()
            if trait and traits.get(trait) is None:
                return jsonify(error="Unknown trait."), 400
        else:
            trait = traits.default_for_species(species or DEFAULT_SPECIES)
        state, fired = save.create_new_game(identity, species=species, trait=trait)
        return jsonify({**state, "events": fired}), 201

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
        fired = events.fire_due(player, clock)
        save.save_models(save_id, player, clock)
        # Keep player/clock at top level (backward-compatible), add events.
        return jsonify({**save.state_dict(player, clock), "events": fired})

    @app.post("/api/player/transform")
    def transform():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        # Identity work happens at Juno's table (a place, never an identity gate).
        if player.location != "the_grid":
            return jsonify(error="Identity work happens at Second Skin, in The Grid."), 400
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
        for cid, npc in NPC.load_unlocked(player).items():
            rel = rels.get(cid, {})
            known = set(rel.get("known_npc_topics", []))
            payload = npc.to_dict()
            # Redact undiscovered preferences — you only see what you've learned.
            payload["preferences"] = {
                t: pref for t, pref in payload["preferences"].items() if t in known
            }
            avail = world.availability(npc, clock)
            affection = rel.get("affection", 0)
            result.append(
                {
                    **payload,
                    "availability": avail,
                    # Reachable only if available AND in your current district.
                    "reachable": avail["available"] and avail.get("district") == player.location,
                    "affection": affection,
                    "stage": social.stage(affection),
                    "talked_today": rel.get("last_talked_day") == day,
                    # Cyberlink: contacts need a real handshake (one conversation).
                    "met": bool(rel.get("last_talked_day")),
                    "messaged_today": rel.get("last_message_day") == day,
                    "dated_this_week": rel.get("last_date_week") == clock.week,
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
        from_district = places.district_of(player.location)
        try:
            world.travel(player, clock, body.get("to"), body.get("mode", "walk"))
        except GameError as err:
            return jsonify(error=str(err)), 400

        day = _day_index(clock)
        # Street encounters happen crossing the city, not stepping through a
        # doorway — local hops are free and instant, so they roll nothing.
        encounter = None
        if places.district_of(player.location) != from_district:
            rels = social.all_relationships(save_id, day)
            met_ids = {cid for cid, rel in rels.items() if rel.get("last_talked_day", 0) > 0}
            present = {
                cid: npc.name
                for cid, npc in NPC.load_unlocked(player).items()
                if (a := world.availability(npc, clock))["available"]
                and a.get("district") == player.location
            }
            encounter = encounters.roll_encounter(
                present, met_ids, luck=player.attributes.get("luck", 0), week=clock.week
            )
            if encounter and encounter.get("affection"):
                social.add_opinion(save_id, encounter["npc_id"], encounter["affection"], day)

        fired = events.fire_due(player, clock)
        save.save_models(save_id, player, clock)
        return jsonify(
            {"state": save.state_dict(player, clock), "encounter": encounter, "events": fired}
        )

    # --- Jobs, debt, and events (Milestone 4) ---

    @app.get("/api/jobs")
    def jobs_list():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, _clock = models
        return jsonify(
            [
                {**job, "reachable": job["district"] == player.location}
                for job in jobs.all_jobs().values()
            ]
        )

    @app.post("/api/job")
    def work_job():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = jobs.work(player, clock, body.get("job_id"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        fired = events.fire_due(player, clock)
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "result": result, "events": fired})

    @app.post("/api/debt/pay")
    def pay_debt():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            amount = int(body.get("amount", 0))
        except (TypeError, ValueError):
            return jsonify(error="Enter a valid amount."), 400
        paid = min(amount, player.credits, player.debt)
        if paid <= 0:
            return jsonify(error="Nothing to pay, or not enough credits."), 400
        player.credits -= paid
        player.debt -= paid
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "paid": paid})

    # --- Mama Vex's gigs (the fixer economy) ---

    @app.get("/api/gigs")
    def gigs_today():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        day = _day_index(clock)
        gig = fixer.today_gig(day)
        vex_avail = world.availability(NPC.load("vex"), clock)
        return jsonify(
            {
                "gig": gig,
                "done_today": player.last_gig_day == day,
                "reachable": (player.location == fixer.GIG_DISTRICT and vex_avail["available"]),
            }
        )

    @app.post("/api/gig")
    def work_gig():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        day = _day_index(clock)
        if not world.availability(NPC.load("vex"), clock)["available"]:
            return jsonify(error="Vex isn't holding court right now."), 400
        try:
            choice = fixer.run_gig(player, clock, day, body.get("gig_id"), body.get("choice_index"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        # The clean/dirty fork: who hears about it, and how they take it.
        if choice.get("affection"):
            fx = choice["affection"]
            social.add_opinion(save_id, fx["npc"], fx["delta"], day)
        if choice.get("offense"):
            fx = choice["offense"]
            social.record_offense(save_id, fx["npc"], fx["delta"], day, fx["severity"])
        fired = events.fire_due(player, clock)
        save.save_models(save_id, player, clock)
        return jsonify(
            {
                "state": save.state_dict(player, clock),
                "result": {
                    "text": choice["result"],
                    "pay": choice["pay"],
                    "cred_gained": choice.get("cred", 0),
                },
                "events": fired,
            }
        )

    # --- Items, shop, and gifting (Milestone 6) ---

    @app.get("/api/items")
    def items_list():
        return jsonify(data.load("items"))

    @app.get("/api/shop")
    def shop_stock():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, clock = models
        shops = data.load("shops")
        here = shops.get(player.location)
        discount = traits.effect(player, "shop_discount", 0.0)
        day = _day_index(clock)
        return jsonify(
            {
                "district": player.location,
                "name": here["name"] if here else None,
                "blurb": here.get("blurb") if here else None,
                "stock": shop.stock(player.location, discount=discount, day=day),
                "tiers": shop.tiers(player.location, player.street_cred, discount=discount),
                "street_cred": player.street_cred,
                # The Night Market talks: once a night, a vendor drops a hint.
                "gossip_available": (
                    player.location == "night_market"
                    and places.is_open("night_market", clock)
                    and player.gossip_day != day
                ),
            }
        )

    @app.post("/api/shop/buy")
    def shop_buy():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = shop.buy(player, clock, body.get("item_id"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        fired = events.fire_due(player, clock)
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "bought": result, "events": fired})

    @app.post("/api/message")
    def send_link_message():
        """Ping a known contact over the Cyberlink — anywhere, any hour."""
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        npc_id = body.get("npc_id")
        try:
            npc = NPC.load(npc_id)
        except KeyError:
            return jsonify(error="No such character."), 404
        if not npc.unlocked_for(player):
            return jsonify(error="No such character."), 404
        try:
            result = cyberlink.send_message(
                save_id, player, clock, npc_id, body.get("tone"), _day_index(clock)
            )
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "message": result})

    @app.post("/api/market/gossip")
    def market_gossip():
        """Ask around the Night Market: once a night, a vendor hints at one
        cast member's undiscovered preference. A rumor, not a fact — nothing
        is marked discovered; the night just points you somewhere."""
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        if player.location != "night_market":
            return jsonify(error="Gossip flows where the broth does — find the Night Market."), 400
        if not places.is_open("night_market", clock):
            return jsonify(error=data.load("venues")["night_market"]["closed_line"]), 400
        day = _day_index(clock)
        if player.gossip_day == day:
            return jsonify(error="The vendors have told you all they'll tell you tonight."), 400

        rels = social.all_relationships(save_id, day)
        candidates = []
        for cid, npc in sorted(NPC.load_unlocked(player).items()):
            known = set(rels.get(cid, {}).get("known_npc_topics", []))
            for topic in sorted(npc.preferences):
                if topic not in known:
                    sentiment = preferences.sentiment_of(npc.preferences, topic)
                    candidates.append((npc.name, topic, sentiment))
        if not candidates:
            return jsonify(
                {
                    "text": (
                        "Tonight the stalls only talk about the weather. "
                        "You know everyone too well."
                    )
                }
            )

        rng = random.Random(f"gossip:{day}")
        name, topic, sentiment = rng.choice(candidates)
        topic_name = data.load("topics").get(topic, {}).get("name", topic)
        leaning = "soft on" if sentiment in ("love", "like") else "sour on"
        text = (
            f"The broth vendor leans in, conspiratorial over the steam: "
            f"“{name}? Word around the stalls is they're {leaning} {topic_name.lower()}. "
            f"You didn't hear it from me.”"
        )
        player.gossip_day = day
        clock.advance(15)
        save.save_models(save_id, player, clock)
        return jsonify(
            {
                "npc": name,
                "topic": topic_name,
                "text": text,
                "state": save.state_dict(player, clock),
            }
        )

    # --- Gantry 9: tea service + the Lookout ---

    @app.get("/api/teahouse")
    def teahouse_state():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, clock = models
        cfg = data.load("teahouse")
        tea = teahouse.active(player, clock)
        return jsonify(
            {
                "venue": cfg["venue"],
                "minutes": cfg["minutes"],
                "energy": cfg["energy"],
                "menu": cfg["menu"],
                "active": {"id": player.tea_id, **tea} if tea else None,
                "sipped_today": player.tea_day == _day_index(clock),
            }
        )

    @app.post("/api/teahouse/sip")
    def teahouse_sip():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            poured = teahouse.sip(player, clock, body.get("tea_id"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"poured": poured, "state": save.state_dict(player, clock)})

    # --- The Steeps: the paid soak + THE DATING SYSTEM ---

    @app.post("/api/soak")
    def soak():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = bathhouse.soak(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"soak": result, "state": save.state_dict(player, clock)})

    @app.get("/api/date/venues")
    def date_venues():
        """Where the city dates: scene metadata without the scenes."""
        return jsonify(
            {
                vid: {k: s[k] for k in ("venue", "title", "cost", "minutes", "energy")}
                for vid, s in dating.scenes().items()
            }
        )

    @app.post("/api/date/start")
    def date_start():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            beat = dating.start(
                save_id,
                player,
                clock,
                body.get("npc_id"),
                body.get("venue"),
                _day_index(clock),
                clock.week,
            )
        except KeyError:
            return jsonify(error="No such person."), 404
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"date": beat, "state": save.state_dict(player, clock)})

    @app.post("/api/date/choose")
    def date_choose():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            beat = dating.choose(
                save_id, player, clock, body.get("choice_index"), _day_index(clock), clock.week
            )
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"date": beat, "state": save.state_dict(player, clock)})

    @app.post("/api/date/leave")
    def date_leave():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = dating.leave(save_id, player, clock, clock.week)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"date": result, "state": save.state_dict(player, clock)})

    # --- The Tide Line: salvage runs at slack water ---

    @app.post("/api/salvage")
    def salvage_run():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = salvage.run(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"salvage": result, "state": save.state_dict(player, clock)})

    # --- The Stacks: the research desk ---

    @app.get("/api/stacks")
    def stacks_state():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, clock = models
        cfg = data.load("stacks")
        return jsonify(
            {
                "venue": cfg["venue"],
                "minutes": cfg["research"]["minutes"],
                "energy": cfg["research"]["energy"],
                "researched_today": player.research_day == _day_index(clock),
                # The draft only files itself once — then you can see them.
                "draft": None if NPC.load("index").unlocked_for(player) else cfg["draft"],
            }
        )

    @app.post("/api/research")
    def research():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = stacks.research(save_id, player, clock, body.get("subject"), _day_index(clock))
        except KeyError:
            return jsonify(error="The archive has no file under that name."), 404
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"research": result, "state": save.state_dict(player, clock)})

    @app.get("/api/lookout")
    def lookout():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, clock = models
        if player.location != "gantry_9":
            return jsonify(
                error="The Lookout board hangs at Gantry 9 — the view doesn't travel."
            ), 400
        return jsonify(almanac.compose(player, clock, _day_index(clock)))

    @app.post("/api/item/use")
    def item_use():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = inventory.use_item(player, body.get("item_id"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "used": result})

    @app.post("/api/gift")
    def gift():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            npc = NPC.load(body.get("npc_id"))
        except KeyError:
            return jsonify(error="No such character."), 404
        if not npc.unlocked_for(player):
            return jsonify(error="No such character."), 404

        avail = world.availability(npc, clock)
        if not (avail["available"] and avail.get("district") == player.location):
            return jsonify(error=f"You need to be with {npc.name} to give a gift."), 400
        day = _day_index(clock)
        if social.has_gifted_today(save_id, npc.id, day):
            return jsonify(error=f"You've already given {npc.name} something today."), 400

        item_id = body.get("item_id")
        try:
            item = inventory.get_item(item_id)
            inventory.remove_item(player, item_id, 1)  # consumes the gift
        except GameError as err:
            return jsonify(error=str(err)), 400

        react = gifts.reaction(item, npc)
        if react["delta"] >= 0:
            social.add_opinion(save_id, npc.id, react["delta"], day)
        else:
            social.record_offense(save_id, npc.id, react["delta"], day, "minor")
        if react["topic"]:
            social.discover_npc_topic(save_id, npc.id, react["topic"])
        social.mark_gifted(save_id, npc.id, day)
        if npc.id == "juno":
            _grant_juno_unlocks(save_id, player, clock)

        save.save_models(save_id, player, clock)
        return jsonify(
            {
                "state": save.state_dict(player, clock),
                "reaction": {**react, "item": item["name"]},
                "affection": social.get_affection(save_id, npc.id, day),
            }
        )

    # --- The Substrate: dungeon + combat (Milestone 5) ---

    def _dungeon_payload(player):
        # Fog-of-war: only what the player has explored ever leaves the server.
        run = None
        if player.dungeon.get("active"):
            run = dungeon.view(player)
            run["active"] = True
            run["pending_event_data"] = (
                data.load("dungeon_events")[run["pending_event"]]
                if run.get("pending_event")
                else None
            )
        return {
            "run": run,
            "combat": dict(player.combat) if player.combat.get("active") else None,
            "stats": combat.player_stats(player),
            "skills": combat.unlocked_skills(player.combat_level),
            "xp_to_next": combat.xp_to_next(player.combat_level),
        }

    @app.get("/api/dungeon/state")
    def dungeon_state():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, _clock = models
        return jsonify(_dungeon_payload(player))

    @app.post("/api/dungeon/enter")
    def dungeon_enter():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            dungeon.enter(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({**_dungeon_payload(player), "state": save.state_dict(player, clock)})

    def _dungeon_action(fn):
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = fn(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify(
            {**_dungeon_payload(player), "result": result, "state": save.state_dict(player, clock)}
        )

    @app.post("/api/dungeon/move")
    def dungeon_move():
        body = request.get_json(silent=True) or {}
        return _dungeon_action(lambda p, c: dungeon.move(p, c, body.get("dir")))

    @app.post("/api/dungeon/search")
    def dungeon_search():
        return _dungeon_action(dungeon.search)

    @app.post("/api/dungeon/interact")
    def dungeon_interact():
        return _dungeon_action(dungeon.interact)

    @app.post("/api/dungeon/curio")
    def dungeon_curio():
        body = request.get_json(silent=True) or {}
        return _dungeon_action(
            lambda p, c: dungeon.curio_act(p, c, body.get("curio_id"), body.get("verb"))
        )

    @app.post("/api/dungeon/protocol")
    def dungeon_protocol():
        body = request.get_json(silent=True) or {}
        return _dungeon_action(lambda p, c: dungeon.cast_protocol(p, c, body.get("protocol_id")))

    @app.post("/api/dungeon/event")
    def dungeon_event():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = dungeon.choose_event(player, body.get("choice_index"))
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify(
            {**_dungeon_payload(player), "result": result, "state": save.state_dict(player, clock)}
        )

    @app.post("/api/dungeon/leave")
    def dungeon_leave():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            result = dungeon.leave(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        # Delving together builds the bond — deeper floors mean more shared danger.
        if result.get("companion"):
            gained = min(6, 2 + result["left_at_floor"] // 2)
            social.add_opinion(save_id, result["companion"], gained, _day_index(clock))
            result["bond"] = gained
        save.save_models(save_id, player, clock)
        return jsonify(
            {**_dungeon_payload(player), "result": result, "state": save.state_dict(player, clock)}
        )

    @app.post("/api/combat/action")
    def combat_action():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        if not player.combat.get("active"):
            return jsonify(error="You're not in a fight."), 400
        try:
            combat.act(
                player,
                player.combat,
                body.get("action"),
                skill_id=body.get("skill_id"),
                item_id=body.get("item_id"),
                protocol_id=body.get("protocol_id"),
            )
        except GameError as err:
            return jsonify(error=str(err)), 400

        outcome = None
        if player.combat.get("over"):
            if player.combat.get("arena"):
                outcome = arena.finish_fight(player)
            else:
                outcome = dungeon.finish_combat(player)
                # Even a rout deepens the bond a little — you went down together.
                if outcome.get("result") == "defeat" and outcome.get("companion"):
                    social.add_opinion(save_id, outcome["companion"], 1, _day_index(clock))
            # A defeated NPC boss surfaces: make sure their relationship row
            # exists (new games pre-seed it; older saves won't have one).
            if outcome.get("unlocked"):
                npc = NPC.load(outcome["unlocked"]["npc"])
                social.ensure_relationship(save_id, npc.id, npc.starting_disposition)
        save.save_models(save_id, player, clock)
        return jsonify(
            {
                **_dungeon_payload(player),
                "outcome": outcome,
                "state": save.state_dict(player, clock),
            }
        )

    # --- The Pit: arena ladder (no XP, no loot — cred and titles) ---

    @app.get("/api/arena")
    def arena_view():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, clock = models
        return jsonify(arena.view(player, clock))

    @app.post("/api/arena/fight")
    def arena_fight():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            bout = arena.start_fight(player, clock)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify(
            {**_dungeon_payload(player), "bout": bout, "state": save.state_dict(player, clock)}
        )

    # --- Party: one dungeon companion at a time ---

    @app.get("/api/party")
    def party_state():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        day = _day_index(clock)
        candidates = []
        for cid, npc in NPC.load_unlocked(player).items():
            spec = npc.companion
            if not spec:
                continue
            affection = social.get_affection(save_id, cid, day)
            # Some companions want more than affection — Ondo won't delve with
            # anyone who hasn't beaten them in the ring.
            event = spec.get("requires_event")
            locked = bool(event) and event not in player.fired_events
            candidates.append(
                {
                    "id": cid,
                    "name": npc.name,
                    "role": spec["role"],
                    "element": spec["element"],
                    "blurb": spec.get("locked_blurb", "") if locked else spec.get("blurb", ""),
                    "affection": affection,
                    "locked": locked,
                    "recruitable": not locked and affection >= dungeon.RECRUIT_AFFECTION,
                }
            )
        return jsonify(
            {
                "companion": player.companion or None,
                "required_affection": dungeon.RECRUIT_AFFECTION,
                "candidates": candidates,
            }
        )

    @app.post("/api/party/recruit")
    def party_recruit():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            npc = NPC.load(body.get("npc_id"))
        except KeyError:
            return jsonify(error="No such character."), 404
        if not npc.unlocked_for(player):
            return jsonify(error="No such character."), 404
        if not npc.companion:
            return jsonify(error=f"{npc.name} won't delve."), 400
        event = npc.companion.get("requires_event")
        if event and event not in player.fired_events:
            reason = npc.companion.get("locked_blurb", f"{npc.name} isn't ready to follow you.")
            return jsonify(error=reason), 400
        if player.dungeon.get("active"):
            return jsonify(error="You can't change your party inside the Substrate."), 400
        affection = social.get_affection(save_id, npc.id, _day_index(clock))
        if affection < dungeon.RECRUIT_AFFECTION:
            return (
                jsonify(error=f"{npc.name} doesn't trust you enough to follow you down there."),
                400,
            )
        player.companion = npc.id
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "companion": npc.id})

    @app.post("/api/party/dismiss")
    def party_dismiss():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        if player.dungeon.get("active"):
            return jsonify(error="You can't change your party inside the Substrate."), 400
        player.companion = ""
        save.save_models(save_id, player, clock)
        return jsonify({"state": save.state_dict(player, clock), "companion": None})

    # --- Equipment & gems ---

    def _equipment_payload(player):
        return {
            "slots": {k: dict(v) for k, v in player.equipment.items()},
            "slot_order": list(equipment.SLOTS),
            "bonuses": equipment.bonuses(player),
            "stats": combat.player_stats(player),
            "augments": {
                "installed": equipment.augments_installed(player),
                "capacity": equipment.augment_capacity(player),
            },
        }

    @app.get("/api/equipment")
    def equipment_state():
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        _, player, _clock = models
        return jsonify(_equipment_payload(player))

    def _equipment_action(fn):
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        try:
            fn(player)
        except GameError as err:
            return jsonify(error=str(err)), 400
        save.save_models(save_id, player, clock)
        return jsonify({**_equipment_payload(player), "state": save.state_dict(player, clock)})

    @app.post("/api/equipment/equip")
    def equipment_equip():
        body = request.get_json(silent=True) or {}
        return _equipment_action(
            lambda p: equipment.equip(p, body.get("item_id"), body.get("slot"))
        )

    @app.post("/api/equipment/unequip")
    def equipment_unequip():
        body = request.get_json(silent=True) or {}
        return _equipment_action(lambda p: equipment.unequip(p, body.get("slot")))

    @app.post("/api/equipment/socket")
    def equipment_socket():
        body = request.get_json(silent=True) or {}
        return _equipment_action(
            lambda p: equipment.socket_gem(
                p, body.get("slot"), body.get("gem_id"), body.get("index")
            )
        )

    @app.post("/api/equipment/unsocket")
    def equipment_unsocket():
        body = request.get_json(silent=True) or {}
        return _equipment_action(
            lambda p: equipment.unsocket_gem(p, body.get("slot"), body.get("index"))
        )

    @app.get("/api/difficulty")
    def difficulty_options():
        return jsonify(data.load("difficulty"))

    @app.post("/api/difficulty")
    def set_difficulty():
        body = request.get_json(silent=True) or {}
        models = save.load_models()
        if models is None:
            return jsonify(error="No game in progress."), 404
        save_id, player, clock = models
        level = body.get("level")
        if level not in data.load("difficulty"):
            return jsonify(error="Unknown difficulty."), 400
        player.difficulty = level
        save.save_models(save_id, player, clock)
        return jsonify(save.state_dict(player, clock))

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
        if not npc.unlocked_for(player):
            return jsonify(error="No such character."), 404

        avail = world.availability(npc, clock)
        if not avail["available"]:
            return jsonify(error=f"{npc.name} isn't available right now."), 400
        if avail.get("district") != player.location:
            place = places.get(avail.get("district")) or {}
            where = place.get("name", "another district")
            return jsonify(error=f"You need to be in {where} to reach {npc.name}."), 400
        if social.has_talked_today(save_id, npc.id, _day_index(clock)):
            return jsonify(error=f"You've already spent real time with {npc.name} today."), 400

        affection = social.get_affection(save_id, npc.id, _day_index(clock))
        tree = dialogue.tree_for_npc(npc.id, affection, location=player.location)
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

        # Use the tree the conversation started with (locked via dialogue_id) so
        # crossing an affection threshold mid-conversation can't switch trees.
        tree = dialogue.tree_by_id(body.get("dialogue_id")) or dialogue.tree_for_npc(npc.id)
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
        # The Tell (luminal trait): heartfelt choices glow — and land harder.
        # Petrichor Blend (Gantry 9 tea): same key, steeped instead of innate.
        base = round(choice.get("affection", 0) * world.TIER_MULTIPLIER.get(tier, 0))
        if base > 0:
            base += traits.effect(player, "dialogue_affection_bonus", 0)
            base += teahouse.effect(player, clock, "dialogue_affection_bonus", 0)
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
        # The Tell cuts both ways — everyone can see you mean it.
        offense = choice.get("offense")
        if offense:
            delta = offense.get("delta", 0) - traits.effect(player, "offense_extra", 0)
            social.record_offense(save_id, npc.id, delta, day, offense.get("severity", "minor"))

        after = social.get_affection(save_id, npc.id, day)
        payload = {"ended": next_id is None, "gained": after - before, "affection": after}
        if npc.id == "juno":
            granted = _grant_juno_unlocks(save_id, player, clock)
            if granted:
                save.save_models(save_id, player, clock)
                payload["unlocked_transformations"] = granted
        if next_id is not None:
            payload["node"] = dialogue.node_view(tree, next_id, player)
        return jsonify(payload)

    return app


# Exposed for tests / reference.
STARTING_SPECIES = DEFAULT_SPECIES

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host=config.HOST, port=config.PORT)
