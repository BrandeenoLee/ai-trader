"""One check-in run: reconcile orders, settle cash, let eligible strategies decide, place orders.

Usage:
  python -m bot.checkin            # normal scheduled run (decides which slot this is)
  python -m bot.checkin --force    # run every strategy now, ignoring slots (market must be open)
"""
from __future__ import annotations

import argparse
import sys
import traceback
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import ai as ai_mod
from . import broker as broker_mod
from . import config, guardrails, journal, ledger, report, state, strategies

ET = ZoneInfo("America/New_York")
SLOTS_FILE = "slots_run.json"
TERMINAL = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced", "stopped", "suspended"}


def _slot_minutes(s: str) -> int:
    h, m = map(int, s.split(":"))
    return h * 60 + m


def current_slot(now_utc: datetime, done: list | None = None) -> int | None:
    """The slot to run now: the highest-priority slot whose time has passed today and that
    hasn't run yet. A late or missed trigger is caught up by the next one, but nothing new
    starts in the last minutes before the close."""
    et = now_utc.astimezone(ET)
    minutes = et.hour * 60 + et.minute
    if minutes >= config.LAST_CHECKIN_ET_MIN:
        return None
    done = done or []
    due = [i for i, s in enumerate(config.CHECKIN_SLOTS_ET)
           if _slot_minutes(s) <= minutes and i not in done]
    return min(due) if due else None


def ensure_ledger(broker, today: str) -> dict:
    led = ledger.load()
    if led is None:
        led = ledger.new_ledger(today)
        journal.log("start", None, note="tournament started", date=today)
    if led["benchmark"] is None:
        p = broker.latest_prices([config.BENCHMARK]).get(config.BENCHMARK)
        if p:
            led["benchmark"] = {"symbol": config.BENCHMARK, "price": p["price"], "date": today,
                                "qty": config.STARTING_CASH / p["price"]}
    return led


def reconcile(broker, led: dict, today: str) -> None:
    settle_day = broker.next_trading_day(today)
    for sid, acct in led["strategies"].items():
        for order in list(acct["pending_orders"]):
            try:
                st = broker.order_status(order["order_id"])
            except Exception as e:
                journal.log("error", sid, where="order_status", order=order["order_id"], error=str(e))
                continue
            if st["filled_qty"] > order.get("booked_qty", 0):
                booked = ledger.apply_fill(acct, order, st["filled_qty"], st["filled_avg_price"], settle_day)
                if booked:
                    journal.log("fill", sid, symbol=order["symbol"], order_id=order["order_id"],
                                fill_price=st["filled_avg_price"], **booked)
            if st["status"] in TERMINAL:
                ledger.close_order(acct, order)
                if st["status"] != "filled":
                    journal.log("order_closed", sid, symbol=order["symbol"], order_id=order["order_id"],
                                status=st["status"], filled_qty=st["filled_qty"])
        ledger.settle(acct, today)


def trades_today(sid: str, today_et: str) -> int:
    return sum(1 for r in journal.entries(sid, kinds=("order",)) if r.get("date_et") == today_et)


def eligible(led: dict, snap, slot: int | None, force: bool) -> list:
    if ai_mod.over_hard_cap():
        journal.log("budget", None, note="monthly hard cap reached; no AI calls")
        return []
    out = []
    spy_eq = benchmark_equity(led, snap)
    behind_pace = ai_mod.ahead_of_pace()
    for sid, acct in led["strategies"].items():
        if force:
            out.append(sid)
            continue
        level = acct["checkin_level"]
        if slot is None or slot >= level:
            continue
        if behind_pace and slot > 0:
            prices = {s: snap.price(s) or 0 for s in acct["positions"]}
            if ledger.net_equity(acct, prices) < spy_eq:
                continue  # spending ahead of target: trailing strategies keep only their first slot
        out.append(sid)
    return out


def benchmark_equity(led: dict, snap) -> float:
    b = led.get("benchmark")
    if not b:
        return config.STARTING_CASH
    p = snap.price(b["symbol"]) or b["price"]
    return round(b["qty"] * p, 4)


def run_strategy(sid: str, led: dict, snap, broker, ai, now_et: datetime, slot_info: str) -> bool:
    acct = led["strategies"][sid]
    notes = (config.NOTES_DIR / f"{sid}.md").read_text()
    if sid == "E" and "No strategy defined yet" in notes:
        journal.log("skip", sid, reason="strategy E not designed yet")
        return False
    system = strategies.system_prompt(sid, notes)
    user = strategies.user_prompt(sid, acct, snap, now_et.strftime("%a %Y-%m-%d %H:%M"), slot_info)
    decision, usage = ai.decide(system, user)
    cost = ai_mod.record_spend(sid, config.TRADER_MODEL, usage)
    acct["ai_cost"] = round(acct["ai_cost"] + cost, 6)

    today_et = now_et.date().isoformat()
    proposals = sorted(decision.get("orders", []) or [], key=lambda o: o.get("action") != "sell")
    results = []
    for prop in proposals:
        sym = str(prop.get("symbol", "")).upper().strip()
        info = strategies.market_info(broker, sym, snap.cache) if sym else None
        d = guardrails.check(sid, prop, acct, info, trades_today(sid, today_et), config.MAX_ORDERS_PER_DAY)
        entry = {**prop, "symbol": sym}
        if not d.approved:
            entry["result"] = "rejected: " + "; ".join(d.reasons)
            results.append(entry)
            continue
        order = d.order
        client_id = f"{sid}-{uuid.uuid4().hex[:12]}"
        try:
            oid = broker.submit_limit(order["symbol"], order["side"], order["qty"],
                                      order["limit_price"], client_id)
        except Exception as e:
            entry["result"] = f"error: {e}"
            results.append(entry)
            journal.log("error", sid, where="submit", symbol=sym, error=str(e))
            continue
        rec = {**order, "order_id": oid, "client_id": client_id, "confidence": prop.get("confidence"),
               "submitted": now_et.isoformat()}
        (ledger.reserve_buy if order["side"] == "buy" else ledger.reserve_sell)(acct, rec)
        entry["result"] = f"placed {order['side']} {order['qty']:g} @ {order['limit_price']}"
        if d.reasons:
            entry["result"] += " (" + "; ".join(d.reasons) + ")"
        results.append(entry)
        journal.log("order", sid, date_et=today_et, **rec)
    journal.log("decision", sid, slot=slot_info, summary=decision.get("summary", ""),
                orders=results, cost=round(cost, 5), usage=usage)
    return True


def snapshot_equity(led: dict, snap, today: str) -> None:
    row = {"date": today}
    for sid, acct in led["strategies"].items():
        prices = {s: snap.price(s) or 0 for s in acct["positions"]}
        row[sid] = ledger.net_equity(acct, prices)
    row[config.BENCHMARK] = benchmark_equity(led, snap)
    hist = led["equity_history"]
    if hist and hist[-1]["date"] == today:
        hist[-1] = row
    else:
        hist.append(row)


def run(broker=None, ai=None, force: bool = False, now_utc: datetime | None = None) -> dict:
    broker = broker or broker_mod.make_broker()
    ai = ai or ai_mod.make_ai()
    clock = broker.clock()
    now_utc = now_utc or clock["now"]
    now_et = now_utc.astimezone(ET)
    today = now_et.date().isoformat()
    if not clock["is_open"]:
        print("Market closed; nothing to do.")
        return {"ran": []}
    slot = None
    if not force:
        done = state.load(SLOTS_FILE, {})
        slot = current_slot(now_utc, done.get(today, []))
        if slot is None:
            print(f"No check-in slot due at {now_et:%H:%M} ET.")
            return {"ran": []}
        state.save(SLOTS_FILE, {today: done.get(today, []) + [slot]})

    led = ensure_ledger(broker, today)
    reconcile(broker, led, today)
    snap = strategies.MarketSnapshot(broker)
    ran = []
    if guardrails.kill_switch_on():
        journal.log("kill_switch", None, note="kill switch on; no trading")
    else:
        slot_label = "manual run" if force else f"slot {slot + 1}"
        for sid in eligible(led, snap, slot, force):
            acct = led["strategies"][sid]
            info = f"{slot_label}, check-in level {acct['checkin_level']}/day"
            try:
                if run_strategy(sid, led, snap, broker, ai, now_et, info):
                    ran.append(sid)
            except Exception as e:
                traceback.print_exc()
                journal.log("error", sid, where="run_strategy", error=str(e))
    snapshot_equity(led, snap, today)
    ledger.save(led)
    report.build_dashboard(led)
    print(f"Check-in done at {now_et:%H:%M} ET; strategies run: {ran or 'none'}")
    return {"ran": ran}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="run every strategy now, ignoring slots")
    args = p.parse_args(argv)
    run(force=args.force)


if __name__ == "__main__":
    from .ghreport import run_reported
    sys.exit(run_reported(main))
