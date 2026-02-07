# Requirements: backtesting/insight_generator.py

## Source File Analysis
- **File Path:** `app/backtesting/insight_generator.py`
- **Lines of Code:** 535
- **Audit Status:** PASSED_WITH_NOTES
- **Audit Date:** 2026-02-07T05:30:00Z

## Purpose
Generate data-driven insights, risk warnings, and actionable recommendations for trading strategies. Uses template-based generation with statistical analysis to provide deterministic, traceable output without LLM/NLP.

## Dependencies
- **Internal:** None (domain-level module)
- **External:**
  - `logging`
  - `datetime`
  - `typing` (Any, Dict, List, Optional)
  - `numpy`

## Classes/Functions

### Classes
- **InsightGenerator:** Main class for generating insights and recommendations
  - `__init__(risk_free_rate: float = 0.02)`
  - `generate_statistical_insights(metrics: Dict[str, float]) -> List[str]`
  - `generate_risk_warnings(metrics: Dict[str, float]) -> List[Dict[str, Any]]`
  - `generate_recommendations(metrics: Dict[str, float], regimes: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`
  - `format_markdown_report(...) -> str`
  - `get_insights() -> List[str]`
  - `get_warnings() -> List[Dict[str, Any]]`
  - `get_recommendations() -> List[Dict[str, Any]]`

## Business Logic

### Statistical Insights Generation
Analyzes performance metrics and generates insights for:
- Total returns (categorized as excellent/good/positive/negative)
- Sharpe ratio (exceptional/good/marginal/poor)
- Maximum drawdown (minimal/moderate/significant/severe)
- Win rate (strong/positive/marginal/poor)
- Volatility (low/moderate/elevated/high)
- Profit factor (excellent/strong/marginal/poor)

### Risk Warning System
Generates warnings at three levels:
- **CRITICAL:** Catastrophic drawdown >50%, negative Sharpe ratio
- **WARNING:** Significant drawdown 20-50%, poor risk-adjusted returns, high volatility, low win rate, profit factor <1.0
- **INFO:** Moderate drawdown, marginal profit factor

### Recommendation Engine
Provides actionable recommendations based on:
- Risk management (stop-loss, position sizing)
- Signal quality enhancement
- Entry timing improvement
- Position management optimization
- Regime filtering
- Paper trading validation

## Data Models
No dedicated data models. Uses dictionaries for:
- Performance metrics: `Dict[str, float]`
- Warnings: `List[Dict[str, Any]]` with keys: level, metric, value, message
- Recommendations: `List[Dict[str, Any]]` with keys: priority, action, rationale

## API Contracts
N/A - This is a library module, not an API endpoint

## Error Handling
- Catches specific exceptions: `RuntimeError`, `ValueError`, `TypeError`, `KeyError`, `AttributeError`, `IndexError`
- All exceptions logged with `logger.error()` including stack traces (`exc_info=True`)
- Returns empty list on error (graceful degradation)

## Performance Considerations
- Single-pass analysis of metrics
- O(1) lookups for metric thresholds
- Minimal computational overhead
- Stateful design allows re-generation without re-computation

## Testing Strategy
- Unit tests for each generation method
- Edge cases: empty metrics, None values, extreme values
- Verify warning/recommendation thresholds
- Test markdown report formatting

## Audit Notes

### Non-Critical Issues
1. **Type Hints (TYP-002):** Uses old syntax `Optional[X]` instead of `X | None`
   - Impact: Low - code is functional and type-safe
   - Recommendation: Update to modern syntax in future refactor

2. **Any Type Usage (TYP-003):** Uses `Any` without documentation for Dict values
   - Lines: 37, 142, 276
   - Impact: Low - structure is documented in docstrings
   - Recommendation: Create TypedDict for warning/recommendation structures

### What Was Checked
- ✅ No print() statements (uses logger)
- ✅ No mutable default arguments
- ✅ Proper exception handling (specific exceptions, logged)
- ✅ Google style docstrings
- ✅ Absolute imports only
- ✅ No circular imports
- ✅ All functions have return type hints

### BASE_RULES Compliance
See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

**File-specific rules:**
- FMT-007: No mutable defaults ✅
- TYP-001: 100% type coverage ✅
- TYP-002: Modern syntax - uses old style (non-blocking)
- TYP-003: Any without justification - documented in docstrings (acceptable)
- LOG-004: Error logging with stack traces ✅
- CC-006: Explicit error handling ✅

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated: 2026-02-07T05:30:00Z*
