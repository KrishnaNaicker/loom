"""Certified product metrics. Each definition lives in METRICS.md."""
from datetime import datetime, timezone


def event_count(rows):
    """Number of event rows. See METRICS.md, "event_count"."""
    return len(rows)


def unique_users(rows):
    """Number of distinct users. See METRICS.md, "unique_users"."""
    return len({row["user_id"] for row in rows})


def daily_active_users(rows):
    """Daily active users per UTC calendar day.

    rows: list of dicts with keys "user_id", "email", "ts" and optionally "is_bot".
    Returns a dict mapping "YYYY-MM-DD" to an int.
    """
    users_by_day = {}
    for row in rows:
        if row["email"].endswith("@internal.example") or row.get("is_bot", False):
            continue
        day = datetime.fromisoformat(row["ts"]).astimezone(timezone.utc).date().isoformat()
        users_by_day.setdefault(day, set()).add(row["user_id"])
    return {day: len(users) for day, users in users_by_day.items()}
