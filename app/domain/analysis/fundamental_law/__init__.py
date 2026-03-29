"""
Fundamental Law of Active Management Module

This module implements the Fundamental Law of Active Management (Grinold-Kahn),
which decomposes the Information Ratio into skill (IC) and breadth (BR) components:

    IR = IC * sqrtBR * TC

Where:
    - IR = Information Ratio (risk-adjusted excess return)
    - IC = Information Coefficient (forecasting skill)
    - BR = Breadth (independent betting opportunities per year)
    - TC = Transfer Coefficient (implementation efficiency)

Key Components:
    - FundamentalLawCalculator: Main calculator for IR decomposition
    - ICCalculator: Calculate Information Coefficient and related metrics
    - BreadthCalculator: Calculate strategy breadth and independence
    - Data models: FundamentalLawComponents, ICMetrics, BreadthMetrics, StrategyAnalysis

Usage:
    >>> from app.domain.analysis.fundamental_law import (
    ...     FundamentalLawCalculator,
    ...     ICCalculator,
    ...     BreadthCalculator,
    ... )
    >>>
    >>> # Analyze a strategy
    >>> calculator = FundamentalLawCalculator()
    >>> components = calculator.calculate_fundamental_law(
    ...     information_ratio=Decimal("1.0"),
    ...     information_coefficient=Decimal("0.05"),
    ...     breadth=Decimal("400")
    ... )
    >>>
    >>> # Analyze forecast skill
    >>> ic_calc = ICCalculator()
    >>> ic_metrics = ic_calc.calculate_ic(forecasts, returns)
    >>>
    >>> # Calculate breadth
    >>> br_calc = BreadthCalculator()
    >>> br_metrics = br_calc.calculate_breadth(
    ...     n_assets=100,
    ...     rebalance_frequency="weekly"
    ... )

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
    McGraw-Hill, 2nd Edition, Chapter 9
"""

from app.domain.analysis.fundamental_law.breadth_calculator import BreadthCalculator
from app.domain.analysis.fundamental_law.fundamental_law import FundamentalLawCalculator
from app.domain.analysis.fundamental_law.ic_calculator import ICCalculator
from app.domain.analysis.fundamental_law.models import (
    BreadthMetrics,
    FundamentalLawComponents,
    ICMetrics,
    StrategyAnalysis,
)

__all__ = [
    "BreadthCalculator",
    "BreadthMetrics",
    "FundamentalLawCalculator",
    "FundamentalLawComponents",
    "ICCalculator",
    "ICMetrics",
    "StrategyAnalysis",
]
