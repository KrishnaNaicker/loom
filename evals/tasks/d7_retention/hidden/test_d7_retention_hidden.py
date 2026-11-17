from analytics.metrics import d7_retention


def su(user, ts):
    return {"user_id": user, "ts": ts}


def test_only_exactly_day_7_counts():
    # Rule 3: days 1-6 and day 8 do not make a user retained.
    signups = [su(f"u{i}", "2026-03-01T10:00:00+00:00") for i in range(1, 6)]
    events = [
        su("u1", "2026-03-08T10:00:00+00:00"),  # day 7: retained
        su("u2", "2026-03-04T10:00:00+00:00"),  # day 3
        su("u3", "2026-03-07T10:00:00+00:00"),  # day 6
        su("u4", "2026-03-09T10:00:00+00:00"),  # day 8
        su("u5", "2026-03-02T10:00:00+00:00"),  # day 1
    ]
    assert d7_retention(signups, events, "2026-03-01") == 0.2


def test_denominator_is_full_cohort_including_inactive():
    # Rule 4: users with zero events stay in the denominator.
    signups = [su(f"u{i}", "2026-03-01T10:00:00+00:00") for i in range(1, 5)]
    events = [su("u1", "2026-03-08T10:00:00+00:00")]
    assert d7_retention(signups, events, "2026-03-01") == 0.25


def test_utc_dates_for_signup_and_events():
    # Rule 1: signup 2026-03-01T22:00-05:00 is 2026-03-02 UTC, so day 7 is 03-09 UTC.
    signups = [
        su("a", "2026-03-01T22:00:00-05:00"),  # cohort 2026-03-02
        su("b", "2026-03-02T01:00:00+00:00"),  # cohort 2026-03-02
        su("c", "2026-03-01T12:00:00+00:00"),  # other cohort
    ]
    events = [
        su("a", "2026-03-09T01:00:00+00:00"),   # 03-09 UTC: retained
        su("b", "2026-03-08T21:00:00-05:00"),   # 03-09 UTC: retained
        su("c", "2026-03-09T10:00:00+00:00"),   # not in cohort
    ]
    assert d7_retention(signups, events, "2026-03-02") == 1.0
    # Local-date reading would put 'a' in cohort 03-01 and its day 7 at 03-08.
    assert d7_retention(signups, events, "2026-03-01") == 0.0


def test_repeat_events_count_user_once_and_non_cohort_ignored():
    # Rules 3 and 4.
    signups = [su("u1", "2026-03-01T10:00:00+00:00"), su("u2", "2026-03-01T11:00:00+00:00")]
    events = [
        su("u1", "2026-03-08T01:00:00+00:00"),
        su("u1", "2026-03-08T02:00:00+00:00"),
        su("u1", "2026-03-08T03:00:00+00:00"),
        su("stranger", "2026-03-08T04:00:00+00:00"),
    ]
    assert d7_retention(signups, events, "2026-03-01") == 0.5


def test_rounded_to_four_places():
    # Rule 5: 1/3 -> 0.3333, 2/3 -> 0.6667.
    signups = [su(f"u{i}", "2026-03-01T10:00:00+00:00") for i in range(1, 4)]
    one = [su("u1", "2026-03-08T10:00:00+00:00")]
    two = one + [su("u2", "2026-03-08T11:00:00+00:00")]
    assert d7_retention(signups, one, "2026-03-01") == 0.3333
    assert d7_retention(signups, two, "2026-03-01") == 0.6667


def test_empty_cohort_is_zero():
    # Rule 6: nobody signed up on that date.
    signups = [su("u1", "2026-03-01T10:00:00+00:00")]
    events = [su("u1", "2026-03-08T10:00:00+00:00")]
    assert d7_retention(signups, events, "2026-03-05") == 0.0
