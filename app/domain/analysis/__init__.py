"""
Analysis Module for Algorithmic Trading System

This module provides comprehensive analysis tools for:
- Performance metrics and attribution
- Risk analysis and decomposition
- Fundamental Law of Active Management (Grinold-Kahn)
- Information Coefficient calculation
- Strategy breadth analysis
- Vectorization verification and performance optimization

Key Components:
- fundamental_law: IR = IC * sqrtBR decomposition and analysis
- vectorization: Code vectorization auditing and benchmarking
"""

from app.domain.analysis.fundamental_law import (
    BreadthCalculator,
    BreadthMetrics,
    FundamentalLawCalculator,
    FundamentalLawComponents,
    ICCalculator,
    ICMetrics,
    StrategyAnalysis,
)
from app.domain.analysis.vectorization import (
    BenchmarkResult,
    VectorizationAuditor,
    VectorizationBenchmark,
    VectorizationIssue,
    VectorizationPatterns,
    VectorizationReport,
)

__all__ = [
    "BenchmarkResult",
    # Breadth
    "BreadthCalculator",
    "BreadthMetrics",
    # Fundamental Law
    "FundamentalLawCalculator",
    "FundamentalLawComponents",
    # Information Coefficient
    "ICCalculator",
    "ICMetrics",
    "StrategyAnalysis",
    # Vectorization
    "VectorizationAuditor",
    "VectorizationBenchmark",
    "VectorizationIssue",
    "VectorizationPatterns",
    "VectorizationReport",
]
