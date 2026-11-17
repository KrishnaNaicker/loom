from analytics.metrics import daily_active_users


def ev(user, ts, email=None, **extra):
    row = {"user_id": user, "email": email or f"{user}@customer.example", "ts": ts}
    row.update(extra)
    return row


def test_day_is_utc_date_not_local_date():
    rows = [
        ev("u1", "2026-03-01T23:30:00-05:00"),
        ev("u2", "2026-03-01T12:00:00+00:00"),
        ev("u3", "2026-03-01T20:00:00-08:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 1, "2026-03-02": 2}


def test_positive_offset_moves_event_to_previous_utc_day():
    rows = [
        ev("u1", "2026-03-02T01:00:00+05:30"),
        ev("u2", "2026-03-02T12:00:00+00:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 1, "2026-03-02": 1}


def test_internal_emails_excluded_but_lookalike_domains_kept():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("staff1", "2026-03-01T09:00:00+00:00", email="alice@internal.example"),
        ev("staff2", "2026-03-01T10:00:00+00:00", email="bob@internal.example"),
        ev("u2", "2026-03-01T10:00:00+00:00", email="carol@internal.example.com"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 2}


def test_bot_rows_excluded():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00", is_bot=False),
        ev("u2", "2026-03-01T09:30:00+00:00"),
        ev("crawler", "2026-03-01T10:00:00+00:00", is_bot=True),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 2}


def test_user_whose_only_rows_are_excluded_is_not_active():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("u2", "2026-03-01T10:00:00+00:00", is_bot=True),
        ev("u2", "2026-03-02T10:00:00+00:00"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 1, "2026-03-02": 1}


def test_day_with_only_excluded_rows_is_absent():
    rows = [
        ev("u1", "2026-03-01T09:00:00+00:00"),
        ev("crawler", "2026-03-02T10:00:00+00:00", is_bot=True),
        ev("staff", "2026-03-02T11:00:00+00:00", email="ops@internal.example"),
    ]
    assert daily_active_users(rows) == {"2026-03-01": 1}
