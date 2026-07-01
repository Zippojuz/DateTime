"""Milestone 0 smoke test: the API boots and the health check responds."""

from app import create_app


def test_health_ok():
    client = create_app().test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["game"] == "nexus-city"


def test_data_files_are_valid_json():
    """Seed data must be loadable — cheap guard against broken JSON edits."""
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent.parent / "data"
    for name in ("characters", "districts", "items", "enemies", "events"):
        with open(data_dir / f"{name}.json") as f:
            json.load(f)


def test_vael_has_pronouns():
    """Every character carries their own pronouns (see Identity Philosophy)."""
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent.parent / "data"
    with open(data_dir / "characters.json") as f:
        characters = json.load(f)
    assert characters["vael"]["pronouns"] == "she/her"
