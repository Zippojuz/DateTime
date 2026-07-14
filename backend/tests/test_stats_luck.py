"""Speed→crit, agility→dodge (+defense), and luck's thumb on every scale."""

from game import combat, dungeon, encounters, jobs
from game.calendar import GameClock
from game.player import Player


def _player(level=5, **attrs):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    for k, v in attrs.items():
        p.attributes[k] = v
    return p


class FixedRng:
    """Every chance draw returns the same value; no variance, no crit jitter."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def uniform(self, a, b):
        return 1.0

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return a


# --- Crit from speed (+luck) ----------------------------------------------------


def test_crit_chance_scales_with_speed_and_luck():
    assert combat.crit_chance(0) == combat.CRIT_BASE
    assert combat.crit_chance(20) > combat.crit_chance(10)
    assert combat.crit_chance(20, luck=20) > combat.crit_chance(20)
    assert combat.crit_chance(1000, luck=1000) == combat.CRIT_CAP  # hard cap


def test_player_stats_expose_crit_and_dodge():
    slow = combat.player_stats(_player(wit=0, luck=0))
    fast = combat.player_stats(_player(wit=20, luck=20))
    assert fast["speed"] > slow["speed"]
    assert fast["crit"] > slow["crit"]
    assert 0 < slow["crit"] <= combat.CRIT_CAP


def test_fast_player_crits_where_a_slow_one_does_not():
    # A draw between the two crit chances: the fast build crits, the slow doesn't.
    slow = _player(wit=0, luck=0)  # speed 10 -> crit 0.10
    fast = _player(wit=20, luck=20)  # speed 30 -> crit 0.28
    draw = FixedRng(0.2)
    state = combat.start(slow, "chrome_vixen", 1, 100)
    combat.act(slow, state, "attack", rng=draw)
    assert not any("crit!" in line for line in state["log"])
    state = combat.start(fast, "chrome_vixen", 1, 100)
    combat.act(fast, state, "attack", rng=draw)
    assert any("crit!" in line for line in state["log"])


# --- Dodge from agility (+luck), defense share ----------------------------------


def test_agility_raises_defense_but_wit_still_counts():
    base = combat.player_stats(_player(agility=0, wit=10))
    nimble = combat.player_stats(_player(agility=10, wit=10))
    witless = combat.player_stats(_player(agility=10, wit=0))
    assert nimble["defense"] == base["defense"] + 5  # agility // 2
    assert nimble["defense"] > witless["defense"]  # wit's share remains


def test_nimble_player_dodges_the_blow():
    p = _player(agility=20, luck=20)  # dodge capped at 0.30
    state = combat.start(p, "chrome_vixen", 1, 100)
    hp = state["player_hp"]
    combat.act(p, state, "guard", rng=FixedRng(0.25))
    assert state["player_hp"] == hp
    assert any("twist aside" in line for line in state["log"])


def test_clumsy_player_takes_the_hit():
    p = _player(agility=0, luck=0)  # dodge 0
    state = combat.start(p, "chrome_vixen", 1, 100)
    hp = state["player_hp"]
    combat.act(p, state, "guard", rng=FixedRng(0.25))
    assert state["player_hp"] < hp


def test_telegraphed_signatures_cannot_be_dodged():
    p = _player(level=10, agility=20, luck=20)
    state = combat.start(p, "warden_lyss", 2, 200)
    state["charging"] = {"name": "Test Lance", "power": 1.5, "telegraph": "..."}
    hp = state["player_hp"]
    combat.act(p, state, "attack", rng=FixedRng(0.25))
    assert state["player_hp"] < hp  # it lands despite max dodge
    assert any("Test Lance" in line for line in state["log"])


# --- Luck everywhere --------------------------------------------------------------


def test_luck_widens_the_flee_window():
    # 0.75 draw: base 0.6 fails, +20 luck (0.6 + 0.4 -> capped 0.9) succeeds.
    unlucky = _player(luck=0)
    state = combat.start(unlucky, "chrome_vixen", 1, 100)
    combat.act(unlucky, state, "flee", rng=FixedRng(0.75))
    assert state["fled"] is False
    lucky = _player(luck=20)
    state = combat.start(lucky, "chrome_vixen", 1, 100)
    combat.act(lucky, state, "flee", rng=FixedRng(0.75))
    assert state["fled"] is True


def test_luck_fattens_loot_rolls():
    enemy = {"role": "normal", "tier": 1}
    from game import data

    base_chance = data.load("loot")["normal"]["1"]["chance"]
    draw = FixedRng(min(0.99, base_chance * 1.3))  # between base and luck-boosted
    assert combat.roll_drops(enemy, draw, luck=0) == []
    assert combat.roll_drops(enemy, draw, luck=20) != []


def test_luck_helps_find_hidden_seams():
    p = _player(wit=0, luck=18)  # +6 from luck // 3
    p.location = dungeon.ENTRANCE_DISTRICT
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    run = p.dungeon
    host = next(
        rid
        for rid, room in run["rooms"].items()
        for e in room["exits"].values()
        if e["hidden"] and not e["revealed"]
    )
    run["at"] = host
    # d6 low-rolls a 1: wit 0 + luck 18//3 + 1 = 7 meets DC 7; without luck it misses.
    assert dungeon.search(p, clock, rng=FixedRng(0.5))["found"] is True
    hidden = [e for r in run["rooms"].values() for e in r["exits"].values() if e["hidden"]]
    for e in hidden:
        e["revealed"] = False
    p.attributes["luck"] = 0
    assert dungeon.search(p, clock, rng=FixedRng(0.5))["found"] is False


def test_luck_pads_found_credits():
    p = _player(luck=20)
    p.location = dungeon.ENTRANCE_DISTRICT
    dungeon.enter(p, GameClock(), seed=7)
    room = {"content": {"type": "treasure", "looted": False}}
    before = p.credits
    result = dungeon._resolve_room(p, p.dungeon, room, FixedRng(0.4))  # credits branch
    assert result["type"] == "treasure"
    # randint low roll = 8, floor 1, fortune 1.4 -> 11 (vs 8 without luck)
    assert p.credits - before == round(8 * 1.4)


def test_lucky_workers_catch_tips():
    p = _player(luck=10)
    p.location = "docking_quarter"
    result = jobs.work(p, GameClock(), "dock_hauling", rng=FixedRng(0.2))  # < 0.30
    assert result["tip"] == jobs.TIP_BASE + 10
    p2 = _player(luck=0)
    p2.location = "docking_quarter"
    result = jobs.work(p2, GameClock(), "dock_hauling", rng=FixedRng(0.2))
    assert result["tip"] == 0


def test_luck_invites_more_encounters():
    # 0.65 gate draw: base 0.6 misses, luck 10 (0.7) catches it.
    assert encounters.roll_encounter({}, set(), rng=FixedRng(0.65), luck=0) is None
    assert encounters.roll_encounter({}, set(), rng=FixedRng(0.65), luck=10) is not None
