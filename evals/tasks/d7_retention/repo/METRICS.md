# Certified metrics

This file defines the metrics computed in analytics/metrics.py. When the code and this document disagree, this document wins.

Signups are dicts with a user_id, which appears at most once across all signups, and ts, an ISO-8601 timestamp with a UTC offset such as -05:00 or +00:00, for when the user signed up. Events are dicts with a user_id and a ts in the same format, and a user can have any number of them.

## signup_count(signups)

The number of rows in signups. This one is implemented and feeds the growth dashboard.

## active_user_count(events)

The number of distinct user_id values in events. This is implemented and is used for rough activity reporting.

## d7_retention(signups, events, cohort_date)

Takes cohort_date as a YYYY-MM-DD string and returns a float. Every timestamp is converted to UTC and reduced to its calendar date before anything is compared, and the date written in the string is never used. The cohort is every user whose signup date equals cohort_date, including users who never produced a single event. For each cohort user, day 7 is their signup date plus seven calendar days, and the user is retained when they have at least one event dated exactly on that day; events on any other day, earlier or later, do not make a user retained. Events from users outside the cohort are ignored. The result is the number of retained cohort users divided by the size of the whole cohort, where each user counts once however many day-7 events they have, and the denominator is the full cohort and not just the users who were active. The value is rounded to four decimal places with Python's round(value, 4). If nobody signed up on cohort_date the result is 0.0.
