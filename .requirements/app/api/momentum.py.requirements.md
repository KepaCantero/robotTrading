# momentum.py

## Purpose
FastAPI endpoints for momentum analysis and strategy management including technical indicators, momentum signals, and strategy CRUD operations.

---

## Type Definitions / Data Classes

### MomentumType (Enum)
- **PRICE_MOMENTUM**: Price-based momentum signals
- **VOLUME_MOMENTUM**: Volume-based momentum signals
- **VOLATILITY_MOMENTUM**: Volatility-based momentum signals

### Timeframe (Enum)
- **DAILY / 1d**: Daily timeframe
- **HOURLY / 1h**: Hourly timeframe
- **FOUR_HOUR / 4h**: 4-hour timeframe
- **WEEKLY / 1w**: Weekly timeframe

### MomentumStrategy (Service model)
```python
class MomentumStrategy:
    name: str                       # REQUIRED - unique strategy name
    description: str                # REQUIRED - strategy description
    momentum_type: MomentumType     # REQUIRED - type of momentum
    timeframe: Timeframe            # REQUIRED - analysis timeframe
    min_strength: float             # REQUIRED - minimum signal strength (0-100)
    min_confidence: float           # REQUIRED - minimum confidence (0-100)
    signal_duration: int            # REQUIRED - signal duration in hours
    rsi_oversold: float             # REQUIRED - RSI oversold threshold
    rsi_overbought: float           # REQUIRED - RSI overbought threshold
    ema_short_period: int           # REQUIRED - short EMA period
    ema_long_period: int            # REQUIRED - long EMA period
    min_volume_ratio: float         # REQUIRED - minimum volume ratio
    volume_spike_threshold: float   # REQUIRED - volume spike threshold
    max_position_size: float        # REQUIRED - max position size %
    stop_loss_pct: float            # REQUIRED - stop loss percentage
    take_profit_pct: float          # REQUIRED - take profit percentage
    is_active: bool                 # REQUIRED - whether strategy is active
```

**Validation Rules:**
- `min_strength` and `min_confidence` must be 0-100
- `signal_duration` must be positive
- `ema_short_period` < `ema_long_period`
- Percentages must be non-negative

### MomentumFilter (Service model)
```python
class MomentumFilter:
    momentum_types: Optional[List[MomentumType]]  # OPTIONAL - filter by types
    timeframes: Optional[List[Timeframe]]         # OPTIONAL - filter by timeframes
    min_strength: float                           # REQUIRED - minimum strength
    min_confidence: float                         # REQUIRED - minimum confidence
    active_only: bool                             # REQUIRED - only active signals
    max_age_hours: int                            # REQUIRED - maximum signal age
```

---

## Function Signatures (Contracts)

### `get_momentum_overview(service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** Service is initialized
**Post:** Returns overview with top assets, strategies count, available types
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `analyze_asset_momentum_post(request_data: Dict[str, Any], service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** request_data contains valid symbol and timeframe
**Post:** Returns momentum analysis with indicators and signals
**Raises:** HTTPException(400) on invalid input, HTTPException(404) if no analysis, HTTPException(500) on errors
**Retry:** No
**Side Effects:** May create new analysis in service

### `analyze_asset_momentum(symbol: str, timeframe: Timeframe, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** symbol is non-empty string
**Post:** Returns momentum analysis with indicators and signals
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** May create new analysis in service

### `get_momentum_signals_for_symbol(symbol: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** symbol is valid trading symbol
**Post:** Returns all momentum signals for the symbol
**Raises:** HTTPException(404) if no signals found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_momentum_signals(momentum_types, timeframes, min_strength, min_confidence, active_only, max_age_hours, limit, service) -> Dict[str, Any]`
**Pre:** Filter criteria are valid (strength/confidence 0-100, limit 1-200)
**Post:** Returns filtered signals matching criteria
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_top_momentum_signals(limit: int, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** limit is between 1-50
**Post:** Returns top N momentum signals by score
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `create_momentum_strategy(strategy_data: Dict[str, Any], service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** strategy_data contains required fields (name, description, timeframe, momentum_type or momentum_types)
**Post:** Creates strategy and returns confirmation
**Raises:** HTTPException(422) on validation errors, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Creates new strategy in service

### `get_momentum_strategy(strategy_name: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** strategy_name is provided
**Post:** Returns strategy details
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `update_momentum_strategy(strategy_name: str, strategy_data: Dict[str, Any], service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** strategy exists, strategy_data contains valid updates
**Post:** Updates strategy fields and returns updated strategy
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Modifies strategy in service

### `delete_momentum_strategy(strategy_name: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** strategy_name exists
**Post:** Deletes strategy and returns confirmation
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Removes strategy from service

### `get_momentum_strategies(service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns all momentum strategies
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_strategy_signals(strategy_name: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** strategy_name exists
**Post:** Returns signals generated by the strategy
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `analyze_multiple_assets(symbols: List[str], timeframe: Timeframe, background_tasks: BackgroundTasks, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** symbols list length <= 20
**Post:** Returns momentum analysis for each symbol
**Raises:** HTTPException(400) if > 20 symbols, HTTPException(500) on errors
**Retry:** No
**Side Effects:** May create analyses for each symbol

### `get_technical_indicators(symbol: str, timeframe: Timeframe, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** symbol is valid
**Post:** Returns technical indicators (RSI, EMA, MACD, ATR, etc.)
**Raises:** HTTPException(404) if no analysis, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_momentum_stats(service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns statistics (signal counts, type distribution, averages)
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_momentum_analyses(service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns all momentum analyses
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_momentum_analysis(analysis_id: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** analysis_id exists
**Post:** Returns specific momentum analysis
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `delete_momentum_analysis(analysis_id: str, service: MomentumAnalysisService) -> Dict[str, Any]`
**Pre:** analysis_id exists
**Post:** Deletes analysis and returns confirmation
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Removes analysis from service

---

## Acceptance Criteria
- [ ] All symbol parameters converted to uppercase
- [ ] Timeframe string mapping handles all valid formats (daily, 1d, hourly, 1h, etc.)
- [ ] Batch analysis limited to 20 symbols maximum
- [ ] All limit parameters validated (1-200 for signals, 1-50 for top)
- [ ] Strategy creation validates required fields
- [ ] Strategy update preserves unchanged fields
- [ ] All responses include UTC timestamp
- [ ] Signal filtering respects all filter criteria
- [ ] Technical indicators return all expected fields

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - No logging present |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Good validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Rate limiting on batch endpoints | ⚠️ PARTIAL - Limit of 20 but no rate limiting |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling with context | ⚠️ PARTIAL - Basic error handling |
| API-009 | 09-logging-observability.md | Request logging | ❌ GAP - No request logging |
| API-010 | 08-configuration.md | Enum validation | ✅ OK - Proper enum handling |

---

## Dependencies
- **External:** fastapi, requests
- **Internal:** app.models.momentum, app.services.momentum_analysis

---

## Required Tests
- **test_momentum_endpoints.py:**
  - Test get_momentum_overview returns valid structure
  - Test analyze_asset_momentum with various timeframes
  - Test analyze_asset_momentum_post handles invalid timeframe strings
  - Test get_momentum_signals with all filter combinations
  - Test create_momentum_strategy with valid/invalid data
  - Test create_momentum_strategy handles both momentum_type and momentum_types
  - Test update_momentum_strategy updates only provided fields
  - Test delete_momentum_strategy returns 404 for non-existent strategy
  - Test analyze_multiple_assets enforces 20 symbol limit
  - Test get_technical_indicators returns all expected indicators
  - Test get_momentum_stats calculates correct averages
  - Test all endpoints handle connection errors gracefully

---

## Notes
- Comprehensive endpoint coverage (20+ endpoints)
- Timeframe mapping handles multiple string formats
- Strategy CRUD operations fully implemented
- No authentication/authorization visible
- Consider pagination for list endpoints (strategies, analyses)
