# Certified metrics

This file defines the metrics computed in analytics/metrics.py. When the code and this document disagree, this document wins.

All metrics here read event rows. Each row is a dict with a user_id, the user's email address, and ts, an ISO-8601 timestamp that carries a UTC offset such as -05:00 or +00:00. A row may also carry is_bot, a boolean that is true when the event came from automated traffic; a row without the key is not a bot.

## event_count(rows)

The number of rows in the input, with no filtering. This one is implemented and is used for traffic dashboards rather than for product metrics.

## unique_users(rows)

The number of distinct user_id values in the input, again with no filtering. This is implemented and is only used for capacity planning.

## daily_active_users(rows)

Returns a dict mapping each UTC calendar day, written as a YYYY-MM-DD string, to the number of active users on that day. Rows from employee accounts, meaning rows whose email ends with @internal.example, and rows whose is_bot is true are not real usage, so they are dropped before anything else happens. Each remaining row is assigned to a day by converting its ts to UTC and taking the calendar date of the result; the date as written in the string is never used. A user is active on a day when they have at least one remaining row on that day, and a user with many events on one day is counted once. Only days with at least one active user appear in the output, so a day whose rows were all dropped is absent, and empty input gives an empty dict.
