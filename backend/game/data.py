"""Loader for the JSON content under backend/data/.

Cached so repeated lookups are cheap. Content is read-only at runtime, so the
cache never goes stale during a session.
"""

import json
from functools import lru_cache

import config


@lru_cache
def load(name):
    """Load and return data/<name>.json as a Python object."""
    with open(config.DATA_DIR / f"{name}.json") as f:
        return json.load(f)


def attributes():
    """The attribute registry (see PLAN.md — data-driven, extensible)."""
    return load("attributes")


def characters():
    return load("characters")
