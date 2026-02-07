# Requirements: services/deploy_decision_orchestrator/deploy_decision_orchestrator.py

## Source File Analysis
- **File Path**: `app/services/deploy_decision_orchestrator/deploy_decision_orchestrator.py`
- **Lines of Code**: 755
- **Status**: AUDIT COMPLETE

## Purpose
Master deployment decision orchestration. Synthesizes outputs from all services (BacktestOrchestrator, ValidationEngine, StrategyRecommender, PortfolioConstructor) to make final APPROVED/CONDITIONAL/REJECTED decision.

## Dependencies
- Internal:
  - `app.services.capacity_fade_validation` (CapacityFadeRequest, CapacityFadeValidator, FeasibilityDecision)
  - `.models` (DeploymentDecision, DeploymentInput, DeploymentRationale)
- External:
  - `logging`
  - `datetime` (datetime)
  - `decimal` (Decimal)
  - `typing`

## Classes/Functions

### Main Class
1. **DeployDecisionOrchestrator** (lines 29-741)
   - Purpose: Master orchestrator for deployment decisions

   **Constants:**
   - `FEASIBILITY_THRESHOLDS` (lines 42-46): approved=1.0, conditional=0.7, rejected=0
   - `RECOMMENDATION_THRESHOLDS` (lines 48-54): strong_buy=80, buy=65, hold=50, review=35, not_recommended=0
   - `CONFIDENCE_THRESHOLDS` (lines 56-60): high=75, medium=50, low=0

   **Public Methods:**
   - `__init__()` (lines 62-66): Initialize orchestrator with CapacityFadeValidator
   - `make_decision()` (lines 68-219): Main decision-making method with 8-step process
   - `get_decision_history()` (lines 709-717): Get historical decisions
   - `get_orchestrator_status()` (lines 719-740): Get operational status

   **Private Assessment Methods:**
   - `_assess_feasibility()` (lines 221-232): Score feasibility ratio
   - `_assess_validation()` (lines 234-247): Score validation results
   - `_assess_risk()` (lines 249-289): Score risk metrics (drawdown, sharpe, win rate)
   - `_assess_capacity_fade()` (lines 291-367): T4.1 capacity fade validation (CRITICAL - 40% weight)
   - `_calculate_overall_score()` (lines 369-418): Weighted score calculation
   - `_determine_status()` (lines 420-480): Determine deployment status and confidence
   - `_generate_rationale()` (lines 482-647): Generate detailed decision rationale
   - `_generate_recommendation_text()` (lines 649-677): Human-readable recommendation
   - `_determine_next_steps()` (lines 679-707): Recommended actions

### Factory Function
1. **get_deploy_orchestrator()** (lines 747-753): Singleton pattern

## Business Logic

### Decision Flow (8 Steps):
1. **HARD GATES**: Feasibility & Validation
2. **SOFT GATES**: Recommendation & Risk
3. **CAPACITY FADE**: T4.1 integration (40% weight)
4. **SYNTHESIS**: Combine scores into final decision

### Decision Thresholds:
- **APPROVED**: Overall score >= 80 (high confidence) or >= 60 (medium)
- **CONDITIONAL**: Score 45-79, or feasibility ratio 0.7-1.0
- **REJECTED**: Score < 45, failed validation, feasibility < 0.7, or capacity fade failed

### T4.1 Capacity Fade Integration:
- **CRITICAL**: 40% weight in overall score
- Hard gate: capacity_fade_feasible=False → automatic REJECTION
- Weights when available: CapacityFade 40%, Feasibility 25%, Validation 15%, Risk 12%, Recommendation 8%
- Weights when unavailable (backward compatible): Feasibility 42%, Validation 25%, Risk 20%, Recommendation 13%

## Data Models
Uses imported data models from `.models`:
- DeploymentDecision
- DeploymentInput
- DeploymentRationale

## API Contracts
No REST API - service layer module.

## Error Handling
- Exception handling in `make_decision()` (lines 191-219)
- Returns DeploymentDecision with success=False on error
- Comprehensive logging

## Performance Considerations
- Stateful: maintains decision_history list
- Singleton pattern for resource efficiency
- Decimal arithmetic for precision

## Testing Strategy
Recommended test coverage:
1. Decision threshold tests (approved/conditional/rejected boundaries)
2. T4.1 capacity fade integration tests
3. Edge cases: missing capital data, extreme values
4. Hard gate verification (validation, feasibility, capacity fade)

## Compliance with BASE_RULES.md

### PASSING Rules:
- ✅ **ARCH-001**: Layered architecture - service layer correctly positioned
- ✅ **CC-001**: Descriptive names - clear method and variable names
- ✅ **CC-006**: Explicit error handling - try/except with error logging
- ✅ **LOG-003**: Appropriate logging levels - info/error with emoji indicators
- ✅ **LOG-004**: Error logging - exceptions logged with context
- ✅ **TYP-001**: Type hints - comprehensive type coverage
- ✅ **DP-002**: Factory pattern - get_deploy_orchestrator() singleton
- ✅ **DP-004**: Dependency injection - CapacityFadeValidator injected

### GAPS IDENTIFIED:
None - Code quality is high. All BASE_RULES are satisfied.

## Audit Status: PASSED

**Audited By:** Claude (Backend Developer Agent)
**Audit Date:** 2026-02-07
**Batches:** 0098

### Summary
This module demonstrates excellent code quality:
- Clear decision-making logic with well-defined thresholds
- Proper T4.1 capacity fade integration (40% weight, hard gate)
- Comprehensive assessment of 5 factors
- Detailed rationale generation
- Backward compatibility when capacity data unavailable
- Good error handling with fallback to REJECTED
- Observability features (history, status)

No critical gaps found. Module is production-ready.

---
*Auto-generated on Thu Feb  5 20:33:01 CET 2026*
*Updated for GAP audit on 2026-02-07*
