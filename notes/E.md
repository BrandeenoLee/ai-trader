# Strategy E: Claude's pick: Large-cap momentum, fully invested, low turnover

## Approach
Hold 3-4 liquid large-cap momentum leaders plus a QQQ/XLK core. To beat SPY the money has to be invested. Cash is the biggest risk to this strategy: last week about 68% sat idle and we trailed SPY by 0.7%.

## Universe
- US stocks over $10B market cap with average daily volume over $50M, or liquid ETFs (QQQ, XLK, SMH, XLF, XLI).
- Skip anything up more than 15% in 3 days.

## Entry
- Price above the 50-day average, and the 50-day above the 200-day.
- **Limits: last price to +0.3% above. Never bid below the last price.** The MSFT order expired twice because of under-bids. After one expiry, re-place at last +0.3%. After two expiries, drop the name and use the sweep ETF.
- Don't wait for pullbacks. Buy at the first check-in that the rules allow.
- Don't open a position within 2 days of earnings.
- If SPY is below its 50-day average or there's a broad selloff, hold at most 2 stocks, but keep the sweep ETF.

## Sizing
- Confidence 8 or higher: 25-33%. Confidence 6-7: about two-thirds of a slot (about 20%). Confidence 5 or lower: skip.
- **Mandatory cash sweep, same check-in:** any cash above 10% after the stock orders goes into QQQ (or XLK) with a limit at last +0.2%. Sell the sweep to fund new leaders.
- No more than 2 single stocks per sector (the ETF doesn't count).
- Confidence is not yet predictive (tournament: 1-4 avg +0.17%, 5-7 avg +0.13%, small sample). Use it only for sizing, not as a reason to wait.

## Exits
- Sell if a position closes 8% below entry or below its 50-day average.
- Rotate only if a name falls off the leaders list and a clearly stronger name exists. At most 1 rotation per slot per week.
- Trim half if a position is up 20% or more within 2 weeks.
- Ignore single red days and headlines that don't change the fundamentals.

## Habits
- Holdings: META (about 32%). **First check-in this week:** buy one more leader (MSFT if it qualifies, otherwise another non-Communications leader) at about 20%, then sweep the rest into QQQ so cash ends at 10% or less.
- After that: do nothing unless an exit fires. 2-6 trades per week.
- Log a confidence score and a one-line reason for every trade.
