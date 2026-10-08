"""Friday review: score the week, let Claude rewrite each strategy's notes, adjust
check-in levels, email the recap and rebuild the dashboard.

Usage:
  python -m bot.review              # the weekly review (run after Friday's close)
  python -m bot.review --design-e   # have Claude design strategy E (run once before week 1)
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ai as ai_mod
from . import broker as broker_mod
from . import config, journal, ledger, report, state, strategies
from .checkin import benchmark_equity, reconcile, snapshot_equity

ET = ZoneInfo("America/New_York")

REVIEW_SYSTEM = """You are the weekly reviewer for one strategy in an AI paper-trading tournament.
Five strategies each trade a virtual $500; the goal is to beat SPY buy-and-hold after costs.
You will see this week's results, every decision with its reasoning and outcome, and the current
strategy notes. Rewrite the notes so next week's trader does better.

Guidance:
- One week is a small sample. Change rules gradually; don't overfit to one lucky or unlucky trade.
- Keep the notes short and concrete (under ~300 words): rules, sizing habits, things to avoid.
- Keep the strategy's identity; improve how it's executed rather than turning it into a different strategy.
- Note whether high-confidence trades actually did better than low-confidence ones, and adjust how
  confidence should be used.
- The hard rules (cash only, no shorting, limit orders, exclusions, confidence-based size caps) are
  enforced in code and need not be repeated."""

DESIGN_E_EXTRA = """
This strategy is "Claude's pick": you may redesign it from scratch each week into whatever
strategy you are now most confident can beat SPY with $500 under these rules. The notes you write
ARE the strategy: state the approach, the universe, entry and exit rules, and sizing. Then give
an honest 1-10 confidence that it beats SPY next week."""


def week_start_row(hist: list, today: str) -> dict | None:
    """Equity row from the last trading day before this week's Monday."""
    d = date.fromisoformat(today)
    monday = (d - timedelta(days=d.weekday())).isoformat()
    prior = [r for r in hist if r["date"] < monday]
    return prior[-1] if prior else (hist[0] if hist else None)


def confidence_table(prices: dict) -> dict:
    """Average return of filled buys by stated confidence tier (fill -> exit or latest price)."""
    orders = {r["order_id"]: r for r in journal.entries(kinds=("order",))}
    sells = {}
    for f in journal.entries(kinds=("fill",)):
        if f["side"] == "sell":
            sells.setdefault((f["strategy"], f["symbol"]), []).append(f)
    tiers = {"1-4": [], "5-7": [], "8-10": []}
    for f in journal.entries(kinds=("fill",)):
        if f["side"] != "buy":
            continue
        o = orders.get(f["order_id"], {})
        conf = o.get("confidence")
        if conf is None:
            continue
        later = [s for s in sells.get((f["strategy"], f["symbol"]), []) if s["ts"] > f["ts"]]
        exit_px = later[0]["eff_price"] if later else prices.get(f["symbol"])
        if not exit_px:
            continue
        r = (exit_px / f["eff_price"] - 1) * 100
        key = "1-4" if conf <= 4 else ("5-7" if conf <= 7 else "8-10")
        tiers[key].append(r)
    return {k: {"n": len(v), "avg": (sum(v) / len(v)) if v else None} for k, v in tiers.items()}


def review_prompt(sid: str, perf: dict, week_entries: list, notes: str, conf: dict) -> str:
    lines = [f"Strategy {sid}: {config.STRATEGIES[sid]['name']}",
             f"This week: {perf['week_ret']:+.2f}% (SPY {perf['spy_week']:+.2f}%). "
             f"Since start: {perf['total_ret']:+.2f}% (SPY {perf['spy_total']:+.2f}%). "
             f"AI cost to date ${perf['ai_cost']:.2f}; spread penalties paid ${perf['penalty']:.2f}.",
             f"Current holdings: {perf['holdings'] or 'cash only'}", "",
             "Tournament-wide: average return of filled buys by stated confidence (all strategies):"]
    for t, v in conf.items():
        lines.append(f"- {t}: {v['n']} buys, avg {v['avg']:+.2f}%" if v["n"] else f"- {t}: none")
    lines += ["", "## This week's journal"]
    for r in week_entries:
        if r["kind"] == "decision":
            acts = "; ".join(f"{o.get('action')} {o.get('symbol')} conf {o.get('confidence')} "
                             f"({o.get('reasoning', '')}) -> {o.get('result')}" for o in r.get("orders", []))
            lines.append(f"- {r['ts'][:16]} DECISION: {acts or 'hold'}. {r.get('summary', '')}")
        elif r["kind"] == "fill":
            extra = f", P&L {r['pnl']:+.2f}" if r.get("pnl") is not None else ""
            lines.append(f"- {r['ts'][:16]} FILL {r['side']} {r['qty']:g} {r['symbol']} @ {r['eff_price']:.2f}{extra}")
        elif r["kind"] == "order_closed":
            lines.append(f"- {r['ts'][:16]} ORDER {r['status']} {r['symbol']} (filled {r['filled_qty']:g})")
    if len(lines) > 200:
        lines = lines[:200] + ["- (journal truncated)"]
    lines += ["", "<current_notes>", notes.strip(), "</current_notes>", "",
              "Submit the review with the complete updated notes."]
    return "\n".join(lines)


def run(broker=None, ai=None, today: str | None = None, send: bool = True) -> dict:
    broker = broker or broker_mod.make_broker()
    ai = ai or ai_mod.make_ai()
    now_et = broker.clock()["now"].astimezone(ET)
    today = today or now_et.date().isoformat()
    led = ledger.load()
    if led is None:
        print("No ledger yet; the tournament hasn't started.")
        return {}
    reconcile(broker, led, today)
    snap = strategies.MarketSnapshot(broker)
    snapshot_equity(led, snap, today)

    hist = led["equity_history"]
    now_row, base = hist[-1], week_start_row(hist, today)
    spy_now = now_row[config.BENCHMARK]
    spy_week = (spy_now / base[config.BENCHMARK] - 1) * 100
    spy_total = (spy_now / config.STARTING_CASH - 1) * 100

    held = {s for a in led["strategies"].values() for s in a["positions"]}
    prices = {s: (snap.price(s) or 0) for s in held}
    conf = confidence_table({**prices, **{s: p["price"] for s, p in snap.prices.items()}})
    monday = (date.fromisoformat(today) - timedelta(days=date.fromisoformat(today).weekday())).isoformat()
    week = {"date": today, "benchmark": {"week_ret": spy_week, "total_ret": spy_total},
            "strategies": {}, "confidence": conf}

    over_cap = ai_mod.over_hard_cap()
    week_costs = {}
    for e in journal.entries(kinds=("decision",), since=monday):
        week_costs[e["strategy"]] = week_costs.get(e["strategy"], 0) + e.get("cost", 0)

    for sid, acct in led["strategies"].items():
        eq = now_row[sid]
        week_ret = (eq / base[sid] - 1) * 100
        total_ret = (eq / config.STARTING_CASH - 1) * 100
        trades = sum(1 for e in journal.entries(sid, kinds=("fill",), since=monday))
        perf = {"week_ret": week_ret, "total_ret": total_ret, "spy_week": spy_week, "spy_total": spy_total,
                "ai_cost": acct["ai_cost"], "penalty": acct["penalty_paid"],
                "holdings": ", ".join(f"{s} {p['qty']:g}" for s, p in acct["positions"].items())}
        result = {"week_ret": week_ret, "total_ret": total_ret, "vs_spy": total_ret - spy_total,
                  "trades": trades, "ai_cost_week": week_costs.get(sid, 0.0)}
        # learning step
        notes_path = config.NOTES_DIR / f"{sid}.md"
        if not over_cap:
            try:
                system = REVIEW_SYSTEM + (DESIGN_E_EXTRA if sid == "E" else "")
                user = review_prompt(sid, perf, journal.entries(sid, since=monday), notes_path.read_text(), conf)
                out, usage = ai.review(system, user)
                cost = ai_mod.record_spend(sid, config.REVIEW_MODEL, usage)
                acct["ai_cost"] = round(acct["ai_cost"] + cost, 6)
                result["ai_cost_week"] += cost
                if out.get("notes_markdown"):
                    notes_path.write_text(out["notes_markdown"].strip() + "\n")
                result["self_assessment"] = out.get("self_assessment", "")
                result["confidence_beat_spy"] = out.get("confidence_beat_spy")
                journal.log("review", sid, lessons=out.get("lessons", ""),
                            self_assessment=out.get("self_assessment", ""),
                            confidence_beat_spy=out.get("confidence_beat_spy"), cost=round(cost, 5))
            except Exception as e:
                traceback.print_exc()
                journal.log("error", sid, where="review", error=str(e))
        # earned check-ins: beat SPY this week -> one more per day, else one fewer
        lvl = acct["checkin_level"] + (1 if week_ret > spy_week else -1)
        acct["checkin_level"] = max(config.CHECKIN_MIN_LEVEL, min(config.CHECKIN_MAX_LEVEL, lvl))
        result["level"] = acct["checkin_level"]
        week["strategies"][sid] = result

    # E's confidence track record: last week's stated confidence vs this week's outcome
    past = state.read_jsonl(report.WEEKLY_FILE)
    log = past[-1].get("e_confidence_log", []) if past else []
    if not past:  # first week: seed with the confidence stated at design time
        seed = [r for r in journal.entries("E", kinds=("review",)) if r["ts"][:10] < monday
                and r.get("confidence_beat_spy") is not None]
        if seed:
            log = [{"week": "design", "confidence": seed[-1]["confidence_beat_spy"], "beat": None}]
    if log and log[-1].get("beat") is None:
        log[-1]["beat"] = week["strategies"]["E"]["week_ret"] > spy_week
    if week["strategies"]["E"].get("confidence_beat_spy") is not None:
        log.append({"week": today, "confidence": week["strategies"]["E"]["confidence_beat_spy"], "beat": None})
    week["e_confidence_log"] = log
    week["month_spend"] = ai_mod.month_total()

    state.append_jsonl(report.WEEKLY_FILE, week)
    ledger.save(led)
    report.build_dashboard(led)
    body = report.recap_text(week)
    if send:
        report.send_email(f"Trading tournament recap - week ending {today}", body)
    print(body)
    return week


def design_e(ai=None) -> str:
    ai = ai or ai_mod.make_ai()
    path = config.NOTES_DIR / "E.md"
    user = ("Week 0: no trades yet. Design the strategy you are most confident can beat SPY "
            "over the next 6-8 weeks with $500 under the hard rules. The trader will see account "
            "status, momentum leaders, sharp recent drops, small-cap movers and headlines at each "
            "check-in (2-5 times per trading day).\n\n<current_notes>\n" + path.read_text().strip()
            + "\n</current_notes>")
    out, usage = ai.review(REVIEW_SYSTEM + DESIGN_E_EXTRA, user)
    ai_mod.record_spend("E", config.REVIEW_MODEL, usage)
    notes = out.get("notes_markdown", "").strip()
    if notes:
        path.write_text(notes + "\n")
        journal.log("review", "E", lessons="Initial strategy design", self_assessment=out.get("self_assessment", ""),
                    confidence_beat_spy=out.get("confidence_beat_spy"))
    print(notes)
    print(f"\nConfidence it beats SPY next week: {out.get('confidence_beat_spy')}/10")
    return notes


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--design-e", action="store_true", help="have Claude design strategy E")
    p.add_argument("--no-email", action="store_true")
    args = p.parse_args(argv)
    if args.design_e:
        design_e()
    else:
        run(send=not args.no_email)


if __name__ == "__main__":
    sys.exit(main())
