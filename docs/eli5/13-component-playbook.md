# The component playbook

## The short version

Every trade passes through a handful of named components, and each one runs a small, knowable strategy. This page is a card for each: its job, its real numbers from the config, and its place in the line.

## The map

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 500" role="img" aria-label="Map of the seven components with their one-line logic, color-coded by layer">
  <rect x="1" y="1" width="758" height="498" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="24" width="340" height="88" rx="13" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="200" y="58" font-size="15" font-weight="bold" fill="#2B2D42">Strategy engines</text>
    <text x="200" y="80" font-size="11.5" fill="#2B2D42">trend: ADX 25+, MACD cross</text>
    <text x="200" y="98" font-size="11.5" fill="#2B2D42">reversion: z-score past 2.0</text>
    <rect x="390" y="24" width="340" height="88" rx="13" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="560" y="58" font-size="15" font-weight="bold" fill="#2B2D42">Signal scorer</text>
    <text x="560" y="80" font-size="11.5" fill="#2B2D42">three scores, 0 to 100</text>
    <text x="560" y="98" font-size="11.5" fill="#2B2D42">reject under 60 / 70 / 50</text>
    <rect x="30" y="126" width="340" height="88" rx="13" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="200" y="160" font-size="15" font-weight="bold" fill="#FFFFFF">Portfolio risk manager</text>
    <text x="200" y="182" font-size="11.5" fill="#FFFFFF">exposure 80%, sector 30%</text>
    <text x="200" y="200" font-size="11.5" fill="#FFFFFF">loss 5%, drawdown 15%</text>
    <rect x="390" y="126" width="340" height="88" rx="13" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="560" y="160" font-size="15" font-weight="bold" fill="#FFFFFF">Circuit breakers</text>
    <text x="560" y="182" font-size="11.5" fill="#FFFFFF">market halts: 7, 13, 20%</text>
    <text x="560" y="200" font-size="11.5" fill="#FFFFFF">API: 5 fails, 300 s</text>
    <rect x="30" y="228" width="340" height="88" rx="13" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="200" y="262" font-size="15" font-weight="bold" fill="#FFFFFF">Portfolio service</text>
    <text x="200" y="284" font-size="11.5" fill="#FFFFFF">fetch, then risk check</text>
    <text x="200" y="302" font-size="11.5" fill="#FFFFFF">breaker guards every call</text>
    <rect x="390" y="228" width="340" height="88" rx="13" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="560" y="262" font-size="15" font-weight="bold" fill="#2B2D42">Execution engine</text>
    <text x="560" y="284" font-size="11.5" fill="#2B2D42">one cycle per tick</text>
    <text x="560" y="302" font-size="11.5" fill="#2B2D42">risk check per signal</text>
    <rect x="210" y="330" width="340" height="88" rx="13" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="364" font-size="15" font-weight="bold" fill="#FFFFFF">Paper trading</text>
    <text x="380" y="386" font-size="11.5" fill="#FFFFFF">$100k fake cash</text>
    <text x="380" y="404" font-size="11.5" fill="#FFFFFF">0.1% fee, plus slippage</text>
    <rect x="40" y="446" width="16" height="16" rx="4" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="64" y="459" font-size="11" fill="#2B2D42" text-anchor="start">Sky — entry</text>
    <rect x="180" y="446" width="16" height="16" rx="4" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="204" y="459" font-size="11" fill="#2B2D42" text-anchor="start">Mint — coordination</text>
    <rect x="330" y="446" width="16" height="16" rx="4" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="354" y="459" font-size="11" fill="#2B2D42" text-anchor="start">Sunflower — math</text>
    <rect x="480" y="446" width="16" height="16" rx="4" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="504" y="459" font-size="11" fill="#2B2D42" text-anchor="start">Coral — risk</text>
    <rect x="610" y="446" width="16" height="16" rx="4" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="634" y="459" font-size="11" fill="#2B2D42" text-anchor="start">Grape — results</text>
  </g>
</svg>

Color is the layer, like on page one. Yellow computes, red guards, purple keeps the books, green runs the show. Read left to right, top to bottom — that's roughly the order work flows.

## The pipeline

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 276" role="img" aria-label="Pipeline from market data through analysis, scoring, risk, portfolio and execution to paper trading">
  <defs>
    <marker id="pipeArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="274" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="44" width="160" height="60" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="105" y="68" font-size="14" font-weight="bold" fill="#FFFFFF">Market data</text>
    <text x="105" y="88" font-size="11" fill="#FFFFFF">quotes and bars</text>
    <rect x="208" y="44" width="160" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="288" y="68" font-size="14" font-weight="bold" fill="#2B2D42">Strategy engines</text>
    <text x="288" y="88" font-size="11" fill="#2B2D42">ADX, MACD, RSI</text>
    <rect x="391" y="44" width="160" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="471" y="68" font-size="14" font-weight="bold" fill="#2B2D42">Signal scorer</text>
    <text x="471" y="88" font-size="11" fill="#2B2D42">score 0 to 100</text>
    <rect x="574" y="44" width="160" height="60" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="654" y="68" font-size="14" font-weight="bold" fill="#FFFFFF">Risk manager</text>
    <text x="654" y="88" font-size="11" fill="#FFFFFF">caps and vetoes</text>
    <line x1="187" y1="74" x2="204" y2="74" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
    <line x1="370" y1="74" x2="387" y2="74" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
    <line x1="553" y1="74" x2="570" y2="74" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
    <path d="M 654 108 V 156 H 105 V 184" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
    <rect x="25" y="190" width="160" height="60" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="105" y="214" font-size="14" font-weight="bold" fill="#FFFFFF">Portfolio service</text>
    <text x="105" y="234" font-size="11" fill="#FFFFFF">state plus risk check</text>
    <rect x="208" y="190" width="160" height="60" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="288" y="214" font-size="14" font-weight="bold" fill="#2B2D42">Execution engine</text>
    <text x="288" y="234" font-size="11" fill="#2B2D42">validated orders</text>
    <rect x="391" y="190" width="160" height="60" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="471" y="214" font-size="14" font-weight="bold" fill="#FFFFFF">Paper trading</text>
    <text x="471" y="234" font-size="11" fill="#FFFFFF">fills with fees</text>
    <line x1="187" y1="220" x2="204" y2="220" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
    <line x1="370" y1="220" x2="387" y2="220" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pipeArrow)"/>
  </g>
</svg>

A price tick enters on the left and either dies at a gate or becomes a paper fill on the right. Every arrow is a rejection point. Most ideas don't get past the scorer.

## Strategy engines — the analyst

There's no class named `TechnicalAnalyst` in this repo; the strategy engines play that part, in `app/engines/strategy_engines/`. `TrendFollowingStrategyEngine` buys when ADX (a trend-strength gauge) is over 25 and MACD (12/26/9) crosses up. Volume must be at least 1.2x its 20-bar average. `MeanReversionStrategyEngine` computes a z-score — how far the price sits from its own mean, in deviations — and buys under -2.0. Both get indicators from `TechnicalIndicatorCalculator`, a thin wrapper over `TechnicalIndicators`, which also does RSI: period 14, under 30 oversold, over 70 overbought. Inputs are quotes plus 200-bar history buffers; the output is a `Signal`.

## SignalScorerService — the grader

`SignalScorerService` in `app/services/signal_scorer.py` delegates the math to `SignalEvaluationEngine`. Every idea gets three scores from 0 to 100: strength, confidence, and liquidity. Strength blends volatility (60%) with volume ratio (40%); confidence blends data quality (70%) with trend consistency (30%). The combined score weights them 40% strength, 40% confidence, and 20% liquidity. A signal survives only if strength is at least 60, confidence at least 70, and liquidity at least 50. Those floors are the defaults in `TradingThresholds`. Survivors land in a priority queue of 1,000, and a 10-minute cooldown (`signal_cooldown_minutes`) stops the same symbol from spamming.

## PortfolioRiskManager — the risk boss

The risk job has no plain `RiskManager` class; it's `PortfolioRiskManager` in `app/services/portfolio_risk_manager.py`. Its `assess_portfolio_risk` measures total exposure, per-sector exposure, pairwise correlations, daily loss, drawdown, volatility, and currency exposure. A violation fires when exposure passes 80% or a sector passes 30%. A correlation above 0.7, daily loss past 5%, or drawdown past 15% fires too. Severity then sets the level: any critical violation means CRITICAL, a high one (or three medium) means HIGH, one medium means MEDIUM. It also owns the tripwires at 5% daily loss, 10% drawdown, and 5% volatility, and caches correlation results for one hour.

## CircuitBreakerManager — two referees, one name

Two different classes carry this exact name, and they guard different things. The one in `app/services/api_circuit_breaker.py` guards API calls: five failures open the circuit, calls stop for 300 seconds, then three half-open successes close it. It runs four of them — API errors, data service, order execution, broker connection. The one in `app/services/circuit_breaker_manager.py` watches the market itself. It tracks SPY every 30 seconds and maps drops of 7%, 13%, and 20% to Level 1, 2, and 3 halts. A VIX reading of 25 logs a warning; 35 pauses all trading, with auto-resume once the halt lifts.

## PortfolioService — the keeper

`PortfolioService` in `app/services/portfolio_service.py` wraps a `PortfolioProvider` and never trusts it blindly. Every fetch first checks whether the API circuit breaker is open; if it is, you get `None` back instead of an error storm. Each successful fetch is followed by a full `PortfolioRiskManager` assessment, so the risk level stays fresh. It also owns the `CurrencyHedgingEngine` and the sector and country diversification validators. Adding a position runs the risk assessment with that position included, before anything moves.

## ExecutionEngine — the runner

The runner lives in `app/domain/strategies/execution_engine.py`. Its `run_cycle` asks the registry for the active strategy, calls `generate_signals`, then runs `risk_check` on each signal. Signals that pass get logged and returned; the rest are rejected with a reason. A second class with the same name sits in `app/domain/engines/execution_engine.py` and picks how an order goes out: MARKET, LIMIT, TWAP, VWAP, or ICEBERG. TWAP spreads an order over time, VWAP tracks the day's average price, and ICEBERG hides the true size.

## PaperTradingService — the dress rehearsal

`PaperTradingService` in `app/services/paper_trading_service.py` trades real prices with fake money — and charges you for it. The default config starts with $100,000 and a 100 ms delay. It charges a 0.1% commission, 0.05% slippage and 0.01% market impact, with no partial fills. Position size is capped at 50% of equity; the daily loss and drawdown limits (5% and 15%) come straight from the trading config. `_can_execute_trade` checks cash, the position cap, and both loss limits before anything fills. In REALISTIC mode, slippage is added to the fill price — buys pay more, sells get less. Portfolios, sessions, and trades live in memory, so a restart wipes the slate.

## Where it lives in the code

- `app/engines/strategy_engines/` — trend, momentum, mean reversion, breakout, pairs, and arbitrage engines; indicators come from `app/domain/services/analysis/momentum.py`.
- `app/services/signal_scorer.py` and `app/services/signal_evaluation_engine.py` — scoring service and its math; cooldown and queue in `app/services/signal_scoring_engine.py`.
- `app/services/portfolio_risk_manager.py` — limits, violations, and risk levels.
- `app/services/api_circuit_breaker.py` and `app/services/circuit_breaker_manager.py` — both breaker managers.
- `app/services/portfolio_service.py` — the portfolio keeper.
- `app/domain/strategies/execution_engine.py` and `app/domain/engines/execution_engine.py` — both execution engines.
- `app/services/paper_trading_service.py` — the simulation.
- `app/shared/config/trading_config.py` — most defaults quoted on this page.

## Want to go deeper?

- [Strategies](05-strategies.md) — the engines in detail, one page per idea.
- [Risk engine](06-risk-engine.md) — the limits and what trips them.
- [Execution](07-execution.md) — how a validated signal becomes an order.
