"""Broker and market-data access.

AlpacaBroker talks to Alpaca's Trading API (paper by default) and free market data.
FakeBroker simulates a market so the whole system can be tested with no keys.
Both expose the same methods, so the rest of the code doesn't care which it gets.
"""
from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta, timezone


def make_broker():
    """Real Alpaca broker if keys are set and DRY_RUN is not, otherwise the simulator."""
    if os.environ.get("DRY_RUN") == "1" or not os.environ.get("ALPACA_API_KEY"):
        return FakeBroker()
    return AlpacaBroker(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"],
                        paper=os.environ.get("ALPACA_LIVE") != "1")


def _iso(d) -> str:
    return d.isoformat() if isinstance(d, date) else str(d)[:10]


class AlpacaBroker:
    def __init__(self, key: str, secret: str, paper: bool = True):
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.historical.news import NewsClient
        from alpaca.data.historical.screener import ScreenerClient
        from alpaca.trading.client import TradingClient

        if not paper:
            print("WARNING: running against a LIVE Alpaca account")
        self.paper = paper
        self.trading = TradingClient(key, secret, paper=paper)
        self.data = StockHistoricalDataClient(key, secret)
        self.news_client = NewsClient(key, secret)
        self.screener = ScreenerClient(key, secret)
        self._asset_cache: dict = {}

    # --- calendar ---------------------------------------------------------
    def clock(self) -> dict:
        c = self.trading.get_clock()
        return {"is_open": c.is_open, "now": c.timestamp.astimezone(timezone.utc)}

    def next_trading_day(self, d: str) -> str:
        from alpaca.trading.requests import GetCalendarRequest
        start = date.fromisoformat(d) + timedelta(days=1)
        cal = self.trading.get_calendar(GetCalendarRequest(start=start, end=start + timedelta(days=10)))
        return _iso(cal[0].date) if cal else _iso(start)

    def is_trading_day(self, d: str) -> bool:
        from alpaca.trading.requests import GetCalendarRequest
        day = date.fromisoformat(d)
        cal = self.trading.get_calendar(GetCalendarRequest(start=day, end=day))
        return bool(cal)

    # --- reference data ---------------------------------------------------
    def asset_info(self, symbol: str) -> dict | None:
        if symbol in self._asset_cache:
            return self._asset_cache[symbol]
        try:
            a = self.trading.get_asset(symbol)
        except Exception:
            self._asset_cache[symbol] = None
            return None
        info = {
            "tradable": bool(a.tradable),
            "exchange": getattr(a.exchange, "value", str(a.exchange)),
            "fractionable": bool(a.fractionable),
            "asset_class": getattr(a.asset_class, "value", str(a.asset_class)),
            "name": a.name,
        }
        self._asset_cache[symbol] = info
        return info

    # --- prices -------------------------------------------------------------
    def latest_prices(self, symbols: list) -> dict:
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockLatestQuoteRequest, StockLatestTradeRequest
        out = {}
        if not symbols:
            return out
        for chunk in _chunks(symbols, 100):
            trades = self.data.get_stock_latest_trade(
                StockLatestTradeRequest(symbol_or_symbols=chunk, feed=DataFeed.IEX))
            quotes = self.data.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=chunk, feed=DataFeed.IEX))
            for s in chunk:
                t, q = trades.get(s), quotes.get(s)
                bid = float(q.bid_price) if q and q.bid_price else 0.0
                ask = float(q.ask_price) if q and q.ask_price else 0.0
                price = float(t.price) if t else ((bid + ask) / 2 if bid and ask else 0.0)
                if price > 0:
                    out[s] = {"price": price, "bid": bid, "ask": ask}
        return out

    def daily_bars(self, symbols: list, days: int = 70) -> dict:
        """Daily closes/volumes through yesterday (SIP feed; free tier allows data >15 min old)."""
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        end = datetime.now(timezone.utc) - timedelta(minutes=20)
        start = end - timedelta(days=int(days * 1.6) + 5)
        out = {}
        for chunk in _chunks(symbols, 100):
            bars = self.data.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                start=start, end=end, feed=DataFeed.SIP))
            from zoneinfo import ZoneInfo
            today_et = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
            for s, rows in bars.data.items():
                # completed sessions only: today's partial bar would make "1-day change" read 0%
                done = [b for b in rows
                        if _iso(b.timestamp.astimezone(ZoneInfo("America/New_York")).date()) < today_et]
                out[s] = [{"date": _iso(b.timestamp.astimezone(ZoneInfo("America/New_York")).date()),
                           "close": float(b.close), "volume": float(b.volume)} for b in done][-days:]
        return out

    def news(self, symbols: list, hours: int = 24, limit: int = 40) -> list:
        from alpaca.data.requests import NewsRequest
        start = datetime.now(timezone.utc) - timedelta(hours=hours)
        try:
            res = self.news_client.get_news(NewsRequest(
                symbols=",".join(symbols) if symbols else None, start=start,
                limit=limit, exclude_contentless=True))
        except Exception as e:  # news is optional context
            print(f"news unavailable: {e}")
            return []
        items = res.data.get("news", []) if hasattr(res, "data") else []
        return [{"headline": n.headline, "summary": (n.summary or "")[:300],
                 "symbols": list(n.symbols or []), "created_at": str(n.created_at)}
                for n in items]

    def movers(self, top: int = 20) -> dict:
        from alpaca.data.requests import MarketMoversRequest
        try:
            m = self.screener.get_market_movers(MarketMoversRequest(top=top))
        except Exception as e:
            print(f"movers unavailable: {e}")
            return {"gainers": [], "losers": []}
        conv = lambda xs: [{"symbol": x.symbol, "pct": float(x.percent_change),
                            "price": float(x.price)} for x in xs]
        return {"gainers": conv(m.gainers), "losers": conv(m.losers)}

    def most_actives(self, top: int = 50) -> list:
        from alpaca.data.requests import MostActivesRequest
        try:
            m = self.screener.get_most_actives(MostActivesRequest(top=top))
        except Exception as e:
            print(f"most actives unavailable: {e}")
            return []
        return [a.symbol for a in m.most_actives]

    # --- orders -------------------------------------------------------------
    def submit_limit(self, symbol: str, side: str, qty: float, limit: float,
                     client_id: str) -> str:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import LimitOrderRequest
        o = self.trading.submit_order(LimitOrderRequest(
            symbol=symbol, qty=qty, limit_price=limit,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY, client_order_id=client_id))
        return str(o.id)

    def order_status(self, order_id: str) -> dict:
        o = self.trading.get_order_by_id(order_id)
        return {"status": getattr(o.status, "value", str(o.status)),
                "filled_qty": float(o.filled_qty or 0),
                "filled_avg_price": float(o.filled_avg_price or 0)}

    def cancel(self, order_id: str) -> None:
        try:
            self.trading.cancel_order_by_id(order_id)
        except Exception as e:
            print(f"cancel {order_id}: {e}")


def _chunks(xs, n):
    xs = list(xs)
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# --- Simulator -----------------------------------------------------------------

class FakeBroker:
    """Deterministic random-walk market for tests and dry runs. Fills a limit order
    immediately when it is marketable at the current simulated price."""

    SMALLCAPS = ["TINY", "MICR", "NANO", "SMAL", "LILP"]

    def __init__(self, seed: int = 7, today: str | None = None):
        from . import config
        self.rng = random.Random(seed)
        self.today = today or date.today().isoformat()
        self.now = datetime.now(timezone.utc)
        self.prices = {}
        for s in config.LIQUID_UNIVERSE + [config.BENCHMARK, "GME", "AMC"]:
            self.prices[s] = round(self.rng.uniform(20, 400), 2)
        for s in self.SMALLCAPS:
            self.prices[s] = round(self.rng.uniform(1, 6), 2)
        self.orders: dict = {}
        self._n = 0

    def advance(self, days: int = 0, minutes: int = 0) -> None:
        for s in self.prices:
            vol = 0.04 if s in self.SMALLCAPS else 0.012
            self.prices[s] = round(max(0.5, self.prices[s] * (1 + self.rng.gauss(0.0004, vol))), 2)
        if days:
            d = date.fromisoformat(self.today)
            for _ in range(days):
                d += timedelta(days=1)
                while d.weekday() >= 5:
                    d += timedelta(days=1)
            self.today = d.isoformat()
        self.now += timedelta(days=days, minutes=minutes)

    def clock(self) -> dict:
        return {"is_open": True, "now": self.now}

    def next_trading_day(self, d: str) -> str:
        x = date.fromisoformat(d) + timedelta(days=1)
        while x.weekday() >= 5:
            x += timedelta(days=1)
        return x.isoformat()

    def is_trading_day(self, d: str) -> bool:
        return date.fromisoformat(d).weekday() < 5

    def asset_info(self, symbol: str) -> dict | None:
        if symbol not in self.prices:
            return None
        return {"tradable": True, "exchange": "NASDAQ", "fractionable": symbol not in self.SMALLCAPS,
                "asset_class": "us_equity", "name": symbol}

    def latest_prices(self, symbols: list) -> dict:
        out = {}
        for s in symbols:
            if s in self.prices:
                p = self.prices[s]
                spread = p * (0.02 if s in self.SMALLCAPS else 0.0004)
                out[s] = {"price": p, "bid": round(p - spread / 2, 4), "ask": round(p + spread / 2, 4)}
        return out

    def daily_bars(self, symbols: list, days: int = 70) -> dict:
        out = {}
        for s in symbols:
            if s not in self.prices:
                continue
            r = random.Random(f"{s}{self.today}")
            p, rows = self.prices[s], []
            vol_shares = 3e5 if s in self.SMALLCAPS else 2e7
            # walk backwards from today's price so the series ends near it
            for i in range(days):
                rows.append({"date": (date.fromisoformat(self.today) - timedelta(days=i + 1)).isoformat(),
                             "close": round(p, 2), "volume": vol_shares * r.uniform(0.5, 1.5)})
                p /= 1 + r.gauss(0, 0.015)
            rows.reverse()
            out[s] = rows
        return out

    def news(self, symbols: list, hours: int = 24, limit: int = 40) -> list:
        return [{"headline": f"{s} announces quarterly update", "summary": "Simulated headline.",
                 "symbols": [s], "created_at": self.now.isoformat()} for s in symbols[:5]]

    def movers(self, top: int = 20) -> dict:
        return {"gainers": [{"symbol": s, "pct": 12.0, "price": self.prices[s]} for s in self.SMALLCAPS[:3]],
                "losers": [{"symbol": s, "pct": -9.0, "price": self.prices[s]} for s in self.SMALLCAPS[3:]]}

    def most_actives(self, top: int = 50) -> list:
        return self.SMALLCAPS + ["AAPL", "NVDA", "TSLA"]

    def submit_limit(self, symbol, side, qty, limit, client_id) -> str:
        self._n += 1
        oid = f"fake-{self._n}"
        p = self.prices[symbol]
        marketable = (side == "buy" and limit >= p) or (side == "sell" and limit <= p)
        self.orders[oid] = {"status": "filled" if marketable else "new",
                            "filled_qty": qty if marketable else 0.0,
                            "filled_avg_price": min(p, limit) if side == "buy" else max(p, limit),
                            "symbol": symbol, "side": side, "qty": qty, "limit": limit}
        return oid

    def order_status(self, order_id: str) -> dict:
        o = self.orders[order_id]
        if o["status"] == "new":  # may fill later as the price moves
            p = self.prices[o["symbol"]]
            if (o["side"] == "buy" and o["limit"] >= p) or (o["side"] == "sell" and o["limit"] <= p):
                o.update(status="filled", filled_qty=o["qty"], filled_avg_price=o["limit"])
        return {k: o[k] for k in ("status", "filled_qty", "filled_avg_price")}

    def cancel(self, order_id: str) -> None:
        o = self.orders.get(order_id)
        if o and o["status"] == "new":
            o["status"] = "canceled"
