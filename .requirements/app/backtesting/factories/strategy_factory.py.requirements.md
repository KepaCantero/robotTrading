# strategy_factory.py

## Purpose
Factory pattern implementation for centralized strategy creation, reducing God Object anti-pattern in backtesting by extracting strategy instantiation logic from ComprehensiveBacktestRunner.

---

## Type Definitions / Data Classes

### StrategyFactory (Factory Class)
```python
class StrategyFactory:
    STRATEGY_CLASSES: Dict[str, Type]  # REQUIRED - Maps strategy types to classes
```

**Strategy Classes Mapping:**
```python
{
    'mean_reversion': MeanReversionStrategy,      # REQUIRED
    'momentum': MomentumStrategy,                  # REQUIRED
    'modular_momentum': ModularMomentumStrategy,   # REQUIRED
    'pairs_trading': PairsTradingStrategy,         # REQUIRED
}
```

### Strategy Configuration Schema
```python
strategy_config: Dict[str, Any] = {
    'type': str,                    # REQUIRED - Strategy type from STRATEGY_CLASSES
    'parameters': Dict[str, Any],   # OPTIONAL - Strategy-specific parameters
    'thresholds': {                 # OPTIONAL - Trading thresholds
        'buy_threshold': Decimal,   # REQUIRED if thresholds present - > sell_threshold
        'sell_threshold': Decimal,  # REQUIRED if thresholds present - < buy_threshold
        'stop_loss': Decimal,       # OPTIONAL - Negative value (e.g., -0.05 for -5%)
        'take_profit': Decimal,     # OPTIONAL - Positive value (e.g., 0.10 for +10%)
    }
}
```

**Validation Rules:**
- `type` must exist in `STRATEGY_CLASSES` keys
- If `thresholds.buy_threshold` exists, must be > `thresholds.sell_threshold`
- `stop_loss` must be negative decimal (e.g., -0.05)
- `take_profit` must be positive decimal (e.g., 0.10)
- Default thresholds: buy=0.7 (70%), sell=0.3 (30%), stop=-0.05 (-5%), take=0.10 (+10%)

---

## Function Signatures (Contracts)

### `StrategyFactory.create_strategy(strategy_config: Dict[str, Any], symbols: Optional[List[str]] = None) -> Any`
**Pre:** `strategy_config['type']` must be in `STRATEGY_CLASSES`
**Post:** Returns initialized strategy instance matching requested type
**Raises:** `ValueError` if strategy_type is unknown
**Retry:** No
**Side Effects:** Logs strategy creation at INFO level

### `StrategyFactory.get_strategy_name(strategy: Any) -> str`
**Pre:** `strategy` must be a valid strategy instance
**Post:** Returns strategy name from `strategy.name` attribute or class name
**Raises:** No
**Retry:** No
**Side Effects:** None

### `StrategyFactory.extract_thresholds(strategy_config: Dict[str, Any]) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns thresholds dict with default values if not specified in config
**Raises:** No
**Retry:** No
**Side Effects:** None

### `StrategyFactory.create_baseline_config(base_config: Dict[str, Any]) -> Dict[str, Any]`
**Pre:** `base_config` must contain 'strategy' key with valid structure
**Post:** Returns strategy configuration dict for baseline testing
**Raises:** No
**Retry:** No
**Side Effects:** None

### `StrategyFactory.create_multi_strategy_configs(base_config: Dict[str, Any]) -> List[Dict[str, Any]]`
**Pre:** `base_config.input.symbols` must be list of valid symbols
**Post:** Returns list of 3 strategy configs (momentum, mean_reversion, modular_momentum)
**Raises:** No
**Retry:** No
**Side Effects:** None

### `StrategyFactory.list_available_strategies() -> List[str]`
**Pre:** None
**Post:** Returns list of available strategy type names
**Raises:** No
**Retry:** No
**Side Effects:** None

### `StrategyFactory.validate_config(strategy_config: Dict[str, Any]) -> bool`
**Pre:** None
**Post:** Returns True if config is valid, False otherwise
**Raises:** No
**Retry:** No
**Side Effects:** Logs validation warnings at WARNING level

### `create_strategy_from_config(strategy_config: Dict[str, Any], symbols: Optional[List[str]] = None) -> Any`
**Pre:** Same as `create_strategy`
**Post:** Same as `create_strategy`
**Raises:** `ValueError` if strategy_type is unknown
**Retry:** No
**Side Effects:** None (convenience function)

### `get_strategy_metadata(strategy: Any) -> Dict[str, Any]`
**Pre:** `strategy` must be valid instance
**Post:** Returns dict with 'name', 'class', 'module' keys
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-FCT-001: Factory creates valid strategy instances for all 4 strategy types
- [ ] AC-FCT-002: Factory raises ValueError with helpful message for unknown strategy types
- [ ] AC-FCT-003: Threshold validation rejects buy_threshold <= sell_threshold
- [ ] AC-FCT-004: Default thresholds are applied when not specified in config
- [ ] AC-FCT-005: Multi-strategy configs generate exactly 3 configurations
- [ ] AC-FCT-006: All strategy creation is logged at INFO level
- [ ] AC-FCT-007: validate_config returns False for invalid configurations
- [ ] AC-FCT-008: Strategy classes are registered in STRATEGY_CLASSES mapping

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES | Single Responsibility - Factory only creates strategies | ✅ OK |
| SOL-002 | BASE_RULES | Open/Closed - New strategies added without modifying factory | ✅ OK |
| DP-002 | BASE_RULES | Factory pattern appropriate for runtime type selection | ✅ OK |
| DP-004 | BASE_RULES | Dependency injection via config dict | ✅ OK |
| LOG-003 | BASE_RULES | Appropriate log levels (INFO for creation) | ✅ OK |
| TYP-001 | BASE_RULES | Type hints on all functions | ⚠️ PARTIAL - Some functions missing return types |
| CC-006 | BASE_RULES | Explicit error handling with ValueError | ✅ OK |
| ARCH-007 | BASE_RULES | Composition over inheritance | ✅ OK |

### Trading-Specific Rules

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-003 | BASE_RULES | No look-ahead bias - config validation prevents future data | ✅ OK |
| TRD-004 | BASE_RULES | Audit trail - all strategy creation logged | ✅ OK |

**NOTE:** This analysis considers all 96 rules from BASE_RULES.md

---

## Dependencies
- **External:** None (only stdlib: logging, typing)
- **Internal:**
  - `app.strategies.mean_reversion.MeanReversionStrategy`
  - `app.strategies.momentum.MomentumStrategy`
  - `app.strategies.momentum_modular.strategy.ModularMomentumStrategy`
  - `app.strategies.pairs_trading.PairsTradingStrategy`

---

## Required Tests
- **tests/backtesting/factories/test_strategy_factory.py:**
  - Test create_strategy for all 4 strategy types (success path)
  - Test create_strategy raises ValueError for unknown type
  - Test create_strategy with missing 'type' defaults to 'momentum'
  - Test get_strategy_name returns strategy.name or class name
  - Test extract_thresholds returns defaults when not specified
  - Test extract_thresholds returns provided thresholds
  - Test create_baseline_config generates valid config
  - Test create_multi_strategy_configs generates 3 configs
  - Test list_available_strategies returns all 4 types
  - Test validate_config accepts valid configurations
  - Test validate_config rejects buy_threshold <= sell_threshold
  - Test validate_config rejects unknown strategy types
  - Test validate_config logs warnings for invalid configs
  - Test convenience function create_strategy_from_config
  - Test convenience function get_strategy_metadata

---

## Notes
Extracted from ComprehensiveBacktestRunner to follow Single Responsibility Principle and reduce God Object anti-pattern. Factory pattern enables strategy polymorphism and decouples strategy creation from backtesting logic.
