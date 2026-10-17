# Backtesting

## The short version

A backtest replays market history to answer one question: would this strategy have made money? You feed it old prices and trading signals, and it simulates every fill with real costs. At the end you get metrics, a score and a verdict — before any real cash moves.

## One run, step by step

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 462" role="img" aria-label="Flow of one backtest: config, old prices and signals, t+1 simulation, friction, then metrics and result">
  <defs><marker id="arrowA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker></defs>
  <rect x="1" y="1" width="758" height="460" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="150" y="28" width="470" height="62" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="385" y="53" font-size="16" font-weight="bold" fill="#FFFFFF">BacktestConfig</text>
    <text x="385" y="75" font-size="12.5" fill="#FFFFFF">cash, commission, slippage, t+1</text>
    <line x1="385" y1="90" x2="385" y2="110" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowA)"/>
    <circle cx="112" cy="59" r="14" fill="#2B2D42"/><text x="112" y="64" font-size="13" font-weight="bold" fill="#FFFFFF">1</text>
    <rect x="150" y="114" width="470" height="62" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="385" y="139" font-size="16" font-weight="bold" fill="#FFFFFF">Old prices + signals</text>
    <text x="385" y="161" font-size="12.5" fill="#FFFFFF">both sorted by time</text>
    <line x1="385" y1="176" x2="385" y2="196" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowA)"/>
    <circle cx="112" cy="145" r="14" fill="#2B2D42"/><text x="112" y="150" font-size="13" font-weight="bold" fill="#FFFFFF">2</text>
    <rect x="150" y="200" width="470" height="62" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="385" y="225" font-size="16" font-weight="bold" fill="#2B2D42">Simulate each bar</text>
    <text x="385" y="247" font-size="12.5" fill="#2B2D42">t+1: fill at the next open</text>
    <line x1="385" y1="262" x2="385" y2="282" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowA)"/>
    <circle cx="112" cy="231" r="14" fill="#2B2D42"/><text x="112" y="236" font-size="13" font-weight="bold" fill="#FFFFFF">3</text>
    <rect x="150" y="286" width="470" height="62" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="385" y="311" font-size="16" font-weight="bold" fill="#FFFFFF">Pay the friction</text>
    <text x="385" y="333" font-size="12.5" fill="#FFFFFF">commission $1 + 0.1% slippage</text>
    <line x1="385" y1="348" x2="385" y2="368" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowA)"/>
    <circle cx="112" cy="317" r="14" fill="#2B2D42"/><text x="112" y="322" font-size="13" font-weight="bold" fill="#FFFFFF">4</text>
    <rect x="150" y="372" width="470" height="62" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="385" y="397" font-size="16" font-weight="bold" fill="#FFFFFF">Metrics, then result</text>
    <text x="385" y="419" font-size="12.5" fill="#FFFFFF">PerformanceMetrics in BacktestResult</text>
    <circle cx="112" cy="403" r="14" fill="#2B2D42"/><text x="112" y="408" font-size="13" font-weight="bold" fill="#FFFFFF">5</text>
  </g>
</svg>

The main class is `BacktestEngine` in `engine.py`; older code imports it as `SimpleBacktester`, which is just an alias. Everything starts from a `BacktestConfig`: $100,000 of starting cash, a $1 commission per trade, and 0.1% slippage by default. The engine then walks the bars in time order and matches each signal to the next bar of its symbol.

Here's the honesty rule. A signal born on bar t never fills on that bar. It waits in a queue and fills at the open of the next bar for that symbol. The switch is `next_day_execution`, and it's on by default. Without it, a strategy could trade on a closing price it doesn't know yet. That bug is called look-ahead bias, and it's the classic way backtests lie.

Every fill pays friction, and the engine charges both kinds. Commission is $1 per trade by default, or a percentage if the strategy sets one. Slippage is the gap between the price you want and the price you get — 0.1% by default. Buys fill a bit higher, sells a bit lower, and stops in wild markets fill worse. One shared function, `apply_slippage`, does all of it. There's also a guard: a trade is rejected if its expected profit can't beat five times the round-trip commission.

## The verdict

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 268" role="img" aria-label="A score of 20 points per passed check flows into three verdict states: APPROVED, REVISION, REJECTED">
  <defs><marker id="arrowB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker></defs>
  <rect x="1" y="1" width="758" height="266" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="170" y="24" width="420" height="62" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="49" font-size="16" font-weight="bold" fill="#2B2D42">The score</text>
    <text x="380" y="71" font-size="12.5" fill="#2B2D42">20 points per check, 100 max</text>
    <line x1="280" y1="86" x2="144" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <line x1="380" y1="86" x2="380" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <line x1="480" y1="86" x2="616" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <rect x="30" y="132" width="220" height="112" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="140" y="164" font-size="16" font-weight="bold" fill="#9B5DE5">APPROVED</text>
    <text x="140" y="192" font-size="12.5" fill="#2B2D42">all five checks pass</text>
    <text x="140" y="214" font-size="12.5" fill="#2B2D42">ship it as is</text>
    <rect x="270" y="132" width="220" height="112" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="164" font-size="16" font-weight="bold" fill="#9B5DE5">REVISION</text>
    <text x="380" y="192" font-size="12.5" fill="#2B2D42">score 60 or more</text>
    <text x="380" y="214" font-size="12.5" fill="#2B2D42">fix the failed checks</text>
    <rect x="510" y="132" width="220" height="112" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="620" y="164" font-size="16" font-weight="bold" fill="#9B5DE5">REJECTED</text>
    <text x="620" y="192" font-size="12.5" fill="#2B2D42">a hard rule broke</text>
    <text x="620" y="214" font-size="12.5" fill="#2B2D42">or score under 60</text>
  </g>
</svg>

When the loop ends, `PerformanceMetricsCalculator` turns your trades into numbers: win rate, Sharpe, drawdown, profit factor and friends. They land in a `PerformanceMetrics` object inside a `BacktestResult`. Then the acceptance package plays judge. Five checks run, and each pass adds 20 points to a score that maxes at 100:

- Sharpe over 1.0
- drawdown under 25%
- profit factor over 1.3
- Monte Carlo P5 above -20%
- return beating the benchmark by 3%

The verdict is a real enum in `acceptance/models.py` — APPROVED, REVISION or REJECTED — and REVISION kicks in at a score of 60. Hard rules can still kill a run: if commissions eat over 20% of gross profit, the verdict is REJECTED no matter the score.

## Many strategies, one pot

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 322" role="img" aria-label="One pot of capital split across three strategies, results combined, and capital moved to winners every 30 days">
  <defs><marker id="arrowC" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker></defs>
  <rect x="1" y="1" width="758" height="320" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="170" y="24" width="420" height="58" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="49" font-size="16" font-weight="bold" fill="#2B2D42">Allocation manager</text>
    <text x="380" y="70" font-size="12.5" fill="#2B2D42">splits capital by weights</text>
    <line x1="300" y1="82" x2="144" y2="112" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="380" y1="82" x2="380" y2="112" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="460" y1="82" x2="616" y2="112" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <rect x="30" y="116" width="220" height="84" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="140" y="146" font-size="15" font-weight="bold" fill="#2B2D42">Strategy A</text>
    <text x="140" y="170" font-size="12.5" fill="#2B2D42">own engine, own budget</text>
    <rect x="270" y="116" width="220" height="84" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="146" font-size="15" font-weight="bold" fill="#2B2D42">Strategy B</text>
    <text x="380" y="170" font-size="12.5" fill="#2B2D42">own engine, own cash</text>
    <rect x="510" y="116" width="220" height="84" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="620" y="146" font-size="15" font-weight="bold" fill="#2B2D42">Strategy C</text>
    <text x="620" y="170" font-size="12.5" fill="#2B2D42">own engine, own slice</text>
    <line x1="140" y1="200" x2="296" y2="230" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="380" y1="200" x2="380" y2="230" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="620" y1="200" x2="464" y2="230" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <rect x="170" y="236" width="420" height="58" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="261" font-size="15" font-weight="bold" fill="#FFFFFF">MultiStrategyResult</text>
    <text x="380" y="282" font-size="12.5" fill="#FFFFFF">one combined scorecard</text>
    <polyline points="590,265 688,265 688,53 596,53" fill="none" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <text x="712" y="159" font-size="11" fill="#2B2D42" transform="rotate(90 712 159)">every 30 days, winners get more</text>
  </g>
</svg>

`MultiStrategyBacktestEngine` runs several strategies side by side on one pot of capital. An allocation manager splits the pot by the weights you set, and each strategy gets its own engine and budget. Every 30 days the `DynamicCapitalReallocationEngine` moves money toward the winners. If the whole portfolio drops 20% early, the run stops. A meta-analyzer can also read many past results and suggest combinations that work well together.

## Where it lives in the code

- `app/backtesting/engine.py` — `BacktestEngine` (alias `SimpleBacktester`): the bar loop, t+1 fills, commission guard.
- `app/backtesting/models.py` — `BacktestConfig`, `BacktestResult`, `PerformanceMetrics`, `Trade`.
- `app/backtesting/shared/slippage_utils.py` — the one slippage formula every engine shares.
- `app/backtesting/acceptance/` — `VerdictDeterminer`, `ScoringService`, and the states in `models.py`; thresholds in `acceptance_criteria.py`.
- `app/backtesting/engines/multi_strategy_engine.py` — `MultiStrategyBacktestEngine`; `meta_analyzer/` sits nearby.

## Want to go deeper?

- [The data pipeline](04-data-pipeline.md) — where the old prices come from.
- [Strategies](05-strategies.md) — who generates the signals you're replaying.
