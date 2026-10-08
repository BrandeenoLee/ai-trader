"""Plain-code checks every AI proposal must pass before an order is sent.

The AI proposes; this module decides. Nothing here calls the AI.
A proposal looks like:
  {"action": "buy"|"sell"|"hold", "symbol": "AAPL", "amount_usd": 120.0,   # buys
   "sell_fraction": 0.5,                                                     # sells (0-1]
   "limit_price": 187.50, "confidence": 7, "reasoning": "..."}
Market info for the symbol:
  {"price", "bid", "ask", "avg_dollar_volume", "tradable", "exchange",
   "fractionable", "asset_class"}
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import config, ledger

MIN_ORDER_USD = 1.00  # Alpaca's minimum for fractional orders


@dataclass
class Decision:
    approved: bool
    reasons: list = field(default_factory=list)  # why rejected, or what was adjusted
    order: dict | None = None  # {"symbol","side","qty","limit_price","penalty_pct"}


def kill_switch_on() -> bool:
    return config.KILL_SWITCH_FILE.exists()


def tier_fraction(confidence) -> float:
    try:
        c = int(confidence)
    except (TypeError, ValueError):
        c = 1
    c = max(1, min(10, c))
    for lo, hi, frac in config.CONFIDENCE_TIERS:
        if lo <= c <= hi:
            return frac
    return config.CONFIDENCE_TIERS[0][2]


def spread_penalty(info: dict, strategy_id: str) -> float:
    bid, ask, price = info.get("bid") or 0, info.get("ask") or 0, info["price"]
    half = ((ask - bid) / 2 / price) if (bid > 0 and ask > bid and price > 0) else 0.0
    if config.STRATEGIES[strategy_id]["universe"] == "smallcap" or not is_liquid(info):
        half *= config.SMALLCAP_PENALTY_MULTIPLIER
    return max(config.BASE_SPREAD_PENALTY, round(half, 6))


def is_liquid(info: dict) -> bool:
    return (info["price"] >= config.LIQUID_MIN_PRICE
            and (info.get("avg_dollar_volume") or 0) >= config.LIQUID_MIN_DOLLAR_VOLUME)


def _floor(x: float, places: int) -> float:
    m = 10 ** places
    return math.floor(x * m) / m


def check(strategy_id: str, proposal: dict, acct: dict, info: dict | None,
          trades_today: int, max_trades_per_day: int) -> Decision:
    action = str(proposal.get("action", "hold")).lower()
    if action == "hold":
        return Decision(False, ["hold: no trade proposed"])
    if kill_switch_on():
        return Decision(False, ["kill switch is on"])
    if action not in ("buy", "sell"):
        return Decision(False, [f"action '{action}' not allowed (buy/sell/hold only)"])

    symbol = str(proposal.get("symbol", "")).upper().strip()
    if not symbol:
        return Decision(False, ["no symbol"])
    if symbol in config.EXCLUDED_SYMBOLS:
        return Decision(False, [f"{symbol} is on the exclusion list"])
    if trades_today >= max_trades_per_day:
        return Decision(False, ["daily trade limit reached"])
    if info is None:
        return Decision(False, [f"no market data for {symbol}"])
    if not info.get("tradable") or info.get("asset_class") != "us_equity":
        return Decision(False, [f"{symbol} is not a tradable US equity"])
    if info.get("exchange") not in config.ALLOWED_EXCHANGES:
        return Decision(False, [f"{symbol} trades on {info.get('exchange')} (listed exchanges only)"])

    price = info["price"]
    if not price or price <= 0:
        return Decision(False, ["invalid price"])
    universe = config.STRATEGIES[strategy_id]["universe"]
    if universe == "liquid" and not is_liquid(info):
        return Decision(False, [f"{symbol} fails liquidity floor for this strategy"])

    try:
        limit = float(proposal.get("limit_price") or 0)
    except (TypeError, ValueError):
        limit = 0.0
    if limit <= 0:
        return Decision(False, ["missing limit price (limit orders only)"])
    if abs(limit - price) / price > config.LIMIT_PRICE_BAND:
        return Decision(False, [f"limit {limit:.2f} is more than "
                                f"{config.LIMIT_PRICE_BAND:.0%} from price {price:.2f}"])
    limit = round(limit, 2 if limit >= 1 else 4)

    reasons = []
    penalty = spread_penalty(info, strategy_id)
    places = 4 if info.get("fractionable") else 0

    if action == "buy":
        try:
            amount = float(proposal.get("amount_usd") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            return Decision(False, ["buy amount must be positive"])
        # 1) settled cash only
        if amount > acct["cash"]:
            reasons.append(f"amount cut from ${amount:.2f} to settled cash ${acct['cash']:.2f}")
            amount = acct["cash"]
        # 2) confidence-scaled position cap
        eq = ledger.equity(acct, {symbol: price})
        cap = tier_fraction(proposal.get("confidence")) * eq
        held = ledger.position_value(acct, symbol, price)
        pending = sum(o["qty"] * o["limit_price"] for o in acct["pending_orders"]
                      if o["symbol"] == symbol and o["side"] == "buy")
        room = cap - held - pending
        if amount > room:
            reasons.append(f"amount cut to ${max(room, 0):.2f} by the "
                           f"{tier_fraction(proposal.get('confidence')):.0%} position cap")
            amount = room
        # 3) liquidity: never more than a small slice of daily volume
        adv = info.get("avg_dollar_volume") or 0
        if not is_liquid(info):
            max_slice = adv * config.SMALLCAP_MAX_ADV_FRACTION
            if amount > max_slice:
                reasons.append(f"amount cut to ${max_slice:.2f} (1% of avg daily volume)")
                amount = max_slice
        qty = _floor(amount / limit, places)
        if qty <= 0 or qty * limit < MIN_ORDER_USD:
            return Decision(False, reasons + ["order too small after limits"])
        order = {"symbol": symbol, "side": "buy", "qty": qty,
                 "limit_price": limit, "penalty_pct": penalty}
        return Decision(True, reasons, order)

    # sell
    pos = acct["positions"].get(symbol)
    free = (pos["qty"] - pos.get("reserved_qty", 0.0)) if pos else 0.0
    if free <= 0:
        return Decision(False, [f"no {symbol} shares to sell (no shorting)"])
    try:
        frac = float(proposal.get("sell_fraction") or 1.0)
    except (TypeError, ValueError):
        frac = 1.0
    frac = max(0.0, min(1.0, frac))
    qty = free if frac >= 0.999 else _floor(free * frac, 4 if info.get("fractionable") else 0)
    qty = round(min(qty, free), 9)
    if qty <= 0:
        return Decision(False, ["sell quantity rounds to zero"])
    order = {"symbol": symbol, "side": "sell", "qty": qty,
             "limit_price": limit, "penalty_pct": penalty}
    return Decision(True, reasons, order)
