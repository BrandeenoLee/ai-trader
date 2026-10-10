# Strategy B notes: Mean reversion

## Entry setup (core, unchanged)
- Look for liquid names with a sharp 5-day drop that is large for their volatility (about 2x their normal 5-day move or more), while the 60-day trend is still intact and price is near or above its 50d MA.
- Skip drops caused by clear bad news: earnings misses, guidance cuts, or sector-wide regulatory or pricing shocks (e.g. VZ/T -8% in one day on 10/09).
- An unexplained drop is not an automatic skip. Check for news first. If none turns up and the trend is intact, take a small position instead of deferring again (INTC was passed over twice without a news check).

## Sizing and cash
- Holding one ~$72 position with the rest in cash lags SPY in up weeks (+0.14% vs +0.68%). Target 2-4 positions in uncorrelated dips (different sectors) when setups exist, with about 40-60% of the account invested.
- If no setup qualifies, cash is fine. Don't force trades that break the entry rules.
- Spread costs are heavy ($1.96 so far, about 0.4% of the account). Prefer large, tight-spread names. Make each position big enough that the spread is a small share of it, and don't trade in and out.

## Orders
- Place limits close to the current price.
- Check every fill against its limit. The CRM buy (limit 222.5) filled at 228.72, which is above the limit and should be impossible. Treat it as an execution or data anomaly, and mention any repeat in the decision reasoning.

## Exits (CRM: fill 228.72, entered 10/08)
- Take profit when the price gets back to about the pre-drop level (roughly +5%, ~240 for CRM).
- Cut at about -5% from the fill price (~217 for CRM), or right away if bad news comes out.
- Time stop: no bounce within about 10 trading days (CRM by ~10/22) means exit and recycle the cash.

## Confidence
- Tournament data so far: conf 1-4 averaged +0.17% (1 buy) and conf 5-7 averaged +0.13% (4 buys). That's too few trades to show any calibration. Keep confidence honest, use the middle of the range for textbook setups, and don't inflate it to get bigger size.
