# The trader's guide

Who this is for: you own the money side. You want to know what the robot holds, why it traded, and what stops it going rogue. The code details are someone else's problem.

## Your mental model

Strategies turn prices into signals, and a signal is just an opinion with a confidence score from 0 to 100. Four risk gates stand between an opinion and an order, and any gate can say no.

Fills update one portfolio: cash, positions, and running profit and loss. Today the system trades paper money only — no real broker is wired in yet.

## Read this first

1. [The life of a trade](02-life-of-a-trade.md) — the six-step loop behind every position you'll ever see.
2. [The risk engine](06-risk-engine.md) — the gates and breakers that protect your capital.
3. [Strategies](05-strategies.md) — what the three brains believe and which numbers drive them.
4. [The portfolio](08-portfolio.md) — positions, P&L, and how capital splits between strategies.
5. [The dashboard](11-dashboard.md) — where you watch runs, objectives, and verdicts.

## Your flows

- Follow a trade from signal to updated position: [the life of a trade](02-life-of-a-trade.md).
- Know your limits: [the risk engine](06-risk-engine.md) — 25% max position, 30/80/95 exposure caps, stop-loss required.
- See why a strategy acted (or sulked): [strategies](05-strategies.md).
- Check where the money sits: [the portfolio](08-portfolio.md) — momentum 50%, mean reversion 25%, pairs 25% by default.
- Watch and compare runs: [the dashboard](11-dashboard.md), plus [IBKR](12-ibkr.md) when a live broker joins.

## Your commands

```bash
./scripts/start_paper_trading.sh    # paper trading: API on :8000, dashboard on :8501
./scripts/stop_paper_trading.sh     # stop the background API server
make dashboard                      # backtesting dashboard on :8503
```

## Watch out

- A signal with confidence under 60 is ignored. A "missing" trade often just scored low.
- The market breaker pauses all trading on big SPY drops and cancels pending orders. It resumes on its own.
- Trading only happens inside regular market hours, 9am to 4pm. Weekend silence is by design.
- There's no live broker yet — only the paper engine and a contract to implement. Real money needs an adapter.
