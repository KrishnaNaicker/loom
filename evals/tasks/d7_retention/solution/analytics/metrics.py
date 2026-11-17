"""Certified product metrics. Each definition lives in METRICS.md."""
from datetime import datetime, timedelta, timezone


def signup_count(signups):
    """Number of signup rows. See METRICS.md, "signup_count"."""
    return len(signups)


def active_user_count(events):
    """Number of distinct users with events. See METRICS.md, "active_user_count"."""
    return len({e["user_id"] for e in events})


def _utc_date(ts):
    return datetime.fromisoformat(ts).astimezone(timezone.utc).date()


def d7_retention(signups, events, cohort_date):
    """Day-7 retention of the signup cohort on cohort_date ("YYYY-MM-DD").

    signups: list of dicts with keys "user_id", "ts".
    events: list of dicts with keys "user_id", "ts".
    Returns a float.
    """
    target = datetime.strptime(cohort_date, "%Y-%m-%d").date()
    cohort = {s["user_id"] for s in signups if _utc_date(s["ts"]) == target}
    if not cohort:
        return 0.0
    day7 = target + timedelta(days=7)
    retained = {
        e["user_id"] for e in events
        if e["user_id"] in cohort and _utc_date(e["ts"]) == day7
    }
    return round(len(retained) / len(cohort), 4)
