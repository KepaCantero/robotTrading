# Vectorization Verification Module

**Brecha #4 - ALTA Prioridad** (High Performance)

## Overview

The Vectorization Verification module provides comprehensive tools for auditing and benchmarking vectorized code to ensure high-performance numerical computing in algorithmic trading systems.

## Features

### 1. VectorizationAuditor

Audit Python code for non-vectorized patterns that can significantly impact performance:

```python
from app.analysis.vectorization import VectorizationAuditor

auditor = VectorizationAuditor()

# Audit a file
issues = auditor.audit_file("path/to/code.py")

# Audit a directory
report = auditor.audit_directory("app/strategies")
print(report.get_summary())

# Audit a code snippet
code = """
for i in range(len(array)):
    result[i] = array[i] * 2
"""
issues = auditor.audit_code_snippet(code)
```

**Detected Patterns:**
- `for` loops with array indexing
- `range(len(array))` patterns
- `.apply()` on DataFrames/Series
- `.iterrows()` and `.itertuples()` usage
- List comprehensions with numerical operations
- `enumerate()` loops
- `while` loops with numerical operations

### 2. VectorizationBenchmark

Benchmark vectorized vs non-vectorized implementations:

```python
from app.analysis.vectorization import VectorizationBenchmark

benchmark = VectorizationBenchmark()

# Run individual benchmarks
result = benchmark.benchmark_sum(n_elements=1_000_000)
print(result.get_summary())
# Output:
# Benchmark: array_sum
#   Elements: 1,000,000
#   Vectorized: 0.0213ms
#   Non-Vectorized: 78.44ms
#   Speedup: 368.84x

# Run all benchmarks
results = benchmark.run_all_benchmarks()
report = benchmark.generate_report(results)
print(report)
```

**Available Benchmarks:**
- Array sum
- Exponentially weighted mean (EWM)
- Rolling calculations
- Correlation matrix
- Element-wise operations
- Boolean filtering
- Group-by aggregation
- Percentage change

### 3. VectorizationPatterns

Library of common anti-patterns and vectorized alternatives:

```python
from app.analysis.vectorization import VectorizationPatterns

# Get specific pattern
pattern = VectorizationPatterns.elementwise_operation()
print(pattern)

# Get all patterns
all_patterns = VectorizationPatterns.get_all_patterns()

# Get trading-specific examples
trading_examples = VectorizationPatterns.get_trading_specific_examples()
```

**Pattern Categories:**
- Element-wise operations
- Filtering with conditions
- Rolling window calculations
- Group-by aggregations
- Correlation matrices
- Conditional assignment
- Exponential weighted operations
- Percentage change
- Cumulative operations
- Shift/lag operations
- Ranking/percentiles
- Distance matrices
- Interpolation
- And more...

## Scoring System

The auditor calculates a vectorization score from 0-100:

```
Score = 100 - (critical × 10) - (high × 5) - (medium × 2) - (low × 1)
```

**Grade Scale:**
- A: 90-100 (Excellent)
- B: 75-89 (Good)
- C: 60-74 (Fair)
- D: 40-59 (Poor)
- F: 0-39 (Failing)

## Installation

The module is part of the AlgoTrading project. No additional installation required.

```bash
# Run tests
pytest app/tests/analysis/test_vectorization.py -v

# Run demo
python app/analysis/vectorization/demo.py
```

## File Structure

```
app/analysis/vectorization/
├── __init__.py                 # Module exports
├── models.py                   # Data models (Issue, Report, BenchmarkResult)
├── vectorization_auditor.py    # Code auditing functionality
├── benchmark.py                # Benchmarking utilities
├── patterns.py                 # Pattern library
├── demo.py                     # Demo script
└── README.md                   # This file
```

## Usage Examples

### Example 1: Audit a Strategy File

```python
from app.analysis.vectorization import VectorizationAuditor

auditor = VectorizationAuditor()
report = auditor.audit_directory("app/strategies/momentum_modular")

print(f"Score: {report.vectorization_score}/100 ({report.get_grade()})")
print(f"Issues found: {report.total_issues_found}")
print(f"Files scanned: {report.total_files_scanned}")

# View top issues
for issue in report.get_top_issues(5):
    print(f"  {issue.get_display_summary()}")
```

### Example 2: Run Performance Benchmarks

```python
from app.analysis.vectorization import VectorizationBenchmark

benchmark = VectorizationBenchmark()

# Benchmark specific operations relevant to trading
results = [
    benchmark.benchmark_rolling_calculation(n_elements=50_000, window=20),
    benchmark.benchmark_ewm_calculate(n_elements=100_000, span=20),
    benchmark.benchmark_correlation(n_elements=5_000, n_assets=100),
]

for result in results:
    print(f"{result.function_name}: {result.speedup:.1f}x speedup")
```

### Example 3: Get Vectorization Suggestions

```python
from app.analysis.vectorization import VectorizationPatterns

# Get pattern for specific issue
suggestion = VectorizationPatterns.get_suggestion_for_issue("iterrows")
print(suggestion)
# Shows how to replace .iterrows() with vectorized operations

# Get trading-specific examples
examples = VectorizationPatterns.get_trading_specific_examples()
print(examples["bollinger_bands"])
# Shows vectorized Bollinger Bands calculation
```

## Test Coverage

The module has comprehensive test coverage with 83 tests covering:

- Data model validation
- AST-based code detection
- Benchmark accuracy
- Pattern library completeness
- Integration workflows
- Edge cases and error handling

```bash
pytest app/tests/analysis/test_vectorization.py -v
# 83 passed, 1 warning
```

## Performance Impact

Typical speedups from vectorization:

| Operation | Speedup |
|-----------|---------|
| Array sum | 100-400x |
| Rolling mean | 500-2000x |
| Element-wise ops | 100-500x |
| Correlation matrix | 500-2000x |
| Group-by aggregation | 50-200x |
| EWM calculation | 100-300x |

## Key Rules Enforced

1. **No for loops for numerical calculations** - Use NumPy vectorized operations
2. **No .apply() on DataFrames** - Use vectorized operations instead
3. **No .iterrows()** - Extremely slow, use .values or vectorized ops
4. **No list comprehensions for numerical work** - Use NumPy arrays
5. **Use numba JIT for critical loops** - When vectorization isn't possible

## Integration with AUDIT_PLAN_COMPLETO

This module addresses **Brecha #4 - ALTA Prioridad** from the audit plan:

- ✓ Vectorization verification
- ✓ Prohibited for loops detection
- ✓ Performance benchmarking
- ✓ Actionable recommendations
- ✓ Pattern library for refactoring

## License

MIT License - See project root for details.
