"""Two simulated weeks end to end: check-ins, fills, settlement, Friday reviews, dashboard."""
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bot import ai, broker, checkin, config, journal, ledger, review, state

ET = ZoneInfo("America/New_York")


def at(b, day: date, hhmm: str):
    h, m = map(int, hhmm.split(":"))
    b.now = datetime(day.year, day.month, day.day, h, m, tzinfo=ET).astimezone(timezone.utc)
    b.today = day.isoformat()


def test_two_week_tournament(isolated):
    b, a = broker.FakeBroker(seed=3, today="2026-10-12"), ai.FakeAI(seed=5)
    review.design_e(a)
    assert "No strategy defined yet" not in (config.NOTES_DIR / "E.md").read_text()

    day = date(2026, 10, 12)  # a Monday
    for _ in range(10):
        for slot in config.CHECKIN_SLOTS_ET:
            h, m = map(int, slot.split(":"))
            at(b, day, f"{h:02d}:{m + 5:02d}")
            b.advance(minutes=1)
            checkin.run(b, a)
        if day.weekday() == 4:
            at(b, day, "16:30")
            week = review.run(b, a, today=day.isoformat(), send=False)
            assert set(week["strategies"]) == set(config.STRATEGIES)
            for r in week["strategies"].values():
                assert config.CHECKIN_MIN_LEVEL <= r["level"] <= config.CHECKIN_MAX_LEVEL
        day += timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        b.advance(days=0)

    led = ledger.load()
    for sid, acct in led["strategies"].items():
        assert acct["cash"] >= -1e-6, sid
        assert acct["reserved"] >= -1e-6, sid
        for sym, pos in acct["positions"].items():
            assert pos["qty"] > 0 and sym not in config.EXCLUDED_SYMBOLS
            assert pos.get("reserved_qty", 0) <= pos["qty"] + 1e-9

    orders = journal.entries(kinds=("order",))
    fills = journal.entries(kinds=("fill",))
    assert orders and fills, "simulation should trade"
    assert all(o["symbol"] not in config.EXCLUDED_SYMBOLS for o in orders)
    # earned check-ins: lower-level strategies made fewer decisions on later slots
    assert len(state.read_jsonl("weekly.jsonl")) == 2
    assert ai.month_total(date(2026, 10, 20)) > 0
    assert len(led["equity_history"]) == 10

    html = (config.DOCS_DIR / "index.html").read_text()
    assert "AI Strategy Tournament" in html and "__DATA__" not in html
    data = json.loads((config.DOCS_DIR / "data.json").read_text())
    assert data["weekly"] and data["equity"]


def test_closed_market_and_off_slot_do_nothing(isolated):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    at(b, date(2026, 10, 12), "09:35")  # before the first slot
    assert checkin.run(b, a)["ran"] == []
    b.clock = lambda: {"is_open": False, "now": b.now}
    assert checkin.run(b, a, force=True)["ran"] == []


def test_kill_switch_blocks_all_orders(isolated):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    config.KILL_SWITCH_FILE.write_text("halt")
    at(b, date(2026, 10, 12), "09:50")
    checkin.run(b, a)
    assert journal.entries(kinds=("order",)) == []


def test_hard_budget_cap_stops_ai_calls(isolated, monkeypatch):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    monkeypatch.setattr(ai, "over_hard_cap", lambda d=None: True)
    at(b, date(2026, 10, 12), "09:50")
    assert checkin.run(b, a)["ran"] == []


def test_duplicate_trigger_for_same_slot_is_skipped(isolated):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    at(b, date(2026, 10, 12), "09:47")
    assert checkin.run(b, a)["ran"]
    at(b, date(2026, 10, 12), "10:10")  # a delayed second trigger for the same slot
    assert checkin.run(b, a)["ran"] == []


def test_missed_morning_slot_is_caught_up_once(isolated):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    at(b, date(2026, 10, 12), "11:20")  # the 9:45 trigger never fired
    assert set(checkin.run(b, a)["ran"]) >= {"A", "B", "C", "D"}
    at(b, date(2026, 10, 12), "11:50")
    assert checkin.run(b, a)["ran"] == []  # level-2 strategies wait for the 15:30 slot


def test_no_new_checkins_right_before_close(isolated):
    b, a = broker.FakeBroker(today="2026-10-12"), ai.FakeAI()
    at(b, date(2026, 10, 12), "15:55")
    assert checkin.run(b, a)["ran"] == []
