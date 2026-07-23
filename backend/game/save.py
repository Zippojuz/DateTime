"""Persistence for the single autosave. (Milestone 1)

One save row + one player row. Attributes and identity are stored as JSON blobs
so the schema is stable as attributes grow. Multi-slot saves are deferred
(see PLAN.md).
"""

import json

from db import get_connection

from game import events, social, university
from game.calendar import GameClock
from game.npc import NPC
from game.player import Player


def create_new_game(identity, species=None, trait="", user_id=None):
    """Start a fresh game for one account, replacing only *their* save. Fires
    any events already due (e.g. the day-1 arrival story beat) so they surface
    immediately rather than waiting for the first action. Returns
    (state, fired_events)."""
    player = Player.create(identity, **({"species": species} if species else {}), trait=trait)
    # Pin each randomized study guide to one stat for this playthrough.
    player.book_seeds = university.roll_book_seeds()
    clock = GameClock()
    with get_connection() as conn:
        old = conn.execute("SELECT id FROM save WHERE user_id IS ?", (user_id,)).fetchone()
        if old:
            conn.execute("DELETE FROM player WHERE save_id=?", (old["id"],))
            conn.execute("DELETE FROM save WHERE id=?", (old["id"],))  # cascades
        cur = conn.execute("INSERT INTO save (user_id) VALUES (?)", (user_id,))
        save_id = cur.lastrowid
        _insert_player(conn, save_id, player, clock)
        # Seed each relationship at the NPC's starting disposition (neutral by
        # default), so affection begins neutral rather than empty.
        for cid, npc in NPC.load_all().items():
            social.seed_relationship(conn, save_id, cid, npc.starting_disposition)
    fired = events.fire_due(player, clock)
    save_models(save_id, player, clock)
    return state_dict(player, clock), fired


def load_models(user_id=None):
    """Return (save_id, Player, GameClock) for one account's save, or None.

    With user_id=None, falls back to the *newest* save — engine tests and dev
    scripts run effectively single-user, and the newest save is the one they
    just created; the API always passes the session's user."""
    with get_connection() as conn:
        if user_id is None:
            row = conn.execute("SELECT * FROM player ORDER BY save_id DESC LIMIT 1").fetchone()
        else:
            row = conn.execute(
                """SELECT player.* FROM player
                   JOIN save ON save.id = player.save_id
                   WHERE save.user_id = ?""",
                (user_id,),
            ).fetchone()
    if row is None:
        return None
    player = Player(
        identity=json.loads(row["current_identity"]),
        species=row["species"],
        trait=row["trait"],
        attributes=json.loads(row["attributes"]),
        energy=row["energy"],
        created_identity=json.loads(row["created_identity"]),
        unlocked_transformations=json.loads(row["unlocked_transformations"]),
        preferences=json.loads(row["preferences"]),
        location=row["location"],
        credits=row["credits"],
        debt=row["debt"],
        debt_due_week=row["debt_due_week"],
        fired_events=json.loads(row["fired_events"]),
        inventory=json.loads(row["inventory"]),
        combat_level=row["combat_level"],
        combat_xp=row["combat_xp"],
        difficulty=row["difficulty"],
        max_floor=row["max_floor"],
        dungeon=json.loads(row["dungeon"]),
        combat=json.loads(row["combat"]),
        equipment=json.loads(row["equipment"]),
        companion=row["companion"],
        protocols=json.loads(row["protocols"]),
        last_gig_day=row["last_gig_day"],
        street_cred=row["street_cred"],
        arena_wins=row["arena_wins"],
        gossip_day=row["gossip_day"],
        tea_day=row["tea_day"],
        tea_id=row["tea_id"],
        research_day=row["research_day"],
        date=json.loads(row["date"]),
        pawned=json.loads(row["pawned"]),
        transcript=json.loads(row["transcript"]),
        enrollment=json.loads(row["enrollment"]),
        class_day=row["class_day"],
        browse_day=row["browse_day"],
        book_seeds=json.loads(row["book_seeds"]),
        home=row["home"],
        owned_homes=json.loads(row["owned_homes"]),
        stash=json.loads(row["stash"]),
        rent_paid_week=row["rent_paid_week"],
    )
    clock = GameClock(
        week=row["clock_week"],
        day=row["clock_day"],
        minute_of_day=row["clock_minute"],
    )
    return row["save_id"], player, clock


def get_state(user_id=None):
    """Return one account's state dict, or None if no game is in progress."""
    models = load_models(user_id)
    if models is None:
        return None
    _, player, clock = models
    return state_dict(player, clock)


def save_models(save_id, player, clock):
    with get_connection() as conn:
        conn.execute(
            """UPDATE player SET
                   species=?, trait=?, attributes=?, preferences=?, energy=?,
                   location=?, credits=?, debt=?, debt_due_week=?, fired_events=?,
                   inventory=?,
                   combat_level=?, combat_xp=?, difficulty=?, max_floor=?,
                   dungeon=?, combat=?, equipment=?, companion=?, protocols=?,
                   last_gig_day=?, street_cred=?, arena_wins=?, gossip_day=?,
                   tea_day=?, tea_id=?, research_day=?, date=?, pawned=?,
                   transcript=?, enrollment=?, class_day=?, browse_day=?, book_seeds=?,
                   home=?, owned_homes=?, stash=?, rent_paid_week=?,
                   created_identity=?, current_identity=?, unlocked_transformations=?,
                   clock_week=?, clock_day=?, clock_minute=?
               WHERE save_id=?""",
            (
                player.species,
                player.trait,
                json.dumps(player.attributes),
                json.dumps(player.preferences),
                player.energy,
                player.location,
                player.credits,
                player.debt,
                player.debt_due_week,
                json.dumps(player.fired_events),
                json.dumps(player.inventory),
                player.combat_level,
                player.combat_xp,
                player.difficulty,
                player.max_floor,
                json.dumps(player.dungeon),
                json.dumps(player.combat),
                json.dumps(player.equipment),
                player.companion,
                json.dumps(player.protocols),
                player.last_gig_day,
                player.street_cred,
                player.arena_wins,
                player.gossip_day,
                player.tea_day,
                player.tea_id,
                player.research_day,
                json.dumps(player.date),
                json.dumps(player.pawned),
                json.dumps(player.transcript),
                json.dumps(player.enrollment),
                player.class_day,
                player.browse_day,
                json.dumps(player.book_seeds),
                player.home,
                json.dumps(player.owned_homes),
                json.dumps(player.stash),
                player.rent_paid_week,
                json.dumps(player.created_identity),
                json.dumps(player.current_identity),
                json.dumps(player.unlocked_transformations),
                clock.week,
                clock.day,
                clock.minute_of_day,
                save_id,
            ),
        )


def state_dict(player, clock):
    return {"player": player.to_dict(), "clock": clock.to_dict()}


def _insert_player(conn, save_id, player, clock):
    conn.execute(
        """INSERT INTO player (
               save_id, species, trait, attributes, preferences, energy,
               location, credits, debt, debt_due_week, fired_events, inventory,
               combat_level, combat_xp, difficulty, max_floor, dungeon, combat, equipment,
               companion, protocols, last_gig_day, street_cred, arena_wins,
               gossip_day, tea_day, tea_id, research_day, date, pawned,
               transcript, enrollment, class_day, browse_day, book_seeds,
               home, owned_homes, stash, rent_paid_week,
               created_identity, current_identity, unlocked_transformations,
               clock_week, clock_day, clock_minute)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            save_id,
            player.species,
            player.trait,
            json.dumps(player.attributes),
            json.dumps(player.preferences),
            player.energy,
            player.location,
            player.credits,
            player.debt,
            player.debt_due_week,
            json.dumps(player.fired_events),
            json.dumps(player.inventory),
            player.combat_level,
            player.combat_xp,
            player.difficulty,
            player.max_floor,
            json.dumps(player.dungeon),
            json.dumps(player.combat),
            json.dumps(player.equipment),
            player.companion,
            json.dumps(player.protocols),
            player.last_gig_day,
            player.street_cred,
            player.arena_wins,
            player.gossip_day,
            player.tea_day,
            player.tea_id,
            player.research_day,
            json.dumps(player.date),
            json.dumps(player.pawned),
            json.dumps(player.transcript),
            json.dumps(player.enrollment),
            player.class_day,
            player.browse_day,
            json.dumps(player.book_seeds),
            player.home,
            json.dumps(player.owned_homes),
            json.dumps(player.stash),
            player.rent_paid_week,
            json.dumps(player.created_identity),
            json.dumps(player.current_identity),
            json.dumps(player.unlocked_transformations),
            clock.week,
            clock.day,
            clock.minute_of_day,
        ),
    )
