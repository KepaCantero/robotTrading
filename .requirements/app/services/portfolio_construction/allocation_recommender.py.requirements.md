# Requirements: services/portfolio_construction/allocation_recommender.py

## Source File Analysis
- **File Path**: `app/services/portfolio_construction/allocation_recommender.py`
- **Lines of Code:** 356
- **Status:** AUDIT COMPLETE

## Purpose
T18.1.3: AllocationRecommender - Smart allocation recommendations based on risk profile, objectives, and market conditions with diversification scoring and confidence assessment.

## Dependencies
- Internal: None (standalone module)
- External:
  - `logging`, `dataclasses`, `decimal`, `typing`

## Classes/Functions

### Data Classes
- `AllocationRecommendation`: allocation, reasoning, confidence, metrics, scores

### Main Class: AllocationRecommender
- `__init__()`: Initialize with history
- `recommend_by_risk_profile(risk_profile, available_assets)`: Recommend by conservative/moderate/aggressive
- `recommend_by_objective(objective, available_assets)`: Recommend by growth/income/preservation/balanced
- `recommend_by_capital_tier(capital, available_assets)`: Recommend by capital size (micro/small/medium/large)
- `_conservative_allocation(assets)`: 40% stocks, 50% bonds, 10% alternatives
- `_moderate_allocation(assets)`: 60% stocks, 30% bonds, 10% alternatives
- `_aggressive_allocation(assets)`: 80% stocks, 10% bonds, 10% alternatives
- `_growth_allocation(assets)`: Heavy equity
- `_income_allocation(assets)`: Higher yield assets
- `_preservation_allocation(assets)`: Focus on stable assets
- `_balanced_allocation(assets)`: Equal-weight
- `_equal_allocation(assets)`: Equal weight
- `_sophisticated_allocation(assets)`: Optimized with caps
- `_calculate_diversification_score(allocation)`: Herfindahl index (0-100)
- `_assess_concentration_risk(allocation)`: low/medium/high based on max weight
- `get_recommendation_history(limit)`: Get historical recommendations
- `get_recommender_status()`: Get statistics

## Business Logic
1. **Risk-Based Allocation**:
   - Conservative: 40% stocks, 50% bonds, 10% alternatives (4% expected return)
   - Moderate: 60% stocks, 30% bonds, 10% alternatives (7% expected return)
   - Aggressive: 80% stocks, 10% bonds, 10% alternatives (10% expected return)

2. **Objective-Based Allocation**:
   - Growth: Maximize capital appreciation
   - Income: Focus on yield-generating assets
   - Preservation: Protect capital with conservative positioning
   - Balanced: Equal growth and income

3. **Capital Tier Allocation**:
   - Micro (<€10k): Simple equal-weight
   - Small (€10k-€100k): Conservative
   - Medium (€100k-€500k): Balanced with good diversification
   - Large (€500k+): Sophisticated with full diversification

4. **Diversification**:
   - Herfindahl index: sum of squared weights
   - Score: (1 - Herfindahl) * 100
   - Concentration: low (<25%), medium (25-40%), high (>40%)

## Data Models
- Uses Decimal for all financial calculations
- AllocationRecommendation with comprehensive metrics

## API Contracts
- All recommend methods return AllocationRecommendation
- Async interface for future extensibility

## Error Handling
- No explicit exception handling (simple calculations)
- Returns default allocations for invalid inputs

## Performance Considerations
- Simple calculations (O(n) where n = number of assets)
- History tracking for recommendations

## Testing Strategy
- Test each risk profile allocation
- Test objective-based allocations
- Test capital tier allocations
- Test diversification score calculation
- Test concentration risk assessment

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Clean recommendation engine

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Descriptive method names
- ✅ CC-003: Simple, straightforward logic
- ✅ FMT-007: No mutable defaults
- ✅ LOG-003: Appropriate log levels
- ✅ ARCH-004: Functions mostly < 20 lines

**Minor Notes:**
- String matching for asset types (BOND, DIVIDEND, CASH) is simplistic but functional
- All allocation methods normalize to sum=1.0

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0077*
