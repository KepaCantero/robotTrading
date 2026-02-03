# models.py

## Purpose
Define data models for vectorization verification, including issues, reports, and benchmark results.

---

## Type Definitions / Data Classes

### VectorizationIssue Class/DataClass
```python
@dataclass(frozen=True)
class VectorizationIssue:
    file_path: str                      # REQUIRED - Path to file with issue
    line_number: int                    # REQUIRED - Line number of issue
    issue_type: str                     # REQUIRED - Type: "for_loop", "apply", "iterrows", etc.
    severity: str                       # REQUIRED - "critical", "high", "medium", "low"
    description: str                    # REQUIRED - Human-readable description
    suggestion: str                     # REQUIRED - Fix suggestion
    vectorized_alternative: str         # REQUIRED - Code snippet showing fix
    code_snippet: str | None            # OPTIONAL - Problematic code
    context_lines: dict[str, Any] | None # OPTIONAL - Surrounding context
```

**Validation Rules:**
- severity must be one of: "critical", "high", "medium", "low"
- issue_type must be one of: "for_loop", "list_comp", "apply", "iterrows", "itertuples", "enumerate", "range_len", "while_loop", "nested_loop"
- __post_init__ raises ValueError for invalid severity or issue_type

### VectorizationReport Class/DataClass
```python
@dataclass
class VectorizationReport:
    total_files_scanned: int            # REQUIRED - Number of files scanned
    total_issues_found: int             # REQUIRED - Total issues found
    issues_by_type: dict[str, int]      # REQUIRED - Issue counts by type
    issues_by_severity: dict[str, int]  # REQUIRED - Issue counts by severity
    issues: list[VectorizationIssue]    # REQUIRED - All issues found
    vectorization_score: Decimal        # REQUIRED - Score 0-100 (higher is better)
    recommendations: list[str]          # REQUIRED - Actionable recommendations
    scan_duration: float                # OPTIONAL - Scan time in seconds (default: 0.0)
    files_with_issues: int              # OPTIONAL - Files with issues (default: 0)
    top_offenders: list[tuple[str, int]] # OPTIONAL - Files with most issues (default: [])
```

**Validation Rules:**
- total_files_scanned >= 0
- total_issues_found >= 0
- vectorization_score in [0, 100]
- files_with_issues <= total_files_scanned

### BenchmarkResult Class/DataClass
```python
@dataclass
class BenchmarkResult:
    function_name: str                      # REQUIRED - Name of benchmarked function
    vectorized_time: float                  # REQUIRED - Vectorized execution time (seconds)
    non_vectorized_time: float              # REQUIRED - Non-vectorized execution time (seconds)
    speedup: float                          # REQUIRED - Speedup factor
    n_elements: int                         # REQUIRED - Number of elements processed
    per_element_time_vectorized: float      # REQUIRED - Time per element vectorized (ns)
    per_element_time_non_vectorized: float  # REQUIRED - Time per element non-vectorized (ns)
    memory_usage_vectorized: int | None     # OPTIONAL - Memory usage vectorized (bytes)
    memory_usage_non_vectorized: int | None # OPTIONAL - Memory usage non-vectorized (bytes)
    timestamp: float                        # REQUIRED - Benchmark timestamp
```

**Validation Rules:**
- vectorized_time > 0
- non_vectorized_time > 0
- n_elements > 0
- speedup is calculated if not provided (non_vectorized_time / vectorized_time)

### CodeSnippet Class/DataClass
```python
@dataclass
class CodeSnippet:
    code: str                          # REQUIRED - The code snippet
    line_start: int                    # REQUIRED - Starting line number
    line_end: int                      # REQUIRED - Ending line number
    file_path: str                     # REQUIRED - Source file path
    language: str                      # OPTIONAL - Programming language (default: "python")
```

**Validation Rules:**
- line_start <= line_end
- code is non-empty string

---

## Function Signatures (Contracts)

### `VectorizationIssue.get_severity_weight() -> int`
**Pre:** None
**Post:** Returns weight: critical=10, high=5, medium=2, low=1
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VectorizationIssue.get_display_summary() -> str`
**Pre:** None
**Post:** Returns formatted summary string "[SEVERITY] file:line - type: description"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VectorizationReport.get_grade() -> str`
**Pre:** None
**Post:** Returns letter grade: A (>=90), B (>=75), C (>=60), D (>=40), F (<40)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VectorizationReport.get_summary() -> str`
**Pre:** None
**Post:** Returns formatted summary string with score, files, issues
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VectorizationReport.get_top_issues(limit: int = 10) -> list[VectorizationIssue]`
**Pre:** limit > 0
**Post:** Returns top issues sorted by severity and type
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VectorizationReport.is_compliant(threshold: float = 80.0) -> bool`
**Pre:** threshold in [0, 100]
**Post:** Returns vectorization_score >= threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BenchmarkResult.get_summary() -> str`
**Pre:** None
**Post:** Returns formatted summary with timing and speedup
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BenchmarkResult.get_performance_grade() -> str`
**Pre:** None
**Post:** Returns grade: A+ (>=100x), A (>=50x), B (>=20x), C (>=10x), D (>=2x), F (<2x)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BenchmarkResult.is_significant_speedup(threshold: float = 2.0) -> bool`
**Pre:** threshold > 0
**Post:** Returns speedup >= threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BenchmarkResult.to_dict() -> dict[str, Any]`
**Pre:** None
**Post:** Returns dictionary representation of result
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CodeSnippet.get_relative_path(base_path: str) -> str`
**Pre:** base_path is valid directory path
**Post:** Returns file_path relative to base_path
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CodeSnippet.get_formatted_display() -> str`
**Pre:** None
**Post:** Returns code with line numbers formatted
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] VectorizationIssue validates severity and issue_type in __post_init__
- [ ] VectorizationReport grades follow standard thresholds (90, 75, 60, 40)
- [ ] BenchmarkResult validates positive times in __post_init__
- [ ] All dataclasses use frozen=True where appropriate (VectorizationIssue)
- [ ] Severity weights follow critical=10, high=5, medium=2, low=1
- [ ] Performance grades use meaningful speedup thresholds
- [ ] CodeSnippet formatting includes line numbers
- [ ] All methods have proper type hints
- [ ] Vectorization score is in [0, 100] range

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - VectorizationIssue is frozen |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All methods have type hints |
| TYP-005 | BASE_RULES | Class attribute types | ✅ OK - All attributes typed |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear field names |
| CC-007 | BASE_RULES | Small functions | ✅ OK - Methods are concise |

---

## Dependencies
- **External:** dataclasses, decimal, typing
- **Internal:** None

---

## Required Tests
- **tests/unit/analysis/test_vectorization_models.py:**
  - Test VectorizationIssue validation with valid data (success)
  - Test VectorizationIssue validation with invalid severity (raises ValueError)
  - Test VectorizationIssue validation with invalid issue_type (raises ValueError)
  - Test VectorizationIssue.get_severity_weight() for all severities
  - Test VectorizationIssue.get_display_summary() format
  - Test VectorizationReport.get_grade() threshold boundaries
  - Test VectorizationReport.get_summary() output format
  - Test VectorizationReport.get_top_issues() sorting
  - Test VectorizationReport.is_compliant() with various thresholds
  - Test BenchmarkResult validation with positive times (success)
  - Test BenchmarkResult validation with zero time (raises ValueError)
  - Test BenchmarkResult.get_summary() format
  - Test BenchmarkResult.get_performance_grade() thresholds
  - Test BenchmarkResult.is_significant_speedup() with various values
  - Test BenchmarkResult.to_dict() structure
  - Test CodeSnippet.get_relative_path()
  - Test CodeSnippet.get_formatted_display() line numbers

---

## Notes
- VectorizationIssue is frozen (immutable) to prevent accidental modification
- Vectorization score calculation: 100 - (critical × 10) - (high × 5) - (medium × 2) - (low × 1)
- Performance grades emphasize real-world speedup significance (2x minimum for D grade)
