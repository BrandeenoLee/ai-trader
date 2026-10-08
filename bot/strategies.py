"""Strategy definitions and the market context each strategy sees at a check-in."""
from __future__ import annotations

from statistics import mean, pstdev

from . import config, guardrails, journal, ledger

DESCRIPTIONS = {
    "A": ("Momentum: ride the strongest stocks and ETFs over recent weeks and rotate out as "
          "they weaken. Favour names with strong 20- and 60-day returns trading above their "
          "50-day average."),
    "B": ("Mean reversion: buy solid, liquid stocks after sharp short-term drops that look like "
          "noise rather than bad news, and sell on the bounce. Avoid catching falling knives "
          "with a real fundamental problem."),
    "C": ("Catalyst reader: trade on news. Read the headlines and decide whether the market has "
          "under- or over-reacted. No catalyst, no trade."),
    "D": ("Small-cap explorer: hunt small, thinly traded names other bots skip, using movers and "
          "most-active lists. Spreads are wide and fills are worse, so only act when the edge is "
          "clearly bigger than the trading cost."),
    "E": ("Claude's pick: trade the strategy defined in your notes. You designed it yourself in "
          "the weekly review; follow it, and note where it is or isn't working."),
}

RULES = f"""You are one of five AI strategies competing in a paper-trading tournament.
Each strategy has its own virtual ${config.STARTING_CASH:.0f}. The winner is whichever beats
SPY buy-and-hold by the most after costs. Your AI usage cost is charged against your returns.

Hard rules (enforced in code; orders that break them are trimmed or rejected):
- Buy or sell US-listed stocks/ETFs only. No options, no shorting, no margin.
- Buys use settled cash only. Sale proceeds settle the next trading day.
- Limit orders only, priced within {config.LIMIT_PRICE_BAND:.0%} of the current price. Day orders expire at the close.
- Position size is capped by your stated confidence: 1-4 -> 15%, 5-7 -> 35%, 8-10 -> 75% of your equity in one name.
- Never trade: {', '.join(sorted(config.EXCLUDED_SYMBOLS))}.
- Each fill is charged a simulated spread penalty (more for illiquid names).

Holding is often the right call. Be honest with confidence scores: they are logged and
later compared with outcomes to see whether your confidence means anything."""


def system_prompt(sid: str, notes: str) -> str:
    name = config.STRATEGIES[sid]["name"]
    return (f"{RULES}\n\nYou are strategy {sid}: {name}.\n{DESCRIPTIONS[sid]}\n\n"
            f"Your strategy notes (updated weekly from your own results):\n<notes>\n{notes}\n</notes>")


# --- Market helpers -------------------------------------------------------------

def adv_dollars(bars: list, n: int = 20) -> float:
    rows = bars[-n:]
    return mean(r["close"] * r["volume"] for r in rows) if rows else 0.0


def ret(bars: list, days: int, price: float) -> float | None:
    if len(bars) < days:
        return None
    base = bars[-days]["close"]
    return (price / base - 1) * 100 if base else None


def market_info(broker, symbol: str, cache: dict) -> dict | None:
    """Everything the guardrails need for one symbol (cached for the run)."""
    if symbol in cache:
        return cache[symbol]
    asset = broker.asset_info(symbol)
    if not asset:
        cache[symbol] = None
        return None
    px = broker.latest_prices([symbol]).get(symbol)
    if not px:
        cache[symbol] = None
        return None
    bars = cache.get(("bars", symbol)) or broker.daily_bars([symbol], 30).get(symbol, [])
    info = {**asset, **px, "avg_dollar_volume": adv_dollars(bars)}
    cache[symbol] = info
    return info


class MarketSnapshot:
    """Fetched once per check-in run and shared by all strategies."""

    def __init__(self, broker):
        self.broker = broker
        self.cache: dict = {}
        syms = list(dict.fromkeys(config.LIQUID_UNIVERSE + [config.BENCHMARK]))
        self.prices = broker.latest_prices(syms)
        self.bars = broker.daily_bars(syms, 70)
        for s, b in self.bars.items():
            self.cache[("bars", s)] = b
        self._news = None
        self._small = None

    def price(self, s: str) -> float | None:
        p = self.prices.get(s)
        if not p:
            p = self.broker.latest_prices([s]).get(s)
            if p:
                self.prices[s] = p
        return p["price"] if p else None

    def universe_table(self, sort_key: str, top: int, reverse: bool = True) -> list:
        rows = []
        for s in config.LIQUID_UNIVERSE:
            p, b = self.prices.get(s), self.bars.get(s, [])
            if not p or len(b) < 61:
                continue
            price = p["price"]
            closes = [r["close"] for r in b]
            ma50 = mean(closes[-50:])
            daily = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 60, len(closes))]
            vol = pstdev(daily) * 100 if len(daily) > 2 else 0
            r5 = ret(b, 5, price)
            rows.append({"symbol": s, "price": price, "r1": ret(b, 1, price), "r5": r5,
                         "r20": ret(b, 20, price), "r60": ret(b, 60, price),
                         "vs_ma50": (price / ma50 - 1) * 100,
                         "z5": (r5 / (vol * 5 ** 0.5)) if vol and r5 is not None else 0})
        rows.sort(key=lambda r: (r[sort_key] if r[sort_key] is not None else -1e9), reverse=reverse)
        return rows[:top]

    def news(self) -> list:
        if self._news is None:
            self._news = self.broker.news(config.LIQUID_UNIVERSE[:50], hours=24, limit=40)
        return self._news

    def smallcaps(self) -> list:
        if self._small is None:
            mv = self.broker.movers(20)
            syms = [m["symbol"] for m in mv["gainers"] + mv["losers"]]
            syms += self.broker.most_actives(30)
            syms = [s for s in dict.fromkeys(syms) if s not in config.EXCLUDED_SYMBOLS
                    and s not in config.LIQUID_UNIVERSE and s.isalpha()][:30]
            bars = self.broker.daily_bars(syms, 25) if syms else {}
            px = self.broker.latest_prices(syms) if syms else {}
            pct = {m["symbol"]: m["pct"] for m in mv["gainers"] + mv["losers"]}
            rows = []
            for s in syms:
                if s not in px:
                    continue
                b = bars.get(s, [])
                self.cache[("bars", s)] = b
                p = px[s]
                spread = ((p["ask"] - p["bid"]) / p["price"] * 100) if p["ask"] and p["bid"] else None
                rows.append({"symbol": s, "price": p["price"], "today": pct.get(s, ret(b, 1, p["price"])),
                             "adv": adv_dollars(b), "spread": spread})
            self._small = rows
        return self._small


# --- Context (the user message for a check-in) ------------------------------------

def _f(x, nd=1, pct=False):
    if x is None:
        return "n/a"
    return f"{x:+.{nd}f}%" if pct else f"{x:.{nd}f}"


def account_block(sid: str, acct: dict, snap: MarketSnapshot) -> str:
    prices = {s: snap.price(s) or 0 for s in acct["positions"]}
    eq = ledger.equity(acct, prices)
    lines = [f"Equity ${eq:.2f} (start ${config.STARTING_CASH:.0f}); AI cost so far ${acct['ai_cost']:.2f}",
             f"Settled cash ${acct['cash']:.2f}; unsettled ${sum(u['amount'] for u in acct['unsettled']):.2f}; "
             f"reserved for open buys ${acct['reserved']:.2f}"]
    for s, pos in acct["positions"].items():
        p = prices[s]
        avg = pos["cost_basis"] / pos["qty"] if pos["qty"] else 0
        pl = (p / avg - 1) * 100 if avg else 0
        lines.append(f"- HOLD {s} qty {pos['qty']:g} avg {avg:.2f} price {p:.2f} "
                     f"({pl:+.1f}%, {pos['qty'] * p / eq * 100 if eq else 0:.0f}% of equity)")
    for o in acct["pending_orders"]:
        lines.append(f"- OPEN ORDER {o['side']} {o['qty']:g} {o['symbol']} @ {o['limit_price']}")
    if not acct["positions"]:
        lines.append("- No positions.")
    return "\n".join(lines)


def recent_block(sid: str) -> str:
    rows = journal.recent_decisions(sid, 5)
    if not rows:
        return "No previous decisions yet."
    out = []
    for r in rows:
        acts = "; ".join(f"{o.get('action')} {o.get('symbol')} (conf {o.get('confidence')}) -> {o.get('result')}"
                         for o in r.get("orders", [])) or "hold"
        out.append(f"- {r['ts'][:16]} {acts}. {r.get('summary', '')}")
    return "\n".join(out)


def candidates_block(sid: str, snap: MarketSnapshot) -> str:
    hdr = "| Symbol | Price | 1d | 5d | 20d | 60d | vs 50d MA |\n|---|---|---|---|---|---|---|"
    fmt = lambda r: (f"| {r['symbol']} | {r['price']:.2f} | {_f(r['r1'], pct=True)} | {_f(r['r5'], pct=True)} | "
                     f"{_f(r['r20'], pct=True)} | {_f(r['r60'], pct=True)} | {_f(r['vs_ma50'], pct=True)} |")
    if sid == "A":
        rows = snap.universe_table("r20", 15)
        return "Strongest 20-day performers in the liquid universe:\n" + hdr + "\n" + "\n".join(map(fmt, rows))
    if sid == "B":
        rows = snap.universe_table("z5", 15, reverse=False)
        return ("Sharpest 5-day drops relative to each name's own volatility:\n" + hdr + "\n"
                + "\n".join(map(fmt, rows)))
    if sid == "C":
        news = snap.news()[:25]
        movers = snap.universe_table("r1", 60)
        today = {r["symbol"]: r for r in movers}
        lines = ["Headlines from the last 24h:"]
        for n in news:
            syms = [s for s in n["symbols"] if s in today][:3]
            moves = ", ".join(f"{s} {_f(today[s]['r1'], pct=True)} today" for s in syms)
            lines.append(f"- {n['headline']} [{', '.join(n['symbols'][:4])}] {moves}")
        if not news:
            lines.append("- (no news returned)")
        involved = list(dict.fromkeys(s for n in news for s in n["symbols"] if s in today))[:15]
        lines.append("\nPrices for names in the news:\n" + hdr)
        lines += [fmt(today[s]) for s in involved]
        return "\n".join(lines)
    if sid == "D":
        rows = snap.smallcaps()
        lines = ["Small caps from today's movers and most-active lists:",
                 "| Symbol | Price | Today | Avg daily $ vol | Spread |", "|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['symbol']} | {r['price']:.4g} | {_f(r['today'], pct=True)} | "
                         f"${r['adv'] / 1e6:.2f}M | {_f(r['spread'], 2, pct=False) + '%' if r['spread'] is not None else 'n/a'} |")
        lines.append(f"\nOrders are capped at {config.SMALLCAP_MAX_ADV_FRACTION:.0%} of a name's average daily dollar volume.")
        return "\n".join(lines)
    # E: a broad view
    mom = snap.universe_table("r20", 8)
    drops = snap.universe_table("z5", 6, reverse=False)
    small = snap.smallcaps()[:8]
    news = snap.news()[:10]
    lines = ["Momentum leaders:", hdr] + [fmt(r) for r in mom]
    lines += ["\nSharpest recent drops:", hdr] + [fmt(r) for r in drops]
    lines += ["\nSmall-cap movers: " + ", ".join(f"{r['symbol']} {r['price']:.4g} ({_f(r['today'], pct=True)})" for r in small)]
    lines += ["\nHeadlines:"] + [f"- {n['headline']} [{', '.join(n['symbols'][:3])}]" for n in news]
    return "\n".join(lines)


def user_prompt(sid: str, acct: dict, snap: MarketSnapshot, now_et: str, slot_info: str) -> str:
    spy = snap.price(config.BENCHMARK)
    spy_b = snap.bars.get(config.BENCHMARK, [])
    return f"""Check-in: {now_et} ET ({slot_info}).
SPY {spy:.2f} ({_f(ret(spy_b, 1, spy), pct=True)} vs yesterday's close, {_f(ret(spy_b, 5, spy), pct=True)} over 5 days).

## Your account
{account_block(sid, acct, snap)}

## Your recent decisions
{recent_block(sid)}

## Market data
{candidates_block(sid, snap)}

You may also trade any other allowed symbol you know, but you will only see its price at order time.
Decide now: submit up to three orders, or none to hold."""
