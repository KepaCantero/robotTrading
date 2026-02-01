# demo.py

## Purpose
Demonstration script showcasing the vectorization verification module features: code auditing, benchmarking, and pattern library.

---

## Type Definitions / Data Classes

This module contains no dataclasses - it's a demo script with void functions.

---

## Function Signatures (Contracts)

### `demo_code_auditing() -> None`
**Pre:** VectorizationAuditor is importable
**Post:** Prints code auditing demonstration to stdout
**Raises:** Exception if auditing fails
**Retry:** No
**Side Effects:** Prints to stdout

### `demo_benchmarking() -> None`
**Pre:** VectorizationBenchmark is importable
**Post:** Prints benchmarking demonstration to stdout
**Raises:** Exception if benchmarking fails
**Retry:** No
**Side Effects:** Prints to stdout

### `demo_patterns() -> None`
**Pre:** VectorizationPatterns is importable
**Post:** Prints pattern library demonstration to stdout
**Raises:** Exception if pattern retrieval fails
**Retry:** No
**Side Effects:** Prints to stdout

### `main() -> None`
**Pre:** All demo functions are callable
**Post:** Runs all three demonstrations sequentially
**Raises:** Exception with traceback if any demo fails
**Retry:** No
**Side Effects:** Prints all demonstrations to stdout

---

## Acceptance Criteria
- [ ] demo_code_auditing demonstrates issue detection in sample code
- [ ] demo_code_auditing shows vectorization score calculation
- [ ] demo_benchmarking runs at least 3 benchmark comparisons
- [ ] demo_benchmarking displays speedup calculations
- [ ] demo_patterns shows at least 3 vectorization patterns
- [ ] demo_patterns displays trading-specific examples
- [ ] main() runs all demos in sequence
- [ ] Error handling in main() prints traceback
- [ ] Sample code includes: for loops, .apply(), .iterrows()
- [ ] Output is formatted with section headers and separators

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-002 | BASE_RULES | Modern syntax | ✅ OK - Uses -> None return types |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear demo function names |
| CC-007 | BASE_RULES | Small functions | ✅ OK - Each demo focused on one feature |
| LOG-001 | BASE_RULES | Structured logging | ⚠️ NOT APPLIED - Uses print for demo output |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Presentation layer (demo) |

---

## Dependencies
- **External:** sys, pathlib, traceback
- **Internal:** app.analysis.vectorization.benchmark.VectorizationBenchmark, app.analysis.vectorization.patterns.VectorizationPatterns, app.analysis.vectorization.vectorization_auditor.VectorizationAuditor

---

## Required Tests
- **test_demo.py:**
  - Test demo_code_auditing runs without exception (success path)
  - Test demo_benchmarking runs without exception (success path)
  - Test demo_patterns runs without exception (success path)
  - Test main() runs all demos (success path)
  - Test main() handles exceptions gracefully (error path)
  - Verify sample code contains expected anti-patterns (success path)
  - Verify output contains key takeaways (success path)

---

## Notes
This is a demonstration script for development/education purposes. Not used in production.
Adds project_root to sys.path for imports when run as standalone script.
