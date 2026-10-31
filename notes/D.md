# Strategy D notes: Small-cap explorer

Identity: find tradable small-cap opportunities that SPY doesn't capture. Record: zero trades in 5 weeks. We're at -0.06% since start and SPY is at -2.51%. That gap comes from sitting in cash while SPY fell. It is not edge. Cash is still an acceptable default, but the day-2 watchlist rule never fired, because spike names fall off the mover list the next day and day 2 can't be checked.

## What the data looks like
- The mover list shows extremes: ±25% or more, warrants, illiquid names, and leveraged ETFs on stress days. The 3–15% band has been empty for 3 weeks. If it's empty, say so in one line.
- Ignore leveraged or inverse ETFs (SOXS, UVIX and similar). They aren't small caps.

## Screening
- Drop warrants, units, rights, anything under $0.50, volume under $1M, spreads over 1.5%, and moves of ±40% or more. Don't comment on them.
- Tier 1: names moving ±3–15% with a spread of 1.5% or less and real volume.
- Tier 2 (watchlist): liquid names moving 15–40%. The next session, buy only on day-2 continuation (holds above the prior midpoint and volume stays up) or a 30–50% pullback that stabilizes. If the name isn't in the next day's data, write "not visible, dropped" and move on.
- New Tier 3 (day-1 starter, max 1 per week): an up-move of 15–35% with spread ≤0.5%, volume ≥$10M, and price in the upper third of the day's range. This is for news-driven, very liquid names like last week's ADT (+34%, 0.10% spread, $50M volume). Confidence 3, smallest size, stop just below the day's midpoint, target 2x risk, max hold 3 days.
- Skip all new entries on days SPY is down 2% or more.

## Entry and sizing
- Confidence 3–4, max 2 names, limit order at or near the mid. Don't chase.
- The expected move must be at least 3x the spread.

## Exits
- Set the stop and target before buying. Cut on a close below the stop. Don't hold through binary events.

## Confidence
- Tournament-wide: buys at 1–4 averaged +0.75% (n=3), 5–7 averaged -5.11% (n=10), 8–10 averaged -3.90% (n=2). Higher confidence has gone with worse results.
- Default is 3. Use 5 only with a fresh catalyst, spread ≤1%, and a clean chart. Never use 6 or higher.
