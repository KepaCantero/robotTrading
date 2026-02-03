# config/strategy_config_loader.py

## Purpose
Loads strategy, risk management, and capital tier configuration from YAML files with type-safe access and Decimal precision for financial values.

---

## Type Definitions / Data Classes

### StrategyConfigLoader Class
```python
class StrategyConfigLoader:
    config_dir: Path                    # REQUIRED - Config directory
    _cache: Dict[str, Any]              # PRIVATE - File cache
```

**Configuration Files:**
- `indicators.yaml`: RSI, MA, ATR thresholds
- `risk_management.yaml`: Position sizing, stop loss, take profit
- `capital_tiers.yaml`: Tier thresholds and limits

---

## Function Signatures (Contracts)

### `StrategyConfigLoader.__init__(config_dir) -> None`
**Pre:** None
**Post:** Instance initialized with config_dir or project root default
**Raises:** None
**Retry:** No
**Side Effects:** Sets config_dir, initializes cache

### `StrategyConfigLoader._load_yaml(filename) -> Dict[str, Any]`
**Pre:** filename is string
**Post:** Returns loaded YAML dict or empty dict on error
**Raises:** None (returns {} on error)
**Retry:** No
**Side Effects:** Caches loaded YAML, logs errors

### `StrategyConfigLoader._get_nested(data, key_path, default) -> Any`
**Pre:** data is dict, key_path is dot-notation string
**Post:** Returns nested value or default
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_indicator_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns indicators.yaml content
**Raises:** None
**Retry:** No
**Side Effects:** Loads and caches YAML

### `StrategyConfigLoader.get_rsi_period(variant) -> int`
**Pre:** variant in ["default", "short", "long"]
**Post:** Returns RSI period (default: 14)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_rsi_threshold(threshold) -> int`
**Pre:** threshold in ["extreme_low", "extreme_high", "buy_signal", "sell_signal"]
**Post:** Returns RSI threshold value
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_rsi_adaptive_threshold(market_type, threshold_type) -> int`
**Pre:** market_type and threshold_type are strings
**Post:** Returns adaptive RSI threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_ma_period(length) -> int`
**Pre:** length in ["very_short", "short", "medium", "long", "very_long"]
**Post:** Returns MA period (default: 20)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_atr_period(variant) -> int`
**Pre:** variant in ["default", "short", "long"]
**Post:** Returns ATR period (default: 14)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_atr_multiplier(variant) -> float`
**Pre:** variant in ["tight_stop", "default_stop", "wide_stop"]
**Post:** Returns ATR multiplier (default: 2.0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_risk_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns risk_management.yaml content
**Raises:** None
**Retry:** No
**Side Effects:** Loads and caches YAML

### `StrategyConfigLoader.get_position_sizing(tier, variant) -> Decimal`
**Pre:** tier in ["micro", "small", "medium", "large"]
**Post:** Returns position size as Decimal (0-1 range)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_max_position_size(tier) -> Decimal`
**Pre:** tier is valid tier name
**Post:** Returns max position size as Decimal
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_stop_loss(strategy, variant) -> Decimal`
**Pre:** strategy in ["momentum", "mean_reversion", "pairs_trading"]
**Post:** Returns stop loss as Decimal (0-1 range)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_take_profit(strategy, variant) -> Decimal`
**Pre:** strategy is valid strategy name
**Post:** Returns take profit as Decimal (0-1 range)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_risk_reward_ratio(strategy) -> float`
**Pre:** strategy is valid strategy name
**Post:** Returns min risk/reward ratio (default: 2.0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_max_leverage(tier) -> float`
**Pre:** tier is valid tier name
**Post:** Returns max leverage multiplier (default: 1.0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_tier_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns capital_tiers.yaml content
**Raises:** None
**Retry:** No
**Side Effects:** Loads and caches YAML

### `StrategyConfigLoader.get_tier_thresholds() -> Dict[str, int]`
**Pre:** None
**Post:** Returns tier threshold mappings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_tier_from_capital(capital) -> str`
**Pre:** capital is numeric (int, float, or Decimal)
**Post:** Returns tier name based on capital amount
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_tier_config_value(tier, key_path, default) -> Any`
**Pre:** tier is valid, key_path is dot-notation string
**Post:** Returns tier-specific config value
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_max_positions(tier) -> int`
**Pre:** tier is valid tier name
**Post:** Returns max positions (default: 10)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.get_enabled_strategies(tier) -> list`
**Pre:** tier is valid tier name
**Post:** Returns list of enabled strategies
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyConfigLoader.reload_config() -> None`
**Pre:** None
**Post:** Config cache cleared
**Raises:** None
**Retry:** No
**Side Effects:** Clears _cache dict

### `StrategyConfigLoader.get_all_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns combined config dict
**Raises:** None
**Retry:** No
**Side Effects:** Loads all YAML files

### `get_strategy_config(config_dir) -> StrategyConfigLoader`
**Pre:** None
**Post:** Returns singleton StrategyConfigLoader
**Raises:** None
**Retry:** No
**Side Effects:** Creates singleton if doesn't exist

### `reload_strategy_config() -> None`
**Pre:** None
**Post:** Global config reloaded
**Raises:** None
**Retry:** No
**Side Effects:** Calls reload_config on singleton

---

## Acceptance Criteria
- [ ] All YAML files loaded with safe_load
- [ ] Financial values returned as Decimal type
- [ ] Nested key access with dot notation
- [ ] Tier-based configuration overrides work
- [ ] Strategy-specific parameters accessible
- [ ] Cache improves performance
- [ ] Errors return defaults (not raise)
- [ ] Type hints on all functions
- [ ] Singleton pattern for global instance

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-04T00:00:00Z |
| **Audit Status** | AUDITED |
| **BASE_RULES Version** | a1b2c3d (2026-01-10) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 0 / 0 total |

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-002 | BASE_RULES | Environment variables | ⚠️ PARTIAL - Uses project root default |
| CFG-003 | BASE_RULES | Config validation | ⚠️ PARTIAL - No validation |
| YAML-SEC-001 | Security | safe_load required | ✅ OK - Uses yaml.safe_load() |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK |
| CC-006 | BASE_RULES | Error handling | ✅ OK - Returns {} on errors |
| DEC-001 | Financial | Decimal for money | ✅ OK - Uses Decimal for financial values |

---

## Dependencies
- **External:** logging, decimal, pathlib, typing, yaml
- **Internal:** None (core module)

---

## Required Tests
- **tests/unit/core/config/test_strategy_config_loader.py:**
  - Test get_indicator_config loads YAML
  - Test get_rsi_period returns correct values
  - Test get_rsi_threshold returns thresholds
  - Test get_ma_period returns periods
  - Test get_atr_multiplier returns multipliers
  - Test get_position_sizing returns Decimal
  - Test get_stop_loss returns Decimal
  - Test get_take_profit returns Decimal
  - Test get_tier_from_capital classifies correctly
  - Test get_tier_config_value accesses nested values
  - Test cache improves performance
  - Test reload_config clears cache
  - Test singleton pattern works
  - Test errors return empty dict (not raise)

---

## Notes
- **Financial Precision:** Uses Decimal for all monetary values
- **Default Handling:** All get methods have sensible defaults
- **Cache:** Improves performance by caching YAML files
- **Error Handling:** Returns {} on file errors (fail-safe)
- **Project Root:** Assumes project structure if config_dir not provided
---
