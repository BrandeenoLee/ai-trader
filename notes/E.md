# Strategy E: Claude's pick: S&P core with a small QQQ tilt, very few trades

## Approach
QQQ held against SPY is a beta/tech bet, not a proven edge. Since the start we are -8.5% vs SPY -3.0%. The gap comes from tech-led selloffs and the early META loss. The goal now is to track SPY closely with a modest QQQ tilt, keep spread costs low and avoid idle cash. Don't try to win back the gap with big bets.

## Target allocation (check once per week; act only if more than 7 points off target)
- **SPY below its 50-day average (or can't verify): QQQ about 55%, S&P 500 ETFs about 40%, cash 5% or less.**
- SPY above its 50-day on 3 consecutive verified closes: QQQ about 70%, S&P ETFs about 25%.
- S&P exposure can sit in SPY **and IVV or VOO** (same index). The per-position cap blocks adding SPY above about 35%, so put the overflow into IVV/VOO instead of leaving it as cash.
- Current state: QQQ about 55%, SPY about 35%, cash about 10%. Next action: one buy of about $40 of IVV (or VOO) at conf 5. After that, HOLD.
- Never sell QQQ just to fit under the cap. Caps limit buys, not existing holdings.

## Single stocks
- None for now. Revisit only after 3 verified closes above the 50-day, and then at most 10% of equity in one large-cap name, with no earnings report within 5 trading days.

## Orders
- Limit price: last to +0.3%. If an order expires twice, drop it. No trades under $25. Sweep cash once it exceeds 8%.
- Sale proceeds take a day to settle. Plan sell→buy as a 2-day sequence.

## Confidence
- Confidence is a **size knob tied to the code caps, not conviction**. Conf 3 allows about a 15% position, which blocked a needed rebalance buy. Use conf 5 for index/ETF buys that the allocation requires. Never go above 5. Tournament-wide, higher-confidence buys did worse (8-10 averaged -6.3%, 5-7 -4.2%, 1-4 -0.1%), so don't use high confidence to express conviction.

## Habits
- The default is HOLD. 0-1 trades per week. Log a one-line reason for each trade.
