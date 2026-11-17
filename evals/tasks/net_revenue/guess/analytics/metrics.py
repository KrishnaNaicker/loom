"""Certified product metrics. Each definition lives in METRICS.md."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP


def order_count(orders):
    """Number of order rows. See METRICS.md, "order_count"."""
    return len(orders)


def _utc_day(ts):
    return datetime.fromisoformat(ts).astimezone(timezone.utc).date().isoformat()


def _cents(amount):
    return int((Decimal(amount) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def order_value_cents(orders):
    """Total order value in cents. See METRICS.md, "order_value_cents"."""
    return sum(_cents(o["amount"]) for o in orders)


def net_revenue_cents(orders, refunds):
    """Net revenue per UTC calendar day, in integer cents.

    orders: list of dicts with keys "order_id", "amount" (decimal string), "ts".
    refunds: list of dicts with keys "order_id", "amount" (decimal string), "ts".
    Returns a dict mapping "YYYY-MM-DD" to an int.
    """
    totals = {}
    for o in orders:
        day = _utc_day(o["ts"])
        totals[day] = totals.get(day, Decimal(0)) + Decimal(o["amount"])
    for r in refunds:
        day = _utc_day(r["ts"])
        totals[day] = totals.get(day, Decimal(0)) - Decimal(r["amount"])
    return {
        day: int((total * 100).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        for day, total in totals.items()
    }
