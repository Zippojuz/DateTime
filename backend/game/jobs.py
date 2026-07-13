"""Jobs — the way to earn credits (and pay down the debt). (Milestone 4)

Jobs are tied to districts: you work whatever's available where you're standing.
Pay is a base amount plus a small bonus from the job's associated attribute, so
stats matter. Working costs time and energy.
"""

from game import data
from game.errors import GameError


def all_jobs():
    return data.load("jobs")


def jobs_in(district_id):
    return {jid: job for jid, job in all_jobs().items() if job["district"] == district_id}


def work(player, clock, job_id):
    """Work a job in place. Raises GameError if it's elsewhere or you're too
    tired. Returns a result summary (pay, bonus, job name)."""
    job = all_jobs().get(job_id)
    if job is None:
        raise GameError("No such job.")
    if job["district"] != player.location:
        raise GameError("That job is in another district.")
    if player.energy + job["energy"] < 0:
        raise GameError("Too tired to work — rest first.")

    stat = job.get("stat")
    bonus = player.attributes.get(stat, 0) if stat else 0
    pay = job["pay"] + bonus

    player.energy = max(0, player.energy + job["energy"])
    player.credits += pay
    clock.advance(job["minutes"])
    return {"job": job["name"], "pay": pay, "bonus": bonus, "stat": stat}
