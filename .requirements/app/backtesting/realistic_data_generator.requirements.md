# realistic_data_generator.py

## Purpose
Generate realistic market data using advanced statistical models (Geometric Brownian Motion, GARCH-like volatility clustering, Markov Regime-Switching) replacing simplistic linear/random generation.

---

## Type Definitions / Data Classes

### MarketRegime (Enum)
```python
class MarketRegime(str, Enum):
    BULL = "bull"          # Uptrend, moderate volatility
    BEAR = "bear"          # Downtrend, high volatility
    SIDEWAYS = "sideways"  # Range-bound, low volatility
    VOLATILE = "volatile"  # High volatility, no clear trend
```

### RegimeParameters (dataclass)
```python
@dataclass
class RegimeParameters:
    name: MarketRegime
    drift: float                    # Daily return (annualized / 252)
    volatility: float               # Daily volatility (annual / sqrt(252))
    volume_multiplier: float        # Volume relative to baseline
    jump_probability: float         # Probability of price jump (Poisson)
    jump_mean: float                # Mean jump size (as decimal, e.g., 0.02 = 2%)
    transition_prob: dict           # Probability of transitioning to other regimes
```

**Validation Rules:**
- `drift` typically -0.001 to 0.001 (daily)
- `volatility` typically 0.008 to 0.035 (daily)
- `jump_probability` 0 to 0.05
- `transition_prob` values must sum to 1.0

---

## Function Signatures (Contracts)

### `RealisticDataGenerator.__init__(seed: Optional[int] = None, base_price: float = 100.0, base_volume: int = 50_000_000, regimes: Optional[dict] = None, asset_class: str = "equity")`
**Pre:** seed optional (for reproducibility), base_price > 0, base_volume > 0
**Post:** Generator initialized with regime parameters or defaults
**Raises:** None
**Retry:** No
**Side Effects:** Creates RandomState with seed

### `generate_realistic_quotes(symbol: str, n_days: int, start_date: datetime, use_regime_switching: bool = True, initial_regime: MarketRegime = MarketRegime.BULL) -> List[Quote]`
**Pre:** n_days > 0, symbol non-empty
**Post:** Returns List[Quote] with realistic OHLCV data
**Raises:** None
**Retry:** No
**Side Effects:** Generates prices using GBM with regime-switching

### `_generate_regime_sequence(n_days: int, initial_regime: MarketRegime) -> List[MarketRegime]`
**Pre:** n_days > 0
**Post:** Returns list of regimes for each day using Markov chain
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_prices_to_realistic_quotes(prices: List[float], volumes: List[int], dates: List[datetime], symbol: str, regimes: Optional[List[MarketRegime]] = None) -> List[Quote]`
**Pre:** All lists same length, prices > 0, volumes > 0
**Post:** Returns List[Quote] with realistic OHLC and bid-ask spread
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_monte_carlo_scenario(base_quotes: List[Quote], n_simulations: int = 100, volatility_adjustment: float = 1.0) -> List[List[Quote]]`
**Pre:** base_quotes non-empty, n_simulations > 0
**Post:** Returns list of quote lists (alternative price paths)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Regime-switching model produces realistic market cycles
- [ ] GARCH-like volatility clustering implemented
- [ ] Volume correlated with volatility and price movements
- [ ] Jump-diffusion for extreme events (crashes, rallies)
- [ ] OHLC data realistic (open != close, high/low reflect intraday range)
- [ ] Bid-ask spread correlates with volatility
- [ ] Price precision based on asset class (equity 2 decimals, forex 4-5 decimals)
- [ ] Overnight gaps between close and next open (0.1% to 0.5% typical)
- [ ] Volume increases with volatility and price movements
- [ ] Monte Carlo scenarios preserve statistical properties
- [ ] Minimum price floor at $0.01 (no negative prices)

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some functions > 20 lines |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Data generation only |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| MATH-001 | Custom | No negative prices | ✅ OK - Floor at 0.01 |
| MATH-002 | Custom | Realistic volatility clustering | ✅ OK - GARCH-like model |

**Statistical Models Implemented:**
- ✅ Geometric Brownian Motion (GBM)
- ✅ GARCH-like volatility clustering (omega, alpha, beta parameters)
- ✅ Markov Regime-Switching Model (4 regimes)
- ✅ Jump-diffusion (Poisson process)
- ✅ Volume-price correlation

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, dataclasses, datetime, enum, typing, numpy
- **Internal:**
  - app.core.decimal_utils (round_price, to_decimal)
  - app.models.market_data.Quote

---

## Required Tests
- **test_realistic_data_generator.py:**
  - Success: Generate quotes with regime switching
  - Success: Generate quotes without regime switching
  - Success: All regime types appear in sequence
  - Success: GARCH volatility clustering (volatility autocorrelation)
  - Success: Volume correlates with price movements
  - Success: Jump-diffusion creates extreme moves
  - Success: OHLC consistency (high >= open/close/low, low <= open/close/high)
  - Success: Bid-ask spread correlates with volatility
  - Success: Overnight gaps between close and next open
  - Success: Monte Carlo scenarios have different paths
  - Success: Price never goes negative
  - Edge: Zero days (returns empty)
  - Edge: Regime transition probabilities sum to 1.0
  - Integration: Asset class precision (equity 2 decimals, forex 5 decimals)
  - Integration: Volume increases with volatility

---

## Notes
- Replaces simplistic linear/random data generation
- Default regimes calibrated from historical equity data
- GARCH parameters: omega=0.00002, alpha=0.08, beta=0.90
- Volume model: base * regime_multiplier * vol_multiplier * lognormal_noise
- Bid-ask spread: 3-15 bps correlated with volatility
- Minimum spreads by asset class: equity $0.01, forex $0.00001
