"""The Triumvirate: three megacorps forever at war, identical at heart.

Oceania, Eurasia, Eastasia (with apologies to Orwell): every week two of them
are allied against the third, the pairing rotates, and all three insist the
current arrangement has always been the arrangement. All three are wholly
owned subsidiaries of the same unlisted shell (Ministry Holdings, no address,
no phone) — which none of their ads mention and all of their lawyers deny.
"""

from game import data

_ROTATION = [
    ("oceania", "eurasia", "eastasia"),  # allies, allies, enemy
    ("eurasia", "eastasia", "oceania"),
    ("eastasia", "oceania", "eurasia"),
]


def war_state(week):
    """This week's alignment: two allies, one enemy — eternal, until next week."""
    ally_a, ally_b, enemy = _ROTATION[(week - 1) % len(_ROTATION)]
    corps = data.load("corps")
    return {
        "allies": [ally_a, ally_b],
        "enemy": enemy,
        "line": (
            f"{corps[ally_a]['name']} and {corps[ally_b]['name']} have always "
            f"stood together against {corps[enemy]['name']}. Always."
        ),
        # The joint communiqué, and the housekeeping that makes it true.
        "bulletin": (
            f"JOINT STATEMENT ({corps[ally_a]['name']} & {corps[ally_b]['name']}): "
            f"{corps[enemy]['name']} has never manufactured a trustworthy product. "
            f"Records indicating otherwise have been corrected."
        ),
    }


def view(week):
    """The corps plus this week's war, for the API."""
    return {"corps": data.load("corps"), "war": war_state(week)}
