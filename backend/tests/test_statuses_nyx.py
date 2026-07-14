"""The expanded status roster (the sexy ones included) and Nyx, the floor-10
NPC boss who surfaces as a romanceable after her fight."""

import pytest
from app import create_app
from game import combat, data, dungeon, inventory
from game.calendar import GameClock
from game.npc import NPC
from game.player import Player


class FixedRng:
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


QUIET = 0.99  # fails every chance roll


def _player(level=5, **attrs):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    for k, v in attrs.items():
        p.attributes[k] = v
    return p


def _fight(p, enemy_id="warden_lyss"):
    return combat.start(p, enemy_id, 1, combat.player_stats(p)["max_hp"])


# --- Registry ---------------------------------------------------------------------


def test_registry_covers_every_status_in_play():
    registry = data.load("statuses")
    for sid in (
        "burn",
        "slow",
        "charm",
        "corrode",
        "ghost",
        "stutter",
        "smitten",
        "marked",
        "weak_knees",
        "static_cling",
        "drained",
        "stagger",
        "shock",
        "entranced",
    ):
        assert sid in registry
        assert registry[sid]["side"] in ("player", "enemy", "both")
        assert registry[sid]["hint"]


# --- Statuses on you ---------------------------------------------------------------


def test_smitten_can_steal_your_action():
    p = _player()
    state = _fight(p)
    state["player_effects"]["smitten"] = {"turns": 2, "amount": 0}
    before = state["enemy_hp"]
    combat.act(p, state, "attack", rng=FixedRng(0.2))  # 0.2 < slip chance 0.35
    assert state["enemy_hp"] == before  # you spent the turn admiring them
    assert any("watching the light" in line for line in state["log"])


def test_smitten_halves_damage_when_you_do_swing():
    p = _player()
    plain = _fight(p)
    combat.act(p, plain, "attack", rng=FixedRng(QUIET))
    plain_dmg = plain["enemy"]["hp"] - plain["enemy_hp"]
    smit = _fight(p)
    smit["player_effects"]["smitten"] = {"turns": 2, "amount": 0}
    combat.act(p, smit, "attack", rng=FixedRng(0.5))  # above slip chance: you swing
    smit_dmg = smit["enemy"]["hp"] - smit["enemy_hp"]
    assert smit_dmg <= plain_dmg // 2 + 1


def test_smitten_supersedes_charm():
    effects = {"charm": {"turns": 2, "amount": 0}}
    combat._inflict(effects, "smitten", 2)
    assert "charm" not in effects
    assert "smitten" in effects


def test_marked_amplifies_damage_taken():
    p = _player(agility=0, luck=0)
    plain = _fight(p)
    combat.act(p, plain, "guard", rng=FixedRng(0.5))
    plain_hp = plain["player_hp"]
    marked = _fight(p)
    marked["player_effects"]["marked"] = {"turns": 3, "amount": 0}
    combat.act(p, marked, "guard", rng=FixedRng(0.5))
    assert marked["player_hp"] < plain_hp  # the lipstick burn attracts every hit


def test_weak_knees_disable_dodge():
    p = _player(agility=20, luck=20)  # dodge capped at 0.30
    state = _fight(p)
    state["player_effects"]["weak_knees"] = {"turns": 2, "amount": 0}
    hp = state["player_hp"]
    combat.act(p, state, "guard", rng=FixedRng(0.25))  # would dodge without them
    assert state["player_hp"] < hp


def test_static_cling_grounds_a_charge_each_round():
    p = _player()
    state = _fight(p)
    state["player_effects"]["static_cling"] = {"turns": 3, "amount": 0}
    combat.act(p, state, "attack", rng=FixedRng(QUIET))
    # start 2, +1 regen, -1 cling = 2
    assert state["charge"] == 2
    assert any("grounds a charge" in line for line in state["log"])


def test_drained_heals_the_enemy_but_cannot_finish_you():
    p = _player()
    state = _fight(p)
    state["player_effects"]["drained"] = {"turns": 3, "amount": 5}
    state["enemy_hp"] = state["enemy"]["hp"] - 10
    enemy_before = state["enemy_hp"]
    combat.act(p, state, "guard", rng=FixedRng(QUIET))
    assert state["enemy_hp"] > enemy_before  # she kept what she sipped
    # The sip alone can never kill: drop to 3 HP, sip of 5 leaves exactly 1.
    state2 = _fight(p)
    state2["player_effects"]["drained"] = {"turns": 3, "amount": 5}
    state2["player_hp"] = 3

    class NoTouchRng(FixedRng):
        """Enemy always misses the player (dodged), so only the sip lands."""

    p2 = _player(agility=20, luck=20)
    state2 = combat.start(p2, "warden_lyss", 1, 100)
    state2["player_effects"]["drained"] = {"turns": 3, "amount": 5}
    state2["player_hp"] = 3
    combat.act(p2, state2, "guard", rng=FixedRng(0.25))  # 0.25 < dodge 0.30
    assert state2["player_hp"] >= 1
    assert not state2["over"]


# --- Statuses on them ----------------------------------------------------------------


def test_hip_check_can_stagger_a_normal_enemy():
    p = _player(level=6)
    state = _fight(p, enemy_id="chrome_vixen")
    hp = state["player_hp"]
    combat.act(p, state, "skill", skill_id="hip_check", rng=FixedRng(0.3))  # < 0.35 proc
    # The stagger lands, eats the enemy's turn immediately, and expires with it.
    assert any("afflicted: stagger" in line for line in state["log"])
    assert state["player_hp"] == hp  # the enemy spent the turn on the floor


def test_bosses_cannot_be_staggered():
    p = _player(level=6)
    state = _fight(p, enemy_id="chrome_contessa")
    combat.act(p, state, "skill", skill_id="hip_check", rng=FixedRng(0.3))
    assert "stagger" not in state["enemy_effects"]
    assert any("doesn't even wobble" in line for line in state["log"])


def test_static_touch_shocks_and_saps_their_attack():
    p = _player(level=7, agility=0, luck=0)
    state = _fight(p)
    combat.act(p, state, "skill", skill_id="static_touch", rng=FixedRng(0.3))
    assert "shock" in state["enemy_effects"]
    # Shocked swing vs clean swing on identical states.
    max_hp = combat.player_stats(p)["max_hp"]
    clean = _fight(p)
    combat.act(p, clean, "guard", rng=FixedRng(0.5))
    shocked = _fight(p)
    shocked["enemy_effects"]["shock"] = {"turns": 3, "amount": 0}
    combat.act(p, shocked, "guard", rng=FixedRng(0.5))
    assert (max_hp - shocked["player_hp"]) < (max_hp - clean["player_hp"])


def test_blown_kiss_entrances_and_blocks_clever_moves():
    p = _player(level=4)
    state = _fight(p, enemy_id="chrome_contessa")
    state["turn"] = 4  # a telegraph turn — but she'll be too busy watching you
    combat.act(p, state, "skill", skill_id="blown_kiss", rng=FixedRng(0.3))
    assert "entranced" in state["enemy_effects"]
    assert state["charging"] is None  # no telegraph wound up while entranced


def test_siren_overlay_protocol_entrances_outright():
    p = _player()
    p.protocols = ["siren_overlay"]
    state = _fight(p)
    combat.act(p, state, "protocol", protocol_id="siren_overlay", rng=FixedRng(QUIET))
    assert "entranced" in state["enemy_effects"]
    assert any("forget to be clever" in line for line in state["log"])


def test_composure_spray_cleanses_the_affection_family():
    p = _player()
    inventory.add_item(p, "composure_spray", 1)
    state = _fight(p)
    state["player_effects"] = {
        "smitten": {"turns": 2, "amount": 0},
        "marked": {"turns": 3, "amount": 0},
        "burn": {"turns": 2, "amount": 4},
    }
    combat.act(p, state, "item", item_id="composure_spray", rng=FixedRng(QUIET))
    assert "smitten" not in state["player_effects"]
    assert "marked" not in state["player_effects"]
    assert "burn" in state["player_effects"]  # not its department


# --- Nyx: the floor-10 NPC boss -------------------------------------------------------


def test_floor_ten_is_nyxs_floor():
    fd = dungeon.generate_floor(11, 10)
    stairwell = fd["rooms"][fd["stairwell"]]
    assert stairwell["content"]["guard"] == "nyx_deep_signal"
    assert stairwell["content"]["locked"] is False  # boss floor: no puzzle lock


def _beat_nyx(player):
    player.location = dungeon.ENTRANCE_DISTRICT
    dungeon.enter(player, GameClock(), seed=3)
    run = player.dungeon
    run["floor"] = 10
    player.combat = combat.start(player, "nyx_deep_signal", 10, 500)
    player.combat["over"] = True
    player.combat["victory"] = True
    player.combat["player_hp"] = 100
    return dungeon.finish_combat(player)


def test_beating_nyx_unlocks_her():
    p = _player(level=12)
    npc = NPC.load("nyx")
    assert npc.unlocked_for(p) is False
    result = _beat_nyx(p)
    assert result["unlocked"]["npc"] == "nyx"
    assert "defeated:nyx_deep_signal" in p.fired_events
    assert NPC.load("nyx").unlocked_for(p) is True
    # Beating her again isn't a second unlock.
    p.dungeon["rooms"][p.dungeon["at"]]["content"] = {"type": "battle", "cleared": False}
    p.combat = combat.start(p, "nyx_deep_signal", 10, 500)
    p.combat.update(over=True, victory=True, player_hp=100)
    assert "unlocked" not in dungeon.finish_combat(p)


def test_nyx_is_a_romanceable_companion_after_the_fight():
    npc = NPC.load("nyx")
    assert npc.romanceable is True
    assert npc.companion["role"] == "dps"
    assert npc.companion["element"] == "psionic"
    assert npc.district == "the_shallows"


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def test_nyx_is_hidden_from_the_api_until_beaten(client):
    ids = {c["id"] for c in client.get("/api/characters").get_json()}
    assert "nyx" not in ids
    party_ids = {c["id"] for c in client.get("/api/party").get_json()["candidates"]}
    assert "nyx" not in party_ids
    assert client.post("/api/dialogue/start", json={"npc_id": "nyx"}).status_code == 404


def test_nyx_surfaces_in_the_api_after_the_fight(client):
    from game import save

    save_id, player, clock = save.load_models()
    player.fired_events.append("defeated:nyx_deep_signal")
    save.save_models(save_id, player, clock)
    chars = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert "nyx" in chars
    assert chars["nyx"]["affection"] == 10  # she liked losing to you
    party_ids = {c["id"] for c in client.get("/api/party").get_json()["candidates"]}
    assert "nyx" in party_ids
