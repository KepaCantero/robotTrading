"""
Fundamental Law of Active Management Calculator

This module implements the Fundamental Law of Active Management, which
decomposes the Information Ratio into skill (IC) and breadth (BR) components.

The Fundamental Law:
    IR = IC × √BR × TC

Where:
    IR = Information Ratio (risk-adjusted excess return)
    IC = Information Coefficient (forecasting skill)
    BR = Breadth (independent betting opportunities per year)
    TC = Transfer Coefficient (implementation efficiency)

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
    Chapter 9: The Fundamental Law of Active Management
"""

from __future__ import annotations

import logging
from decimal import Decimal

import numpy as np
import pandas as pd

from app.domain.analysis.fundamental_law.breadth_calculator import BreadthCalculator
from app.domain.analysis.fundamental_law.ic_calculator import ICCalculator
from app.domain.analysis.fundamental_law.models import FundamentalLawComponents, StrategyAnalysis
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class FundamentalLawCalculator:
    """
    Calculate and analyze the Fundamental Law of Active Management.

    The Fundamental Law decomposes the Information Ratio into:
    1. Skill component (IC): How good are your forecasts?
    2. Breadth component (√BR): How many opportunities do you have?
    3. Transfer component (TC): How well are forecasts implemented?

    This calculator helps identify which component is limiting performance
    and provides actionable improvement suggestions.

    Methods:
        - calculate_fundamental_law: Calculate components from known values
        - decompose_ir: Decompose IR from returns and forecasts
        - analyze_strategy: Comprehensive strategy analysis

    Examples:
        >>> calculator = FundamentalLawCalculator()
        >>> components = calculator.calculate_fundamental_law(
        ...     information_ratio=Decimal("1.0"),
        ...     information_coefficient=Decimal("0.05"),
        ...     breadth=Decimal("400")
        ... )
        >>> components.validate()
        True
    """

    def __init__(self):
        """Initialize the Fundamental Law Calculator."""
        self.ic_calculator = ICCalculator()
        self.breadth_calculator = BreadthCalculator()

    def calculate_fundamental_law(
        self,
        information_ratio: Decimal,
        information_coefficient: Decimal,
        breadth: Decimal,
        transfer_coefficient: Decimal = Decimal("1.0"),
    ) -> "FundamentalLawComponents":
        """
        Calculate Fundamental Law components from known values.

        This verifies that the components satisfy the Fundamental Law:
            IR = IC × √BR × TC

        Args:
            information_ratio: The observed Information Ratio
            information_coefficient: The Information Coefficient (skill)
            breadth: The annual breadth (independent bets per year)
            transfer_coefficient: The Transfer Coefficient (implementation)
                - Default: 1.0 (unconstrained)
                - Realistic range: 0.5-1.0

        Returns:
            FundamentalLawComponents with calculated values

        Raises:
            ValueError: If any input is invalid

        Examples:
            >>> calculator = FundamentalLawCalculator()
            >>> # IR = 0.05 × √400 × 1.0 = 0.05 × 20 × 1.0 = 1.0
            >>> components = calculator.calculate_fundamental_law(
            ...     information_ratio=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400")
            ... )
            >>> components.validate()
            True
        """
        # Validate inputs
        if information_ratio < 0:
            raise ValueError(f"Information Ratio cannot be negative: {information_ratio}")

        if information_coefficient < -1 or information_coefficient > 1:
            raise ValueError(
                f"Information Coefficient must be in [-1, 1]: {information_coefficient}"
            )

        if breadth < 0:
            raise ValueError(f"Breadth cannot be negative: {breadth}")

        if transfer_coefficient < 0 or transfer_coefficient > 1:
            logger.warning(
                f"Transfer Coefficient outside typical range [0, 1]: {transfer_coefficient}"
            )

        # Calculate breadth square root
        breadth_sqrt = self._calculate_breadth_sqrt(breadth)

        # Create components
        from app.domain.analysis.fundamental_law.models import FundamentalLawComponents

        return FundamentalLawComponents(
            information_ratio=information_ratio,
            information_coefficient=information_coefficient,
            breadth=breadth,
            breadth_sqrt=breadth_sqrt,
            transfer_coefficient=transfer_coefficient,
        )

    def decompose_ir(
        self,
        returns: pd.Series,
        forecasts: pd.Series,
        benchmark_returns: pd.Series,
        rebalance_frequency: str = "monthly",
    ) -> "FundamentalLawComponents":
        """
        Decompose Information Ratio into IC and BR components.

        This method analyzes actual returns and forecasts to calculate
        all components of the Fundamental Law.

        Process:
        1. Calculate IR = active_return / tracking_error
        2. Calculate IC = correlation(forecasts, returns)
        3. Calculate BR from trading frequency and asset independence
        4. Estimate TC from efficiency of implementation
        5. Verify: IR ≈ IC × √BR × TC

        Args:
            returns: Portfolio returns (aligned with forecasts)
            forecasts: Predicted returns from alpha model
            benchmark_returns: Benchmark returns for calculating active return
            rebalance_frequency: How often positions are rebalanced
                Used for breadth calculation

        Returns:
            FundamentalLawComponents with decomposed values

        Raises:
            ValueError: If series have different lengths or insufficient data

        Examples:
            >>> calculator = FundamentalLawCalculator()
            >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01] * 20)
            >>> forecasts = getattr(config.trading, 'max_risk_per_trade', 0.02)5, -0.005, 0.02, 0.008] * 20)
            >>> benchmark = pd.Series([0.005, 0.01, -0.005, 0.01, 0.005] * 20)
            >>> components = calculator.decompose_ir(returns, forecasts, benchmark)
            >>> components.information_ratio > 0
            True
        """
        # Validate inputs
        if len(returns) != len(forecasts) or len(returns) != len(benchmark_returns):
            raise ValueError(
                f"Returns, forecasts, and benchmark must have same length: "
                f"{len(returns)}, {len(forecasts)}, {len(benchmark_returns)}"
            )

        # Step 1: Calculate Information Ratio
        ir = self._calculate_information_ratio(returns, benchmark_returns)

        # Step 2: Calculate Information Coefficient
        ic_metrics = self.ic_calculator.calculate_ic(forecasts, returns)
        ic = ic_metrics.ic

        # Step 3: Calculate Breadth
        # Estimate from the data
        n_assets = 1  # Default to single asset if not specified

        # Estimate rebalancing frequency from data
        periods_per_year = self._estimate_periods_per_year(returns)
        annual_breadth = Decimal(str(periods_per_year)) * Decimal(n_assets)

        # Assume moderate independence for single asset
        independence_factor = Decimal("1.0")
        breadth = annual_breadth * independence_factor

        # Step 4: Calculate Transfer Coefficient
        # TC = IR / (IC × √BR)
        breadth_sqrt = self._calculate_breadth_sqrt(breadth)

        # Handle negative IR (underperforming strategy)
        if ir < 0:
            # For negative IR, we can't properly decompose
            # Return a zero-based analysis
            transfer_coefficient = Decimal("0.0")
        elif ic > 0 and breadth_sqrt > 0:
            transfer_coefficient = ir / (ic * breadth_sqrt)
            # Clamp to reasonable range
            transfer_coefficient = max(Decimal("0.0"), min(Decimal("1.0"), transfer_coefficient))
        else:
            transfer_coefficient = Decimal("0.5")  # Default assumption

        from app.domain.analysis.fundamental_law.models import FundamentalLawComponents

        return FundamentalLawComponents(
            information_ratio=max(ir, Decimal("0")),  # Clamp to non-negative
            information_coefficient=abs(ic),  # Use absolute value for skill
            breadth=breadth,
            breadth_sqrt=breadth_sqrt,
            transfer_coefficient=transfer_coefficient,
        )

    def analyze_strategy(
        self,
        components: "FundamentalLawComponents",
        strategy_name: str,
    ) -> "StrategyAnalysis":
        """
        Analyze strategy performance using the Fundamental Law.

        This provides a comprehensive assessment including:
        - Skill level (based on IC)
        - Breadth assessment (based on BR)
        - IR quality (based on Information Ratio)
        - Transfer efficiency (based on TC)
        - Actionable improvement suggestions

        Args:
            components: The Fundamental Law components for the strategy
            strategy_name: Name/identifier of the strategy

        Returns:
            StrategyAnalysis with assessment and suggestions

        Examples:
            >>> calculator = FundamentalLawCalculator()
            >>> components = calculator.calculate_fundamental_law(
            ...     information_ratio=Decimal("0.6"),
            ...     information_coefficient=Decimal("0.03"),
            ...     breadth=Decimal("400")
            ... )
            >>> analysis = calculator.analyze_strategy(components, "Momentum Strategy")
            >>> analysis.skill_level
            'good'
        """
        # Assess skill level (based on IC)
        skill_level = self._assess_skill_level(components.information_coefficient)

        # Assess breadth (based on BR)
        breadth_assessment = self._assess_breadth(components.breadth)

        # Assess IR quality
        ir_assessment = self._assess_ir(components.information_ratio)

        # Assess transfer coefficient
        tc_assessment = self._assess_tc(components.transfer_coefficient)

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(
            components=components,
            skill_level=skill_level,
            breadth_assessment=breadth_assessment,
            ir_assessment=ir_assessment,
            tc_assessment=tc_assessment,
        )

        from app.domain.analysis.fundamental_law.models import StrategyAnalysis

        return StrategyAnalysis(
            strategy_name=strategy_name,
            components=components,
            skill_level=skill_level,
            breadth_assessment=breadth_assessment,
            improvement_suggestions=suggestions,
        )

    def compare_strategies(
        self,
        strategies: dict[str, "FundamentalLawComponents"],
    ) -> pd.DataFrame:
        """
        Compare multiple strategies using the Fundamental Law.

        Args:
            strategies: Dictionary of {strategy_name: components}

        Returns:
            DataFrame with comparison metrics for each strategy

        Examples:
            >>> calculator = FundamentalLawCalculator()
            >>> strategies = {
            ...     "Momentum": calculator.calculate_fundamental_law(
            ...         Decimal("0.8"), Decimal("0.04"), Decimal("400")
            ...     ),
            ...     "Value": calculator.calculate_fundamental_law(
            ...         Decimal("0.6"), Decimal("0.03"), Decimal("300")
            ...     ),
            ... }
            >>> comparison = calculator.compare_strategies(strategies)
            >>> len(comparison) == 2
            True
        """
        comparison_data = []

        for name, components in strategies.items():
            comparison_data.append(
                {
                    "Strategy": name,
                    "IR": float(components.information_ratio),
                    "IC": float(components.information_coefficient),
                    "BR": float(components.breadth),
                    "√BR": float(components.breadth_sqrt),
                    "TC": float(components.transfer_coefficient),
                    "Theoretical IR": float(components.get_theoretical_ir()),
                    "Efficiency Gap": float(components.get_efficiency_gap()),
                }
            )

        return pd.DataFrame(comparison_data).set_index("Strategy")

    def calculate_required_ic_for_target_ir(
        self,
        target_ir: Decimal,
        breadth: Decimal,
        transfer_coefficient: Decimal = Decimal("1.0"),
    ) -> Decimal:
        """
        Calculate required IC for a target Information Ratio.

        Rearranging the Fundamental Law:
            IR = IC × √BR × TC
            ∴ IC = IR / (√BR × TC)

        Args:
            target_ir: Desired Information Ratio
            breadth: Current or expected breadth
            transfer_coefficient: Expected transfer coefficient

        Returns:
            Required Information Coefficient

        Examples:
            >>> calculator = FundamentalLawCalculator()
            >>> ic = calculator.calculate_required_ic_for_target_ir(
            ...     target_ir=Decimal("1.0"),
            ...     breadth=Decimal("400")
            ... )
            >>> abs(ic - Decimal("0.05")) < Decimal("0.01")
            True
        """
        breadth_sqrt = self._calculate_breadth_sqrt(breadth)
        denominator = breadth_sqrt * transfer_coefficient

        if denominator == 0:
            raise ValueError("Cannot calculate required IC: denominator is zero")

        required_ic = target_ir / denominator

        # IC is bounded by [-1, 1]
        required_ic = max(Decimal("-1.0"), min(Decimal("1.0"), required_ic))

        return required_ic

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _calculate_breadth_sqrt(self, breadth: Decimal) -> Decimal:
        """Calculate square root of breadth."""
        import math

        sqrt_value = Decimal(str(math.sqrt(float(breadth))))
        return round(sqrt_value, 4)

    def _calculate_information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> Decimal:
        """
        Calculate Information Ratio from returns.

        IR = mean(active_return) / std(active_return)

        Where active_return = returns - benchmark_returns
        """
        # Calculate active returns
        active_returns = returns - benchmark_returns

        # Remove NaN values
        active_returns = active_returns.dropna()

        if len(active_returns) < 2:
            raise ValueError(
                "Insufficient data to calculate Information Ratio: "
                f"need at least 2 observations, got {len(active_returns)}"
            )

        # Calculate mean and std of active returns
        mean_active = Decimal(str(active_returns.mean()))
        std_active = Decimal(str(active_returns.std()))

        if std_active == 0:
            logger.warning("Tracking error is zero, returning IR of 0")
            return Decimal("0")

        # Annualize (using configured trading days per year)
        config = get_config()
        trading_days = getattr(config.trading, 'fundamental_law_trading_days_per_year', 252)
        daily_ir = mean_active / std_active
        annual_ir = daily_ir * Decimal(str(np.sqrt(trading_days)))

        return round(annual_ir, 4)

    def _estimate_periods_per_year(self, returns: pd.Series) -> float:
        """Estimate number of trading periods per year from index."""
        config = get_config()
        default_trading_days = getattr(config.trading, 'fundamental_law_trading_days_per_year', 252)

        if not isinstance(returns.index, pd.DatetimeIndex):
            # Assume daily if not DatetimeIndex
            return float(default_trading_days)

        # Calculate days in data
        days = (returns.index[-1] - returns.index[0]).days
        if days < 1:
            return float(default_trading_days)

        # Calculate periods per day
        periods_per_day = len(returns) / days

        # Convert to annual
        return periods_per_day * 365.25

    def _assess_skill_level(self, ic: Decimal) -> str:
        """Assess forecasting skill based on IC using config thresholds."""
        config = get_config()
        ic_excellent = Decimal(str(getattr(config.trading, 'fundamental_law_ic_excellent', 0.05)))
        ic_good = Decimal(str(getattr(config.trading, 'fundamental_law_ic_good', 0.03)))
        ic_fair = Decimal(str(getattr(config.trading, 'fundamental_law_ic_fair', 0.01)))

        if ic >= ic_excellent:
            return "excellent"
        elif ic >= ic_good:
            return "good"
        elif ic >= ic_fair:
            return "fair"
        else:
            return "poor"

    def _assess_breadth(self, breadth: Decimal) -> str:
        """
        Assess breadth level.

        Uses configured thresholds from centralized config.
        """
        config = get_config()
        # Get breadth thresholds from config (use defaults if not available)
        breadth_high = getattr(config.trading, 'breadth_high_threshold', Decimal("1000"))
        breadth_medium = getattr(config.trading, 'breadth_medium_threshold', Decimal("100"))

        if breadth >= breadth_high:
            return "high"
        elif breadth >= breadth_medium:
            return "medium"
        else:
            return "low"

    def _assess_ir(self, ir: Decimal) -> str:
        """Assess Information Ratio quality using config thresholds."""
        config = get_config()
        ir_excellent = Decimal(str(getattr(config.trading, 'fundamental_law_ir_excellent', 1.0)))
        ir_good = Decimal(str(getattr(config.trading, 'fundamental_law_ir_good', 0.5)))
        ir_fair = Decimal(str(getattr(config.trading, 'fundamental_law_ir_fair', 0.25)))

        if ir >= ir_excellent:
            return "excellent"
        elif ir >= ir_good:
            return "good"
        elif ir >= ir_fair:
            return "fair"
        else:
            return "poor"

    def _assess_tc(self, tc: Decimal) -> str:
        """Assess Transfer Coefficient using config thresholds."""
        config = get_config()
        tc_excellent = Decimal(str(getattr(config.trading, 'fundamental_law_tc_excellent', 0.8)))
        tc_good = Decimal(str(getattr(config.trading, 'fundamental_law_tc_good', 0.6)))
        tc_fair = Decimal(str(getattr(config.trading, 'fundamental_law_tc_fair', 0.4)))

        if tc >= tc_excellent:
            return "excellent"
        elif tc >= tc_good:
            return "good"
        elif tc >= tc_fair:
            return "fair"
        else:
            return "poor"

    def _generate_suggestions(
        self,
        components: "FundamentalLawComponents",
        skill_level: str,
        breadth_assessment: str,
        ir_assessment: str,
        tc_assessment: str,
    ) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        # IC-based suggestions
        if skill_level == "poor":
            suggestions.append(
                "CRITICAL: Improve forecast quality. Current IC is too low. "
                "Consider: 1) Revising alpha model, 2) Adding new signals, "
                "3) Removing noise from forecasts"
            )
        elif skill_level == "fair":
            suggestions.append(
                "Improve forecasting skill. Current IC is modest. "
                "Consider: 1) Feature engineering, 2) Alternative data sources, "
                "3) Machine learning models"
            )

        # Breadth-based suggestions
        if breadth_assessment == "low":
            suggestions.append(
                "Increase strategy breadth. Current opportunities are limited. "
                "Consider: 1) Expanding asset universe, 2) Increasing trading frequency, "
                "3) Adding uncorrelated strategies"
            )
        elif breadth_assessment == "medium":
            suggestions.append(
                "Consider increasing breadth for better diversification. "
                "Options: 1) Add more assets, 2) Trade more frequently, "
                "3) Reduce asset correlation"
            )

        # TC-based suggestions
        if tc_assessment == "poor":
            suggestions.append(
                "CRITICAL: Improve implementation efficiency. "
                "Transfer Coefficient is low, meaning forecasts aren't "
                "being converted to positions effectively. "
                "Consider: 1) Relaxing portfolio constraints, "
                "2) Reducing turnover limits, 3) Optimizing execution"
            )
        elif tc_assessment == "fair":
            suggestions.append(
                "Improve implementation. Some forecast value is being lost "
                "in the conversion to positions. Review constraints and "
                "execution processes."
            )

        # IR-based suggestions
        if ir_assessment == "poor":
            suggestions.append(
                "Overall Information Ratio is poor. Focus on the highest-impact "
                "improvement based on IC, BR, and TC analysis above."
            )

        # Check for efficiency gap
        gap = components.get_efficiency_gap()
        if gap > Decimal("0.2"):
            suggestions.append(
                f"Large efficiency gap detected ({gap:.2f}). "
                f"Theoretical IR is {components.get_theoretical_ir():.2f} "
                f"but actual IR is {components.information_ratio:.2f}. "
                f"Focus on improving implementation (TC)."
            )

        return suggestions
