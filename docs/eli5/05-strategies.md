# Trading strategies

## The short version

A strategy is the part of the brain that turns prices into opinions. It reads fresh market data, boils it down to a few numbers, and answers with a signal: buy, sell, or hold. Here are the three core strategies, plus the referee that can team them up.

## From quote to signal

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 220" role="img" aria-label="Diagram of the shared signal pipeline: quote in, indicators in the middle, signal out">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="218" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="60" width="200" height="120" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="90" font-size="16" font-weight="bold" fill="#FFFFFF">Quote</text>
    <text x="130" y="118" font-size="12.5" fill="#FFFFFF">symbol · prices</text>
    <text x="130" y="140" font-size="12.5" fill="#FFFFFF">volume · timestamp</text>
    <rect x="280" y="60" width="200" height="120" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="90" font-size="16" font-weight="bold" fill="#2B2D42">Indicators</text>
    <text x="380" y="118" font-size="12.5" fill="#2B2D42">RSI · EMA · z-score</text>
    <text x="380" y="140" font-size="12.5" fill="#2B2D42">ROC · OBV · ATR</text>
    <rect x="530" y="60" width="200" height="120" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="630" y="90" font-size="16" font-weight="bold" fill="#FFFFFF">Signal</text>
    <text x="630" y="114" font-size="12.5" fill="#FFFFFF">BUY / SELL / HOLD</text>
    <text x="630" y="134" font-size="12.5" fill="#FFFFFF">symbol · price · confidence</text>
    <text x="630" y="154" font-size="12.5" fill="#FFFFFF">timestamp · metadata</text>
    <line x1="232" y1="120" x2="276" y2="120" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="482" y1="120" x2="526" y2="120" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
  </g>
</svg>

Every strategy follows the same pipeline, whatever its style. A quote (a snapshot of one symbol's prices and volume) goes in. The strategy turns price history into indicators, small numbers that describe the trend or the stretch. Then it wraps its verdict in a `Signal`, a data class from `app/domain/models/signal.py`. Its type is BUY, SELL or HOLD, and its confidence is a 0-100 score. Under 60, the signal isn't actionable, so downstream code ignores it. All strategies extend `BaseStrategy` from `app/domain/strategies/base.py`, so they share two methods: `generate_signals()` and `risk_check()`.

## The three strategies

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" role="img" aria-label="Diagram of the three strategies, each with its name, its indicators, and the question it asks">
  <rect x="1" y="1" width="758" height="418" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="30" width="130" height="100" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="85" font-size="14.5" font-weight="bold" fill="#2B2D42">Momentum</text>
    <rect x="180" y="30" width="290" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="325" y="64" font-size="12.5" fill="#2B2D42">RSI 14 · EMA 20</text>
    <text x="325" y="86" font-size="12.5" fill="#2B2D42">volume ratio · ROC · OBV</text>
    <text x="325" y="108" font-size="12.5" fill="#2B2D42">Stoch RSI · ATR gate</text>
    <rect x="500" y="30" width="230" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="615" y="85" font-size="11" fill="#2B2D42">Is this uptrend real and strong?</text>
    <rect x="30" y="160" width="130" height="100" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="215" font-size="13.5" font-weight="bold" fill="#2B2D42">Mean reversion</text>
    <rect x="180" y="160" width="290" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="325" y="204" font-size="12.5" fill="#2B2D42">z-score vs. own average</text>
    <text x="325" y="226" font-size="12.5" fill="#2B2D42">lookback + volatility cap</text>
    <rect x="500" y="160" width="230" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="615" y="215" font-size="11" fill="#2B2D42">Is this price stretched too far?</text>
    <rect x="30" y="290" width="130" height="100" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="345" font-size="13.5" font-weight="bold" fill="#2B2D42">Pairs trading</text>
    <rect x="180" y="290" width="290" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="325" y="324" font-size="12.5" fill="#2B2D42">cointegration test</text>
    <text x="325" y="346" font-size="12.5" fill="#2B2D42">hedge ratio + spread</text>
    <text x="325" y="368" font-size="12.5" fill="#2B2D42">entry 2.0 · exit 0.5</text>
    <rect x="500" y="290" width="230" height="100" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="615" y="345" font-size="11" fill="#2B2D42">Will these two prices meet again?</text>
  </g>
</svg>

**Momentum** buys strength, and `momentum.py` runs it. Its RSI (a 0-100 score of how fast price moved lately, period 14) must sit between 40 and 60. Price must hold above its EMA 20, a trend line that follows recent prices. Volume and ROC (rate of change) must confirm, and OBV (a running volume total) must not fall. Two guards watch the door: no BUY when RSI hits 70, no SELL at 30. A scoring engine then re-checks each signal before it leaves.

**Mean reversion** bets that stretched prices snap back, and `mean_reversion.py` runs it. It computes a z-score, which counts how far price sits from its own average, in normal steps. A very negative z-score means cheap: buy. Very positive means expensive: sell. A lookback window sets how much history counts, and a volatility cap blocks assets that swing too wildly.

**Pairs trading** works on two symbols at once, in `pairs_trading.py`. It first tests them for cointegration, a statistical bond where two prices wander but keep meeting again. The hedge ratio says how many units of one asset balance the other, and their difference is the spread. When the spread's z-score passes 2.0, the pair enters; near 0.5, it exits.

## When strategies team up

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 320" role="img" aria-label="Diagram of the ensemble: three strategies feed one ensemble box, which outputs one combined signal">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="318" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="25" width="210" height="64" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Momentum</text>
    <rect x="275" y="25" width="210" height="64" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Mean reversion</text>
    <rect x="525" y="25" width="210" height="64" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="630" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Pairs trading</text>
    <line x1="130" y1="91" x2="130" y2="121" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="380" y1="91" x2="380" y2="121" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="630" y1="91" x2="630" y2="121" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="100" y="125" width="560" height="100" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="152" font-size="15" font-weight="bold" fill="#2B2D42">Ensemble — the referee</text>
    <text x="380" y="178" font-size="12" fill="#2B2D42">WeightedEnsemble · Sharpe weights</text>
    <text x="380" y="200" font-size="12" fill="#2B2D42">VotingEnsemble · majority vote (min 2)</text>
    <text x="380" y="222" font-size="12" fill="#2B2D42">RegimeBasedSelector · by market regime</text>
    <line x1="380" y1="227" x2="380" y2="252" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="190" y="258" width="380" height="50" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="279" font-size="14" font-weight="bold" fill="#FFFFFF">One combined signal</text>
    <text x="380" y="298" font-size="11.5" fill="#FFFFFF">next stop: the risk engine</text>
  </g>
</svg>

An ensemble is a team of strategies with a referee, and it lives with the engines, not in the strategies folder. `WeightedEnsemble` gives each member a weight based on its Sharpe ratio (profit divided by risk). `VotingEnsemble` waits for agreement: at least two strategies must point the same way. `RegimeBasedSelector` reads the market's mood (trending, wild, or calm) and picks the strategy that fits. When members disagree, the config picks the referee's rule: weighted, majority, or strongest.

## Where it lives in the code

- `app/domain/strategies/momentum.py` — `MomentumStrategy`: RSI, EMA, volume ratio, ROC, OBV.
- `app/domain/strategies/mean_reversion.py` — `MeanReversionStrategy`: z-score with a lookback window.
- `app/domain/strategies/pairs_trading.py` — `PairsTrading`: cointegration, hedge ratio, spread z-score.
- `app/domain/models/signal.py` — the `Signal` model: type, confidence, strength, metadata.
- `app/engines/strategy_engines/ensemble.py` — `WeightedEnsemble`, `VotingEnsemble`, `RegimeBasedSelector`.
- `app/shared/config/params/trading_thresholds.py` — the default numbers, like RSI 70/30 and the 40-60 zone.

## Want to go deeper?

- [The risk engine](06-risk-engine.md) — what can veto a signal before real money moves.
- [The life of a trade](02-life-of-a-trade.md) — follow one signal to a filled order.
- [Backtesting](09-backtesting.md) — how strategies prove themselves on old data.
