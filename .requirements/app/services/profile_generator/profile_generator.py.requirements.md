# Requirements: services/profile_generator/profile_generator.py

## Source File Analysis
- **File Path**: `app/services/profile_generator/profile_generator.py`
- **Lines of Code:** 600
- **Status:** AUDIT COMPLETE

## Purpose
T2.1: ProfileGenerator - Maps user input to investment profiles using configuration templates, with MAESTRO PHASE 1 integration for absolute return optimization and feasibility validation.

## Dependencies
- Internal:
  - `app.maestro.phase_1.*` (AbsoluteReturnTarget, CapacityFadeAnalyzer, etc.)
  - `.models` (CapitalTier, InvestmentObjective, InvestmentProfile, etc.)
- External:
  - `logging`, `datetime`, `decimal`, `pathlib`, `typing`
  - `yaml`

## Classes/Functions

### Main Class: ProfileGenerator
- `__init__(config_path)`: Initialize with YAML config
- `_load_profile_templates()`: Load from investment_profiles.yaml
- `_get_default_templates()`: Get built-in default templates
- `generate(request)`: Generate investment profile
- `_determine_capital_tier(capital)`: Determine tier (micro/small/medium/large)
- `_get_profile_template(objective, tier)`: Get template from config
- `_create_profile_from_template(...)`: Create profile from template
- `_validate_profile(profile, request)`: Validate and return warnings
- `_integrate_maestro_phase_1(profile, request)`: Enhance with MAESTRO analysis
- `get_profile(profile_id)`: Get cached profile
- `get_generation_history(limit)`: Get history
- `get_generator_status()`: Get statistics

### Global Functions
- `get_profile_generator(config_path)`: Get singleton instance

## Business Logic
1. **Profile Generation**:
   - Capital tier classification (micro: <€25k, small: €25k-€100k, medium: €100k-€500k, large: >€500k)
   - Objective-aware module selection
   - Risk-aware parameter configuration

2. **MAESTRO PHASE 1 Integration**:
   - Required annual return from EUR targets
   - Required alpha with tax/cost consideration
   - Capacity fade adjusted alpha
   - Position sizing optimization
   - Feasibility validation

3. **Default Templates**:
   - maximizar_capital: Aggressive growth focus
   - maximizar_dividendos: Dividend/income focus
   - capital_preservation: Conservative preservation
   - balanced_growth: Balanced approach
   - income_generation: Yield focus

## Data Models
- InvestmentProfile: Complete profile with all parameters
- ProfileGenerationResult: success, profile, warnings, timing

## API Contracts
- ProfileGenerationRequest: input_id, capital, objective, risk, horizon, targets
- Returns ProfileGenerationResult with profile or error

## Error Handling
- Exception types: `(FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError)`
- Graceful fallback to default templates
- MAESTRO integration errors don't block generation

## Performance Considerations
- YAML loaded once at initialization
- Profile cache for quick retrieval
- Generation history tracked

## Testing Strategy
- Test profile generation for all objectives
- Test capital tier detection
- Test MAESTRO integration
- Test validation warnings
- Test fallback to defaults

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Excellent integration with MAESTRO PHASE 1

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Clear class and method names
- ✅ CC-002: Minimal duplication (DRY templates)
- ✅ CC-006: Explicit error handling
- ✅ LOG-004: Error logging with context
- ✅ LOG-006: Timing captured (generation_time_ms)
- ✅ CFG-002: YAML configuration (env via MAESTRO)
- ✅ DP-002: Factory pattern (get_profile_generator)
- ✅ ARCH-004: Functions mostly < 20 lines
- ✅ FMT-007: No mutable defaults (uses dataclasses)

**Minor Notes:**
- MAESTRO integration is comprehensive
- Default templates provide good fallback

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0078*
