"""
Data Models for Fundamental Law of Active Management

This module defines the data models and types used throughout the
fundamental law analysis components.

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
    McGraw-Hill, 2nd Edition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FundamentalLawComponents:
    """
    Components of the Fundamental Law of Active Management.

    The Fundamental Law states:
        IR = IC × √BR × TC

    Where:
        IR = Information Ratio (active return / tracking error)
        IC = Information Coefficient (correlation between forecasts and returns)
        BR = Breadth (number of independent betting opportunities per year)
        TC = Transfer Coefficient (how well forecasts are converted to positions)

    Attributes:
        information_ratio: The Information Ratio, typically ranging from 0 to 2.0
            - IR > 1.0: Excellent performance
            - IR 0.5-1.0: Good performance
            - IR < 0.5: Poor performance
        information_coefficient: The Information Coefficient, typically [-1, 1]
            but in practice usually [0, 0.1] for most strategies
            - IC > 0.05: Excellent forecasting skill
            - IC 0.03-0.05: Good forecasting skill
            - IC 0.01-0.03: Fair forecasting skill
            - IC < 0.01: Poor forecasting skill
        breadth: The number of independent bets per year
            - BR > 1000: High breadth
            - BR 100-1000: Medium breadth
            - BR < 100: Low breadth
        breadth_sqrt: Square root of breadth, represents the "breadth factor"
        transfer_coefficient: How efficiently forecasts are converted to positions
            - TC = 1.0: Perfect conversion (unconstrained)
            - TC = 0.5-1.0: Realistic range for most strategies
            - TC < 0.5: Significant constraints limiting performance

    Examples:
        >>> components = FundamentalLawComponents(
        ...     information_ratio=Decimal("1.2"),
        ...     information_coefficient=Decimal("0.05"),
        ...     breadth=Decimal("400"),
        ...     breadth_sqrt=Decimal("20.0"),
        ...     transfer_coefficient=Decimal("1.0")
        ... )
        >>> # Verify the fundamental law: IR = IC × √BR × TC
        >>> components.validate()
        True
    """

    information_ratio: Decimal
    information_coefficient: Decimal
    breadth: Decimal
    breadth_sqrt: Decimal
    transfer_coefficient: Decimal

    def validate(self, tolerance: Decimal = Decimal("0.01")) -> bool:
        """
        Validate that the components satisfy the Fundamental Law.

        The law states: IR = IC × √BR × TC

        Args:
            tolerance: Acceptable deviation from exact equality (default: 1%)

        Returns:
            True if the components satisfy the law within tolerance

        Raises:
            ValueError: If any component is negative

        Examples:
            >>> components = FundamentalLawComponents(
            ...     information_ratio=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400"),
            ...     breadth_sqrt=Decimal("20.0"),
            ...     transfer_coefficient=Decimal("1.0")
            ... )
            >>> components.validate()
            True
        """
        logger.debug(
            "Validating Fundamental Law components",
            extra={
                "ir": float(self.information_ratio),
                "ic": float(self.information_coefficient),
                "breadth": float(self.breadth),
                "tc": float(self.transfer_coefficient),
            },
        )

        # Validate all components are non-negative
        if self.information_ratio < 0:
            logger.error(
                "Information Ratio cannot be negative",
                extra={"value": float(self.information_ratio)},
            )
            raise ValueError("Information Ratio cannot be negative")
        if self.information_coefficient < 0:
            logger.error(
                "Information Coefficient cannot be negative",
                extra={"value": float(self.information_coefficient)},
            )
            raise ValueError("Information Coefficient cannot be negative")
        if self.breadth < 0:
            logger.error("Breadth cannot be negative", extra={"value": float(self.breadth)})
            raise ValueError("Breadth cannot be negative")
        if self.transfer_coefficient < 0:
            logger.error(
                "Transfer Coefficient cannot be negative",
                extra={"value": float(self.transfer_coefficient)},
            )
            raise ValueError("Transfer Coefficient cannot be negative")

        # Calculate expected IR from components
        expected_ir = self.information_coefficient * self.breadth_sqrt * self.transfer_coefficient

        # Check if actual IR matches expected IR within tolerance
        difference = abs(self.information_ratio - expected_ir)

        # Use relative tolerance for better handling of different scales
        if self.information_ratio != 0:
            relative_difference = difference / abs(self.information_ratio)
            is_valid = relative_difference <= tolerance
        else:
            is_valid = difference <= tolerance

        logger.info(
            f"Fundamental Law validation {'passed' if is_valid else 'failed'}",
            extra={
                "is_valid": is_valid,
                "difference": float(difference),
                "tolerance": float(tolerance),
            },
        )

        return is_valid

    def get_theoretical_ir(self) -> Decimal:
        """
        Calculate the theoretical Information Ratio from components.

        Returns:
            The theoretical IR based on IC, BR, and TC

        Examples:
            >>> components = FundamentalLawComponents(
            ...     information_ratio=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400"),
            ...     breadth_sqrt=Decimal("20.0"),
            ...     transfer_coefficient=Decimal("1.0")
            ... )
            >>> components.get_theoretical_ir()
            Decimal('1.000')
        """
        return self.information_coefficient * self.breadth_sqrt * self.transfer_coefficient

    def get_efficiency_gap(self) -> Decimal:
        """
        Calculate the gap between actual and theoretical IR.

        A positive gap indicates room for improvement by either:
        - Improving forecast implementation (increase TC)
        - Better constraint management

        Returns:
            The difference between theoretical and actual IR

        Examples:
            >>> components = FundamentalLawComponents(
            ...     information_ratio=Decimal("0.8"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400"),
            ...     breadth_sqrt=Decimal("20.0"),
            ...     transfer_coefficient=Decimal("1.0")
            ... )
            >>> components.get_efficiency_gap()
            Decimal('0.200')
        """
        return self.get_theoretical_ir() - self.information_ratio


@dataclass
class ICMetrics:
    """
    Information Coefficient metrics for evaluating forecast skill.

    The Information Coefficient (IC) measures the correlation between
    forecasted returns and actual returns, indicating the skill of
    the forecasting model.

    Attributes:
        ic: Raw Information Coefficient using Pearson correlation
            - Measures linear relationship between forecasts and returns
            - Range: [-1, 1], but typically [0, 0.1] in practice
        ic_rank: Rank IC using Spearman correlation
            - More robust to outliers than Pearson IC
            - Measures monotonic relationship
            - Often preferred in practice
        ic_decay: IC values over different forward horizons
            - Shows how long predictive signal persists
            - Format: [IC_period1, IC_period2, ...]
            - Example: [IC_1day, IC_5day, IC_10day, IC_20day]
        statistical_significance: P-value for IC statistical test
            - H0: IC = 0 (no forecasting skill)
            - p < 0.05 indicates statistically significant skill
        confidence_interval: 95% confidence interval for IC
            - Lower and upper bounds of the confidence interval
            - Format: (lower_bound, upper_bound)

    Examples:
        >>> metrics = ICMetrics(
        ...     ic=Decimal("0.05"),
        ...     ic_rank=Decimal("0.04"),
        ...     ic_decay= getattr(config.trading, 'max_risk_per_trade', 0.02)")],
        ...     statistical_significance=0.001,
        ...     confidence_interval=(Decimal("0.03"), Decimal("0.07"))
        ... )
        >>> metrics.is_significant()
        True
    """

    ic: Decimal
    ic_rank: Decimal
    ic_decay: list[Decimal]
    statistical_significance: float
    confidence_interval: tuple[Decimal, Decimal]

    def is_significant(self, alpha: float = 0.05) -> bool:
        """
        Check if the IC is statistically significant.

        Args:
            alpha: Significance level (default: 0.05 for 95% confidence)

        Returns:
            True if IC is statistically significant at the given level

        Examples:
            >>> metrics = ICMetrics(
            ...     ic=Decimal("0.05"),
            ...     ic_rank=Decimal("0.04"),
            ...     ic_decay=[],
            ...     statistical_significance=0.001,
            ...     confidence_interval=(Decimal("0.03"), Decimal("0.07"))
            ... )
            >>> metrics.is_significant()
            True
            >>> metrics.is_significant(alpha=0.001)
            False
        """
        is_sig = self.statistical_significance < alpha
        logger.debug(
            f"IC significance check: {'significant' if is_sig else 'not significant'}",
            extra={
                "ic": float(self.ic),
                "p_value": self.statistical_significance,
                "alpha": alpha,
                "is_significant": is_sig,
            },
        )
        return is_sig

    def get_skill_level(self) -> str:
        """
        Categorize the forecasting skill based on IC value.

        Returns:
            Skill category: "excellent", "good", "fair", or "poor"

        Examples:
            >>> metrics = ICMetrics(
            ...     ic=Decimal("0.06"),
            ...     ic_rank=Decimal("0.05"),
            ...     ic_decay=[],
            ...     statistical_significance=0.001,
            ...     confidence_interval=(Decimal("0.04"), Decimal("0.08"))
            ... )
            >>> metrics.get_skill_level()
            'excellent'
        """
        if self.ic >= Decimal("0.05"):
            skill_level = "excellent"
        elif self.ic >= Decimal("0.03"):
            skill_level = "good"
        elif self.ic >= Decimal("0.01"):
            skill_level = "fair"
        else:
            skill_level = "poor"

        logger.debug(
            f"IC skill level assessed: {skill_level}",
            extra={
                "ic": float(self.ic),
                "skill_level": skill_level,
            },
        )
        return skill_level

    def get_skill_level_config(self) -> str:
        """
        Get skill level using configured thresholds.

        Uses the same config-based assessment as FundamentalLawCalculator.
        """
        config = get_config()
        ic_excellent = Decimal(str(getattr(config.trading, 'fundamental_law_ic_excellent', 0.05)))
        ic_good = Decimal(str(getattr(config.trading, 'fundamental_law_ic_good', 0.03)))
        ic_fair = Decimal(str(getattr(config.trading, 'fundamental_law_ic_fair', 0.01)))

        if self.ic >= ic_excellent:
            return "excellent"
        elif self.ic >= ic_good:
            return "good"
        elif self.ic >= ic_fair:
            return "fair"
        else:
            return "poor"

    def get_signal_persistence(self) -> str:
        """
        Assess how long the predictive signal persists.

        Returns:
            Persistence description based on IC decay pattern

        Examples:
            >>> metrics = ICMetrics(
            ...     ic=Decimal("0.05"),
            ...     ic_rank=Decimal("0.04"),
            ...     ic_decay=[Decimal("0.05"), Decimal("0.04"), Decimal("0.03")],
            ...     statistical_significance=0.001,
            ...     confidence_interval=(Decimal("0.03"), Decimal("0.07"))
            ... )
            >>> metrics.get_signal_persistence()
            'medium'
        """
        if not self.ic_decay or len(self.ic_decay) < 2:
            logger.debug("Signal persistence unknown: insufficient decay data")
            return "unknown"

        # Calculate decay rate
        initial_ic = self.ic_decay[0]
        final_ic = self.ic_decay[-1]

        if initial_ic == 0:
            logger.warning("Signal persistence unknown: initial IC is zero")
            return "unknown"

        decay_ratio = abs(final_ic) / abs(initial_ic)

        # Get persistence thresholds from config
        from app.shared.config.centralized_config import get_config

        cfg = get_config()
        long_threshold = Decimal(str(getattr(cfg.trading, 'signal_persistence_long', 0.7)))
        medium_threshold = Decimal(str(getattr(cfg.trading, 'signal_persistence_medium', 0.4)))

        if decay_ratio >= long_threshold:
            persistence = "long"  # Signal persists well
        elif decay_ratio >= medium_threshold:
            persistence = "medium"  # Moderate decay
        else:
            persistence = "short"  # Signal decays quickly

        logger.debug(
            f"Signal persistence assessed: {persistence}",
            extra={
                "decay_ratio": float(decay_ratio),
                "initial_ic": float(initial_ic),
                "final_ic": float(final_ic),
                "persistence": persistence,
            },
        )

        return persistence


@dataclass
class BreadthMetrics:
    """
    Breadth metrics for evaluating strategy coverage.

    Breadth measures the number of independent betting opportunities
    per year. Higher breadth allows lower IC to achieve the same IR.

    Attributes:
        annual_breadth: Total number of bets per year
            - Example: Weekly rebalancing of 100 stocks = 52 × 100 = 5200
            - Adjusted for independence factor
        independence_factor: Factor accounting for correlation between bets
            - Range: [0, 1]
            - 1.0 = All bets are independent
            - 0.1 = High correlation (bets are nearly redundant)
        effective_breadth: Annual breadth adjusted for independence
            - effective_breadth = annual_breadth × independence_factor
        notes: Additional context about the breadth calculation

    Examples:
        >>> metrics = BreadthMetrics(
        ...     annual_breadth=Decimal("5200"),
        ...     independence_factor=Decimal("0.5"),
        ...     effective_breadth=Decimal("2600"),
        ...     notes="Weekly rebalancing, 100 stocks, moderate correlation"
        ... )
        >>> metrics.get_breadth_category()
        'high'
    """

    annual_breadth: Decimal
    independence_factor: Decimal
    effective_breadth: Decimal
    notes: str = ""

    def get_breadth_category(self) -> str:
        """
        Categorize the breadth level.

        Returns:
            Category: "high", "medium", or "low"

        Examples:
            >>> metrics = BreadthMetrics(
            ...     annual_breadth=Decimal("2000"),
            ...     independence_factor=Decimal("1.0"),
            ...     effective_breadth=Decimal("2000"),
            ...     notes=""
            ... )
            >>> metrics.get_breadth_category()
            'high'
        """
        # Get breadth thresholds from config (use defaults if not available)
        config = get_config()
        breadth_high = getattr(config.trading, 'breadth_high_threshold', 1000)
        breadth_medium = getattr(config.trading, 'breadth_medium_threshold', 100)

        if self.effective_breadth >= Decimal(str(breadth_high)):
            category = "high"
        elif self.effective_breadth >= Decimal(str(breadth_medium)):
            category = "medium"
        else:
            category = "low"

        logger.debug(
            f"Breadth category assessed: {category}",
            extra={
                "effective_breadth": float(self.effective_breadth),
                "annual_breadth": float(self.annual_breadth),
                "independence_factor": float(self.independence_factor),
                "category": category,
            },
        )

        return category

    def get_breadth_sqrt(self) -> Decimal:
        """
        Calculate the square root of effective breadth.

        Returns:
            √(effective_breadth), the breadth factor in the Fundamental Law

        Examples:
            >>> metrics = BreadthMetrics(
            ...     annual_breadth=Decimal("400"),
            ...     independence_factor=Decimal("1.0"),
            ...     effective_breadth=Decimal("400"),
            ...     notes=""
            ... )
            >>> metrics.get_breadth_sqrt()
            Decimal('20.00')
        """
        import math

        sqrt_value = Decimal(str(math.sqrt(float(self.effective_breadth))))
        return round(sqrt_value, 2)


@dataclass
class StrategyAnalysis:
    """
    Comprehensive analysis of a strategy using the Fundamental Law.

    This class provides actionable insights about strategy performance
    by decomposing the Information Ratio into its components.

    Attributes:
        strategy_name: Name/identifier of the strategy
        components: The Fundamental Law components for this strategy
        skill_level: Assessment of forecasting skill
            - "excellent", "good", "fair", "poor"
        breadth_assessment: Assessment of breadth level
            - "high", "medium", "low"
        improvement_suggestions: List of actionable suggestions

    Examples:
        >>> from decimal import Decimal
        >>> components = FundamentalLawComponents(
        ...     information_ratio=Decimal("0.6"),
        ...     information_coefficient=Decimal("0.03"),
        ...     breadth=Decimal("400"),
        ...     breadth_sqrt=Decimal("20.0"),
        ...     transfer_coefficient=Decimal("1.0")
        ... )
        >>> analysis = StrategyAnalysis(
        ...     strategy_name="Momentum Strategy",
        ...     components=components,
        ...     skill_level="good",
        ...     breadth_assessment="medium",
        ...     improvement_suggestions=["Increase trading frequency", "Add more assets"]
        ... )
        >>> print(analysis.get_summary())
        Strategy: Momentum Strategy
        IR: 0.60, IC: 0.03, BR: 400
        Skill: good, Breadth: medium
    """

    strategy_name: str
    components: FundamentalLawComponents
    skill_level: str
    breadth_assessment: str
    improvement_suggestions: list[str] = field(default_factory=list)

    def get_improvement_plan(self) -> str:
        """
        Get a formatted improvement plan for the strategy.

        Returns:
            Formatted string with improvement suggestions

        Examples:
            >>> analysis = StrategyAnalysis(
            ...     strategy_name="Test Strategy",
            ...     components=FundamentalLawComponents(
            ...         information_ratio=Decimal("0.5"),
            ...         information_coefficient= getattr(config.trading, 'max_risk_per_trade', 0.02)"),
            ...         breadth=Decimal("100"),
            ...         breadth_sqrt=Decimal("10.0"),
            ...         transfer_coefficient=Decimal("0.8")
            ...     ),
            ...     skill_level="fair",
            ...     breadth_assessment="medium",
            ...     improvement_suggestions=["Improve alpha model", "Reduce constraints"]
            ... )
            >>> plan = analysis.get_improvement_plan()
            >>> "Improve alpha model" in plan
            True
        """
        lines = [f"Improvement Plan for {self.strategy_name}", "=" * 50, ""]

        if not self.improvement_suggestions:
            lines.append("No specific improvement suggestions available.")
            lines.append("")
            lines.append("General recommendations:")

            # Add general suggestions based on skill level
            if self.skill_level == "poor":
                lines.append("  • Focus on improving forecast quality (IC)")
                lines.append("  • Review and refine alpha generation model")

            if self.breadth_assessment == "low":
                lines.append("  • Increase trading frequency")
                lines.append("  • Expand universe of tradeable assets")

            tc = self.components.transfer_coefficient
            if tc < Decimal("0.7"):
                lines.append("  • Reduce portfolio constraints to improve TC")

            lines.append("")
        else:
            lines.append("Specific Recommendations:")
            for i, suggestion in enumerate(self.improvement_suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")

        return "\n".join(lines)

    def get_summary(self) -> str:
        """
        Get a summary of the strategy analysis.

        Returns:
            Formatted summary string

        Examples:
            >>> components = FundamentalLawComponents(
            ...     information_ratio=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400"),
            ...     breadth_sqrt=Decimal("20.0"),
            ...     transfer_coefficient=Decimal("1.0")
            ... )
            >>> analysis = StrategyAnalysis(
            ...     strategy_name="Test Strategy",
            ...     components=components,
            ...     skill_level="excellent",
            ...     breadth_assessment="high"
            ... )
            >>> summary = analysis.get_summary()
            >>> "Test Strategy" in summary
            True
        """
        lines = [
            f"Strategy: {self.strategy_name}",
            f"IR: {self.components.information_ratio:.2f}, "
            f"IC: {self.components.information_coefficient:.3f}, "
            f"BR: {self.components.breadth:.0f}",
            f"Skill: {self.skill_level}, Breadth: {self.breadth_assessment}",
            f"TC: {self.components.transfer_coefficient:.2f}",
        ]
        return "\n".join(lines)

    def get_ir_decomposition(self) -> dict:
        """
        Get the IR decomposition as percentages.

        Returns:
            Dictionary showing contribution of each component

        Examples:
            >>> components = FundamentalLawComponents(
            ...     information_ratio=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05"),
            ...     breadth=Decimal("400"),
            ...     breadth_sqrt=Decimal("20.0"),
            ...     transfer_coefficient=Decimal("1.0")
            ... )
            >>> analysis = StrategyAnalysis(
            ...     strategy_name="Test",
            ...     components=components,
            ...     skill_level="excellent",
            ...     breadth_assessment="high"
            ... )
            >>> decomp = analysis.get_ir_decomposition()
            >>> "ic_contribution" in decomp
            True
        """
        return {
            "information_ratio": float(self.components.information_ratio),
            "ic_contribution": float(self.components.information_coefficient),
            "breadth_contribution": float(self.components.breadth_sqrt),
            "tc_contribution": float(self.components.transfer_coefficient),
            "theoretical_ir": float(self.components.get_theoretical_ir()),
            "efficiency_gap": float(self.components.get_efficiency_gap()),
        }
