from analytics.metrics import net_revenue_cents


def order(oid, amount, ts):
    return {"order_id": oid, "amount": amount, "ts": ts}


def refund(oid, amount, ts):
    return {"order_id": oid, "amount": amount, "ts": ts}


def test_sums_orders_per_day():
    orders = [
        order("a", "10.00", "2026-03-01T09:00:00+00:00"),
        order("b", "5.50", "2026-03-01T10:00:00+00:00"),
        order("c", "7.25", "2026-03-02T10:00:00+00:00"),
    ]
    assert net_revenue_cents(orders, []) == {"2026-03-01": 1550, "2026-03-02": 725}


def test_refund_subtracted():
    orders = [order("a", "20.00", "2026-03-01T09:00:00+00:00")]
    refunds = [refund("a", "4.50", "2026-03-01T15:00:00+00:00")]
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 1550}


def test_refund_issued_later_reduces_the_original_orders_day():
    orders = [order("a", "20.00", "2026-03-01T09:00:00+00:00")]
    refunds = [refund("a", "5.00", "2026-03-03T15:00:00+00:00")]
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 1500}


def test_empty_input():
    assert net_revenue_cents([], []) == {}
