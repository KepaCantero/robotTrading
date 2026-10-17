# Regime detection: reading the market's mood

## The short version

Markets have moods. Sometimes prices climb for months, sometimes they thrash around wildly, and sometimes they just drift. A regime is a name for the mood the market is in right now. The app works the mood out from price history alone. It matters because the regime decides which strategies are allowed to trade.

## The six regimes

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 440" role="img" aria-label="State diagram of the six regimes and the trigger for each">
  <defs>
    <marker id="regArrA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="438" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="255" y="22" width="250" height="88" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="46" font-size="13" font-weight="bold" fill="#2B2D42">Hysteresis gate</text>
    <text x="380" y="68" font-size="11.5" fill="#2B2D42">same raw label</text>
    <text x="380" y="88" font-size="11.5" fill="#2B2D42">three checks in a row</text>
    <rect x="30" y="22" width="210" height="88" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="135" y="48" font-size="14" font-weight="bold" fill="#FFFFFF">trending_up</text>
    <text x="135" y="72" font-size="11.5" fill="#FFFFFF">slope above +2%</text>
    <text x="135" y="92" font-size="11.5" fill="#FFFFFF">prices climbing steadily</text>
    <rect x="520" y="22" width="210" height="88" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="625" y="48" font-size="14" font-weight="bold" fill="#FFFFFF">trending_down</text>
    <text x="625" y="72" font-size="11.5" fill="#FFFFFF">slope below -2%</text>
    <text x="625" y="92" font-size="11.5" fill="#FFFFFF">prices falling steadily</text>
    <rect x="290" y="186" width="180" height="88" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="220" font-size="13.5" font-weight="bold" fill="#2B2D42">every new close</text>
    <text x="380" y="244" font-size="12" fill="#2B2D42">re-run the checks</text>
    <rect x="30" y="186" width="210" height="88" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="135" y="212" font-size="14" font-weight="bold" fill="#2B2D42">mean_reverting</text>
    <text x="135" y="236" font-size="11.5" fill="#2B2D42">flat slope, normal vol</text>
    <text x="135" y="256" font-size="11.5" fill="#2B2D42">prices snap back</text>
    <rect x="520" y="186" width="210" height="88" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="625" y="212" font-size="14" font-weight="bold" fill="#FFFFFF">high_volatility</text>
    <text x="625" y="236" font-size="11.5" fill="#FFFFFF">yearly vol above 30%</text>
    <text x="625" y="256" font-size="11.5" fill="#FFFFFF">wild swings</text>
    <rect x="145" y="352" width="210" height="74" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="250" y="384" font-size="14" font-weight="bold" fill="#FFFFFF">low_volatility</text>
    <text x="250" y="408" font-size="11.5" fill="#FFFFFF">yearly vol under 12%</text>
    <rect x="405" y="352" width="210" height="74" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="510" y="380" font-size="14" font-weight="bold" fill="#FFFFFF">unknown</text>
    <text x="510" y="402" font-size="11.5" fill="#FFFFFF">under 100 closes</text>
    <text x="510" y="420" font-size="11.5" fill="#FFFFFF">confidence stays zero</text>
    <line x1="380" y1="184" x2="380" y2="116" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="320" y1="186" x2="152" y2="116" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="440" y1="186" x2="608" y2="116" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="290" y1="230" x2="246" y2="230" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="470" y1="230" x2="514" y2="230" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="330" y1="274" x2="266" y2="348" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
    <line x1="430" y1="274" x2="494" y2="348" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrA)"/>
  </g>
</svg>

The `RegimeBasedSelector` in the strategy ensemble owns this job during live trading. It keeps its own price history: every quote adds one close, and only the last 200 are kept. The math reads the last 100 closes (`regime_lookback`). With fewer than 100, the regime is `unknown` and confidence stays at zero.

Detection measures two things. First, trend: fit a straight line through the 100 closes, take its slope, and divide by the average price. If that normalized slope is above 2%, the regime is `trending_up`; below -2%, it's `trending_down`. Trend is always checked first, so a real trend is never mislabeled as noise.

Second, volatility: the spread of daily returns, scaled up to a yearly figure. Above 30% a year, the regime is `high_volatility`. Under 12% a year — that's the 30% line times 0.4 — it's `low_volatility`. A flat slope with volatility in between is called `mean_reverting`.

Raw labels would flip-flop on noisy days, so there's a hysteresis gate. The regime only changes after the same raw label shows up three checks in a row. Until then, the old regime stands. Confidence grows with how far the slope or volatility overshoots its threshold, capped at 100. Every outgoing signal carries the regime and its confidence in its metadata.

## What the regime switches

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 350" role="img" aria-label="Flow from prices through detection math to a regime verdict and the strategy shortlist">
  <defs>
    <marker id="regArrB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="348" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="26" width="210" height="116" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="56" font-size="14" font-weight="bold" fill="#FFFFFF">Prices come in</text>
    <text x="130" y="84" font-size="12" fill="#FFFFFF">the last 100 closes</text>
    <text x="130" y="108" font-size="12" fill="#FFFFFF">one added per quote</text>
    <rect x="275" y="26" width="210" height="116" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="52" font-size="14" font-weight="bold" fill="#2B2D42">Detection math</text>
    <text x="380" y="78" font-size="12" fill="#2B2D42">slope of best-fit line</text>
    <text x="380" y="100" font-size="12" fill="#2B2D42">plus yearly volatility</text>
    <text x="380" y="122" font-size="12" fill="#2B2D42">slope first, vol second</text>
    <rect x="525" y="26" width="210" height="116" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="630" y="52" font-size="14" font-weight="bold" fill="#2B2D42">The verdict</text>
    <text x="630" y="78" font-size="12" fill="#2B2D42">one of six labels</text>
    <text x="630" y="100" font-size="12" fill="#2B2D42">confidence 0 to 100</text>
    <text x="630" y="122" font-size="12" fill="#2B2D42">needs 3 votes</text>
    <line x1="237" y1="84" x2="271" y2="84" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrB)"/>
    <line x1="487" y1="84" x2="521" y2="84" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrB)"/>
    <line x1="630" y1="146" x2="630" y2="196" stroke="#2B2D42" stroke-width="2" marker-end="url(#regArrB)"/>
    <rect x="25" y="202" width="710" height="122" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="230" font-size="14" font-weight="bold" fill="#FFFFFF">The strategy shortlist switches</text>
    <text x="380" y="256" font-size="12" fill="#FFFFFF">trending → trend + momentum</text>
    <text x="380" y="278" font-size="12" fill="#FFFFFF">high vol → breakout + momentum</text>
    <text x="380" y="300" font-size="12" fill="#FFFFFF">quiet or reverting → mean reversion</text>
    <text x="380" y="318" font-size="11.5" fill="#FFFFFF">unknown → every strategy runs</text>
  </g>
</svg>

The regime picks the shortlist of strategies that may generate signals, through `regime_strategy_map`. Trending markets run `trend_following` and `momentum_engine`, and `trending_up` adds breakout. Quiet and reverting markets hand the mic to `mean_reversion_engine`. Wild markets go back to breakout and momentum. When the regime is `unknown`, or the preferred names aren't loaded, every strategy runs — nothing goes silent by accident.

Backtesting speaks a second language. Its detector labels the market bull, bear or neutral: bull is price above the 200-day average with a rising slope. It also grades volatility low, normal or high against the historical median. Structure gets called trend, range or transition from the fit's R-squared (how well a line explains prices). A separate detector uses a hidden Markov model, or HMM — a statistical machine that guesses which hidden state produced the returns you see. It learns states from returns and rolling volatility, then names them bear, sideways or bull by average return. The regime doesn't reweight anything in a backtest; it slices the run into pieces and scores the strategy inside each slice.

## When detection fails

Every detector has a plan B. The ensemble's selector says `unknown` when it lacks history, and `unknown` means all strategies run — the failure is soft. The HMM path needs `hmmlearn`, an optional package. When it's missing, a fallback class wraps sklearn's `GaussianMixture`, which clusters states but forgets time. It treats every day as independent and hands every state the same transition odds. The swap is logged as a warning, and `pip install hmmlearn` restores the real model.

The backtest runner chains its fallbacks. It tries the HMM first; if training fails, it retries with K-means clustering. If that fails too, a simple threshold method labels each day bear, neutral or bull from return and volatility cutoffs. Under 252 quotes the regime test is skipped entirely. And a detector that errors returns `unknown` with zero confidence instead of crashing.

## Where it lives in the code

- `app/engines/strategy_engines/ensemble.py` — `RegimeBasedSelector`: the six regimes, the thresholds, hysteresis, and the strategy map.
- `app/backtesting/validation/regime_detector.py` — bull, bear, neutral plus volatility and structure; defaults in `models.py` (`RegimeConfig`).
- `app/engines/context_engine/regime_detectors/hmm_regime_detector.py` — `HMMRegimeDetector` and the `GaussianMixture` fallback.
- `app/engines/context_engine/volatility_analyzers/volatility_regime_detector.py` — high, normal, low volatility by percentiles 75 and 25.
- `app/services/regime_detection_chan.py` — Ernest Chan's version, with hmm, kmeans, threshold and momentum methods.
- `app/backtesting/comprehensive_backtest_runner.py` — `run_regime_test_backtest`: the fallback chain and per-regime scoring.
- `docs/developer/HMMLEARN_FALLBACK_QUICK_REFERENCE.md` — the hmmlearn swap, in detail.

## Want to go deeper?

- [The strategies](05-strategies.md) — the engines the regime chooses between.
- [Backtesting](09-backtesting.md) — where regime slices grade a strategy.
- [The risk engine](06-risk-engine.md) — what can veto a signal whatever the mood.
