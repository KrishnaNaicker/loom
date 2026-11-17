# Certified metrics

This file defines the metrics computed in analytics/metrics.py. When the code and this document disagree, this document wins.

Orders are dicts with an order_id that is unique per order, an amount, and ts, an ISO-8601 timestamp with a UTC offset such as -05:00 or +00:00. Refunds are dicts with the order_id of the order being refunded, a positive amount, and a ts for when the refund was issued. Amounts are decimal strings and may carry more than two decimal places, for example "19.995".

## order_count(orders)

The number of rows in orders. This one is implemented and feeds the operations dashboard.

## order_value_cents(orders)

The total of all order amounts in integer cents, with no refunds and no per-day split. This is implemented and is used for rough sanity checks only.

## net_revenue_cents(orders, refunds)

Returns a dict mapping each UTC calendar day, written as a YYYY-MM-DD string, to that day's net revenue in integer cents. An order belongs to the calendar date of its ts after converting to UTC; the date written in the string is never used. A refund belongs to the day of the order it refers to, found through order_id, and not to the day the refund was issued, so the refund's own ts plays no part. A refund whose order_id matches no order is ignored, and an order may have several refunds, all of which are subtracted. Every amount is parsed as a decimal.Decimal and never as a float. For each day the net is the sum of that day's order amounts minus the sum of the refunds belonging to that day, computed exactly in dollars. Rounding happens once per day: the day's net is converted to cents and rounded to an integer using round-half-even on that total only, and individual orders and refunds are never rounded. The output has an entry for every day that has at least one order, even when the net is zero or negative, and empty input gives an empty dict.
