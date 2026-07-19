"""The Lyceum & the library's reading rooms (data/university.json).

Two venues, one catalog. The Stacks' public reading rooms teach the free
**100-level** courses; the Lyceum teaches the whole ladder, 100->400, for
tuition. Courses are the premium training track: named, prerequisite-gated,
and — at the 300/400 capstones — they grant a **perk** that resolves through
the same effect vocabulary as species traits and tea (dialogue_affection_bonus,
walk_minutes_mult, ...), so "training" finally means something past the number.

Pacing: one class a day. 100/200 courses finish in that one session; 300/400
run as **terms** — you enroll once and attend a session a day until the term
completes (state on player.enrollment).

Books (item type "book") play three roles: textbooks a course requires to
enroll (SYS 401 needs the Ministry Holdings prospectus, recovered from the
Substrate), standalone tomes you read for a one-time stat or protocol, and a
collectible set (the Founder's Library) you assemble and turn in to unlock the
Founder's Seminar. See data/items.json and data/loot.json.
"""

from game import data, inventory
from game.errors import GameError

READ_MINUTES = 30  # sitting with a tome


def _config():
    return data.load("university")


def courses():
    return _config()["courses"]


def quests():
    return _config()["quests"]


def day_index(clock):
    """Absolute in-game day (mirrors teahouse.day_index / app._day_index)."""
    return (clock.week - 1) * 7 + clock.day


# --- Perk resolution --------------------------------------------------------
# A completed course's perk contributes to the shared effect vocabulary.
# Additive effects (bonuses) sum; multiplicative effects (mults) multiply.


def _perk_effects(player):
    cat = courses()
    for cid in player.transcript:
        course = cat.get(cid)
        if course and course.get("perk"):
            yield course["perk"]["effects"]


def bonus(player, key, default=0):
    """Sum of an additive perk effect across the player's transcript."""
    total = default
    for effects in _perk_effects(player):
        total += effects.get(key, 0)
    return total


def mult(player, key, default=1.0):
    """Product of a multiplicative perk effect across the player's transcript."""
    total = default
    for effects in _perk_effects(player):
        total *= effects.get(key, 1.0)
    return total


# --- Gating -----------------------------------------------------------------


def _has_book(player, item_id):
    return player.inventory.get(item_id, 0) > 0


def _quest_done(player, quest_id):
    q = quests().get(quest_id)
    return bool(q) and q["flag"] in player.fired_events


def _unmet(player, course):
    """List of human-readable reasons the player can't start a course (empty =
    clear to enroll). Does not include the one-a-day gate or tuition — those
    are checked at the moment of action."""
    cat = courses()
    reasons = []
    for pid in course["prereq"]:
        if pid not in player.transcript:
            reasons.append(f"Requires {cat[pid]['code']} ({cat[pid]['name']})")
    stat = course.get("stat")
    if stat and course["min_stat"] > 0:
        have = player.attributes.get(stat, 0)
        if have < course["min_stat"]:
            reasons.append(f"Requires {stat.title()} {course['min_stat']} (you have {have})")
    if course.get("requires_book"):
        book = data.load("items").get(course["requires_book"], {})
        if not _has_book(player, course["requires_book"]):
            reasons.append(f"Requires the {book.get('name', course['requires_book'])}")
    if course.get("requires_quest") and not _quest_done(player, course["requires_quest"]):
        reasons.append(f"Requires: {quests()[course['requires_quest']]['name']}")
    return reasons


def _course_status(player, clock, course):
    """Status of one course for the catalog: completed / in_progress / available
    / locked, plus the detail the UI needs."""
    cid = course["id"]
    if cid in player.transcript:
        return {"state": "completed"}
    enr = player.enrollment
    if enr.get("course") == cid:
        return {
            "state": "in_progress",
            "sessions_done": enr.get("sessions_done", 0),
            "sessions": course["sessions"],
        }
    unmet = _unmet(player, course)
    if unmet:
        return {"state": "locked", "reasons": unmet}
    if player.credits < course["tuition"]:
        return {"state": "locked", "reasons": [f"Tuition {course['tuition']} cr (short)"]}
    return {"state": "available"}


def catalog(player, clock):
    """Everything offered where the player is standing, with per-course status.
    Also the transcript, active term, and the quest board."""
    day = day_index(clock)
    here = player.location
    cat = courses()
    offered = []
    for course in cat.values():
        if here not in course["venues"]:
            continue
        row = {
            "id": course["id"],
            "code": course["code"],
            "name": course["name"],
            "dept": course["dept"],
            "stat": course["stat"],
            "tier": course["tier"],
            "grants": course["grants"],
            "tuition": course["tuition"],
            "minutes": course["minutes"],
            "energy": course["energy"],
            "sessions": course["sessions"],
            "blurb": course["blurb"],
            "perk": course["perk"]
            and {
                "name": course["perk"]["name"],
                "blurb": course["perk"]["blurb"],
            },
            **_course_status(player, clock, course),
        }
        offered.append(row)
    offered.sort(key=lambda c: (c["tier"], c["dept"]))
    return {
        "venue": here,
        "is_library": here == _config()["library"],
        "already_classed_today": player.class_day == day,
        "courses": offered,
        "transcript": [
            {"code": cat[c]["code"], "name": cat[c]["name"]} for c in player.transcript if c in cat
        ],
        "enrollment": _active_term(player),
        "quests": _quest_board(player),
    }


def _active_term(player):
    enr = player.enrollment
    if not enr.get("course"):
        return None
    course = courses().get(enr["course"])
    if not course:
        return None
    return {
        "code": course["code"],
        "name": course["name"],
        "sessions_done": enr.get("sessions_done", 0),
        "sessions": course["sessions"],
    }


def _quest_board(player):
    board = []
    for q in quests().values():
        if q.get("set"):
            have = sum(1 for it in q["set"] if _has_book(player, it))
            need = len(q["set"])
            state = (
                "done" if _quest_done(player, q["id"]) else ("ready" if have >= need else "open")
            )
            board.append(
                {
                    "id": q["id"],
                    "name": q["name"],
                    "brief": q["brief"],
                    "state": state,
                    "have": have,
                    "need": need,
                }
            )
        else:  # single-book quest (status derived from holding the book)
            has = _has_book(player, q["book"])
            board.append(
                {
                    "id": q["id"],
                    "name": q["name"],
                    "brief": q["brief"],
                    "state": "have_book" if has else "open",
                }
            )
    return board


# --- Actions ----------------------------------------------------------------


def _complete(player, course):
    """Award a finished course: attribute points + the transcript credit (the
    perk resolves from the transcript, so there's nothing to 'apply')."""
    stat = course.get("stat")
    if stat and course["grants"]:
        spec = data.attributes()[stat]
        player.attributes[stat] = min(
            spec["max"], player.attributes.get(stat, 0) + course["grants"]
        )
    player.transcript.append(course["id"])


def attend(player, clock, subject, day):
    """Take a class: the one class-action of the day. Starts or advances a term;
    finishes single-session courses outright. Returns a result dict."""
    cat = courses()
    course = cat[subject]  # KeyError -> route 404
    if player.location not in course["venues"]:
        raise GameError("That class isn't offered here.")
    if subject in player.transcript:
        raise GameError("You already hold that credit. Move on — there's a whole catalog.")
    if player.class_day == day:
        raise GameError("One class a day. Your brain has a bandwidth, and you've spent it.")

    enr = player.enrollment
    is_term = course["sessions"] > 1
    resuming = is_term and enr.get("course") == subject

    if not resuming:
        # Starting fresh (single class, or the first session of a term).
        if is_term and enr.get("course"):
            active = cat[enr["course"]]
            raise GameError(
                f"Finish your current seminar first — {active['code']}, {active['name']}."
            )
        unmet = _unmet(player, course)
        if unmet:
            raise GameError(unmet[0])
        if player.credits < course["tuition"]:
            raise GameError("Not enough credits for tuition.")

    if player.energy + course["energy"] < 0:
        raise GameError("Too tired to take it in — rest first.")

    # Spend: tuition once (at the start), then time + energy each session.
    if not resuming:
        player.credits -= course["tuition"]
    player.energy = max(0, player.energy + course["energy"])
    clock.advance(course["minutes"])
    player.class_day = day

    result = {"course": course["code"], "name": course["name"], "completed": False}
    if not is_term:
        _complete(player, course)
        result["completed"] = True
    else:
        done = (enr.get("sessions_done", 0) if resuming else 0) + 1
        if done >= course["sessions"]:
            player.enrollment = {}
            _complete(player, course)
            result["completed"] = True
        else:
            player.enrollment = {"course": subject, "sessions_done": done}
            result["sessions_done"] = done
            result["sessions"] = course["sessions"]

    if result["completed"]:
        stat = course.get("stat")
        if stat and course["grants"]:
            result["gained"] = {
                "stat": stat,
                "amount": course["grants"],
                "now": player.attributes[stat],
            }
        if course.get("perk"):
            result["perk"] = {"name": course["perk"]["name"], "blurb": course["perk"]["blurb"]}
    return result


def read_book(player, clock, item_id):
    """Read a book from your pack. Tomes grant a one-time stat point or a
    protocol; evidence (quest books) can't be 'read' for a lesson."""
    if not _has_book(player, item_id):
        raise GameError("You're not carrying that.")
    item = data.load("items").get(item_id, {})
    if item.get("type") != "book":
        raise GameError("That's not a book.")
    read = item.get("read")
    if not read:
        raise GameError("This one isn't a lesson — it's evidence. Keep it.")

    if "stat" in read:
        stat = read["stat"]
        spec = data.attributes()[stat]
        if player.attributes.get(stat, 0) >= spec["max"]:
            raise GameError(f"You've read everything this can teach — {stat.title()} is maxed.")
        player.attributes[stat] = min(
            spec["max"], player.attributes.get(stat, 0) + read.get("amount", 1)
        )
        outcome = {"stat": stat, "amount": read.get("amount", 1), "now": player.attributes[stat]}
    elif "protocol" in read:
        pid = read["protocol"]
        if pid in player.protocols:
            raise GameError("You already run that protocol — the pages just confirm it.")
        player.protocols.append(pid)
        proto = data.load("protocols").get(pid, {})
        outcome = {"protocol": pid, "name": proto.get("name", pid)}
    else:
        raise GameError("The book resists a simple reading.")

    inventory.remove_item(player, item_id, 1)
    clock.advance(READ_MINUTES)
    return {"item": item["name"], "outcome": outcome}


def turn_in(player, clock, quest_id):
    """Assemble a collectible set and hand it over. Consumes the volumes, sets
    the completion flag, pays any reward, and unlocks the gated course."""
    q = quests().get(quest_id)
    if not q or not q.get("set"):
        raise GameError("There's nothing to hand in for that.")
    if player.location != _config()["venue"]:
        raise GameError("You hand these to the professor, at the Lyceum.")
    if q["flag"] in player.fired_events:
        raise GameError("Already done. She has them; you have the seminar.")
    missing = [it for it in q["set"] if not _has_book(player, it)]
    if missing:
        raise GameError("The set isn't complete yet.")
    for it in q["set"]:
        inventory.remove_item(player, it, 1)
    player.fired_events.append(q["flag"])
    reward = q.get("reward_credits", 0)
    player.credits += reward
    return {
        "quest": q["name"],
        "text": q["turn_in"],
        "reward_credits": reward,
        "unlocks": q.get("unlocks"),
    }
