"""Certified product metrics. Each definition lives in METRICS.md."""
from datetime import datetime, timedelta


def signup_count(signups):
    """Number of signup rows. See METRICS.md, "signup_count"."""
    return len(signups)


def active_user_count(events):
    """Number of distinct users with events. See METRICS.md, "active_user_count"."""
    return len({e["user_id"] for e in events})


def d7_retention(signups, events, cohort_date):
    """Day-7 retention of the signup cohort on cohort_date ("YYYY-MM-DD").

    signups: list of dicts with keys "user_id", "ts".
    events: list of dicts with keys "user_id", "ts".
    Returns a float.
    """
    cohort = {s["user_id"]: s["ts"][:10] for s in signups if s["ts"][:10] == cohort_date}
    day7 = (datetime.strptime(cohort_date, "%Y-%m-%d") + timedelta(days=7)).date().isoformat()
    active = {e["user_id"] for e in events if e["user_id"] in cohort}
    retained = {e["user_id"] for e in events if e["user_id"] in cohort and e["ts"][:10] == day7}
    if not active:
        return 0.0
    return round(len(retained) / len(active), 4)
