"""Milestone 4: jobs, debt, and seasonal events."""

import pytest
from app import create_app
from game import events
from game.calendar import GameClock


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


# --- Starting state ---------------------------------------------------------


def test_player_starts_with_debt(client):
    player = client.get("/api/game/state").get_json()["player"]
    assert player["debt"] == 500
    assert player["debt_due_week"] == 52


# --- Jobs -------------------------------------------------------------------


def test_jobs_list_reports_reachability(client):
    jobs = {j["id"]: j for j in client.get("/api/jobs").get_json()}
    # Start in the Docking Quarter — dock hauling is reachable, others aren't.
    assert jobs["dock_hauling"]["reachable"] is True
    assert jobs["grid_gig"]["reachable"] is False


def test_working_pays_credits_with_stat_bonus(client):
    # dock_hauling: base 18 + courage(5) bonus = 23; -15 energy; +2h.
    # A luck tip may land on top (random), so subtract it before asserting.
    res = client.post("/api/job", json={"job_id": "dock_hauling"}).get_json()
    tip = res["result"]["tip"]
    assert res["result"]["pay"] - tip == 23
    assert res["result"]["bonus"] == 5
    player = res["state"]["player"]
    assert player["credits"] == 73 + tip  # 50 + 23 (+ any tip)
    assert player["energy"] == 85
    assert res["state"]["clock"]["time"] == "10:00"  # 08:00 + 2h


def test_cannot_work_a_job_in_another_district(client):
    resp = client.post("/api/job", json={"job_id": "grid_gig"})
    assert resp.status_code == 400
    assert "another district" in resp.get_json()["error"].lower()


def test_cannot_work_when_too_tired(client):
    # Drain energy: two long dock-adjacent shifts aren't here, so nap-drain via
    # repeated hauling (each -15) until the next is refused.
    last = None
    for _ in range(8):
        last = client.post("/api/job", json={"job_id": "dock_hauling"})
    assert last.status_code == 400
    assert "tired" in last.get_json()["error"].lower()


# --- Debt -------------------------------------------------------------------


def test_pay_debt_reduces_debt_and_credits(client):
    # credits -> 73 (+ any random luck tip, which we subtract back out)
    job = client.post("/api/job", json={"job_id": "dock_hauling"}).get_json()
    tip = job["result"]["tip"]
    res = client.post("/api/debt/pay", json={"amount": 40}).get_json()
    assert res["paid"] == 40
    player = res["state"]["player"]
    assert player["credits"] == 33 + tip
    assert player["debt"] == 460


def test_cannot_pay_more_than_you_have(client):
    # Only 50 credits at start; paying 100 pays at most 50.
    res = client.post("/api/debt/pay", json={"amount": 100}).get_json()
    assert res["paid"] == 50
    assert res["state"]["player"]["credits"] == 0


def test_pay_debt_rejects_nonpositive(client):
    assert client.post("/api/debt/pay", json={"amount": 0}).status_code == 400


# --- Events -----------------------------------------------------------------


def test_arrival_event_fires_on_first_action(client):
    res = client.post("/api/action", json={"action": "wait"}).get_json()
    ids = [e["id"] for e in res["events"]]
    assert "arrival" in ids


def test_events_fire_once(client):
    first = client.post("/api/action", json={"action": "wait"}).get_json()
    assert any(e["id"] == "arrival" for e in first["events"])
    second = client.post("/api/action", json={"action": "wait"}).get_json()
    assert all(e["id"] != "arrival" for e in second["events"])


def test_future_event_not_yet_due():
    clock = GameClock(week=1, day=1)
    due = events.due_events(clock, fired=[])
    ids = [e["id"] for e in due]
    assert "arrival" in ids
    assert "lumen_festival" not in ids  # week 4, not reached


def test_event_becomes_due_after_its_date():
    clock = GameClock(week=4, day=6)
    due_ids = [e["id"] for e in events.due_events(clock, fired=[])]
    assert "lumen_festival" in due_ids
