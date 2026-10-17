# Strategy optimization, meta-labeling and walk-forward

## The short version

Optimization means trying many parameter sets for a strategy and keeping the best one. A parameter is a knob, like a lookback window of 20 days. The danger is overfitting: you tune the knobs so well to past noise that live results disappoint. This repo fights back with three tools. Labeling turns past prices into clean teaching examples. Meta-labeling adds a second model that decides how much to bet. Walk-forward keeps checking that your gains survive on data the tuner never saw.

## The loop, and the guards around it

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 310" role="img" aria-label="The optimization loop: pick parameters, run backtest, score, learn, repeat, with guards in the middle">
  <defs>
    <marker id="aA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="738" height="308" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="40" width="200" height="62" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="130" y="66" font-size="14" font-weight="bold" fill="#FFFFFF">1. Pick parameters</text>
    <text x="130" y="88" font-size="11.5" fill="#FFFFFF">grid, random or Optuna</text>
    <rect x="510" y="40" width="200" height="62" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="610" y="66" font-size="14" font-weight="bold" fill="#2B2D42">2. Run backtest</text>
    <text x="610" y="88" font-size="11.5" fill="#2B2D42">same data, new knobs</text>
    <rect x="510" y="210" width="200" height="62" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="610" y="236" font-size="14" font-weight="bold" fill="#FFFFFF">3. Score result</text>
    <text x="610" y="258" font-size="11.5" fill="#FFFFFF">Sharpe ratio, drawdown</text>
    <rect x="30" y="210" width="200" height="62" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="130" y="236" font-size="14" font-weight="bold" fill="#2B2D42">4. Learn, suggest next</text>
    <text x="130" y="258" font-size="11.5" fill="#2B2D42">TPE sampler in Optuna</text>
    <line x1="230" y1="71" x2="510" y2="71" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aA)"/>
    <line x1="610" y1="102" x2="610" y2="210" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aA)"/>
    <line x1="510" y1="241" x2="230" y2="241" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aA)"/>
    <line x1="130" y1="210" x2="130" y2="102" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aA)"/>
    <text x="370" y="200" font-size="11" fill="#2B2D42">hundreds of trials</text>
    <rect x="250" y="106" width="240" height="76" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="370" y="130" font-size="13" font-weight="bold" fill="#FFFFFF">Overfitting guards</text>
    <text x="370" y="150" font-size="11.5" fill="#FFFFFF">walk-forward windows</text>
    <text x="370" y="168" font-size="11.5" fill="#FFFFFF">purge and embargo</text>
  </g>
</svg>

Three engines can drive the loop. Grid search tries every combination you list. Random search samples combinations. The Bayesian optimizer uses Optuna and learns from past trials where the good values hide. Without Optuna installed, it falls back to random search.

**The guards matter more than the engine.** Walk-forward splits history into windows: tune on 24 months, test on the next 6, then roll forward and repeat. Purging deletes training samples whose outcome still overlaps the test window. An embargo adds a small gap after each test window. Together they stop the tuner from peeking at the future, which is exactly what overfitting feeds on. The backtest optimizer also applies a Bonferroni correction, a penalty you pay for testing many variants at once.

**A scorer decides when to stop.** `RobustnessScorer` blends consistency, parameter stability, sensitivity and in-sample versus out-of-sample decay into one score from 0 to 100. You need 80 or more to pass; 60 to 79 means watch it closely, and below that the run fails.

## Labels first: the triple barrier

Before any model learns, raw prices must become labels, short answers like "this moment was a good buy". The code uses the triple barrier method from López de Prado's book.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 330" role="img" aria-label="A price path between three barriers: take profit above, stop loss below, time limit on the right">
  <rect x="1" y="1" width="738" height="328" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif">
    <line x1="70" y1="78" x2="540" y2="78" stroke="#6BCB77" stroke-width="2.5" stroke-dasharray="8 6"/>
    <text x="70" y="66" font-size="12" font-weight="bold" fill="#2B2D42">upper barrier: take profit</text>
    <line x1="70" y1="224" x2="540" y2="224" stroke="#FF6B6B" stroke-width="2.5" stroke-dasharray="8 6"/>
    <text x="70" y="246" font-size="12" font-weight="bold" fill="#2B2D42">lower barrier: stop loss</text>
    <line x1="540" y1="44" x2="540" y2="254" stroke="#4D96FF" stroke-width="2.5" stroke-dasharray="8 6"/>
    <text x="552" y="106" font-size="12" font-weight="bold" fill="#2B2D42">vertical barrier:</text>
    <text x="552" y="124" font-size="12" fill="#2B2D42">time limit</text>
    <polyline points="80,205 130,165 175,185 225,135 275,105 320,78" fill="none" stroke="#2B2D42" stroke-width="2.5"/>
    <circle cx="320" cy="78" r="6" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="332" y="74" font-size="12" font-weight="bold" fill="#9B5DE5">label +1: profit hit first</text>
    <rect x="70" y="260" width="440" height="58" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="290" y="280" font-size="13" font-weight="bold" fill="#2B2D42" text-anchor="middle">TripleBarrierConfig</text>
    <text x="290" y="298" font-size="11.5" fill="#2B2D42" text-anchor="middle">defaults: +2%, -1%, 5 bars</text>
    <text x="290" y="313" font-size="11.5" fill="#2B2D42" text-anchor="middle">width scales with volatility</text>
  </g>
</svg>

Each event gets three barriers: profit above, stop below, and time on the right. Whichever barrier the price hits first decides the label. Barriers scale with volatility, so wild assets get wider stops. These labels feed the learning strategies, which also weight samples by uniqueness for overlapping events.

## Meta-labeling: direction versus size

Asking one model both when to trade and how big is a lot to ask. Meta-labeling splits the job in two, and the repo has a real pipeline for it.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 350" role="img" aria-label="Meta-labeling flow: features feed a primary model for direction, then a meta model judges confidence, then the sizer sets position size within risk caps">
  <defs>
    <marker id="aB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="738" height="348" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="40" y="36" width="210" height="62" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="145" y="62" font-size="14" font-weight="bold" fill="#FFFFFF">Features</text>
    <text x="145" y="84" font-size="11.5" fill="#FFFFFF">trend, volatility, volume</text>
    <rect x="450" y="36" width="250" height="62" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="575" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Primary model</text>
    <text x="575" y="84" font-size="11.5" fill="#2B2D42">direction: buy, sell, skip</text>
    <line x1="250" y1="67" x2="450" y2="67" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aB)"/>
    <rect x="230" y="160" width="280" height="64" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="370" y="186" font-size="14" font-weight="bold" fill="#2B2D42">Meta model: MetaLabeling</text>
    <text x="370" y="208" font-size="11.5" fill="#2B2D42">will the call be right?</text>
    <line x1="145" y1="98" x2="300" y2="160" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aB)"/>
    <line x1="575" y1="98" x2="440" y2="160" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aB)"/>
    <rect x="100" y="270" width="310" height="62" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="255" y="296" font-size="13" font-weight="bold" fill="#FFFFFF">MetaLabelingPositionSizer</text>
    <text x="255" y="318" font-size="11.5" fill="#FFFFFF">size grows with confidence p</text>
    <rect x="470" y="270" width="230" height="62" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="585" y="296" font-size="14" font-weight="bold" fill="#FFFFFF">Risk caps</text>
    <text x="585" y="318" font-size="11.5" fill="#FFFFFF">max bet size, stops</text>
    <line x1="300" y1="224" x2="255" y2="270" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aB)"/>
    <line x1="440" y1="224" x2="585" y2="270" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#aB)"/>
  </g>
</svg>

The primary model keeps direction: buy, sell or skip. The meta model reads the same features plus the primary call, and estimates the chance that call is right. The Kelly rule f = 2p - 1 turns that chance p into a fraction of your capital. Confidence of 0.55 gives a small bet; strong confidence gives a big one, capped by risk limits. Weak signals get skipped entirely.

## What's real, what's planned

**Real today.** Everything above exists in the codebase with tests. `triple_barrier.py` runs inside the supervised learning engine. The compliance engine and `position_sizing_engine.py` can both call the meta-labeling code. Walk-forward exists in two places: the validator under `app/backtesting/validation/` and `ParameterOptimizationService`. `BacktestMetaAnalyzer` clusters past results, and `LearningEngineStorage` saves model weights safely, without pickle.

**Planned, not wired in.** The default live sizing path is still ATR and Kelly, without meta-labels. The integration doc lists what comes next: portfolio-level meta-models, regime-aware confidence thresholds, ensemble meta-models, online learning, and drawdown-based sizing. Treat those as roadmap, not shipped features.

## Where it lives in the code

- `app/domain/optimization/` — the optimizers: `bayesian_optimizer.py` (Optuna), `grid_search_optimizer.py`, `factory.py`, plus `robustness_scorer.py` and `parameter_stability_metrics.py`.
- `app/domain/portfolio_optimization/` — a different beast: weights across assets, not strategy knobs (mean-variance, Black-Litterman, NCO).
- `app/backtesting/labeling/` — `triple_barrier.py`, `meta_labeling.py`, `bet_sizing_meta.py`, `concurrent_training.py`.
- `app/backtesting/validation/` — `walk_forward.py`, `cross_validation.py` (purged CV with embargo), `parameter_stability.py`.
- `app/backtesting/walk_forward_validator.py` — the bigger validator, with stress tests and Monte Carlo runs.
- `app/backtesting/meta_analyzer/` — `meta_analyzer.py`, `audit_trail.py`, `learning_storage.py`.
- `app/services/position_sizing_engine.py` — `PositionSizingEngine` and `MetaLabelingPositionSizer`.

## Go deeper

- [Backtesting](09-backtesting.md) — the sandbox all of this runs in.
- [The strategies](05-strategies.md) — the strategies whose knobs get tuned.
- [The bibliography](22-bibliography.md) — where the López de Prado ideas came from.
