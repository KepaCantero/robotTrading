# multi_objective.py

## Purpose
 file for multi objective

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### ParetoSolution
**Purpose:** A solution on the Pareto front.

Represents a non-dominated solution in multi-objective optimization...
### ParetoFront
**Purpose:** Pareto front of non-dominated solutions.

Contains all non-dominated solutions from multi-objective ...
### MultiObjectiveOptimizer
**Purpose:** Multi-objective optimizer using Pareto dominance.

Finds Pareto front of non-dominated solutions.
Us...
### ScalarizationOptimizer
**Purpose:** Multi-objective optimizer using scalarization.

Converts multi-objective problem to single-objective...

---

## Function Signatures (Contracts)

### `ParetoSolution.dominates(self, other) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoSolution.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.calculate_crowding_distance(self, front) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.get_pareto_front(self) -> List[ParetoSolution]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.get_best_by_objective(self, objective_index) -> Optional[ParetoSolution]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.get_best_by_weighted_criteria(self, weights) -> Optional[ParetoSolution]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.get_knee_point(self) -> Optional[ParetoSolution]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.get_diverse_solutions(self, n_solutions, use_crowding) -> List[ParetoSolution]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ParetoFront.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ScalarizationOptimizer.scalarize(self, objectives, ideal_point) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `find_non_dominated_solutions(solutions) -> List[Tuple[Dict[str, Any], Tuple[float, ...]]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `calculate_hypervolume(front, reference_point) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD


---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_multi_objective.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/optimization/parameter/multi_objective.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
