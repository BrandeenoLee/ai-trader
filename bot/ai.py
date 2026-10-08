"""Claude API calls, spend tracking and budget enforcement.

The AI never touches the broker. It returns structured proposals (via a forced
tool call) that the guardrails then approve, trim or reject.
"""
from __future__ import annotations

import calendar
import os
import random
from datetime import date

from . import config, state

SPEND_FILE = "ai_spend.json"

DECISION_TOOL = {
    "name": "submit_decision",
    "description": "Submit this check-in's trading decision. Use action 'hold' with no orders to do nothing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "orders": {
                "type": "array", "maxItems": 3,
                "description": "Zero to three orders. Empty means hold.",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["buy", "sell"]},
                        "symbol": {"type": "string"},
                        "amount_usd": {"type": "number", "description": "Buys: dollars to spend."},
                        "sell_fraction": {"type": "number", "description": "Sells: fraction of the position, 0-1."},
                        "limit_price": {"type": "number", "description": "Limit price, within 3% of current price."},
                        "confidence": {"type": "integer", "minimum": 1, "maximum": 10},
                        "reasoning": {"type": "string", "description": "One or two sentences."},
                    },
                    "required": ["action", "symbol", "limit_price", "confidence", "reasoning"],
                },
            },
            "summary": {"type": "string", "description": "One sentence on your read of the situation."},
        },
        "required": ["orders", "summary"],
    },
}

REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit the weekly review for one strategy.",
    "input_schema": {
        "type": "object",
        "properties": {
            "notes_markdown": {"type": "string",
                               "description": "The complete updated strategy notes file (replaces the old one)."},
            "lessons": {"type": "string", "description": "2-4 sentences: what worked, what didn't, what changed."},
            "self_assessment": {"type": "string", "description": "One line for the weekly email."},
            "confidence_beat_spy": {"type": "integer", "minimum": 1, "maximum": 10,
                                    "description": "How confident you are this strategy beats SPY next week."},
        },
        "required": ["notes_markdown", "lessons", "self_assessment", "confidence_beat_spy"],
    },
}


# --- Spend tracking ------------------------------------------------------------

def _month(d: date | None = None) -> str:
    return (d or date.today()).strftime("%Y-%m")


def spend() -> dict:
    return state.load(SPEND_FILE, {})


def month_total(d: date | None = None) -> float:
    return spend().get(_month(d), {}).get("total", 0.0)


def record_spend(strategy: str | None, model: str, usage: dict, d: date | None = None) -> float:
    pin, pout = config.MODEL_PRICES[model]
    cost = (usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout) / 1e6
    data = spend()
    m = data.setdefault(_month(d), {"total": 0.0, "calls": 0, "by_strategy": {}})
    m["total"] = round(m["total"] + cost, 6)
    m["calls"] += 1
    key = strategy or "review"
    m["by_strategy"][key] = round(m["by_strategy"].get(key, 0.0) + cost, 6)
    state.save(SPEND_FILE, data)
    return cost


def over_hard_cap(d: date | None = None) -> bool:
    return month_total(d) >= config.MONTHLY_HARD_CAP_USD


def ahead_of_pace(d: date | None = None) -> bool:
    """True when spending is running ahead of the soft monthly target."""
    d = d or date.today()
    days = calendar.monthrange(d.year, d.month)[1]
    pace = config.MONTHLY_TARGET_USD * d.day / days
    return month_total(d) > pace


# --- Clients ---------------------------------------------------------------------

def make_ai():
    if os.environ.get("DRY_RUN") == "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        return FakeAI()
    return ClaudeAI()


class ClaudeAI:
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()

    def _call(self, model, system, user, tool, max_tokens):
        resp = self.client.messages.create(
            model=model, max_tokens=max_tokens, system=system, tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user}],
        )
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        return (block.input if block else {}), usage

    def decide(self, system: str, user: str) -> tuple[dict, dict]:
        return self._call(config.TRADER_MODEL, system, user, DECISION_TOOL,
                          config.MAX_OUTPUT_TOKENS_TRADER)

    def review(self, system: str, user: str) -> tuple[dict, dict]:
        return self._call(config.REVIEW_MODEL, system, user, REVIEW_TOOL,
                          config.MAX_OUTPUT_TOKENS_REVIEW)


class FakeAI:
    """Stand-in for dry runs: makes plausible random proposals from the candidates it is shown."""

    def __init__(self, seed: int = 11):
        self.rng = random.Random(seed)

    def decide(self, system: str, user: str) -> tuple[dict, dict]:
        import re
        cands = re.findall(r"^\| ([A-Z]{1,5}) \| ([0-9.]+) \|", user, flags=re.M)
        held = re.findall(r"^- HOLD ([A-Z]{1,5}) .* price ([0-9.]+)", user, flags=re.M)
        orders = []
        roll = self.rng.random()
        if held and roll < 0.3:
            sym, price = self.rng.choice(held)
            orders.append({"action": "sell", "symbol": sym, "sell_fraction": 1.0,
                           "limit_price": round(float(price) * 0.995, 2),
                           "confidence": self.rng.randint(3, 9), "reasoning": "Simulated exit."})
        elif cands and roll < 0.75:
            sym, price = self.rng.choice(cands)
            orders.append({"action": "buy", "symbol": sym,
                           "amount_usd": round(self.rng.uniform(60, 300), 2),
                           "limit_price": round(float(price) * 1.004, 2),
                           "confidence": self.rng.randint(1, 10), "reasoning": "Simulated entry."})
        usage = {"input_tokens": len(system + user) // 4, "output_tokens": 150}
        return {"orders": orders, "summary": "Simulated decision."}, usage

    def review(self, system: str, user: str) -> tuple[dict, dict]:
        import re
        m = re.search(r"<current_notes>\n(.*?)\n</current_notes>", user, flags=re.S)
        notes = (m.group(1) if m else "# Notes\n").rstrip()
        if "Week 0" in user:
            notes = "# Strategy E notes: Claude's pick\n\n- (simulated design) buy momentum leaders on pullbacks."
        notes += "\n\n- (simulated review) keep position sizes moderate."
        usage = {"input_tokens": len(system + user) // 4, "output_tokens": 600}
        return {"notes_markdown": notes, "lessons": "Simulated lessons.",
                "self_assessment": "Simulated week.",
                "confidence_beat_spy": self.rng.randint(2, 8)}, usage
