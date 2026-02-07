# Requirements: services/paper_trading_service.py

## Source File Analysis
- **File Path:** `app/services/paper_trading_service.py`
- **Lines of Code:** 621
- **Status:** AUDIT COMPLETE

## Purpose
Paper trading service for realistic trading simulation including fees, slippage, market impact, portfolio management, P&L tracking, risk management, and performance metrics.

## Dependencies
- Internal:
  - `app.core.centralized_config.get_config`
  - `app.models.market_data.Quote`
  - `app.models.order.Order`
  - `app.models.paper_trading.*`
  - `app.models.slippage_analysis.SlippageCalculationParams`
  - `app.services.slippage_analysis_service.DynamicSlippageService`
- External:
  - `asyncio`, `random`, `datetime`, `decimal`, `typing`, `uuid`

## Classes/Functions

### Main Class: PaperTradingService
- `__init__()`: Initialize service with slippage service and config
- `create_portfolio(name, config_id, initial_cash)`: Create new portfolio
- `create_session(portfolio_id, name, description, config_id)`: Create trading session
- `execute_trade(...)`: Execute trade with realistic simulation
- `update_market_prices(quotes)`: Update prices and recalculate metrics
- `get_portfolio(portfolio_id)`: Get portfolio by ID
- `get_session(session_id)`: Get session by ID
- `get_trades(...)`: Get trades with filters
- `get_positions(portfolio_id)`: Get all positions
- `close_session(session_id)`: Close trading session
- `execute_order(order)`: Execute Order object

### Private Methods
- `_create_default_config()`: Create default configuration from centralized config
- `_get_current_price(symbol)`: Get price from cache or mock
- `_generate_mock_price(symbol)`: Generate mock price for testing
- `_can_execute_trade(...)`: Validate trade against risk limits
- `_calculate_execution_costs(...)`: Calculate slippage, commission, market impact
- `_execute_trade(...)`: Execute trade and update portfolio
- `_update_position(...)`: Update or create position
- `_sync_positions_to_portfolio(...)`: Sync positions to portfolio
- `_update_portfolio_metrics(...)`: Recalculate portfolio metrics
- `_update_session_stats(...)`: Update session statistics
- `_calculate_dynamic_slippage(...)`: Calculate slippage using DynamicSlippageService
- `_get_price_history(symbol, days)`: Get price history for volatility

### Global Functions
- `get_paper_trading_service()`: Get singleton instance

## Business Logic
1. **Realistic Simulation**: Slippage, commission, market impact based on mode
2. **Risk Limits**: Max position size, daily loss, drawdown checks
3. **Dynamic Slippage**: Uses DynamicSlippageService for realistic costs
4. **Position Tracking**: Average price, realized P&L, market value
5. **Session Tracking**: Trades, success/failure counts

## Data Models
- PaperPortfolio: cash_balance, total_equity, total_pnl, positions
- PaperPosition: quantity, avg_price, market_value, cost_basis, P&L
- PaperTrade: symbol, side, order_type, prices, status
- PaperTradingSession: session tracking with statistics

## API Contracts
- Centralized config integration for risk limits
- Configurable simulation modes (SIMPLE, REALISTIC)
- Optional partial fills

## Error Handling
- Exception types: `(ValueError, TypeError, KeyError, AttributeError, IndexError)`
- Validates portfolio existence before operations
- Checks cash availability for buys
- Returns rejected trades with status

## Performance Considerations
- Market data cache for price lookups
- Async operations for trade execution delays
- Configurable execution delays (default 100ms)

## Testing Strategy
- Test realistic vs simple mode
- Test risk limit enforcement
- Test position P&L calculations
- Test slippage calculations
- Test partial fill handling

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Comprehensive paper trading implementation

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Clear, descriptive method names
- ✅ CC-006: Explicit error handling
- ✅ LOG-004: Error logging with context
- ✅ LOG-005: No sensitive data logged
- ✅ SEC-007: Input validation for trades
- ✅ TRD-002: Risk validation before execution
- ✅ TRD-003: Position size limits enforced
- ✅ TRD-005: Price validation
- ✅ ASYNC-001: Proper async def usage
- ✅ ASYNC-004: Uses asyncio.sleep() (correct)
- ✅ FMT-007: No mutable defaults

**Minor Notes:**
- `_generate_mock_price()` uses random - appropriate for paper trading
- Dynamic slippage integration is well-designed

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0076*
