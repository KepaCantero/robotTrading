# Requirements: services/asset_identification.py

## Source File Analysis
- **File Path**: `app/services/asset_identification.py`
- **Lines of Code**: 653
- **Audit Date**: 2026-02-07
- **Status**: PASSED

## Purpose
Asset identification and ranking service for AlgoTrading system. Handles identification, ranking, and management of liquid assets for momentum trading strategies across equity, crypto, forex, and commodity asset classes.

## Dependencies

### Internal
- `app.models.assets`:
  - `Asset`: Asset data model
  - `AssetClass`: Enum (EQUITY, CRYPTO, FOREX, COMMODITY)
  - `AssetFilter`: Asset filtering criteria
  - `AssetRanking`: Asset ranking container
  - `AssetUniverse`: Asset universe container
  - `Exchange`: Enum (NASDAQ, NYSE, BINANCE, OANDA, CME)
  - `LiquidityMetrics`: Liquidity scoring data
- `app.services.market_universe_loader`: MarketUniverseLoader (lazy import)

### External
- `asyncio`: Async/await support
- `logging`: Structured logging
- `decimal.Decimal`: Precise financial calculations
- `typing`: Optional, Dict, List, Any

## Classes/Functions

### Main Class
- **`AssetIdentificationService`** (Singleton pattern)
  - `__init__()`: Initialize default universes for all asset classes
  - `async identify_liquid_assets(asset_class, limit) -> List[Asset]`: Get top N liquid assets
  - `async _get_predefined_liquid_assets(asset_class) -> List[Asset]`: Asset source routing
  - `async _get_liquid_equities() -> List[Asset]`: S&P 500 from MarketUniverseLoader
  - `async _get_liquid_cryptos() -> List[Asset]`: Top cryptos from MarketUniverseLoader
  - `async _get_liquid_forex() -> List[Asset]`: Major forex pairs (hardcoded)
  - `async _get_liquid_commodities() -> List[Asset]`: Major commodities (hardcoded)
  - `async _calculate_liquidity_score(asset) -> None`: Update asset liquidity scores
  - `async update_asset_universe(asset_class, assets) -> bool`: Replace universe
  - `async _update_rankings(asset_class) -> None`: Refresh rankings
  - `async get_top_liquid_assets(asset_class, limit) -> List[Asset]`: Query top assets
  - `async get_asset_rankings(asset_class) -> AssetRanking`: Get rankings
  - `async filter_assets(asset_class, filter_criteria) -> List[Asset]`: Filter universe
  - `async get_asset_by_symbol(symbol, asset_class) -> Optional[Asset]`: Symbol lookup
  - `async get_universe_summary(asset_class) -> Dict`: Universe statistics

### Fallback Methods
- `async _get_fallback_equities() -> List[Asset]`: 10 major US stocks
- `async _get_fallback_cryptos() -> List[Asset]`: 5 major cryptocurrencies

### Singleton
- `get_asset_identification_service() -> AssetIdentificationService`: Global instance

## Business Logic

### Asset Class Coverage
1. **EQUITY**: S&P 500 top stocks (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, etc.)
2. **CRYPTO**: BTC, ETH, BNB, SOL, XRP (top by volume)
3. **FOREX**: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY
4. **COMMODITY**: GOLD, SILVER, OIL, NATURAL_GAS, COPPER

### Liquidity Scoring
- Volume score: Based on avg_volume
- Spread score: Based on avg_spread
- Combined score: `asset.combined_liquidity_score`
- Metrics stored in LiquidityMetrics

### Fallback Strategy
1. Try MarketUniverseLoader first
2. If fails, use hardcoded fallback lists
3. Ensures system always has assets available

### Universe Management
- Default: Top 20 assets per class
- Rankings updated on universe refresh
- Liquidity metrics tracked per symbol

## Data Models

### Asset (from models.py)
```python
@dataclass
class Asset:
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: Exchange
    avg_volume: Decimal
    avg_spread: Decimal
    market_cap: Optional[Decimal]
    liquidity_score: float = 0.0

    @property
    def volume_score(self) -> float: ...
    @property
    def spread_score(self) -> float: ...
    @property
    def combined_liquidity_score(self) -> float: ...
```

### AssetUniverse
- Top N liquid assets per class
- Methods: `add_asset()`, `get_top_liquid_assets()`

### AssetRanking
- Per-class asset rankings by liquidity
- Methods: `add_ranking()`

## API Contracts

### identify_liquid_assets()
```python
async def identify_liquid_assets(
    self,
    asset_class: AssetClass,
    limit: int = 20
) -> List[Asset]:
    """
    Returns:
        Top N liquid assets sorted by liquidity_score (descending)

    Error Handling:
        Returns [] on error (logged)
    """
```

### get_asset_by_symbol()
```python
async def get_asset_by_symbol(
    self,
    symbol: str,
    asset_class: Optional[AssetClass] = None
) -> Optional[Asset]:
    """
    Returns:
        Asset if found, None otherwise

    Search Strategy:
        - If asset_class provided, search only that universe
        - Otherwise, search all universes
    """
```

### filter_assets()
```python
async def filter_assets(
    self,
    asset_class: AssetClass,
    filter_criteria: AssetFilter
) -> List[Asset]:
    """
    Returns:
        Assets matching filter criteria
    """
```

## Error Handling

### External API Failures
- MarketUniverseLoader failures caught and logged
- Falls back to hardcoded asset lists
- Never returns empty asset set

### Exception Handling
- Catches: asyncio.TimeoutError, ConnectionError, OSError
- Catches: ValueError, TypeError, KeyError, AttributeError, IndexError
- All errors logged before returning empty/fallback

### Graceful Degradation
- System works even if MarketUniverseLoader unavailable
- Hardcoded fallbacks for all asset classes
- Empty list returned only as last resort

## Performance Considerations

- Lazy import of MarketUniverseLoader (avoid circular dependency)
- Async methods prevent blocking
- Sorting O(n log n) on asset list (acceptable for n=20-500)
- Caching via AssetUniverse/AssetRanking objects

## Testing Strategy

### Unit Tests Needed
- Test identify_liquid_assets for each asset class
- Test liquidity score calculation
- Test universe update and ranking refresh
- Test asset filtering by criteria
- Test symbol lookup (with/without asset_class)
- Test fallback activation on API failure
- Test error handling for all exception paths

### Integration Tests Needed
- Test MarketUniverseLoader integration
- Test data flow from API to Asset objects
- Test universe summary generation

### Edge Cases to Test
- Empty asset class
- Invalid symbol lookup
- API timeout during fetch
- Malformed API response

## Audit Findings

### PASSED Rules
- ✅ FMT-001: Line length ≤ 100 (Black compliant)
- ✅ FMT-007: No mutable defaults (dataclasses used)
- ✅ TYP-001: Type hints present
- ✅ TYP-002: Modern syntax (dict[K,V], Optional[T])
- ✅ ASYNC-001: async def used correctly
- ✅ ASYNC-002: All async calls awaited
- ✅ LOG-003: Appropriate log levels
- ✅ CC-001: Descriptive names
- ✅ CC-005: Early returns (enabled check, empty checks)
- ✅ SOL-001: Single Responsibility (asset identification only)
- ✅ SOL-005: Dependency Inversion (depends on Asset abstractions)
- ✅ DP-004: Singleton pattern (get_asset_identification_service)
- ✅ ARCH-007: Composition (has AssetUniverse, AssetRanking)
- ✅ TRD-003: Position limits (via AssetUniverse top_n)

### Strengths
- Comprehensive asset class coverage
- Graceful fallback strategy
- Clean error handling
- Good separation of concerns
- Lazy imports avoid circular dependencies
- Singleton pattern for shared service

### Recommendations
1. Consider adding asset universe refresh interval
2. Consider adding market hours validation
3. Consider caching liquidity scores
4. Document the rationale for specific asset selections
5. Consider adding region-based filtering

## Compliance with BASE_RULES.md

See ../../BASE_RULES.md for universal rules.

### File-Specific Rules
- RULE-ASSET-001: Must provide fallback assets for all classes (PASS)
- RULE-ASSET-002: Must log all API failures (PASS)
- RULE-ASSET-003: Must use Decimal for financial values (PASS)
- RULE-ASSET-004: Must calculate liquidity scores (PASS)
- RULE-ASSET-005: Must support symbol lookup across classes (PASS)

---
**Audit Status**: PASSED
**Audited By**: Claude (Backend Developer Agent)
**Audit Date**: 2026-02-07
**Priority 1 Issues**: 0
