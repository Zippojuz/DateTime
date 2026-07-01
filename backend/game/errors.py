"""Shared domain error type."""


class GameError(Exception):
    """A player-facing rule violation. Routes map this to HTTP 400."""
