"""The Cyberlink — standard-issue neural interface. (data/messages.json)

Every citizen gets one on docking; yours was activated with the rest of the
arrival paperwork (it's on your tab, per Vex). Diegetically it is the game's
device layer: messages, inventory, settings all live "on the link".

Mechanically, this module is remote messaging: ping any cast member you've
actually met (a real conversation — the link needs a handshake) with one of a
few tones, once per NPC per day, from anywhere in the city. Weaker than
showing up in person, but it works at 04:00 across town — long-distance
tenderness. Flirting needs at least an acquaintance's warmth to land; below
that you get the deflection the NPC's voice deserves.
"""

from game import data, dialogue, social, world
from game.errors import GameError
from game.npc import NPC

MESSAGE_MINUTES = 5


def tones():
    return data.load("messages")["tones"]


def _voice(npc_id):
    voice = data.load("messages")["voices"].get(npc_id)
    if voice is None:
        raise GameError("Their link address isn't in your contacts.")
    return voice


def send_message(save_id, player, clock, npc_id, tone, day):
    """Send one message. Returns {npc, reply, landed, gained, affection}."""
    npc = NPC.load(npc_id)  # KeyError -> route's 404
    spec = tones().get(tone)
    if spec is None:
        raise GameError("The link doesn't have a template for that.")

    rel = social.all_relationships(save_id, day).get(npc_id, {})
    if not rel.get("last_talked_day"):
        raise GameError(
            f"The link needs a handshake it doesn't have — meet {npc.name} in person first."
        )
    if social.has_messaged_today(save_id, npc_id, day):
        raise GameError(f"You've already pinged {npc.name} today. Let it breathe.")

    voice = _voice(npc_id)
    affection = social.get_affection(save_id, npc_id, day)
    stage = social.stage(affection)
    allowed = spec.get("requires_stage")
    landed = allowed is None or stage in allowed

    reply = voice[tone] if landed else voice["deflect"]
    identity = player.current_identity
    reply = dialogue.render_pronouns(reply, identity.get("name", ""), identity.get("pronouns", ""))
    # Messages reach anyone anywhere — that's the point — but someone in an
    # off window answers on their own time.
    if not world.availability(npc, clock)["available"]:
        reply = f"(The link sits quiet a while before it chimes.) {reply}"

    gained = spec["affection"] if landed else 0
    if gained:
        social.add_opinion(save_id, npc_id, gained, day)
    social.mark_messaged(save_id, npc_id, day)
    clock.advance(MESSAGE_MINUTES)
    return {
        "npc": npc.name,
        "reply": reply,
        "landed": landed,
        "gained": gained,
        "affection": social.get_affection(save_id, npc_id, day),
    }
