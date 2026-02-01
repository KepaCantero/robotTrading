# vectorization_auditor.py

## Purpose
Audit Python code for non-vectorized patterns using AST analysis, detecting problematic loops and operations that impact performance in numerical trading systems.

---

## Type Definitions / Data Classes

### VectorizationIssue (imported from models.py)
```python
@dataclass(frozen=True)
class VectorizationIssue:
    file_path: str                      # REQUIRED - Path to file with issue
    line_number: int                    # REQUIRED - Line number of issue
    issue_type: str                     # REQUIRED - Type of issue
    severity: str                       # REQUIRED - "critical", "high", "medium", "low"
    description: str                    # REQUIRED - Issue description
    suggestion: str                     # REQUIRED - Fix suggestion
    vectorized_alternative: str         # REQUIRED - Code showing fix
    code_snippet: str | None            # OPTIONAL - Problematic code
    context_lines: dict[str, Any] | None # OPTIONAL - Context
```

### VectorizationReport (imported from models.py)
```python
@dataclass
class VectorizationReport:
    total_files_scanned: int            # REQUIRED - Number of files scanned
    total_issues_found: int             # REQUIRED - Total issues found
    issues_by_type: dict[str, int]      # REQUIRED - Issue counts by type
    issues_by_severity: dict[str, int]  # REQUIRED - Issue counts by severity
    issues: list[VectorizationIssue]    # REQUIRED - All issues
    vectorization_score: Decimal        # REQUIRED - Score 0-100
    recommendations: list[str]          # REQUIRED - Recommendations
    scan_duration: float                # OPTIONAL - Scan time (default: 0.0)
    files_with_issues: int              # OPTIONAL - Files with issues (default: 0)
    top_offenders: list[tuple[str, int]] # OPTIONAL - Top offending files
```

---

## Function Signatures (Contracts)

### `__init__(exclude_dirs: set[str] | None = None, file_patterns: list[str] | None = None, verbose: bool = False) -> VectorizationAuditor`
**Pre:** None
**Post:** Auditor initialized with exclude dirs and file patterns
**Raises:** None
**Retry:** No
**Side Effects:** Sets up VectorizationPatterns instance

### `audit_file(file_path: str | Path) -> list[VectorizationIssue]`
**Pre:** file_path exists and is readable
**Post:** Returns list of VectorizationIssue objects found
**Raises:** FileNotFoundError if file doesn't exist; SyntaxError if invalid syntax
**Retry:** No
**Side Effects:** Reads and parses file with AST

### `audit_directory(directory: str | Path, pattern: str = "*.py", recursive: bool = True) -> VectorizationReport`
**Pre:** directory exists
**Post:** Returns VectorizationReport with all findings
**Raises:** FileNotFoundError if directory doesn't exist
**Retry:** No
**Side Effects:** Scans all matching Python files

### `calculate_score(issues: list[VectorizationIssue]) -> Decimal`
**Pre:** None
**Post:** Returns score 0-100: 100 - (critical × 10) - (high × 5) - (medium × 2) - (low × 1)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `audit_code_snippet(code: str, filename: str = "<snippet>") -> list[VectorizationIssue]`
**Pre:** code is valid Python string
**Post:** Returns list of VectorizationIssue objects
**Raises:** SyntaxError if code has invalid syntax
**Retry:** No
**Side Effects:** None

### `_check_for_loops(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for problematic for loops
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_apply_usage(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for .apply() usage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_iterrows(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for .iterrows()/.itertuples() usage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_list_comprehensions(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for numerical list comprehensions
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_enumerate_loops(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for enumerate() loops
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_range_len_loops(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for range(len()) patterns
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_while_loops(tree: ast.AST, file_path: str, source_code: str) -> list[VectorizationIssue]`
**Pre:** tree is valid AST
**Post:** Returns list of issues for numerical while loops
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_generate_recommendations(issues: list[VectorizationIssue]) -> list[str]`
**Pre:** None
**Post:** Returns list of actionable recommendations
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AST parsing handles valid Python syntax correctly
- [ ] audit_file raises FileNotFoundError for non-existent files
- [ ] audit_file raises SyntaxError for invalid syntax
- [ ] audit_directory excludes directories in DEFAULT_EXCLUDE_DIRS
- [ ] All check methods detect their specific patterns
- [ ] Severity levels are assigned appropriately (iterrows=critical, apply=high, etc.)
- [ ] Score calculation prevents negative scores (clamped to 0)
- [ ] Recommendations are generated based on issue types and counts
- [ ] Top offenders are sorted by issue count descending
- [ ] Issues include line numbers from AST
- [ ] Vectorized alternatives are provided for each issue

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-001 | BASE_RULES | Use vectorized operations | ✅ OK - Auditor enforces this |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Raises specific exceptions |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Error logging with stack traces | ⚠️ PARTIAL - No error logging |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear method names |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Analysis layer, no infrastructure deps |

---

## Dependencies
- **External:** ast, time, dataclasses, decimal, pathlib, typing
- **Internal:** 
  - app.analysis.vectorization.models.VectorizationIssue, VectorizationReport
  - app.analysis.vectorization.patterns.VectorizationPatterns

---

## Required Tests
- **tests/unit/analysis/test_vectorization_auditor.py:**
  - Test audit_file with vectorized code (no issues)
  - Test audit_file with for loop (detects issue)
  - Test audit_file with .apply() usage (detects issue)
  - Test audit_file with .iterrows() usage (detects critical issue)
  - Test audit_file with range(len()) pattern (detects issue)
  - Test audit_file with enumerate loop (detects issue)
  - Test audit_file with while loop (detects issue)
  - Test audit_file with list comprehension (detects issue)
  - Test audit_file non-existent (raises FileNotFoundError)
  - Test audit_file invalid syntax (raises SyntaxError)
  - Test audit_directory recursive scanning
  - Test audit_directory with exclude_dirs
  - Test calculate_score with no issues (returns 100)
  - Test calculate_score with mixed issues (correct penalty)
  - Test audit_code_snippet with valid code
  - Test audit_code_snippet with invalid syntax (raises SyntaxError)
  - Test recommendations generation
  - Test top offenders sorting

---

## Notes
- Uses AST (Abstract Syntax Tree) analysis, doesn't execute code
- DEFAULT_EXCLUDE_DIRS includes: __pycache__, .git, venv, tests, migrations, etc.
- Issue types: for_loop, list_comp, apply, iterrows, itertuples, enumerate, range_len, while_loop, nested_loop
- Severity: iterrows=critical, apply=high, range_len=high, others vary by context
- Score formula: 100 - (critical × 10) - (high × 5) - (medium × 2) - (low × 1)
