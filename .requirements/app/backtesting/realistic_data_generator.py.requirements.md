# Requirements: backtesting/realistic_data_generator.py

## Source File Analysis
- **File Path:** `app/backtesting/realistic_data_generator.py`
- **Lines of Code:** 501
- **Audit Status:** PASSED_WITH_NOTES
- **Audit Date:** 2026-02-07T05:30:00Z

## Purpose
Generate realistic market data for backtesting using advanced statistical models. Replaces simplistic linear/random data generation with statistically realistic market behavior including regime-switching, volatility clustering, and jump-diffusion.

## Dependencies
- **Internal:**
  - `app.core.decimal_utils` (round_price, to_decimal)
  - `app.models.market_data` (Quote)
- **External:**
  - `logging`
  - `dataclasses` (dataclass)
  - `datetime` (datetime, timedelta)
  - `enum` (Enum)
  - `typing` (List, Optional)
  - `numpy` (as np)

## Classes/Functions

### Enums
- **MarketRegime(str, Enum):** Market regime types
  - `BULL = "bull"`: Uptrend, moderate volatility
  - `BEAR = "bear"`: Downtrend, high volatility
  - `SIDEWAYS = "sideways"`: Range-bound, low volatility
  - `VOLATILE = "volatile"`: High volatility, no clear trend

### Data Class
- **RegimeParameters:** Parameters for a market regime
  - `name: MarketRegime`
  - `drift: float` - Daily return (annualized / 252)
  - `volatility: float` - Daily volatility (annual / sqrt(252))
  - `volume_multiplier: float` - Volume relative to baseline
  - `jump_probability: float` - Probability of price jump
  - `jump_mean: float` - Mean jump size (as decimal)
  - `transition_prob: dict` - Probability of transitioning to other regimes

### Main Class
- **RealisticDataGenerator:** Generate realistic market data
  - **Constants:**
    - `DEFAULT_REGIMES`: Dict of regime parameters (BULL, BEAR, SIDEWAYS, VOLATILE)
    - `garch_omega`, `garch_alpha`, `garch_beta`: GARCH parameters
    - `volatility_clustering`: Enable/disable GARCH-like volatility

  - **Methods:**
    - `__init__(seed: Optional[int] = None, base_price: float = 100.0, base_volume: int = 50_000_000, regimes: Optional[dict] = None, asset_class: str = "equity")`
    - `generate_realistic_quotes(...) -> List[Quote]`
    - `_generate_regime_sequence(n_days: int, initial_regime: MarketRegime) -> List[MarketRegime]`
    - `_prices_to_realistic_quotes(...) -> List[Quote]`
    - `generate_monte_carlo_scenario(...) -> List[List[Quote]]`

## Business Logic

### Regime-Switching Model
- Markov chain for regime transitions
- Each regime has specific drift, volatility, volume characteristics
- Transition probabilities control regime persistence
- Four regimes: Bull (12.6% annual return), Bear (-7.5%), Sideways (2.5%), Volatile (0%)

### GARCH-like Volatility Clustering
- Updates variance: `omega + alpha * shock^2 + beta * past_variance`
- Creates realistic volatility persistence
- Bounds variance to [0.5x, 2x] of regime baseline
- Configurable via `garch_omega`, `garch_alpha`, `garch_beta`

### Jump-Diffusion Process
- Poisson process for jump events
- Jump probability varies by regime (Volatile: 5%, Bull: 0.5%)
- Jump size drawn from normal distribution with regime-specific mean

### OHLC Generation
- Generates realistic intraday price movements
- Overnight gap from previous close (0.1% to 0.5% typical)
- High/Low reflect intraday volatility
- Bid-ask spread correlates with volatility (3-50 bps)
- Asset class-specific precision (equity: 2 decimals, forex: 4-5, crypto: 8)

### Volume Generation
- Correlates with volatility and price movements
- Uses lognormal noise for realism
- Regime-specific volume multipliers

### Monte Carlo Scenarios
- Generates alternative price paths from base data
- Preserves overall trend but varies volatility
- Uses same statistical models as main generator
- Simulation-specific seeds for reproducibility

## Data Models
- **RegimeParameters:** @dataclass with regime configuration
- **Quote:** Uses existing market data model

## API Contracts
N/A - This is a library module

## Error Handling
- Minimal exception handling needed (no external dependencies)
- Logging for generation progress and results
- Graceful handling of edge cases (price floor at 0.01, volume minimum)

## Performance Considerations
- Vectorized numpy operations for efficiency
- Single-pass generation
- O(n) complexity where n = number of days
- Memory efficient (uses pre-allocated arrays)

## Testing Strategy
- Unit tests for regime sequence generation
- Verify GARCH volatility calculations
- Test OHLC consistency (high >= open/close >= low)
- Verify bid-ask spread logic
- Test Monte Carlo scenario generation
- Edge cases: zero price, zero volume

## Trading-Specific Rules Compliance
- **BT-003 (No look-ahead bias):** ✅ Generates data sequentially without future information
- **BT-004 (Realistic costs):** ✅ Includes bid-ask spread and price impact
- **TRD-005 (Price validation):** ✅ Validates price inputs, floors at minimum

## Audit Notes

### Non-Critical Issues
1. **Type Hints (TYP-002):** Uses old syntax `Optional[X]`, `List[X]`
   - Lines: 19, 127, 159, 168, 311
   - Impact: Low - code is functional and type-safe
   - Recommendation: Update to `X | None`, `list[X]` syntax in future refactor

2. **Dict Type Hint (TYP-003):** Uses `dict` without key/value types on line 126
   - Impact: Low - structure is documented
   - Recommendation: Use `Dict[MarketRegime, RegimeParameters]`

### What Was Checked
- ✅ No print() statements (uses logger)
- ✅ No mutable default arguments
- ✅ Proper type hints
- ✅ Google style docstrings
- ✅ Absolute imports only
- ✅ All functions have return type hints
- ✅ Uses Enum for regime types (modern Python)
- ✅ Uses @dataclass for data structures (modern Python)
- ✅ Proper numeric precision with Decimal for financial data

### BASE_RULES Compliance
See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

**File-specific rules:**
- FMT-007: No mutable defaults ✅
- TYP-001: 100% type coverage ✅
- TYP-003: Specific types where possible ✅
- PERF-001: Vectorized numpy operations ✅
- PERF-002: Uses arrays for large data ✅
- BT-003: No look-ahead bias ✅
- BT-004: Realistic transaction costs ✅

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated: 2026-02-07T05:30:00Z*
