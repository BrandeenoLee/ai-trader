"""Virtual sub-accounts: each strategy trades its own $500 inside one Alpaca paper account.

Cash model (mirrors a real cash account):
  cash        settled cash, free to spend
  reserved    cash held back for open buy orders
  unsettled   sale proceeds waiting for settlement (next trading day)
Positions track qty, qty reserved by open sell orders, and cost basis.
Simulated spread penalties are applied to every fill so paper results stay honest.
"""
from __future__ import annotations

from . import config, state

LEDGER_FILE = "ledger.json"


def new_strategy_account(level: int = config.CHECKIN_START_LEVEL) -> dict:
    return {
        "cash": config.STARTING_CASH,
        "reserved": 0.0,
        "unsettled": [],
        "positions": {},
        "pending_orders": [],
        "realized_pnl": 0.0,
        "penalty_paid": 0.0,
        "ai_cost": 0.0,
        "checkin_level": level,
        "trades": 0,
    }


def new_ledger(start_date: str) -> dict:
    return {
        "started": start_date,
        "strategies": {sid: new_strategy_account() for sid in config.STRATEGIES},
        "benchmark": None,  # filled on first run: {"symbol","qty","price","date"}
        "equity_history": [],  # [{"date", "A": eq, ..., "SPY": eq}]
    }


def load() -> dict | None:
    return state.load(LEDGER_FILE, None)


def save(ledger: dict) -> None:
    state.save(LEDGER_FILE, ledger)


# --- Settlement -------------------------------------------------------------

def settle(acct: dict, today: str) -> float:
    """Move proceeds whose settlement date has arrived into spendable cash."""
    still, freed = [], 0.0
    for u in acct["unsettled"]:
        if u["settles"] <= today:
            freed += u["amount"]
        else:
            still.append(u)
    acct["unsettled"] = still
    acct["cash"] = round(acct["cash"] + freed, 6)
    return freed


# --- Order bookkeeping ------------------------------------------------------

def reserve_buy(acct: dict, order: dict) -> None:
    amount = order["qty"] * order["limit_price"]
    if amount > acct["cash"] + 1e-6:
        raise ValueError("insufficient settled cash for reservation")
    acct["cash"] = round(acct["cash"] - amount, 6)
    acct["reserved"] = round(acct["reserved"] + amount, 6)
    order["reserved_cash"] = amount
    acct["pending_orders"].append(order)


def reserve_sell(acct: dict, order: dict) -> None:
    pos = acct["positions"].get(order["symbol"])
    free = (pos["qty"] - pos.get("reserved_qty", 0.0)) if pos else 0.0
    if order["qty"] > free + 1e-9:
        raise ValueError("cannot sell more than held (no shorting)")
    pos["reserved_qty"] = pos.get("reserved_qty", 0.0) + order["qty"]
    acct["pending_orders"].append(order)


def apply_fill(acct: dict, order: dict, filled_qty: float, fill_price: float,
               settle_date: str) -> dict:
    """Book a (partial or full) fill. Returns a summary of what was booked."""
    penalty = order.get("penalty_pct", config.BASE_SPREAD_PENALTY)
    sym = order["symbol"]
    booked = order.setdefault("booked_qty", 0.0)
    new_qty = round(filled_qty - booked, 9)
    if new_qty <= 0:
        return {}
    if order["side"] == "buy":
        eff_price = fill_price * (1 + penalty)
        cost = new_qty * eff_price
        release = new_qty * order["limit_price"]
        acct["reserved"] = round(acct["reserved"] - release, 6)
        order["reserved_cash"] = round(order["reserved_cash"] - release, 6)
        # difference between reserved (limit) and actual cost goes back to cash
        acct["cash"] = round(acct["cash"] + release - cost, 6)
        pos = acct["positions"].setdefault(sym, {"qty": 0.0, "cost_basis": 0.0, "reserved_qty": 0.0})
        pos["qty"] = round(pos["qty"] + new_qty, 9)
        pos["cost_basis"] = round(pos["cost_basis"] + cost, 6)
        acct["penalty_paid"] = round(acct["penalty_paid"] + new_qty * fill_price * penalty, 6)
        result = {"side": "buy", "qty": new_qty, "eff_price": eff_price, "cost": cost}
    else:
        pos = acct["positions"][sym]
        eff_price = fill_price * (1 - penalty)
        proceeds = new_qty * eff_price
        avg_cost = pos["cost_basis"] / pos["qty"] if pos["qty"] else 0.0
        basis_out = avg_cost * new_qty
        pos["qty"] = round(pos["qty"] - new_qty, 9)
        pos["reserved_qty"] = round(pos.get("reserved_qty", 0.0) - new_qty, 9)
        pos["cost_basis"] = round(pos["cost_basis"] - basis_out, 6)
        pnl = proceeds - basis_out
        acct["realized_pnl"] = round(acct["realized_pnl"] + pnl, 6)
        acct["penalty_paid"] = round(acct["penalty_paid"] + new_qty * fill_price * penalty, 6)
        acct["unsettled"].append({"amount": round(proceeds, 6), "settles": settle_date})
        if pos["qty"] <= 1e-9:
            del acct["positions"][sym]
        result = {"side": "sell", "qty": new_qty, "eff_price": eff_price,
                  "proceeds": proceeds, "pnl": pnl}
    order["booked_qty"] = round(booked + new_qty, 9)
    acct["trades"] += 1
    return result


def close_order(acct: dict, order: dict) -> None:
    """Order is done (filled, canceled or expired): release anything still held."""
    if order["side"] == "buy":
        left = order.get("reserved_cash", 0.0)
        acct["reserved"] = round(acct["reserved"] - left, 6)
        acct["cash"] = round(acct["cash"] + left, 6)
        order["reserved_cash"] = 0.0
    else:
        pos = acct["positions"].get(order["symbol"])
        if pos:
            left = order["qty"] - order.get("booked_qty", 0.0)
            pos["reserved_qty"] = max(0.0, round(pos.get("reserved_qty", 0.0) - left, 9))
    acct["pending_orders"] = [o for o in acct["pending_orders"] if o["order_id"] != order["order_id"]]


# --- Valuation ---------------------------------------------------------------

def equity(acct: dict, prices: dict) -> float:
    """Gross equity: cash + reserved + unsettled + positions at market."""
    total = acct["cash"] + acct["reserved"] + sum(u["amount"] for u in acct["unsettled"])
    for sym, pos in acct["positions"].items():
        total += pos["qty"] * prices.get(sym, pos["cost_basis"] / pos["qty"] if pos["qty"] else 0)
    return round(total, 4)


def net_equity(acct: dict, prices: dict) -> float:
    """Equity after charging the strategy for its own AI usage."""
    return round(equity(acct, prices) - acct["ai_cost"], 4)


def position_value(acct: dict, symbol: str, price: float) -> float:
    pos = acct["positions"].get(symbol)
    return pos["qty"] * price if pos else 0.0
