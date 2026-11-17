"""Certified product metrics. Each definition lives in METRICS.md."""
from datetime import datetime, timezone


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
    signup_day = {s["user_id"]: _utc_date(s["ts"]) for s in signups}
    cohort = {u for u, d in signup_day.items() if d == target}
    active = set()
    retained = set()
    for e in events:
        u = e["user_id"]
        if u not in cohort:
            continue
        active.add(u)
        if 1 <= (_utc_date(e["ts"]) - signup_day[u]).days <= 7:
            retained.add(u)
    if not active:
        return 0.0
    return round(len(retained) / len(active), 4)
