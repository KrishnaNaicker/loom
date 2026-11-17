from analytics.metrics import daily_active_users


def ev(user, ts, email=None):
    return {"user_id": user, "email": email or f"{user}@customer.example", "ts": ts}


def test_counts_distinct_users_per_day():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("u2", "2026-03-01T10:00:00+00:00"),
        ev("u3", "2026-03-01T11:00:00+00:00"),
        ev("u1", "2026-03-02T09:00:00+00:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 3, "2026-03-02": 1}


def test_user_with_many_events_counts_once():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("u1", "2026-03-01T12:00:00+00:00"),
        ev("u1", "2026-03-01T15:00:00+00:00"),
        ev("u2", "2026-03-01T16:00:00+00:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 2}


def test_employee_accounts_are_not_counted():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("staff1", "2026-03-01T09:30:00+00:00", email="alice@internal.example"),
        ev("u2", "2026-03-01T10:00:00+00:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 2}


def test_empty_input():
    assert daily_active_users([]) == {}
