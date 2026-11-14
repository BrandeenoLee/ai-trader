# Strategy C notes: Catalyst reader

## Identity
Trade only when a specific headline explains a price move, or explains why a stock didn't move. Look for over- and under-reactions. Holding cash is allowed. The lead over SPY (−0.85% vs SPY −3.01% since start) comes almost entirely from holding cash in falling weeks. W6 confirmed the cost: holding cash in a +2.2% SPY week gave up about 2% of that lead.

## Entry rules
- Each session, name the best catalyst setup and give it a verdict: (a) what the news changes over 12 months, (b) whether the move is bigger than that, (c) buy, or hold with a specific reason.
- **Watchlist carry-forward:** check every flagged-but-skipped name first, every session. Drop a name after 5 sessions or if the thesis breaks.
- **Overreaction (>5% on specific news):** buy only after a green close that beats SPY by at least 1% that day, or after a full session holding above the prior low. A broad-rally green day doesn't count as confirmation.
- **No headline, no trade.** Skip big moves that no news explains.
- **Underreaction:** concrete material news with a move under 1%. Log one named candidate every session. **New (trial):** if 3 sessions in a row end in cash while SPY is up, buy the best stock-specific underreaction at conf 3, provided the news plausibly changes 12-month earnings or guidance. Outages, PR pledges and repeated sector headlines don't qualify.
- Prefer single-company catalysts. Stay out while a sector or macro selloff keeps adding bad news. Don't buy into structural downtrends.

## Data hygiene
- If every price shows 0.0%, the data is stale: hold, and say so.

## Sizing and confidence
- Tournament results: confidence 1–4 avg −0.13% (n=6), 5–7 −4.23% (n=13), 8–10 −6.25% (n=2). Higher confidence has done worse every week so far.
- Starters use confidence 3–4. Never go above 6. Add only after a further confirmed close that beats SPY. Hold at most 2 positions.

## Exits
- **Time stop, strict:** session 1 is the fill day. If the position is below cost at the end of session 3, exit at the next decision, with no extensions. This was applied correctly in W6.
- **Thesis break:** if new negative news widens the story, exit or cut by half.
- **Take profit** once about half the overreaction has retraced.

## Log
- W1: 0 trades, −0.01% vs SPY +0.68%.
- W2: −0.83% vs SPY −1.96%. Bought SMH too early.
- W3: +0.30% vs SPY −0.42%. SMH time-stop exit.
- W4: −0.02% vs SPY −0.54%. Flagged names never followed up.
- W5: −0.33% vs SPY −2.64%. GOOGL bought on a broad-rally day.
- W6: +0.05% vs SPY +2.18%. GOOGL time-stop exit (−$1.18), then cash all week. No qualifying catalyst was found.
