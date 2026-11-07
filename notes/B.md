# Strategy B notes: Mean reversion

## Status
- Since start: -0.05% vs SPY -5.08%. Mostly cash; the only position is XOM (~$76, about 15% of the account).
- Open trade: XOM 0.4501 filled @169.43. Stop 158 (-6.7%), take profit 175 (+3.3%), time stop 11/20. Check all three at the start of every decision. Because the fill came in about 1.7% above the limit, the exit levels are now lopsided. If XOM closes below ~161 (-5% from the fill), exit.

## Entry setup (core)
- Look for liquid names with a sharp 5-day drop of about 2x their normal 5-day move or more, with the 60-day trend intact and price near or above its 50d MA.
- Skip drops caused by clear bad news: earnings misses, guidance cuts, or sector-wide shocks.
- During a broad selloff, wait for a stabilization day (SPY up, or the 5-day drop stops getting worse). Then make one small entry per day at most.

## Deploying cash
- Cash protected the lead, but it can't beat SPY in a rebound. On each new stabilization day, add one more intact-trend dip from a different sector than the current holdings (financials, healthcare, staples, industrials). Target 2-4 positions and 40-60% of the account invested, built up over several days.
- If SPY makes a new -3% or worse day, pause new buys. Keep the existing positions unless their stops are hit.

## Costs and orders
- Spread penalties are now $5.29 (~1.06% of the account). Trade only large, tight-spread names, with each position ≥ ~$70.
- Fills come in 1-3% worse than the limit. Set the limit at or slightly below the last price. **Recompute the stop and take profit from the actual fill price.** Skip a trade if the bounce left from a realistic fill is under ~3%.

## Exits (mechanical)
- Write down the stop, take profit and time stop at entry and re-base them on the fill.
- On the time-stop date, sell that day (NVDA lesson: holding past it cost about $3).
- Exit if price closes at or below the stop, or is within ~1% of it on a down-market day. Exit right away on bad news.
- Defaults: take profit about +5% from the fill, cut at -5%, time stop about 10 trading days.

## Confidence
- Tournament data: conf 1-4 averaged -1.47% (6 buys), 5-7 averaged -5.49% (12), 8-10 averaged -8.61% (2). Higher confidence keeps doing worse.
- Default buys to conf 3. Use 4-5 only for a textbook setup after stabilization with a clean news check. Never go above 5.
