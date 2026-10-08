import pytest

from bot import ledger


def test_buy_fill_then_sell_settles_next_day():
    a = ledger.new_strategy_account()
    o = {"order_id": "1", "symbol": "XYZ", "side": "buy", "qty": 2.0, "limit_price": 50.0, "penalty_pct": 0.001}
    ledger.reserve_buy(a, o)
    assert a["cash"] == 400.0 and a["reserved"] == 100.0
    ledger.apply_fill(a, o, 2.0, 49.0, "2026-10-13")
    ledger.close_order(a, o)
    assert a["reserved"] == pytest.approx(0)
    cost = 2 * 49.0 * 1.001
    assert a["cash"] == pytest.approx(500 - cost)
    assert a["positions"]["XYZ"]["qty"] == 2.0

    s = {"order_id": "2", "symbol": "XYZ", "side": "sell", "qty": 2.0, "limit_price": 55.0, "penalty_pct": 0.001}
    ledger.reserve_sell(a, s)
    ledger.apply_fill(a, s, 2.0, 55.0, "2026-10-14")
    ledger.close_order(a, s)
    assert "XYZ" not in a["positions"]
    proceeds = 2 * 55.0 * 0.999
    assert a["unsettled"] == [{"amount": pytest.approx(proceeds), "settles": "2026-10-14"}]
    cash_before = a["cash"]
    ledger.settle(a, "2026-10-13")
    assert a["cash"] == cash_before  # not yet
    ledger.settle(a, "2026-10-14")
    assert a["cash"] == pytest.approx(cash_before + proceeds)
    assert a["realized_pnl"] == pytest.approx(proceeds - cost)


def test_partial_fill_then_cancel_releases_reservation():
    a = ledger.new_strategy_account()
    o = {"order_id": "1", "symbol": "XYZ", "side": "buy", "qty": 4.0, "limit_price": 25.0, "penalty_pct": 0.0}
    ledger.reserve_buy(a, o)
    ledger.apply_fill(a, o, 1.0, 25.0, "x")
    ledger.apply_fill(a, o, 1.0, 25.0, "x")  # same cumulative qty again: no double booking
    ledger.close_order(a, o)
    assert a["positions"]["XYZ"]["qty"] == 1.0
    assert a["reserved"] == pytest.approx(0)
    assert a["cash"] == pytest.approx(475.0)
    assert a["pending_orders"] == []


def test_no_overspend_or_oversell():
    a = ledger.new_strategy_account()
    with pytest.raises(ValueError):
        ledger.reserve_buy(a, {"order_id": "1", "symbol": "X", "side": "buy", "qty": 10, "limit_price": 60.0})
    with pytest.raises(Exception):
        ledger.reserve_sell(a, {"order_id": "2", "symbol": "X", "side": "sell", "qty": 1, "limit_price": 60.0})


def test_net_equity_charges_ai_cost():
    a = ledger.new_strategy_account()
    a["ai_cost"] = 1.25
    assert ledger.net_equity(a, {}) == pytest.approx(498.75)
