# Glossary

Every term you'll meet in this series, in plain English. Each definition is one line, with a link to the page that explains it properly. Terms sit in alphabetical order, grouped by letter so the page is easy to scan.

## A–D

**Actionable signal** — a signal with confidence of 60 or more; anything lower gets ignored downstream (see [The strategies](05-strategies.md)).

**ADX** — an indicator that measures how strong a trend is, on a scale from 0 to 100 (see [The strategies](05-strategies.md)).

**Agent swarm** — a team of AI agents that split a big task, work in parallel and compare notes (see [The agent swarm](23-agent-swarm.md)).

**Allocation** — the split of your capital across strategies, set by weights like 50/25/25 (see [The portfolio](08-portfolio.md)).

**ATR** — average true range; how far a price typically moves per bar, so bigger means wilder (see [The strategies](05-strategies.md)).

**Backtest** — a replay of market history that simulates every trade and charges the real costs (see [Backtesting](09-backtesting.md)).

**Circuit breaker, API** — a switch that stops calls to a failing service; it moves through CLOSED, OPEN and HALF_OPEN (see [The risk engine](06-risk-engine.md)).

**Circuit breaker, market** — a switch that pauses all trading and cancels pending orders when markets turn dangerous (see [The risk engine](06-risk-engine.md)).

**Cointegration** — a statistical bond where two prices wander apart but keep meeting again (see [The strategies](05-strategies.md)).

**Commission** — the fee a broker charges per trade; backtests default to one dollar (see [Backtesting](09-backtesting.md)).

**Confidence** — a 0-100 score attached to every signal; under 60, downstream code ignores it (see [The strategies](05-strategies.md)).

**Drawdown** — how far your capital has fallen from its highest point so far (see [Backtesting](09-backtesting.md)).

## E–L

**EMA** — exponential moving average; a trend line that follows recent prices and weights the newest ones most (see [The strategies](05-strategies.md)).

**Ensemble** — a team of strategies with a referee that blends their votes into one signal (see [The strategies](05-strategies.md)).

**Exposure** — how much of your money sits at risk in the market right now (see [The risk engine](06-risk-engine.md)).

**Golden test** — a test that pins known correct outputs, so any change that breaks the math fails loudly (see [Backtesting](09-backtesting.md)).

**Hedging** — holding offsetting positions, so a loss on one side is softened by the other (see [The strategies](05-strategies.md)).

**Iceberg order** — a large order split into small hidden pieces, so the market never sees the full size (see [The trading rulebook](20-trading-rules.md)).

**Limit order** — an order that fills only at your price or better (see [Execution](07-execution.md)).

**Look-ahead bias** — using information your strategy couldn't know yet; the classic way backtests lie (see [Backtesting](09-backtesting.md)).

**Long / short** — long profits when the price rises; short profits when it falls (see [The strategies](05-strategies.md)).

## M–R

**MACD** — an indicator that spots trend shifts by comparing two EMAs of different speeds (see [The strategies](05-strategies.md)).

**Market impact** — the price move your own big order causes when it hits the market (see [The trading rulebook](20-trading-rules.md)).

**Market order** — an order that fills right now, at whatever price the market offers (see [Execution](07-execution.md)).

**Mean reversion** — the idea that a stretched price snaps back toward its own average (see [The strategies](05-strategies.md)).

**Meta-labeling** — a second model that filters the first model's signals, betting only on the trustworthy ones (see [The bibliography](22-bibliography.md)).

**Momentum** — the idea that a rising price keeps rising, and a falling one keeps falling (see [The strategies](05-strategies.md)).

**Monte Carlo P5** — the fifth percentile of thousands of shuffled return paths; a bad-luck drawdown estimate (see [Backtesting](09-backtesting.md)).

**Overfitting** — tuning a strategy so tightly to past data that it fails on new data (see [Optimization](26-optimization.md)).

**Pairs trading** — buying one symbol and shorting its cointegrated partner, betting the spread between them closes (see [The strategies](05-strategies.md)).

**Paper trading** — trading real prices with fake money, so you can test the system without risk (see [Execution](07-execution.md)).

**Position** — a bet on one symbol that stays open until you close it (see [The portfolio](08-portfolio.md)).

**Profit factor** — gross profit divided by gross loss; the acceptance check wants more than 1.3 (see [Backtesting](09-backtesting.md)).

**Quote** — a snapshot of one symbol's prices and volume at one moment (see [The strategies](05-strategies.md)).

**Regime** — the market's mood, like trending, wild or calm; it decides which strategy gets to run (see [The strategies](05-strategies.md)).

**RSI** — relative strength index; a 0-100 score of how fast price moved lately, period 14 (see [The strategies](05-strategies.md)).

## S–Z

**Sharpe ratio** — profit divided by volatility; a backtest passes acceptance above 1.0 (see [Backtesting](09-backtesting.md)).

**Signal** — a strategy's output: BUY, SELL or HOLD, plus a confidence score (see [The life of a trade](02-life-of-a-trade.md)).

**Slippage** — the gap between the price you ask for and the price you actually get (see [Backtesting](09-backtesting.md)).

**Sortino ratio** — like Sharpe, but only downside swings count, so big wins don't hurt your score (see [Backtesting](09-backtesting.md)).

**Survivorship bias** — testing only on symbols that still exist today, which quietly flatters your results (see [Backtesting](09-backtesting.md)).

**t+1 fill** — a signal born on bar t waits in a queue and fills at the next bar's open (see [Backtesting](09-backtesting.md)).

**Trade status** — an order's current state: pending, filled, partially filled, cancelled or rejected (see [Execution](07-execution.md)).

**Triple-barrier** — a labeling method with profit, loss and time fences; whichever fence is hit first sets the label (see [The bibliography](22-bibliography.md)).

**TWAP** — time-weighted average price; slicing one order into even pieces spread over time (see [The trading rulebook](20-trading-rules.md)).

**Verdict** — the acceptance package's judgment on a backtest: APPROVED, REVISION or REJECTED (see [Backtesting](09-backtesting.md)).

**VWAP** — volume-weighted average price; the day's average price weighted by volume, a patient order's target (see [The trading rulebook](20-trading-rules.md)).

**Walk-forward** — optimize on one slice of history, validate on the next, then roll the window forward (see [The bibliography](22-bibliography.md)).

**Win rate** — the share of closed trades that ended in profit (see [Backtesting](09-backtesting.md)).

**Z-score** — how far a value sits from its own average, counted in standard deviations (see [The strategies](05-strategies.md)).

Missing a term? Open an issue, or add it here yourself — one line, one link, done.
