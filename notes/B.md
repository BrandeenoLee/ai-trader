# Strategy B notes: Mean reversion

## Entry setup (unchanged core)
- Look for liquid names with a sharp 5-day drop that is large for their volatility (roughly 2x normal 5-day move or more), while the 60-day trend is still intact and price is near or above its 50d MA.
- Skip drops caused by clear bad news: earnings misses, guidance cuts, sector-wide regulatory or pricing shocks (e.g. the VZ/T one-day -8% on 10/09).
- An unexplained sharp drop is not an automatic skip. Before deciding, check for news. If none turns up and the trend is intact, it can be a small position.

## Sizing and cash
- Sitting almost all in cash guarantees lagging SPY in an up week (this week: +0.14% vs SPY +0.68%). Aim for 2-4 small positions in different, uncorrelated dips rather than one starter plus cash.
- Size by setup quality. A low-confidence starter is fine, but don't let one tiny position be the whole book week after week.
- Spread costs are large compared with these tiny positions ($1.96 paid so far vs a ~$72 position). Prefer names with tight spreads, avoid many tiny trades, and don't trade in and out.

## Orders
- Set limit prices near the current price. A limit far below the market either doesn't fill or fills at a very different price. Check the fill price against the limit after every fill. The CRM buy was placed @222.5 but filled @228.72, which is above the limit and looks like a data or execution anomaly; flag any repeat.

## Exits
- Take profits when the price gets back to about the pre-drop level (for CRM, roughly a 5% bounce from the low).
- Cut if the price falls about 5% below the entry/fill price, or if bad news comes out after entry.
- Time stop: if there's no bounce within about 10 trading days, exit and recycle the cash.

## Confidence
- Only one fill so far (conf 3), so there isn't enough data to judge calibration yet. Keep confidence honest; don't inflate it to get bigger size.
