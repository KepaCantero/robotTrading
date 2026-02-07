# Requirements: services/portfolio_service.py

## Source File Analysis
- **File Path**: `app/services/portfolio_service.py`
- **Lines of Code:** 493
- **Status:** AUDIT COMPLETE

## Purpose
TASK-15: Refactored Portfolio Service - Portfolio operations with centralized circuit breaker manager, risk manager, currency hedging engine, and diversification validators.

## Dependencies
- Internal:
  - `app.core.centralized_config.get_config`
  - `app.models.portfolio.*`
  - `app.services.circuit_breaker_manager.CircuitBreakerManager`, `CircuitBreakerType`
  - `app.services.country_diversification_validator.CountryDiversificationValidator`
  - `app.services.currency_hedging_engine.CurrencyHedgingEngine`
  - `app.services.portfolio_risk_manager.PortfolioRiskManager`
  - `app.services.sector_diversification_validator.SectorDiversificationValidator`
- External:
  - `logging`, `datetime`, `decimal`, `typing`

## Classes/Functions

### Main Class: PortfolioService
- `__init__(provider)`: Initialize with circuit breaker, risk manager, hedging, validators
- `get_portfolio()`: Get portfolio with circuit breaker protection
- `get_position(symbol)`: Get position with circuit breaker protection
- `add_position(position)`: Add position with risk assessment
- `update_position(position)`: Update position with risk assessment
- `remove_position(symbol)`: Remove position
- `simulate_trade(symbol, quantity, price)`: Simulate with risk assessment
- `get_service_statistics()`: Get service + manager statistics
- `get_circuit_breaker_status()`: Get all breaker statuses
- `get_risk_assessment(portfolio)`: Get portfolio risk assessment
- `reset_circuit_breakers()`: Reset all breakers
- `reset_statistics()`: Reset all statistics
- `reset_circuit_breaker(breaker_name)`: Reset specific breaker
- `get_portfolio_summary(portfolio)`: Get portfolio summary
- `get_asset_universe()`: Get supported assets
- `get_market_regime(symbol)`: Get regime for symbol
- `get_unhedged_currency_exposure(portfolio)`: Get FX exposure [TASK-5.5]
- `get_hedging_statistics()`: Get hedging stats [TASK-5.5]
- `apply_auto_hedging(portfolio)`: Apply hedging [TASK-5.5]
- `get_sector_allocation()`: Get sector allocation [TASK-5.6]
- `get_country_allocation()`: Get country allocation [TASK-5.6]
- `get_diversification_status(portfolio)`: Get diversification status [TASK-5.6]
- `suggest_rebalancing(portfolio)`: Get rebalancing suggestions [TASK-5.6]
- `_get_asset_class(symbol)`: Determine asset class from symbol

## Business Logic
1. **Circuit Breaker Protection**: All operations check breaker status before API calls
2. **Risk Assessment**: All position changes assessed for risk violations
3. **Currency Hedging**: FX exposure calculation and hedging recommendations [TASK-5.5]
4. **Diversification Validation**: Sector and country limits with rebalancing [TASK-5.6]
5. **Statistics Tracking**: Operations count, success/failure, timing

## Data Models
- Portfolio, Position from models
- Service statistics dictionary
- Hedging statistics dictionary

## API Contracts
- PortfolioProvider interface for data access
- Returns None on circuit breaker open
- Returns False on critical violations

## Error Handling
- Exception types: `(ValueError, TypeError, KeyError, AttributeError, IndexError)`
- Circuit breaker records errors on failure
- Risk assessment prevents critical trades

## Performance Considerations
- Circuit breaker prevents cascading failures
- Statistics tracking for monitoring
- Async-compatible architecture

## Testing Strategy
- Test circuit breaker open/close
- Test risk assessment blocking
- Test hedging calculations
- Test diversification validation
- Test statistics tracking

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Well-refactored service with good separation of concerns

**Checks Against BASE_RULES.md:**
- ✅ SOL-001: Single responsibility (orchestration only)
- ✅ SOL-005: Dependency injection (provider, managers)
- ✅ DP-004: Dependency injection pattern
- ✅ CC-001: Descriptive method names
- ✅ CC-006: Explicit error handling
- ✅ LOG-004: Error logging with context
- ✅ SEC-005: Audit logging for operations
- ✅ TRD-002: Risk validation before trades
- ✅ ARCH-001: Layered architecture (service layer)

**Minor Notes:**
- Mock data in `get_asset_universe()` and `get_market_regime()` - appropriate for service layer
- `_get_asset_class()` uses simple suffix matching - functional

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0078*
