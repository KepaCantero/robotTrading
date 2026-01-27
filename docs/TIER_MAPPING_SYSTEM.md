# Tier Mapping System Documentation

## Overview

The algorithmic trading system uses **THREE different tier naming conventions** for capital classification. This document explains the tier mapping system that provides unified, consistent conversion between all three systems.

## The Three Tier Systems

### 1. InputProfile.capital_flag (English, 3 tiers)

**Location**: `/app/core/models/input_profile.py`

**Usage**: Used throughout the system for gating and feature access

**Tiers**:
- `"small"`: Capital < €50,000
- `"medium"`: Capital €50,000 - €250,000
- `"large"`: Capital >= €250,000

**Implementation**:
```python
@property
def capital_flag(self) -> str:
    """Flag capital as small, medium, or large for gating purposes."""
    if self.capital_initial < Decimal("50000"):
        return "small"
    elif self.capital_initial < Decimal("250000"):
        return "medium"
    else:
        return "large"
```

### 2. investment_profiles.yaml (English, 4 tiers)

**Location**: `/config/investment_profiles.yaml`

**Usage**: Strategy configuration based on capital tiers

**Tiers**:
- `"micro"`: Capital < €15,000
- `"small"`: Capital €15,000 - €50,000
- `"medium"`: Capital €50,000 - €250,000
- `"large"`: Capital >= €250,000

**Structure**:
```yaml
profiles:
  maximizar_capital:
    micro:  # < €15k
      risk_profile: 2
      leverage: 0
      enabled_modules:
        - momentum_modular
    small:  # €15k-€50k
      risk_profile: 3
      leverage: 0.5
      enabled_modules:
        - momentum_modular
        - mean_reversion_modular
    medium:  # €50k-€250k
      risk_profile: 4
      leverage: 1.5
      enabled_modules:
        - momentum_modular
        - mean_reversion_modular
        - pairs_trading_modular
    large:  # >= €250k
      risk_profile: 6
      leverage: 2.5
      enabled_modules:
        - momentum_modular
        - mean_reversion_modular
        - pairs_trading_modular
        - dividend_screener
        - portfolio_optimization
        - ml_ensemble
```

### 3. Config Expectations (Spanish, 3 tiers)

**Location**: Various config files (e.g., `profile_batch_backtest.yaml`)

**Usage**: Database lookups, configuration keys

**Tiers**:
- `"bajo"` (low): Capital < €50,000
- `"medio"` (medium): Capital €50,000 - €250,000
- `"alto"` (high): Capital >= €250,000

## Mapping Relationships

### Visual Mapping

```
Capital Amount → YAML Tier → Capital Flag → Spanish Tier
─────────────────────────────────────────────────────────
€0 - €14,999    → "micro"    → "small"      → "bajo"
€15,000 - €49,999 → "small"  → "small"      → "bajo"
€50,000 - €249,999 → "medium" → "medium"    → "medio"
€250,000+       → "large"    → "large"      → "alto"
```

### Key Differences

1. **Micro Tier Gap**: `InputProfile.capital_flag` doesn't have a "micro" tier
   - Capital < €15k returns "small" in capital_flag
   - But maps to "micro" in investment_profiles.yaml
   - Both map to "bajo" in Spanish

2. **Tier Boundaries**:
   - capital_flag and Spanish use €50k boundary
   - YAML uses €15k and €50k boundaries

## Unified Tier Mapper

**Location**: `/app/core/tier_mapper.py`

The `TierMapper` class provides centralized tier mapping between all three systems.

### Key Functions

#### `get_tier(capital, system=YAML)`

Get tier from capital amount for a specific system.

```python
from app.core.tier_mapper import get_tier, TierSystem
from decimal import Decimal

# Get YAML tier (default)
tier = get_tier(Decimal("100000"))  # Returns "medium"

# Get Spanish tier
tier = get_tier(Decimal("100000"), TierSystem.SPANISH)  # Returns "medio"

# Get capital_flag tier
tier = get_tier(Decimal("100000"), TierSystem.CAPITAL_FLAG)  # Returns "medium"
```

#### `normalize_tier(tier, target_system=YAML)`

Normalize a tier name to a specific system (auto-detects source).

```python
from app.core.tier_mapper import normalize_tier, TierSystem

# Convert Spanish to YAML
yaml_tier = normalize_tier("bajo")  # Returns "small"

# Convert capital_flag to Spanish
spanish_tier = normalize_tier("small", TierSystem.SPANISH)  # Returns "bajo"
```

#### `map_profile_tier_to_config(capital_flag, target_format)`

Convert from InputProfile.capital_flag to config format.

```python
from app.core.tier_mapper import map_profile_tier_to_config

# For config lookups in Spanish
spanish_key = map_profile_tier_to_config("small", "spanish")  # Returns "bajo"

# For YAML config lookups
yaml_key = map_profile_tier_to_config("medium", "yaml")  # Returns "medium"
```

### TierMapper Class Methods

#### `get_tier_from_capital(capital)`

Determine tier from capital using 4-tier YAML system.

```python
from app.core.tier_mapper import TierMapper
from decimal import Decimal

tier = TierMapper.get_tier_from_capital(Decimal("30000"))  # Returns "small"
```

#### `get_capital_flag_tier(capital)`

Determine tier using InputProfile.capital_flag logic (3-tier system).

```python
tier = TierMapper.get_capital_flag_tier(Decimal("30000"))  # Returns "small"
```

#### `to_yaml_tier(tier, source_system=None)`

Convert tier to YAML format.

```python
yaml_tier = TierMapper.to_yaml_tier("bajo", TierSystem.SPANISH)  # Returns "small"
```

#### `to_spanish(tier, source_system=None)`

Convert tier to Spanish format.

```python
spanish_tier = TierMapper.to_spanish("small", TierSystem.CAPITAL_FLAG)  # Returns "bajo"
```

#### `to_capital_flag(tier, source_system=None)`

Convert tier to capital_flag format.

```python
flag = TierMapper.to_capital_flag("micro", TierSystem.YAML)  # Returns "small"
```

#### `detect_system(tier)`

Auto-detect which tier system a tier name belongs to.

```python
system = TierMapper.detect_system("bajo")  # Returns TierSystem.SPANISH
system = TierMapper.detect_system("micro")  # Returns TierSystem.YAML
system = TierMapper.detect_system("small")  # Returns TierSystem.CAPITAL_FLAG
```

#### `is_valid_tier(tier, system=None)`

Check if a tier name is valid.

```python
is_valid = TierMapper.is_valid_tier("bajo")  # True
is_valid = TierMapper.is_valid_tier("invalid")  # False
```

## Usage Examples

### Example 1: ProfileBatchBacktester

**File**: `/app/backtesting/profile_batch_backtester.py`

```python
from app.core.tier_mapper import map_profile_tier_to_config

class ProfileBatchBacktester:
    def _get_capital_tier_key(self, profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key.

        The InputProfile.capital_flag returns 'small', 'medium', 'large'
        but config expects 'bajo', 'medio', 'alto'.
        """
        return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
```

### Example 2: ProfileStrategyMapper

**File**: `/app/services/profile_driven_trading/profile_strategy_mapper.py`

```python
from app.core.tier_mapper import TierMapper, get_tier

def get_capital_tier(capital: Decimal) -> str:
    """
    Determine capital tier from capital amount.

    Uses the centralized TierMapper for consistency.
    """
    return TierMapper.get_tier_from_capital(capital)
```

### Example 3: Direct Usage

```python
from app.core.tier_mapper import (
    TierMapper,
    get_tier,
    normalize_tier,
    map_profile_tier_to_config,
)
from decimal import Decimal

# Scenario 1: Convert capital amount to all tier systems
capital = Decimal("100000")
yaml_tier = get_tier(capital, TierSystem.YAML)  # "medium"
spanish_tier = get_tier(capital, TierSystem.SPANISH)  # "medio"
flag_tier = get_tier(capital, TierSystem.CAPITAL_FLAG)  # "medium"

# Scenario 2: Normalize tier from unknown source
unknown_tier = "bajo"
yaml_tier = normalize_tier(unknown_tier)  # "small"

# Scenario 3: Convert between specific systems
spanish = TierMapper.to_spanish("medium", TierSystem.CAPITAL_FLAG)  # "medio"
yaml = TierMapper.to_yaml_tier("bajo", TierSystem.SPANISH)  # "small"

# Scenario 4: Validate tier
is_valid = TierMapper.is_valid_tier("bajo")  # True
system = TierMapper.detect_system("bajo")  # TierSystem.SPANISH

# Scenario 5: ProfileBatchBacktester usage
capital_flag = "small"  # From InputProfile.capital_flag
config_key = map_profile_tier_to_config(capital_flag, "spanish")  # "bajo"
```

## Validation and Consistency

### Automatic Validation

The tier mapper automatically validates consistency on module import:

```python
# Runs automatically when module is imported
is_valid, warnings = validate_tier_mapping()
```

### Manual Validation

You can manually validate tier mapping consistency:

```python
from app.core.tier_mapper import TierMapper

is_valid, warnings = TierMapper.validate_consistency()

if not is_valid:
    for warning in warnings:
        print(warning)
```

### What Gets Validated

1. **Bidirectional mappings**: Ensures mappings work in both directions
2. **Capital thresholds**: Ensures thresholds are in ascending order
3. **Tier coverage**: Ensures all tiers can be converted between systems

## Edge Cases and Special Handling

### Micro Tier Handling

The "micro" tier in YAML doesn't exist in capital_flag:

```python
# Capital < €15k
yaml_tier = "micro"
capital_flag = TierMapper.to_capital_flag(yaml_tier, TierSystem.YAML)  # Returns "small"
spanish = TierMapper.to_spanish(yaml_tier, TierSystem.YAML)  # Returns "bajo"
```

### Boundary Values

Tier boundaries are inclusive of the lower bound and exclusive of the upper bound:

```python
# €15,000 exactly
TierMapper.get_tier_from_capital(Decimal("15000"))  # Returns "small" (not micro)

# €50,000 exactly
TierMapper.get_tier_from_capital(Decimal("50000"))  # Returns "medium" (not small)

# €250,000 exactly
TierMapper.get_tier_from_capital(Decimal("250000"))  # Returns "large" (not medium)
```

### Zero and Negative Capital

```python
# Zero or negative capital maps to lowest tier
TierMapper.get_tier_from_capital(Decimal("0"))  # Returns "micro"
TierMapper.get_tier_from_capital(Decimal("-1000"))  # Returns "micro"
```

## Testing

Comprehensive unit tests are available at:

**File**: `/tests/unit/core/test_tier_mapper.py`

Run tests:

```bash
pytest tests/unit/core/test_tier_mapper.py -v
```

Test coverage includes:
- Tier determination from capital amounts
- Conversion between all tier systems
- Boundary value testing
- Edge case handling
- Bidirectional mapping consistency
- Integration scenarios

## Migration Guide

### For Existing Code

If you have existing code that manually maps tiers:

**Before**:
```python
def _get_capital_tier_key(profile: InputProfile) -> str:
    tier_map = {
        "small": "bajo",
        "medium": "medio",
        "large": "alto"
    }
    return tier_map.get(profile.capital_flag, "medio")
```

**After**:
```python
from app.core.tier_mapper import map_profile_tier_to_config

def _get_capital_tier_key(self, profile: InputProfile) -> str:
    return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
```

### For New Code

Use the tier mapper for all tier conversions:

```python
from app.core.tier_mapper import (
    TierMapper,
    get_tier,
    normalize_tier,
    map_profile_tier_to_config,
)

# Choose the appropriate function for your use case
```

## Troubleshooting

### Common Issues

**Issue**: Tier not recognized

```python
# Error: ValueError: Tier 'invalid' not recognized
TierMapper.detect_system("invalid")

# Solution: Check valid tiers
TierMapper.list_all_valid_tiers()
```

**Issue**: Unexpected tier mapping

```python
# Why does "micro" map to "small"?
# Because capital_flag doesn't have a "micro" tier
# Both "micro" and "small" in YAML map to "small" in capital_flag

# Solution: Use the appropriate tier system for your use case
```

**Issue**: Import errors

```python
# Error: ModuleNotFoundError: No module named 'app.core.tier_mapper'

# Solution: Check that tier_mapper.py exists in app/core/
# and that Python path includes the project root
```

## Best Practices

1. **Always use the tier mapper** for tier conversions
2. **Validate tiers** before using them in config lookups
3. **Handle edge cases** (micro tier, boundary values)
4. **Log warnings** when tier mapper fails and fallback to manual mapping
5. **Run validation** periodically to ensure consistency

## Future Improvements

Potential enhancements to the tier mapping system:

1. **Custom tier mappings**: Allow users to define custom tier boundaries
2. **Tier migration tool**: Automatically migrate old configs to new tier system
3. **Tier analytics**: Track which tiers are most commonly used
4. **Performance optimization**: Cache tier mappings for faster lookups
5. **Tier validation middleware**: Auto-validate tiers in API endpoints

## References

- **InputProfile**: `/app/core/models/input_profile.py`
- **Tier Mapper**: `/app/core/tier_mapper.py`
- **Unit Tests**: `/tests/unit/core/test_tier_mapper.py`
- **YAML Config**: `/config/investment_profiles.yaml`
- **Batch Backtester**: `/app/backtesting/profile_batch_backtester.py`
- **Strategy Mapper**: `/app/services/profile_driven_trading/profile_strategy_mapper.py`

## Changelog

### Version 1.0.0 (2026-01-26)

- Initial implementation of unified tier mapping system
- Support for 3 tier systems: capital_flag, YAML, Spanish
- Comprehensive validation and consistency checking
- Full unit test coverage
- Integration with ProfileBatchBacktester and ProfileStrategyMapper
