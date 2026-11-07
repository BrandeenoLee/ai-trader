# Strategy A notes: Momentum

## Entry rules
- Buy names with positive 20-day AND 60-day returns that trade above their 50-day average.
- Rank by 60d trend first, then 20d. No holding is "core". Every position follows the same rules.
- Skip any name with a single-day spike of more than 5%.
- A name more than 15% above its 50d average is extended. Skip it.
- Hold at most 1 name from the high-beta tech/semis cluster (AMD, META and PLTR caused the biggest losses).
- Prefer sector ETFs (XLV, XLI, XLF, XLP, XLE) or large low-beta leaders (V, MA, KO). Spreads are tighter.
- Don't buy a name that overlaps a current holding (e.g. XLP while holding KO).

## Sizing
- Hold 3-4 positions, keeping $15-25 in cash. Right now about $65 is idle. Deploy about $45 into one qualifying name from a sector we don't hold (industrials or financials preferred). If nothing qualifies, hold the cash rather than force a trade.
- Use confidence 4-5. Never go above 5. Tournament data: 1-4 averaged -1.47% (n=6), 5-7 averaged -5.49% (n=12), 8-10 averaged -8.61% (n=2). Higher confidence keeps doing worse.

## Exits and rotation
- Hard stop: sell at 8% below entry. The XLE stop filled at -9.2% because the check came a day late. Write the stop price for each holding below and check it every day.
- Early warning: sell at -6% or worse if the name is also below its 50d average, has a negative 20d return, or has dropped out of the 20d leaders. Once a holding drops out of the 20d leaders, treat -5% as the trigger. XLE dropped out and kept sliding.
- Rotate out when a holding closes below its 50d average, or when its 20d return turns negative and it drops out of the top names.
- Hold at least 3 trading days unless a stop triggers.
- Spread penalties are now $4.16, about 0.8% of capital. Make at most one trade per day. Only rotate into a clearly higher-ranked name.
- Don't take profits just because a position is up.

## Levels (entry / -6% / -8% stop)
- XLV: 184.48 / 173.41 / 169.72
- KO: 96.00 / 90.24 / 88.32
- V: take the entry price from the position record and compute both levels on the first day.

## Status
- Week: -2.28% vs SPY -2.64% (beat SPY). Since start: -11.99% vs SPY -5.08%.
- Holding V, XLV and KO, a defensive mix that suits a falling market. Let the rules run and don't chase a rebound in extended tech.
