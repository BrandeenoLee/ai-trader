from bot import config, guardrails, ledger

LIQUID = {"price": 100.0, "bid": 99.98, "ask": 100.02, "avg_dollar_volume": 5e8, "tradable": True,
          "exchange": "NASDAQ", "fractionable": True, "asset_class": "us_equity"}
SMALL = {"price": 2.0, "bid": 1.96, "ask": 2.04, "avg_dollar_volume": 400_000, "tradable": True,
         "exchange": "NASDAQ", "fractionable": False, "asset_class": "us_equity"}


def acct():
    return ledger.new_strategy_account()


def buy(sym="AAPL", amount=100, limit=100.5, conf=6):
    return {"action": "buy", "symbol": sym, "amount_usd": amount, "limit_price": limit, "confidence": conf}


def test_hold_is_not_an_order():
    assert not guardrails.check("A", {"action": "hold"}, acct(), LIQUID, 0, 6).approved


def test_basic_buy_approved():
    d = guardrails.check("A", buy(), acct(), LIQUID, 0, 6)
    assert d.approved and d.order["side"] == "buy"
    assert d.order["qty"] * d.order["limit_price"] <= 100.0 + 1e-9


def test_excluded_symbols_rejected():
    for s in ("GME", "AMC"):
        d = guardrails.check("E", buy(sym=s), acct(), LIQUID, 0, 6)
        assert not d.approved and "exclusion" in d.reasons[0]


def test_short_selling_impossible():
    d = guardrails.check("A", {"action": "sell", "symbol": "AAPL", "limit_price": 100, "confidence": 5},
                         acct(), LIQUID, 0, 6)
    assert not d.approved and "no shorting" in d.reasons[0]


def test_options_and_other_actions_rejected():
    d = guardrails.check("A", {"action": "buy_call", "symbol": "AAPL", "limit_price": 100}, acct(), LIQUID, 0, 6)
    assert not d.approved


def test_limit_price_band():
    d = guardrails.check("A", buy(limit=110), acct(), LIQUID, 0, 6)
    assert not d.approved and "more than" in d.reasons[0]


def test_market_orders_rejected():
    p = buy()
    p.pop("limit_price")
    assert not guardrails.check("A", p, acct(), LIQUID, 0, 6).approved


def test_confidence_tiers_cap_position_size():
    for conf, frac in ((2, 0.15), (6, 0.35), (9, 0.75)):
        d = guardrails.check("A", buy(amount=500, conf=conf), acct(), LIQUID, 0, 6)
        assert d.approved
        assert d.order["qty"] * d.order["limit_price"] <= frac * 500 + 0.01


def test_cap_counts_existing_position_and_open_orders():
    a = acct()
    a["positions"]["AAPL"] = {"qty": 1.0, "cost_basis": 100.0, "reserved_qty": 0.0}
    a["cash"] = 400.0
    d = guardrails.check("A", buy(amount=500, conf=6), a, LIQUID, 0, 6)  # 35% of 500 = 175, hold 100
    assert d.approved and d.order["qty"] * d.order["limit_price"] <= 75.01


def test_cannot_spend_unsettled_cash():
    a = acct()
    a["cash"] = 20.0
    a["unsettled"] = [{"amount": 480.0, "settles": "2099-01-01"}]
    d = guardrails.check("A", buy(amount=300, conf=9), a, LIQUID, 0, 6)
    assert d.approved and d.order["qty"] * d.order["limit_price"] <= 20.0 + 1e-9


def test_liquid_strategies_cannot_buy_illiquid_names():
    d = guardrails.check("A", buy(sym="TINY", amount=50, limit=2.0), acct(), SMALL, 0, 6)
    assert not d.approved and "liquidity" in d.reasons[0]


def test_smallcap_order_capped_by_volume_and_whole_shares():
    d = guardrails.check("D", buy(sym="TINY", amount=375, limit=2.0, conf=9), acct(), SMALL, 0, 6)
    assert d.approved
    assert d.order["qty"] == int(d.order["qty"])  # not fractionable
    assert d.order["qty"] * 2.0 <= 400_000 * config.SMALLCAP_MAX_ADV_FRACTION + 1e-9
    assert d.order["penalty_pct"] > config.BASE_SPREAD_PENALTY


def test_otc_rejected():
    d = guardrails.check("D", buy(sym="PNKY", limit=2.0), acct(), {**SMALL, "exchange": "OTC"}, 0, 6)
    assert not d.approved


def test_daily_limit_and_kill_switch(isolated):
    assert not guardrails.check("A", buy(), acct(), LIQUID, 6, 6).approved
    config.KILL_SWITCH_FILE.write_text("stop")
    d = guardrails.check("A", buy(), acct(), LIQUID, 0, 6)
    assert not d.approved and "kill switch" in d.reasons[0]


def test_sell_fraction_and_reserved_shares():
    a = acct()
    a["positions"]["AAPL"] = {"qty": 2.0, "cost_basis": 200.0, "reserved_qty": 1.0}
    d = guardrails.check("A", {"action": "sell", "symbol": "AAPL", "sell_fraction": 1.0,
                               "limit_price": 100, "confidence": 5}, a, LIQUID, 0, 6)
    assert d.approved and d.order["qty"] == 1.0  # only the unreserved share
