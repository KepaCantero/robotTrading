"""
T1.2: Absolute Return Optimizer

Transforms target EUR per month into operational parameters:
- Calculates required alpha
- Estimates capacity fade at scale
- Optimizes position sizing and leverage
- Validates feasibility of targets
"""

import logging
from decimal import Decimal
from typing import Dict

from .capital_tier_selector import CapitalTierSelector
from .models import AbsoluteReturnTarget, AbsoluteReturnValidation

logger = logging.getLogger(__name__)


class TargetAlphaCalculator:
    """
    T1.2.1: Target Alpha Calculator
    Converts EUR targets to required alpha percentage.
    """

    def __init__(self):
        """Initialize calculator."""
        self.logger = logging.getLogger(__name__)

    def calculate_required_alpha(self, target: AbsoluteReturnTarget) -> Decimal:
        """
        Calculate required alpha as % of capital annually.

        Args:
            target: AbsoluteReturnTarget specification

        Returns:
            Required alpha as % of capital per year
        """
        # Calculate total annual target in EUR
        annual_target = target.target_euros_monthly * 12

        # Adjust for tax (target is after-tax, so we need pre-tax amount)
        pre_tax_amount = annual_target / (1 - target.tax_rate)

        # Add annual commission costs
        annual_commissions = target.commission_per_trade * target.expected_trades_per_month * 12

        total_required = pre_tax_amount + annual_commissions

        # Calculate as percentage of capital
        required_alpha_pct = (total_required / target.capital * 100).quantize(Decimal("0.01"))

        self.logger.info(
            f"📊 Required alpha: {required_alpha_pct}% annually "
            f"(target: €{target.target_euros_monthly}/month, capital: €{target.capital})"
        )

        return required_alpha_pct

    def monthly_to_annual_alpha_pct(self, monthly_target: Decimal, capital: Decimal) -> Decimal:
        """
        Convert monthly target to annual alpha percentage.

        Args:
            monthly_target: Monthly target in EUR
            capital: Available capital

        Returns:
            Annual alpha percentage
        """
        annual = monthly_target * 12
        alpha_pct = (annual / capital * 100).quantize(Decimal("0.01"))
        return alpha_pct


class CapacityFadeAnalyzer:
    """
    T1.2.2: Capacity Fade Analyzer
    Estimates how alpha decays with increasing capital scale.
    """

    # Capacity fade multipliers by scale
    # Based on empirical research: larger capital = smaller alpha due to market impact
    CAPACITY_FADE_CURVE = {
        Decimal("10000"): Decimal("1.0"),  # Baseline, no fade
        Decimal("50000"): Decimal("0.95"),  # -5% fade
        Decimal("100000"): Decimal("0.90"),  # -10% fade
        Decimal("250000"): Decimal("0.85"),  # -15% fade
        Decimal("500000"): Decimal("0.80"),  # -20% fade
        Decimal("1000000"): Decimal("0.75"),  # -25% fade
    }

    def __init__(self):
        """Initialize analyzer."""
        self.logger = logging.getLogger(__name__)

    def estimate_capacity_fade(self, capital: Decimal, base_alpha_pct: Decimal) -> Decimal:
        """
        Estimate capacity fade effect on alpha.

        Args:
            capital: Capital amount
            base_alpha_pct: Baseline alpha % (from backtest at lower capital)

        Returns:
            Estimated alpha % after capacity fade
        """
        # Find appropriate fade multiplier
        fade_multiplier = self._get_fade_multiplier(capital)

        faded_alpha = base_alpha_pct * fade_multiplier

        self.logger.info(
            f"📉 Capacity fade estimate: {base_alpha_pct}% → {faded_alpha}% "
            f"(multiplier: {fade_multiplier} at €{capital})"
        )

        return faded_alpha.quantize(Decimal("0.01"))

    def _get_fade_multiplier(self, capital: Decimal) -> Decimal:
        """Get capacity fade multiplier for capital amount."""
        # Sort thresholds and find the closest one <= capital
        sorted_thresholds = sorted(self.CAPACITY_FADE_CURVE.keys())

        for i, threshold in enumerate(sorted_thresholds):
            if capital <= threshold:
                if i == 0:
                    return self.CAPACITY_FADE_CURVE[threshold]
                # Interpolate between two thresholds
                prev_threshold = sorted_thresholds[i - 1]
                prev_multiplier = self.CAPACITY_FADE_CURVE[prev_threshold]
                curr_multiplier = self.CAPACITY_FADE_CURVE[threshold]

                ratio = (capital - prev_threshold) / (threshold - prev_threshold)
                return (prev_multiplier + (curr_multiplier - prev_multiplier) * ratio).quantize(
                    Decimal("0.001")
                )

        # Capital exceeds maximum threshold, use last multiplier
        return self.CAPACITY_FADE_CURVE[sorted_thresholds[-1]]


class ParameterOptimizer:
    """
    T1.2.3: Parameter Optimizer
    Optimizes position sizing and leverage for target.
    """

    def __init__(self):
        """Initialize optimizer."""
        self.logger = logging.getLogger(__name__)

    def optimize_position_sizing(
        self, capital: Decimal, target_alpha_pct: Decimal, expected_signal_return_pct: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calculate optimal position sizing for target.

        Args:
            capital: Capital amount
            target_alpha_pct: Required alpha percentage
            expected_signal_return_pct: Expected return per signal (from backtest)

        Returns:
            Dict with position_size_pct, num_concurrent_positions, etc.
        """
        # Get tier-specific constraints
        tier = CapitalTierSelector.detect_tier(capital)
        config = CapitalTierSelector.get_tier_config(tier)
        max_position_pct = config["risk_profile"].max_position_size

        # Calculate required position sizing
        # If signal return = 2%, need position_size_pct = target_alpha / signal_return
        if expected_signal_return_pct <= 0:
            raise ValueError(
                f"Expected signal return must be positive, got {expected_signal_return_pct}%"
            )

        required_position_pct = (target_alpha_pct / expected_signal_return_pct).quantize(
            Decimal("0.01")
        )

        # Validate against tier limits
        if required_position_pct > max_position_pct:
            self.logger.warning(
                f"⚠️ Required position size {required_position_pct}% exceeds tier limit {max_position_pct}%"
            )
            required_position_pct = max_position_pct

        # Calculate optimal number of concurrent positions
        # Diversify across multiple positions to reduce risk
        if required_position_pct <= Decimal("0.05"):
            num_positions = max(1, int(max_position_pct / required_position_pct))
        else:
            num_positions = max(1, int(max_position_pct * 10 / required_position_pct))

        num_positions = min(num_positions, config["risk_profile"].diversification_min * 3)

        result = {
            "position_size_pct": required_position_pct,
            "position_size_eur": capital * required_position_pct,
            "num_concurrent_positions": Decimal(str(num_positions)),
            "total_exposure_pct": required_position_pct * num_positions,
            "average_position_size_eur": (capital * required_position_pct / num_positions).quantize(
                Decimal("0.01")
            ),
        }

        self.logger.info(
            f"💰 Position sizing optimized: {required_position_pct}% per position, "
            f"{num_positions} concurrent positions"
        )

        return result

    def optimize_leverage(
        self,
        capital: Decimal,
        target_alpha_pct: Decimal,
        achievable_alpha_without_leverage: Decimal,
    ) -> Decimal:
        """
        Determine optimal leverage for target.

        Args:
            capital: Capital amount
            target_alpha_pct: Required alpha percentage
            achievable_alpha_without_leverage: Alpha achievable without leverage

        Returns:
            Recommended leverage multiplier
        """
        tier = CapitalTierSelector.detect_tier(capital)
        config = CapitalTierSelector.get_tier_config(tier)
        max_leverage = config["risk_profile"].leverage_allowed

        # No leverage needed if already exceeding target
        if achievable_alpha_without_leverage >= target_alpha_pct:
            return Decimal("1.0")

        # Avoid division by zero or negative alpha
        if achievable_alpha_without_leverage <= 0:
            return Decimal("1.0")

        # Calculate required leverage
        required_leverage = (target_alpha_pct / achievable_alpha_without_leverage).quantize(
            Decimal("0.01")
        )

        # Cap at tier maximum
        optimal_leverage = min(required_leverage, max_leverage)

        if optimal_leverage > Decimal("1.0"):
            self.logger.warning(
                f"⚠️ Leverage required: {optimal_leverage}x (max allowed: {max_leverage}x)"
            )

        return optimal_leverage


class FeasibilityValidator:
    """
    T1.2.4: Feasibility Validator
    Validates that return targets are realistic for given capital and constraints.
    """

    # Empirical benchmarks for realistic alpha by tier
    REALISTIC_ALPHA_RANGE = {
        "CONSERVATIVE": (Decimal("2"), Decimal("5")),
        "BALANCED": (Decimal("3"), Decimal("8")),
        "AGGRESSIVE": (Decimal("4"), Decimal("12")),
    }

    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)
        self.alpha_calculator = TargetAlphaCalculator()
        self.fade_analyzer = CapacityFadeAnalyzer()

    def validate_target(self, target: AbsoluteReturnTarget) -> AbsoluteReturnValidation:
        """
        Validate if absolute return target is feasible.

        Args:
            target: AbsoluteReturnTarget to validate

        Returns:
            AbsoluteReturnValidation with feasibility assessment
        """
        # Calculate required alpha
        required_alpha_pct = self.alpha_calculator.calculate_required_alpha(target)

        # Get tier strategy type
        tier = CapitalTierSelector.detect_tier(target.capital)
        config = CapitalTierSelector.get_tier_config(tier)
        strategy_type = config["strategy_type"]

        # Check against realistic benchmarks
        min_realistic, max_realistic = self.REALISTIC_ALPHA_RANGE[strategy_type]

        # Estimate capacity fade for this capital
        faded_alpha = self.fade_analyzer.estimate_capacity_fade(target.capital, max_realistic)

        # Determine feasibility
        is_feasible = required_alpha_pct <= faded_alpha

        # Calculate confidence level
        confidence_level = self._calculate_confidence(required_alpha_pct, faded_alpha)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            target, required_alpha_pct, faded_alpha, is_feasible
        )

        # Calculate monthly costs breakdown
        monthly_costs = {
            "commissions": (target.commission_per_trade * target.expected_trades_per_month),
            "taxes_on_profit": (target.target_euros_monthly * target.tax_rate),
            "total": (
                target.commission_per_trade * target.expected_trades_per_month
                + target.target_euros_monthly * target.tax_rate
            ),
        }

        result = AbsoluteReturnValidation(
            is_feasible=is_feasible,
            required_alpha_pct=required_alpha_pct,
            capacity_fade_adjusted_alpha=faded_alpha,
            recommendation=recommendation,
            confidence_level=confidence_level,
            monthly_costs=monthly_costs,
        )

        status = "✅ FEASIBLE" if is_feasible else "❌ NOT FEASIBLE"
        self.logger.info(
            f"{status}: Target €{target.target_euros_monthly}/month on €{target.capital} capital "
            f"requires {required_alpha_pct}% alpha (realistic: {faded_alpha}% max)"
        )

        return result

    def _calculate_confidence(self, required_alpha: Decimal, feasible_alpha: Decimal) -> str:
        """Calculate confidence level in feasibility."""
        if required_alpha <= feasible_alpha * Decimal("0.7"):
            return "HIGH"
        elif required_alpha <= feasible_alpha * Decimal("0.9"):
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_recommendation(
        self,
        target: AbsoluteReturnTarget,
        required_alpha: Decimal,
        feasible_alpha: Decimal,
        is_feasible: bool,
    ) -> str:
        """Generate recommendation text."""
        if is_feasible:
            margin = feasible_alpha - required_alpha
            return (
                f"Target €{target.target_euros_monthly}/month is feasible for €{target.capital} capital. "
                f"Realistic alpha range: {feasible_alpha}% (with {margin}% safety margin)"
            )
        else:
            gap = required_alpha - feasible_alpha
            needed_capital = (target.target_euros_monthly * 12 / feasible_alpha * 100).quantize(
                Decimal("0.01")
            )
            return (
                f"Target €{target.target_euros_monthly}/month requires {required_alpha}% alpha, "
                f"but only {feasible_alpha}% realistic (gap: {gap}%). "
                f"Consider increasing capital to €{needed_capital} or reducing target."
            )
