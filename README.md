# AI Strategy Tournament

Five Claude-driven trading strategies compete in an Alpaca **paper** account, each with a
virtual $500. Every Friday, Claude reviews each strategy's week and rewrites its notes. The
goal is to find out whether any of them beats SPY buy-and-hold after trading and AI costs.

| Strategy | Idea |
| --- | --- |
| A | Momentum |
| B | Mean reversion |
| C | Catalyst reader (news) |
| D | Small-cap explorer |
| E | Claude's pick (redesigned weekly, with a logged confidence score) |
| SPY | Benchmark: $500 bought on day one and held |

## How it works

```
market data -> Claude proposes -> guardrails (plain code) -> Alpaca -> trade journal
                    ^                                                     |
                    +---- strategy notes <---- Friday review (Opus) <-----+
```

- **The AI proposes; code decides.** `bot/guardrails.py` trims or rejects anything that breaks a rule.
  Rules: stocks/ETFs only, no shorting or margin, settled cash only, limit orders within 3% of the
  price, GME and AMC excluded, listed exchanges only, at most 6 orders per strategy per day.
- **Confidence-scaled sizing.** Max share of a strategy's equity in one position: confidence 1-4 → 15%,
  5-7 → 35%, 8-10 → 75%.
- **Honest paper results.** Every fill is charged a simulated spread penalty (double for illiquid
  names), small-cap orders are capped at 1% of average daily dollar volume, and each strategy's AI
  cost is subtracted from its returns.
- **Earned check-ins.** Each strategy starts at 2 check-ins per trading day. Beating SPY in a week
  earns one more (max 5); trailing loses one (min 1).
- **Budget.** Target $5/month, hard stop at $20/month. If spending runs ahead of the $5 pace,
  strategies trailing SPY drop to one check-in per day.

All settings live in `bot/config.py`.

## Setup

1. **Secrets** (repo → Settings → Secrets and variables → Actions):

   | Secret | What |
   | --- | --- |
   | `ALPACA_API_KEY` | Alpaca **paper** key (starts with `PK`) |
   | `ALPACA_SECRET_KEY` | Alpaca paper secret |
   | `ANTHROPIC_API_KEY` | From platform.claude.com |
   | `EMAIL_USER` | Gmail address that sends the Friday recap |
   | `EMAIL_APP_PASSWORD` | Gmail app password (needs 2-step verification) |
   | `EMAIL_TO` | Optional: where the recap goes (defaults to `EMAIL_USER`) |

2. **Design strategy E**: Actions → *Friday review* → Run workflow → mode `design-e`.
   Read the result in `notes/E.md`.
3. **Optional smoke test**: Actions → *Check-in* → Run workflow with *force* ticked while the market
   is open. Every strategy decides once; check the journal and the Alpaca paper dashboard.
4. **Dashboard**: Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
   Note: a Pages site is public even when the repo is private. It shows trades and reasoning only,
   never keys.

After that, everything runs on schedule: check-ins at 9:45, 11:00, 12:30, 14:00 and 15:30 ET on
trading days, and the review plus recap email on Fridays after the close. Each run commits the
updated state back to the repo.

## Stopping it

- **Kill switch:** create a file named `KILL_SWITCH` in the repo root (any content). All trading stops
  at the next check-in; reviews and the dashboard keep working. Delete the file to resume.
- **Full stop:** Actions → select the workflow → ⋯ → Disable workflow.

## Running locally

```bash
pip install -r requirements.txt pytest
python -m pytest -q                         # 24 tests, no keys needed
DRY_RUN=1 python -m bot.checkin --force     # simulated market + fake AI (writes to *_dryrun folders)
```

With keys exported in your shell, `python -m bot.checkin --force` runs a real paper check-in.

## Files

| Path | What |
| --- | --- |
| `bot/checkin.py` | One check-in: reconcile fills, settle cash, run eligible strategies, place orders |
| `bot/review.py` | Friday review, learning step, check-in levels, recap; `--design-e` |
| `bot/guardrails.py` | Every rule an order must pass |
| `bot/ledger.py` | Virtual $500 sub-accounts with T+1 settlement and spread penalties |
| `bot/strategies.py` | Prompts and the market context each strategy sees |
| `bot/broker.py` | Alpaca Trading API + market data, and a simulator for tests |
| `bot/ai.py` | Claude API calls, spend tracking, budget |
| `bot/report.py` | Recap email and dashboard |
| `notes/` | Each strategy's rules, rewritten weekly by the review |
| `state/` | Ledger, journal, spend, weekly results (committed by the workflows) |
| `docs/` | Generated dashboard |

## Known limits

- Six to eight weeks can't separate skill from luck.
- Paper fills are still cleaner than real ones, especially for small caps.
- GitHub's scheduler can start runs late; a run more than 40 minutes past its slot is skipped.
- If two strategies place opposite orders in the same stock at once, Alpaca may reject one as a
  potential wash trade. It's logged and the strategy tries again at its next check-in.
- Never switch to live trading (`ALPACA_LIVE=1`) without reviewing the paper results first.
