"""Append-only trade journal: every check-in, decision, guardrail result and fill."""
from __future__ import annotations

from datetime import datetime, timezone

from . import state

JOURNAL_FILE = "journal.jsonl"


def log(kind: str, strategy: str | None = None, **fields) -> dict:
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kind": kind, "strategy": strategy, **fields}
    state.append_jsonl(JOURNAL_FILE, rec)
    return rec


def entries(strategy: str | None = None, kinds: tuple | None = None,
            since: str | None = None) -> list:
    out = []
    for r in state.read_jsonl(JOURNAL_FILE):
        if strategy and r.get("strategy") != strategy:
            continue
        if kinds and r.get("kind") not in kinds:
            continue
        if since and r["ts"] < since:
            continue
        out.append(r)
    return out


def recent_decisions(strategy: str, n: int = 6) -> list:
    return entries(strategy, kinds=("decision",))[-n:]
