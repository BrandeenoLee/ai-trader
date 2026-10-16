# Strategy A notes: Momentum

## Entry rules
- Buy names with positive 20-day AND 60-day returns that trade above their 50-day average.
- Rank by 60-day trend first, then 20-day. PLTR, the 60d leader, is still the core pick.
- Don't chase a single-day spike of more than 5%.
- A name more than 15% above its 50d average is extended. Skip it, or give it the smallest position. AMD was the extended name, and it lost 14% in one week.
- Don't hold three names from the same high-beta tech/semis cluster. This week all three holdings fell together (-7.5% vs SPY -1.96%). When redeploying, prefer a leader from a different sector.

## Sizing
- Hold 2-4 positions, keeping $15-25 in cash.
- Default confidence is 5. Use 6 only for a name that leads on both 20d and 60d, is not extended and has no spike. Don't use 7+ for now: tournament results run the wrong way (1-4 avg +0.70%, 5-7 avg -4.68%, n=10).

## Exits and rotation
- Hard stop: sell any position that closes 8% or more below entry, even if its 50d and 20d rules haven't triggered. The 50d rule acts too slowly in a sharp drop; by the time it fired on AMD, the loss had reached 14% (-$22.81).
- Also rotate out when a holding closes below its 50d average, or when its 20d return turns negative and it falls out of the top names.
- Hold at least 3 trading days unless a stop or the 50d break triggers.
- Spread penalties have reached $2.93, about 0.6% of capital. Make at most one rotation per day, and only into a clearly higher-ranked name.
- Don't take profits just because a position is up.

## Execution
- Place limit orders near the current quote.
- Two fills have broken their limits: the META buy at 722.34 against a 720 limit, and the AMD sell at 537.71 against a 544.5 limit. Check every fill against its limit and log any repeat.

## Status
- Week: -7.50% vs SPY -1.96%. Since start: -7.20% vs SPY -1.56%.
- Holding PLTR (core) and META, with the AMD proceeds settling. Once they settle, redeploy about $100-125 into the top-ranked name that is not extended and preferably not tech. Apply the 8% stop to PLTR and META from their entry prices.
