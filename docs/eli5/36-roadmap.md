# The roadmap: where we are, where we go

## The short version

This repo carries two kinds of plans. One asks: can this system trade real money without hurting you? The other grows the brain: better backtests, fancier modules, cleaner code.

The code is ahead of the oldest plan. Position monitoring, Spain tax tracking, and 24/7 market services all exist in `app/` today. The dashboard was just consolidated on NiceGUI, and this ELI5 series is brand new.

But the last mile is untouched. Three giant files still need splitting, a code audit barely started, and no real money has ever traded. Here is the honest map.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 320" role="img" aria-label="Roadmap timeline: eight phases colored by status, with a coral risk gate at the bottom">
  <defs>
    <marker id="roadArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="738" height="318" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="24" y="16" width="12" height="12" rx="3" fill="#6BCB77" stroke="#2B2D42" stroke-width="1.5"/>
    <text x="66" y="27" font-size="11" fill="#2B2D42" text-anchor="start">done</text>
    <rect x="110" y="16" width="12" height="12" rx="3" fill="#FFD93D" stroke="#2B2D42" stroke-width="1.5"/>
    <text x="128" y="27" font-size="11" fill="#2B2D42" text-anchor="start">in progress</text>
    <rect x="212" y="16" width="12" height="12" rx="3" fill="#FFFFFF" stroke="#2B2D42" stroke-width="1.5"/>
    <text x="230" y="27" font-size="11" fill="#2B2D42" text-anchor="start">planned</text>
    <rect x="300" y="16" width="12" height="12" rx="3" fill="#FF6B6B" stroke="#2B2D42" stroke-width="1.5"/>
    <text x="318" y="27" font-size="11" fill="#2B2D42" text-anchor="start">risk gate</text>
    <rect x="20" y="52" width="150" height="66" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="95" y="76" font-size="12.5" font-weight="bold" fill="#2B2D42">Production plan</text>
    <text x="95" y="93" font-size="10.5" fill="#2B2D42">phases 0-2</text>
    <text x="95" y="108" font-size="10.5" fill="#2B2D42">survival + Spain taxes</text>
    <line x1="172" y1="85" x2="186" y2="85" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="190" y="52" width="150" height="66" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="265" y="76" font-size="12.5" font-weight="bold" fill="#2B2D42">Production plan</text>
    <text x="265" y="93" font-size="10.5" fill="#2B2D42">phase 3</text>
    <text x="265" y="108" font-size="10.5" fill="#2B2D42">24/7 multi-market</text>
    <line x1="342" y1="85" x2="356" y2="85" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="360" y="52" width="150" height="66" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="435" y="76" font-size="12.5" font-weight="bold" fill="#2B2D42">Production plan</text>
    <text x="435" y="93" font-size="10.5" fill="#2B2D42">phase 4 polish</text>
    <text x="435" y="108" font-size="10.5" fill="#2B2D42">dashboard done</text>
    <line x1="512" y1="85" x2="526" y2="85" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="530" y="52" width="150" height="66" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="605" y="76" font-size="12.5" font-weight="bold" fill="#2B2D42">FASE 5</text>
    <text x="605" y="93" font-size="10.5" fill="#2B2D42">backtesting engine</text>
    <text x="605" y="108" font-size="10.5" fill="#2B2D42">validators + costs</text>
    <path d="M 605 118 V 138 H 95 V 152" fill="none" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="20" y="158" width="150" height="66" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="95" y="182" font-size="12.5" font-weight="bold" fill="#2B2D42">FASE 6</text>
    <text x="95" y="199" font-size="10.5" fill="#2B2D42">XAI · synthetic · graph</text>
    <text x="95" y="214" font-size="10.5" fill="#2B2D42">modules exist</text>
    <line x1="172" y1="191" x2="186" y2="191" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="190" y="158" width="150" height="66" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="265" y="182" font-size="12.5" font-weight="bold" fill="#2B2D42">God-class splits</text>
    <text x="265" y="199" font-size="10.5" fill="#2B2D42">config done</text>
    <text x="265" y="214" font-size="10.5" fill="#2B2D42">three giants left</text>
    <line x1="342" y1="191" x2="356" y2="191" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="360" y="158" width="150" height="66" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="435" y="182" font-size="12.5" font-weight="bold" fill="#2B2D42">GAP audit</text>
    <text x="435" y="199" font-size="10.5" fill="#2B2D42">one file passed</text>
    <text x="435" y="214" font-size="10.5" fill="#2B2D42">barely started</text>
    <line x1="512" y1="191" x2="526" y2="191" stroke="#2B2D42" stroke-width="2" marker-end="url(#roadArrow)"/>
    <rect x="530" y="158" width="150" height="66" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="605" y="182" font-size="12.5" font-weight="bold" fill="#2B2D42">Live money</text>
    <text x="605" y="199" font-size="10.5" fill="#2B2D42">not started</text>
    <text x="605" y="214" font-size="10.5" fill="#2B2D42">paper trading first</text>
    <rect x="20" y="248" width="660" height="54" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="350" y="270" font-size="12.5" font-weight="bold" fill="#FFFFFF">Risk gate</text>
    <text x="350" y="288" font-size="10.5" fill="#FFFFFF">no real money before a tax review + 30-day paper run</text>
  </g>
</svg>

## The production plan (five phases, 28 weeks)

`PLAN_SUMMARY.md`, `VISUAL_ROADMAP.md`, and `ROLLOUT_PLAN.md` (written January 2025) split the road to production into Phases 0 to 4, with a decision gate after each.

Phases 0 to 3 look done in code. `app/services/position_monitor/` and `emergency_handler/` exist, plus `app/infrastructure/resilience/reconnection_manager.py` and a memory monitor. That covers Phase 1, survival.

Phase 2 left real files too: `app/services/fifo/fifo_integrator.py`, `modelo_721_generator.py`, and a Spain tax engine under `app/services/tax_efficiency/engines/`. A commit this month fixed FIFO sync sessions.

Phase 3 services all exist: `market_scheduler.py`, `forex_risk/`, `broker_failover/`, `rate_limiting/`, and `news_processor/`. Phase 4 is half done — the dashboard is now NiceGUI only, Streamlit is gone, and 46 E2E tests came with it.

What remains: there's no evidence of a 30-day stability run, a full runbook, or any live-money stage. Gate 4 hasn't been passed.

## FASE 5: the backtesting engine

The plan wanted strategy validators, a 5% daily circuit breaker, honest cost models, and vectorized code. Target: 95% rule compliance.

Almost all of it exists now. `app/backtesting/validation/strategy_validator.py` sits next to walk-forward and overfitting checks. `app/services/circuit_breaker/daily_circuit_breaker.py` is real.

The cost side is real too: `slippage_model.py`, `transaction_cost.py`, and `market_impact.py` under `app/backtesting/execution/`. Recent commits fixed drawdown, Sharpe, and Sortino math, plus fills at the next bar's open.

What remains: the plan's clean-bill criteria (strict mypy, 95% compliance) can't be verified from the repo, so treat FASE 5 as done but unproven.

## FASE 6: the advanced modules

The plan describes three showpieces: explainable AI with SHAP and LIME, synthetic data from GANs, and a knowledge graph on Neo4j.

The folders exist and hold code: `app/services/xai/`, `synthetic_data/`, and `knowledge_graph/`. What remains is proving they're wired into daily trading, not just importable.

## The refactoring waves

`REFACTORING_PLAN_GOD_CLASSES.md` wanted four giants split into small files. One is done: `centralized_config.py` went from about 3,800 lines to 860. The other three still stand: the backtest runner at 4,615 lines, the compliance engine at 3,866, and `select_strategy.py` at 2,278.

`REFACTORING_SUMMARY.md` reports duplicate modules deleted and one unified metrics module created. Hard-coded values for trading days and the risk-free rate still live in about 30 files.

The portfolio dependency-injection plan is done: `app/core/di_container.py` exists and a recent commit wired it in. The GAP audit is the laggard — its plan wants every file audited layer by layer, but only one file shows a PASSED stamp.

## Snapshot date

This page is a snapshot from October 2026, and every commit it cites landed on one busy day that month. Plans age fast here. Check `git log` before you trust any status above.

## Where it lives

- `docs/plans/PLAN_SUMMARY.md`, `ROLLOUT_PLAN.md`, `VISUAL_ROADMAP.md` — the production plan.
- `docs/plans/FASE5_Backtesting_Engine.md`, `FASE_6_ADVANCED_MODULES.md` — the engine phases.
- `docs/plans/fix_gap_violations.md`, `refactor-portfolio-di.md` — the cleanup plans.
- `docs/REFACTORING_PLAN_GOD_CLASSES.md`, `docs/REFACTORING_SUMMARY.md` — the splits.
- `docs/architecture/backtesting_workflow_complete_analysis.md` — how a backtest flows today.

## Want to go deeper?

- [Backtesting](09-backtesting.md) — what the engine does with your history.
- [Optimization](26-optimization.md) — tuning strategies without fooling yourself.
- [Deployment](28-deployment.md) — how this leaves your laptop.
