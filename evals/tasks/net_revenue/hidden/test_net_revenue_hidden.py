from analytics.metrics import net_revenue_cents


def order(oid, amount, ts):
    return {"order_id": oid, "amount": amount, "ts": ts}


def refund(oid, amount, ts):
    return {"order_id": oid, "amount": amount, "ts": ts}


def test_refund_attributed_to_original_order_day():
    # Rule 2: refund issued on 03-05 reduces the 03-01 total, not 03-05.
    orders = [
        order("a", "20.00", "2026-03-01T09:00:00+00:00"),
        order("b", "8.00", "2026-03-05T09:00:00+00:00"),
    ]
    refunds = [refund("a", "5.00", "2026-03-05T12:00:00+00:00")]
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 1500, "2026-03-05": 800}


def test_rounding_once_on_day_total():
    # Rule 5: 0.005 + 0.005 = 0.010 -> 1 cent (per-row half-even rounding gives 0).
    orders = [
        order("a", "0.005", "2026-03-01T09:00:00+00:00"),
        order("b", "0.005", "2026-03-01T10:00:00+00:00"),
    ]
    assert net_revenue_cents(orders, []) == {"2026-03-01": 1}
    # 0.015 * 2 = 0.030 -> 3 cents (per-row half-even gives 2 + 2 = 4).
    orders = [
        order("a", "0.015", "2026-03-02T09:00:00+00:00"),
        order("b", "0.015", "2026-03-02T10:00:00+00:00"),
    ]
    assert net_revenue_cents(orders, []) == {"2026-03-02": 3}


def test_round_half_even_not_half_up():
    # Rule 5: 10.005 -> 1000.5 cents -> 1000; 19.995 -> 1999.5 -> 2000.
    orders = [
        order("a", "10.005", "2026-03-01T09:00:00+00:00"),
        order("b", "19.995", "2026-03-02T09:00:00+00:00"),
    ]
    assert net_revenue_cents(orders, []) == {"2026-03-01": 1000, "2026-03-02": 2000}


def test_exact_decimal_arithmetic():
    # Rule 4: floats drift; 0.1 + 0.2 and large sums must be exact.
    orders = [
        order("a", "1000000.10", "2026-03-01T09:00:00+00:00"),
        order("b", "0.20", "2026-03-01T10:00:00+00:00"),
        order("c", "0.285", "2026-03-01T11:00:00+00:00"),
        order("d", "0.145", "2026-03-01T12:00:00+00:00"),
    ]
    refunds = [refund("c", "0.001", "2026-03-04T00:00:00+00:00")]
    # total = 1000000.10 + 0.20 + 0.285 + 0.145 - 0.001 = 1000000.729 -> 100000072.9 -> 100000073
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 100000073}


def test_day_is_utc_and_multiple_refunds_and_unknown_order():
    # Rules 1 and 3: 23:30-05:00 is the next UTC day; several refunds all apply;
    # a refund for an unknown order is ignored.
    orders = [
        order("a", "30.00", "2026-03-01T23:30:00-05:00"),
        order("b", "1.00", "2026-03-01T12:00:00+00:00"),
    ]
    refunds = [
        refund("a", "10.00", "2026-03-10T00:00:00+00:00"),
        refund("a", "2.50", "2026-03-11T00:00:00+00:00"),
        refund("zzz", "99.00", "2026-03-01T12:00:00+00:00"),
    ]
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 100, "2026-03-02": 1750}


def test_day_with_net_zero_still_present():
    # Rule 6: a fully refunded day appears with 0.
    orders = [order("a", "9.99", "2026-03-01T09:00:00+00:00")]
    refunds = [refund("a", "9.99", "2026-03-02T09:00:00+00:00")]
    assert net_revenue_cents(orders, refunds) == {"2026-03-01": 0}
