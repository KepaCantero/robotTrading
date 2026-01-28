"""
Vectorization Verification Module

This module provides tools for auditing and benchmarking vectorized code
to ensure high-performance numerical computing in algorithmic trading systems.

Main Components:
- VectorizationAuditor: Audit code for vectorization compliance
- VectorizationBenchmark: Benchmark vectorized vs non-vectorized code
- VectorizationPatterns: Common vectorization patterns and solutions

Key Rules:
1. No for loops for numerical calculations
2. Use numpy/pandas vectorized operations
3. Avoid .apply() on DataFrames (use vectorized ops)
4. Avoid list comprehensions for numerical work
5. Use numba JIT for critical loops
"""

from app.analysis.vectorization.benchmark import (
    BenchmarkResult,
    VectorizationBenchmark,
)
from app.analysis.vectorization.models import (
    VectorizationIssue,
    VectorizationReport,
)
from app.analysis.vectorization.patterns import VectorizationPatterns
from app.analysis.vectorization.vectorization_auditor import VectorizationAuditor

__all__ = [
    "VectorizationAuditor",
    "VectorizationBenchmark",
    "VectorizationIssue",
    "VectorizationReport",
    "VectorizationPatterns",
    "BenchmarkResult",
]
