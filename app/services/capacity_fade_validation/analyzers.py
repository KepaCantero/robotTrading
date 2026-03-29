"""
T4.1 Capacity Fade Validation - Analyzer Components

Sub-components for capacity fade analysis:
- HistoricalCapacityAnalyzer: Analyzes backtest performance at different capital levels
- LiquidityHeadroom: Calculates daily volume constraints
- AlphaDecayEstimator: Projects alpha at target capital using decay models
"""

import logging
from decimal import Decimal
from typing import Optional

from .models import LiquidityReport

logger = logging.getLogger(__name__)


class HistoricalCapacityAnalyzer:
    """
    Analyzes strategy capacity and how performance degrades with capital scaling.

    Methods:
    - analyze_capacity_impact: Analyzes how alpha decays with capital size
    """

    def __init__(self):
        """Initialize capacity analyzer."""
        logger.info("✅ HistoricalCapacityAnalyzer initialized")

    def analyze_capacity_impact(
        self,
        base_alpha_pct: Decimal,
        backtest_capital_usd: Decimal,
        current_capital_usd: Decimal,
        target_capital_usd: Decimal,
        confidence_level: str = "conservative",
    ) -> dict:
        """
        Analyze capacity impact on alpha using historical data.

        Args:
            base_alpha_pct: Alpha achieved in backtest
            backtest_capital_usd: Capital level used in backtest
            current_capital_usd: Current capital level
            target_capital_usd: Target capital level
            confidence_level: "conservative", "moderate", or "aggressive"

        Returns:
            Dict with capacity analysis metrics
        """
        try:
            # Calculate relative capital scaling
            backtest_to_target_ratio = target_capital_usd / backtest_capital_usd
            target_capital_usd / current_capital_usd

            # Apply fade based on historical degradation patterns
            # Conservative: more fade, moderate: balanced, aggressive: less fade
            fade_factors = {
                "conservative": Decimal("0.65"),  # 35% fade per 10x capital
                "moderate": Decimal("0.75"),  # 25% fade per 10x capital
                "aggressive": Decimal("0.85"),  # 15% fade per 10x capital
            }
            fade_factor = fade_factors.get(confidence_level, fade_factors["conservative"])

            # Estimate fade for each capital scaling
            analysis = {
                "backtest_capital": backtest_capital_usd,
                "current_capital": current_capital_usd,
                "target_capital": target_capital_usd,
                "backtest_to_target_ratio": backtest_to_target_ratio,
                "fade_factor": fade_factor,
                "confidence_level": confidence_level,
            }

            logger.info(f"✅ Capacity impact analyzed: {backtest_to_target_ratio:.2f}x scaling")
            return analysis

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"❌ Capacity impact analysis failed: {e!s}")
            return {"error": str(e)}


class LiquidityHeadroom:
    """
    Calculates position sizing constraints based on daily volume.

    Ensures positions don't exceed safe liquidity limits (typically 5% of daily volume).

    Methods:
    - calculate_headroom: Returns liquidity report for position sizing
    """

    def __init__(self):
        """Initialize liquidity headroom calculator."""
        logger.info("✅ LiquidityHeadroom initialized")

    def calculate_headroom(
        self,
        position_size_usd: Decimal,
        daily_volume_usd: Decimal,
        max_allowed_pct: Optional[Decimal] = None,
    ) -> LiquidityReport:
        """
        Calculate liquidity headroom for a position.

        Args:
            position_size_usd: Size of position in USD
            daily_volume_usd: Average daily trading volume in USD
            max_allowed_pct: Max % of daily volume (default 5%)

        Returns:
            LiquidityReport with headroom analysis
        """
        if max_allowed_pct is None:
            max_allowed_pct = Decimal("5.0")
        try:
            # Calculate percentage of daily volume
            if daily_volume_usd <= 0:
                percent_of_volume = Decimal("100")
                headroom_available = False
                recommended_max = Decimal("0")
                rationale = "Invalid daily volume"
            else:
                percent_of_volume = (position_size_usd / daily_volume_usd) * Decimal("100")
                headroom_available = percent_of_volume <= max_allowed_pct
                recommended_max = daily_volume_usd * (max_allowed_pct / Decimal("100"))

                if headroom_available:
                    rationale = f"Position is {percent_of_volume:.1f}% of daily volume (safe)"
                else:
                    rationale = f"Position is {percent_of_volume:.1f}% of daily volume (exceeds {max_allowed_pct}% limit)"

            report = LiquidityReport(
                position_size_usd=position_size_usd,
                daily_volume_usd=daily_volume_usd,
                percent_of_volume=percent_of_volume,
                headroom_available=headroom_available,
                recommended_max_position=recommended_max,
                rationale=rationale,
            )

            status = "✅" if headroom_available else "⚠️"
            logger.info(f"{status} Liquidity headroom: {percent_of_volume:.1f}% of volume")
            return report

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Headroom calculation failed: {e!s}")
            raise


class AlphaDecayEstimator:
    """
    Estimates alpha at target capital using decay models.

    Models available:
    - sqrt: Square root of capacity scaling (conservative)
    - linear: Linear decay with capital
    - empirical: Historical fade patterns

    Methods:
    - estimate_alpha_at_scale: Projects alpha at target capital
    """

    def __init__(self):
        """Initialize alpha decay estimator."""
        logger.info("✅ AlphaDecayEstimator initialized")

    def estimate_alpha_at_scale(
        self,
        base_alpha_pct: Decimal,
        current_capital_usd: Decimal,
        target_capital_usd: Decimal,
        fade_model: str = "sqrt",
        liquidity_penalty_pct: Optional[Decimal] = None,
    ) -> dict:
        """
        Estimate alpha at target capital using decay model.

        Args:
            base_alpha_pct: Alpha achieved at current/backtest capital
            current_capital_usd: Current capital level
            target_capital_usd: Target capital level
            fade_model: "sqrt", "linear", or "empirical"
            liquidity_penalty_pct: Additional alpha penalty due to liquidity constraints

        Returns:
            Dict with estimated alpha and fade details
        """
        if liquidity_penalty_pct is None:
            liquidity_penalty_pct = Decimal("0")
        try:
            # Calculate capital scaling factor
            capital_ratio = target_capital_usd / current_capital_usd

            # Apply fade based on selected model
            if fade_model == "sqrt":
                # Conservative sqrt(capacity) model
                # Alpha decays as sqrt(capital scaling) implies
                fade_multiplier = Decimal(str(capital_ratio ** Decimal("0.5")))
                estimated_alpha = base_alpha_pct / fade_multiplier
                model_name = "sqrt(capacity) scaling"

            elif fade_model == "linear":
                # Linear decay model (more aggressive)
                decay_rate = Decimal("0.1")  # 10% alpha loss per 2x capital
                fade_multiplier = Decimal("1") + (capital_ratio - Decimal("1")) * decay_rate
                estimated_alpha = base_alpha_pct / fade_multiplier
                model_name = "linear decay"

            else:  # empirical
                # Historical empirical patterns
                # Approximately 25-35% fade per 10x capital
                fade_rate = Decimal("0.03")  # 3% per 1x capital increase
                fade_multiplier = Decimal("1") + (capital_ratio - Decimal("1")) * fade_rate
                estimated_alpha = base_alpha_pct / fade_multiplier
                model_name = "empirical historical pattern"

            # Apply liquidity penalty
            if liquidity_penalty_pct > 0:
                estimated_alpha = estimated_alpha * (
                    Decimal("1") - (liquidity_penalty_pct / Decimal("100"))
                )

            fade_ratio = base_alpha_pct - estimated_alpha if base_alpha_pct > 0 else Decimal("0")
            fade_pct = (
                (fade_ratio / base_alpha_pct * Decimal("100"))
                if base_alpha_pct > 0
                else Decimal("0")
            )

            result = {
                "base_alpha_pct": base_alpha_pct,
                "estimated_alpha_pct": estimated_alpha,
                "capital_scaling_ratio": capital_ratio,
                "fade_ratio": fade_ratio,
                "fade_pct": fade_pct,
                "model": model_name,
                "liquidity_penalty_pct": liquidity_penalty_pct,
            }

            logger.info(
                f"✅ Alpha decay estimated: {base_alpha_pct:.2f}% → {estimated_alpha:.2f}% "
                f"({fade_pct:.1f}% fade) at {capital_ratio:.2f}x capital using {model_name}"
            )
            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Alpha decay estimation failed: {e!s}")
            return {"error": str(e)}

    def calculate_required_alpha(
        self,
        target_monthly_return_usd: Decimal,
        target_capital_usd: Decimal,
    ) -> Decimal:
        """
        Calculate minimum alpha required for target returns.

        Args:
            target_monthly_return_usd: Target monthly return in USD
            target_capital_usd: Target capital level

        Returns:
            Required alpha percentage
        """
        try:
            if target_capital_usd <= 0:
                return Decimal("0")

            annual_return = target_monthly_return_usd * Decimal("12")
            required_alpha = (annual_return / target_capital_usd) * Decimal("100")

            logger.info(
                f"✅ Required alpha: {required_alpha:.2f}% for €{target_monthly_return_usd:,.0f}/month"
            )
            return required_alpha

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Required alpha calculation failed: {e!s}")
            return Decimal("0")
