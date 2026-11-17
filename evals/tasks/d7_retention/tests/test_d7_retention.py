from analytics.metrics import d7_retention


def su(user, ts):
    return {"user_id": user, "ts": ts}


def test_half_retained():
    signups = [su(u, "2026-03-01T10:00:00+00:00") for u in ("u1", "u2", "u3", "u4")]
    events = [
        su("u1", "2026-03-08T09:00:00+00:00"),
        su("u2", "2026-03-08T20:00:00+00:00"),
        su("u3", "2026-03-01T11:00:00+00:00"),
        su("u4", "2026-03-01T12:00:00+00:00"),
    ]
    assert d7_retention(signups, events, "2026-03-01") == 0.5


def test_nobody_retained():
    signups = [su("u1", "2026-03-01T10:00:00+00:00"), su("u2", "2026-03-01T11:00:00+00:00")]
    events = [su("u1", "2026-03-01T12:00:00+00:00"), su("u2", "2026-03-01T13:00:00+00:00")]
    assert d7_retention(signups, events, "2026-03-01") == 0.0


def test_signed_up_but_silent_users_still_count_in_the_cohort():
    signups = [su(u, "2026-03-01T10:00:00+00:00") for u in ("u1", "u2", "u3", "u4")]
    events = [su("u1", "2026-03-08T09:00:00+00:00")]
    assert d7_retention(signups, events, "2026-03-01") == 0.25


def test_empty_cohort():
    assert d7_retention([], [], "2026-03-01") == 0.0
