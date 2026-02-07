# Requirements: services/multi_market_orchestrator.py

## Source File Analysis
- **File Path**: `app/services/multi_market_orchestrator.py`
- **Lines of Code**: 544
- **Status**: AUDIT COMPLETE

## Purpose
Multi-Market Trading Orchestrator - Coordinates trading across multiple asset classes (Stocks US/EU, Forex, Crypto, Dividends) with dynamic capital allocation, strategy selection, sentiment analysis via Marketaux API, and currency hedging for EUR-based investors.

## Dependencies
- Internal:
  - `app.services.crypto_data_service.get_crypto_fetcher`
  - `app.services.forex_data_service.get_forex_fetcher`
  - `app.engines.data_engine.sources.sentiment_sources.NewsSentimentSource`
- External:
  - `asyncio`, `logging`, `dataclasses`, `datetime`, `decimal`, `enum`
  - Standard library only (no third-party dependencies in core logic)

## Classes/Functions

### Enums
- `MarketType`: STOCKS_US, STOCKS_EU, FOREX, CRYPTO, DIVIDENDS
- `MarketRegime`: BULL_VOLATILE, BULL_STABLE, BEAR_VOLATILE, BEAR_STABLE, SIDEWAYS
- `StrategyType`: MOMENTUM, MEAN_REVERSION, PAIRS_TRADING, TREND_FOLLOWING, BREAKOUT, NEWS_SENTIMENT, DIVIDEND_GROWTH

### Data Classes
- `MarketAllocation`: Tracks capital allocation per market
- `MarketSignal`: Trading signal with sentiment and confidence

### Main Class: MultiMarketOrchestrator
- `__init__(total_capital, tax_residence, base_currency, marketaux_api_key)`: Initialize orchestrator
- `analyze_market_regime(market_type)`: MarketRegime - Detect current market regime
- `get_optimal_strategy(market_type, regime)`: StrategyType - Get optimal strategy for market
- `get_marketaux_sentiment(symbol)`: Dict - Get sentiment from Marketaux API with caching
- `calculate_allocations(risk_tolerance)`: Dict - Calculate optimal capital allocation
- `generate_signals(market_type)`: List[MarketSignal] - Generate trading signals
- `execute_trades(signals)`: Dict - Execute trades (logging only in current implementation)
- `run_cycle(risk_tolerance)`: Dict - Run complete trading cycle

### Global Functions
- `get_orchestrator(total_capital, tax_residence, marketaux_api_key)`: Get singleton instance
- `reset_orchestrator()`: Reset global instance

## Business Logic
1. **Capital Allocation**: Dynamic allocation based on risk tolerance and tax residence (ES default)
2. **Strategy Selection**: Maps market regimes to optimal trading strategies
3. **Sentiment Analysis**: Marketaux API integration with 5-minute cache, cleanup on overflow
4. **Currency Considerations**: Optimized for EUR-based investors with tax-aware allocations
5. **Max Allocations**: Per-market limits (US: 40%, EU: 30%, Forex: 15%, Crypto: 10%, Dividends: 20%)

## Data Models
- Uses Decimal for all financial calculations
- Async operations for API calls
- Sentiment cache with TTL (5 minutes)

## API Contracts
- `marketaux_api_key`: Optional token for news sentiment
- Tax-aware allocation for Spanish residents
- Currency hedging considerations (EUR base)

## Error Handling
- Exception handling: `(ValueError, TypeError, KeyError, AttributeError, IndexError)`
- Graceful fallbacks for missing API keys
- Cache overflow protection (cleanup at 10,000 entries)
- Logging for all operations

## Performance Considerations
- Sentiment cache with TTL reduces API calls
- Async operations for concurrent requests
- Cache size limits prevent memory issues
- Top 5 symbols processed for sentiment to limit API usage

## Testing Strategy
- Mock crypto/forex fetchers for unit tests
- Test sentiment cache overflow
- Test allocation calculations for different risk profiles
- Test error handling for API failures
- Test tax-aware allocations for different residences

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** No critical violations found

**Checks Against BASE_RULES.md:**
- ✅ SEC-001: No hardcoded secrets (API key passed as parameter)
- ✅ SEC-007: Input validation for capital amounts
- ✅ LOG-004: Error logging with context
- ✅ LOG-005: No sensitive data in logs (no tokens logged)
- ✅ CC-001: Descriptive names (MarketRegime, StrategyType, etc.)
- ✅ ASYNC-001: Proper async def usage
- ✅ ASYNC-002: Proper await usage
- ✅ ASYNC-004: No blocking time.sleep() in async functions
- ✅ FMT-007: No mutable defaults (default dicts use tuples)
- ✅ ARCH-004: Functions generally < 20 lines
- ✅ TRD-004: Audit trail for trading decisions

**Minor Notes:**
- Mock price generation in `_generate_mock_price()` uses random - acceptable for testing
- `MARKET_SYMBOLS` hardcoded - acceptable as reference data

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0076*
