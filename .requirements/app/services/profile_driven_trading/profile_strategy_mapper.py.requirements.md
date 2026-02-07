# Requirements: services/profile_driven_trading/profile_strategy_mapper.py

## Source File Analysis
- **File Path**: `app/services/profile_driven_trading/profile_strategy_mapper.py`
- **Lines of Code:** 746
- **Status:** AUDIT COMPLETE

## Purpose
ProfileStrategyMapper - Maps InputProfile to strategy combinations, learning engines, capital allocation, and ensemble configurations based on centralized configuration files.

## Dependencies
- Internal:
  - `app.core.centralized_config.get_config`
  - `app.core.models.input_profile.InputProfile`, `ObjectivoInversion`, `RiskTolerance`
  - `app.core.tier_mapper.TierMapper`
  - `app.services.multi_strategy_allocation.*`
- External:
  - `logging`, `decimal`, `pathlib`, `typing`
  - `yaml`
  - `pydantic`

## Classes/Functions

### Pydantic Model
- `StrategyMapping`: Complete trading configuration with validation

### Functions
- `get_capital_tier(capital)`: Determine capital tier using TierMapper
- `create_profile_mapper(...)`: Factory function
- `map_profile_to_strategies(profile)`: Convenience mapping function

### Main Class: ProfileStrategyMapper
- `__init__(...)`: Initialize with config paths
- `_load_yaml(path)`: Load YAML configuration
- `map_profile_to_strategies(profile)`: Map profile to strategy config
- `_get_profile_config(objective, capital_tier)`: Get config from YAML
- `get_capital_allocation(profile)`: Create allocation manager
- `_calculate_strategy_weights(strategies, profile_config, risk_tolerance)`: Calculate weights
- `get_learning_engines(profile)`: Get enabled ML engines
- `get_ensemble_config(profile)`: Get ensemble configuration
- `create_strategy_mapping(profile)`: Create complete mapping
- `get_learning_parameters(profile, engine_type)`: Get engine params
- `_deep_merge(base, override)`: Deep merge dicts

### Module-Level Data
- `CAPITAL_TIER_THRESHOLDS`: small: €15k, medium: €50k, large: €250k

## Business Logic
1. **Tier Mapping**: Uses centralized TierMapper for consistency
2. **Strategy Weights**: Risk-adjusted (conservative: balanced, aggressive: momentum focus)
3. **Learning Engines**: ML ensemble only for large capital
4. **Ensemble Modes**: voting_ensemble (conservative), weighted_ensemble (balanced), regime_selector (aggressive)
5. **Configuration**: From investment_profiles.yaml, learning_parameters.yaml, ensemble.yaml

## Data Models
- StrategyMapping (Pydantic): comprehensive trading configuration
- Risk-adjusted weights based on tolerance

## API Contracts
- InputProfile with capital, objective, risk tolerance, horizon
- Returns StrategyMapping with complete configuration

## Error Handling
- Exception types: `(FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError)`
- Falls back to default templates on config failure
- Falls back to manual tier calculation if TierMapper fails

## Performance Considerations
- YAML loading at initialization
- Configuration cached in memory

## Testing Strategy
- Test profile mapping for all objectives
- Test capital tier detection
- Test strategy weight calculation
- Test learning engine selection
- Test ensemble configuration

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Well-designed mapper with good fallback logic

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Descriptive names
- ✅ CC-002: Minimal duplication
- ✅ CC-006: Explicit error handling
- ✅ LOG-004: Error logging with context
- ✅ CFG-001: Configuration via YAML (Pydantic would be better)
- ✅ CFG-002: Environment variables (via TierMapper)
- ✅ DP-002: Factory pattern (create_profile_mapper)
- ✅ DP-004: Dependency injection (MultiStrategyAllocationManager)
- ✅ FMT-007: No mutable defaults (Pydantic handles this)
- ✅ SOL-004: Interface segregation (focused methods)

**Minor Notes:**
- YAML loading could use Pydantic for validation
- Fallback logic is well-implemented

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0078*
