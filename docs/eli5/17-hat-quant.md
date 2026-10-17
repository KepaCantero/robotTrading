# The quant's guide

Who this is for: you design strategies and judge them with data. You care about indicators, fills, costs, and whether a result is honest.

## Your mental model

A strategy is a function from quotes to signals: indicators in the middle, BUY/SELL/HOLD out with a 0-100 confidence. The backtester replays history with next-bar fills and real friction, then scores the run.

A verdict of APPROVED needs all five checks green; 60 points or more buys you REVISION instead. Ensemble code can combine brains by Sharpe weights, majority vote, or market regime.

## Read this first

1. [Strategies](05-strategies.md) — the three brains, their indicators, and their guard rails.
2. [Backtesting](09-backtesting.md) — t+1 fills, friction, and the acceptance scoring.
3. [The data pipeline](04-data-pipeline.md) — where your rows come from and how they get cleaned.
4. [The portfolio](08-portfolio.md) — allocation weights and the rebalance rules around them.
5. [The dashboard](11-dashboard.md) — where runs, scores and comparisons actually happen.

## Your flows

- Know the strategies and their knobs: [strategies](05-strategies.md) — RSI 70/30, z-score entry, pairs at spread 2.0.
- Prove an idea on history: [backtesting](09-backtesting.md) — Sharpe, drawdown, profit factor, Monte Carlo.
- Get clean data: [the data pipeline](04-data-pipeline.md) — normalizer, quality score, cache, CSVs.
- Split the pot: [the portfolio](08-portfolio.md) — allocation manager, min and max weights, 5% rebalance drift.
- Combine brains: the ensembles in [strategies](05-strategies.md) — weighted, voting, regime-based.

## Your commands

```bash
make dashboard                                        # run and compare backtests, :8503
python -m app.presentation.dashboard.nicegui_app      # same app, no docs build first
make test                                             # the suite
```

## Watch out

- Keep `next_day_execution` on. Turning it off invites look-ahead bias, and the backtest lies to you.
- If commissions eat over 20% of gross profit, the run is REJECTED no matter the score.
- The historical CSVs are daily bars, some back to 1984. Finer detail means live feeds.
- A signal scoring under 60 does nothing downstream. A clever idea at 55 is invisible in production.
- Weights drift back toward winners every 30 days in multi-strategy runs. Past performance chases itself.
