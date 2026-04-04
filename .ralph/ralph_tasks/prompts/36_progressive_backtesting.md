# Progressive Backtesting - Test Execution Plan

## Context

Execute `tests/backtesting/` progressively across 3 dimensions:
1. **Stocks**: from 1 stock to all available (~61)
2. **Time window**: from minimum to 5 years
3. **Investment profiles**: all 5 objectives, with special focus on `maximizar_dividendos`

Each level must PASS before moving to the next.

## Stock Universe

Symbols come from `tests/backtesting/conftest.py`:
- `DEFAULT_SYMBOL` = first available symbol (typically AAPL)
- `QUICK_TEST_SYMBOLS` = first 5 symbols
- `AVAILABLE_SYMBOLS` = all ~61 symbols from `data/historical/`

## Investment Profiles (5 Objectivos de Inversion)

Defined in `app/domain/models/input_profile.py`:

| Objetivo | Key | Focus | Priority in Tests |
|----------|-----|-------|-------------------|
| Maximizar Capital | `maximizar_capital` | Growth | Normal |
| **Maximizar Dividendos** | **`maximizar_dividendos`** | **Dividend income, DRIP, yield on cost** | **HIGH - Primary focus** |
| Capital Preservation | `capital_preservation` | Protect capital | Normal |
| Balanced Growth | `balanced_growth` | Risk/return balance | Normal |
| Income Generation | `income_generation` | Steady income (dividends + options) | Normal |

### Dividend-Specific Details
- **Modules activated**: `dividend_screener`, `dividend_predictor`, `mean_reversion_modular`, `sector_rotation`, `portfolio_optimization`
- **Config**: `config/portfolio/investment_profiles.yaml` (lines 61-111)
- **Optimization**: `config/backtesting/profile_optimization.yaml` (lines 651-671, profile `dividendos`)
- **Batch params**: `config/portfolio/profile_batch_backtest.yaml` (lines 210-216, `dividend_focus: true`)
- **DRIP handling**: `app/backtesting/robust_engine/dividend_handler.py`
- **Dividend screener**: `app/domain/strategies/dividend_screener.py`
- **Dividend analyzer**: `app/domain/strategies/dividend_analyzer.py`
- **Dividend portfolio constructor**: `app/domain/strategies/dividend_portfolio_constructor.py`

### Capital Tiers (4 levels per profile)
| Tier | Capital | Risk Profile |
|------|---------|-------------|
| micro | < EUR 15k | Level 1 |
| small | EUR 15k-50k | Level 2 |
| medium | EUR 50k-250k | Level 3 |
| large | >= EUR 250k | Level 4 |

### Risk Tolerances (3 per profile x tier)
- `bajo` (low), `medio` (medium), `alto` (high)

**Total profile combinations**: 5 objectives x 4 tiers x 3 risks = 60 base (+ 180 with horizons)

## Test Files to Execute

```
tests/backtesting/
├── core/           (basic engine, config, workflow)
├── services/       (trade executor, PnL, positions)
├── metrics/        (advanced metrics, bet sizing)
├── execution/      (capital scaling, concurrent, pessimistic)
├── validation/     (walk-forward, cross-validation, drawdown)
├── analysis/       (clustering, regime, seasonality)
├── ml/             (ensemble, feature importance)
├── profiles/       (profile batch backtester, investor backtest)
├── batch/          (batch optimization, baseline reporter)
├── labeling/       (triple barrier, meta-labeling)
└── feature_engineering/

Also profile-related tests outside backtesting/:
├── tests/unit/parametrization_framework/test_profile_generator.py
├── tests/unit/parametrization_framework/test_profile_generator_t21.py
├── tests/unit/services/test_profile_strategy_mapper.py
├── tests/integration/profiles/
└── tests/unit/parametrization/test_input_processor.py
```

## Rules

1. Each level MUST pass (0 failures) before proceeding to next level
2. If a level fails: diagnose, fix, and re-run that level
3. If a test does NOT execute (collection error, import error): **FIX IT. No skipping.**
4. **You CAN modify app/ if needed** - production code can be fixed
5. After EVERY code change (app/ or tests/), QA gates MUST pass:
   ```bash
   # For app/ changes:
   black app/ && isort app/ && ruff check app/ --fix
   # For tests/ changes:
   black tests/ && isort tests/ && ruff check tests/ --fix
   ```
6. After modifying app/, verify unit tests still pass:
   ```bash
   python -m pytest tests/unit/ -x --timeout=120
   ```
7. Before emitting level completion, ALL backpressure gates must pass:
   ```bash
   black app/ --check && black tests/ --check && echo "BLACK: PASS"
   isort app/ --check-only && isort tests/ --check-only && echo "ISORT: PASS"
   ruff check app/ && ruff check tests/ && echo "RUFF: PASS"
   python -c "import app; print('IMPORTS: PASS')"
   ```
8. Record results for each level in `.ralph/outputs/36_progressive_backtesting_report.md`
9. Use `-x` flag to stop on first failure for quick diagnosis
10. Use `--timeout=300` for potentially slow tests
11. Always run with `-v --tb=short` for detailed output
12. **Profile tests are run TWICE**: once per profile, with `maximizar_dividendos` tested FIRST
13. Dividend-specific assertions MUST verify: DRIP, yield on cost, dividend quality scoring, sector diversification

## Fix Process (OBLIGATORY for every fix)

```
1. Run test with --tb=long to get full traceback
2. Diagnose root cause (test bug vs production bug)
3. If test bug: fix in tests/
4. If production bug: fix in app/
5. After fix, run QA gates on the fixed file(s):
   black <file> && isort <file> && ruff check <file> --fix
6. Re-run the specific test to verify fix works
7. If app/ was touched, run unit tests: python -m pytest tests/unit/ -x
8. Verify ALL backpressure gates pass before emitting completion
```

### Collection Errors = MUST FIX

Tests that fail to collect (import errors, syntax errors, fixture errors) are NOT acceptable as known issues. They MUST be fixed. This may require fixing app/ code if the import chain is broken. Types:
- ImportError / ModuleNotFoundError
- SyntaxError
- NameError at import time
- Fixture not found
- conftest errors
- Missing dependencies
