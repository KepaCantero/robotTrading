# Requirements: services/portfolio_risk_manager.py

## Source File Analysis
- **File Path**: `app/services/portfolio_risk_manager.py`
- **Lines of Code:** 680
- **Status:** AUDIT COMPLETE (Previously audited)

## Purpose
TASK-15: Portfolio Risk Manager - Monitors risk limits, detects violations, calculates metrics, and provides alerts with real-time correlation analysis support.

## Dependencies
- Internal:
  - `app.core.centralized_config.get_config`
  - `app.models.portfolio.Portfolio`, `Position`
- External:
  - `asyncio`, `logging`, `datetime`, `decimal`, `enum`, `typing`

## Classes/Functions

### Enums
- `RiskLevel`: LOW, MEDIUM, HIGH, CRITICAL
- `RiskViolation`: POSITION_SIZE, TOTAL_EXPOSURE, SECTOR_EXPOSURE, SECTOR_CONCENTRATION, COUNTRY_EXPOSURE, COUNTRY_CONCENTRATION, CORRELATION, DAILY_LOSS, DRAWDOWN, VOLATILITY, UNHEDGED_FX_EXPOSURE, EXCESSIVE_FX_CONCENTRATION

### Main Class: PortfolioRiskManager
- `__init__(correlation_analyzer)`: Initialize with config and optional correlation analyzer
- `assess_portfolio_risk(portfolio, new_position)`: Main risk assessment
- `_calculate_risk_metrics_async(portfolio, new_position)`: Calculate metrics with real-time correlation
- `_calculate_risk_metrics(portfolio, new_position)`: Synchronous fallback
- `_detect_risk_violations(risk_metrics)`: Check all limits
- `_determine_risk_level(violations, risk_metrics)`: Calculate overall risk level
- `_generate_recommendations(violations, risk_metrics)`: Generate actionable recommendations
- `_calculate_total_exposure(portfolio, new_position)`: Total exposure as % of capital
- `_calculate_sector_exposures(portfolio, new_position)`: Exposure by sector
- `_calculate_correlations_async(portfolio, new_position)`: Real-time correlation matrix
- `_calculate_correlations(portfolio, new_position)`: Fallback correlation
- `_get_fallback_correlation(pos1, pos2)`: Sector-based correlation estimation
- `_calculate_daily_loss(portfolio)`: Daily loss (simplified)
- `_calculate_drawdown(portfolio)`: Drawdown (simplified)
- `_calculate_portfolio_volatility(portfolio)`: Volatility (simplified)
- `_record_violations(violations, risk_assessment)`: Record to history
- `get_risk_statistics()`: Get overall statistics
- `_calculate_currency_exposure(portfolio, new_position)`: FX exposure calculation [TASK-5.5]
- `_detect_fx_violations(currency_exposures)`: FX violation detection [TASK-5.5]
- `get_recent_violations(limit)`: Get violation history
- `clear_history()`: Clear violation history
- `reset_statistics()`: Reset risk statistics

## Business Logic
1. **Risk Limits**: From centralized config (position, exposure, sector, correlation, daily loss, drawdown)
2. **Violations**: Detected against all configured limits
3. **Risk Levels**: Based on violation severity (critical/high/medium)
4. **Correlation**: Real-time if analyzer available, sector-based fallback
5. **Currency Hedging**: FX exposure tracking and violation detection [TASK-5.5]

## Data Models
- Risk assessment dict with risk_level, metrics, violations, recommendations
- Violation history with timestamp and portfolio_id

## API Contracts
- Optional correlation_analyzer for real-time correlations
- Async and sync variants for correlation calculation

## Error Handling
- Handles async context detection
- Falls back to sync if async unavailable
- Catches KeyError, ValueError for missing attributes

## Performance Considerations
- Correlation cache with 1-hour TTL
- Violation history limited to 1000 entries
- Async/sync hybrid for compatibility

## Testing Strategy
- Test violation detection for all types
- Test risk level calculation
- Test correlation fallback
- Test FX exposure calculation
- Test recommendation generation

## Audit Status

**Status:** PASSED (Previously audited - confirmed)
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Previously passed comprehensive GAP analysis

**Previous Audit Findings:**
- All BASE_RULES verified
- No P0/P1 critical violations
- Minor improvements recommended only

**Checks Against BASE_RULES.md:**
- ✅ SEC-001 to SEC-010: PASS (No hardcoded secrets, audit logging present)
- ✅ LOG-004: PASS (Error logging with stack traces)
- ✅ LOG-005: PASS (No sensitive data in logs)
- ✅ TRD-002 to TRD-005: PASS (Trading validations present)

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0077*
