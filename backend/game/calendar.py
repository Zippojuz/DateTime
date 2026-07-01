"""The 24-hour clock and 52-week calendar. (Milestone 1)

The clock only advances when the player commits to an action (see actions.py);
it pauses in menus and planning. Tracks time of day, day within the week, and
week toward the one-year (52-week) arc.
"""

DAY_MINUTES = 24 * 60
DAYS_PER_WEEK = 7
WEEKS_PER_YEAR = 52

# New games start on week 1, day 1, at 08:00.
START_WEEK = 1
START_DAY = 1
START_MINUTE = 8 * 60


class GameClock:
    def __init__(self, week=START_WEEK, day=START_DAY, minute_of_day=START_MINUTE):
        self.week = week
        self.day = day
        self.minute_of_day = minute_of_day

    def advance(self, minutes):
        """Advance the clock, rolling over days and weeks as needed."""
        total = self.minute_of_day + minutes
        self.minute_of_day = total % DAY_MINUTES
        self.day += total // DAY_MINUTES
        while self.day > DAYS_PER_WEEK:
            self.day -= DAYS_PER_WEEK
            self.week += 1
        # Year-end handling (week > 52) is deferred to the calendar milestone.
        return self

    @property
    def time_str(self):
        hours, minutes = divmod(self.minute_of_day, 60)
        return f"{hours:02d}:{minutes:02d}"

    def to_dict(self):
        return {
            "week": self.week,
            "day": self.day,
            "minute_of_day": self.minute_of_day,
            "time": self.time_str,
        }
