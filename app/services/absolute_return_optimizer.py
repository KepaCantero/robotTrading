"""
PHASE 1 T1.2 - Absolute Return Optimizer

Transforms profit targets (€800/month) into optimized trading parameters.

This service is the bridge between strategic goals (T1.2) and operational execution.

Workflow:
1. Accept profit target (€800/month) and expected monthly alpha from backtesting
2. Calculate required alpha working backwards from profit goal
3. Estimate capacity fade (alpha decay as capital increases)
4. Scale position sizing and leverage to achieve target within risk constraints
5. Validate feasibility and return optimized parameters

Architecture:
Orchestrates 5 specialist components:
- AlphaTargetCalculator: €800 goal → required alpha
- CapacityFadeAnalyzer: Estimate alpha decay with capital
- ParameterScaler: Adjust position sizing for target
- ReturnDistributionValidator: Statistical feasibility check
- MonthlyProfitForecaster: P&L projections and confidence intervals

Integration Points:
- Consumes: CapitalTierStrategySelector outputs (RiskProfile, StrategySelection)
- Uses: AccountConfiguration for tier definitions
- Calls: DeploymentValidator for final safety gates
- Respects: Risk limits as hard constraints (not optional)
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Tuple

from app.services.account_configuration import AccountConfiguration, AccountTier
from app.services.capital_tier_strategy_selector import RiskProfile
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class AlphaTarget:
    """
    Required alpha to achieve profit goal.

    Attributes:
        monthly_profit_goal: Target monthly profit (e.g., €800)
        monthly_alpha_needed: Required alpha before costs/taxes
        gross_profit_needed: After execution costs but before taxes
        net_profit_expected: After taxes (goal amount)
        confidence_score: 0-100% likelihood of achieving this target
        reasoning: Explanation of calculation
    """

    monthly_profit_goal: Decimal
    monthly_alpha_needed: Decimal
    gross_profit_needed: Decimal
    net_profit_expected: Decimal
    confidence_score: Decimal  # 0-100
    reasoning: str = ""

    def validate(self) -> Tuple[bool, str]:
        """Validate alpha target parameters"""
        if self.monthly_profit_goal <= Decimal("0"):
            return False, "monthly_profit_goal must be > 0"
        if self.monthly_alpha_needed <= Decimal("0"):
            return False, "monthly_alpha_needed must be > 0"
        if not (Decimal("0") <= self.confidence_score <= Decimal("100")):
            return False, "confidence_score must be between 0-100"
        return True, "Alpha target valid"


@dataclass
class CapacityFadeEstimate:
    """
    Alpha decay with increasing capital.

    Historical observation: Alpha decreases as capital scales due to:
    - Market impact from larger positions
    - Crowding (more capital following same strategy)
    - Liquidity constraints
    - Slippage on larger orders

    Attributes:
        capital: Current capital
        base_monthly_alpha: Alpha from backtesting at current scale
        estimated_decay_rate: % decay per 10x capital (e.g., 0.10 = 10% decay)
        adjusted_alpha: After accounting for capacity fade
        alpha_at_2x_capital: Projected alpha if capital doubles
        alpha_at_5x_capital: Projected alpha if capital goes to 5x
    """

    capital: Decimal
    base_monthly_alpha: Decimal
    estimated_decay_rate: Decimal  # % decay per 10x (0.0-1.0)
    adjusted_alpha: Decimal
    alpha_at_2x_capital: Decimal
    alpha_at_5x_capital: Decimal
    reasoning: str = ""

    def validate(self) -> Tuple[bool, str]:
        """Validate capacity fade estimate"""
        if self.base_monthly_alpha <= Decimal("0"):
            return False, "base_monthly_alpha must be > 0"
        if not (Decimal("0") <= self.estimated_decay_rate <= Decimal("1")):
            return False, "estimated_decay_rate must be between 0-1"
        if self.adjusted_alpha > self.base_monthly_alpha:
            return False, "adjusted_alpha cannot exceed base_monthly_alpha"
        return True, "Capacity fade estimate valid"


@dataclass
class OptimizedParameters:
    """
    Optimized trading parameters for achieving profit target.

    These parameters balance profit target achievement with risk constraints.
    All values are validated to stay within RiskProfile limits.

    Attributes:
        position_size_pct: Recommended % of capital per trade
        position_size_usd: USD amount per position
        leverage_multiplier: Leverage allowed (1.0x to 2.5x by tier)
        max_concurrent_trades: Maximum simultaneous positions
        monthly_target_return: Target monthly return % (e.g., 0.32% for €800 on €250k)
        required_monthly_alpha: Alpha needed to achieve target
        feasibility_score: 0-100% likelihood of achieving target
        confidence_level: "high" / "medium" / "low"
        risk_level: "conservative" / "balanced" / "aggressive"
        constraints: List of limiting factors
        recommendations: List of improvements
    """

    position_size_pct: Decimal
    position_size_usd: Decimal
    leverage_multiplier: Decimal
    max_concurrent_trades: int
    monthly_target_return: Decimal
    required_monthly_alpha: Decimal
    feasibility_score: Decimal  # 0-100
    confidence_level: str  # high/medium/low
    risk_level: str  # conservative/balanced/aggressive
    constraints: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def validate(self) -> Tuple[bool, str]:
        """Validate optimized parameters"""
        if self.position_size_pct <= Decimal("0"):
            return False, "position_size_pct must be > 0"
        if self.position_size_usd <= Decimal("0"):
            return False, "position_size_usd must be > 0"
        if self.leverage_multiplier < Decimal("1"):
            return False, "leverage_multiplier must be >= 1.0"
        if self.max_concurrent_trades < 1:
            return False, "max_concurrent_trades must be >= 1"
        if not (Decimal("0") <= self.feasibility_score <= Decimal("100")):
            return False, "feasibility_score must be between 0-100"
        if self.confidence_level not in ["high", "medium", "low"]:
            return False, "confidence_level must be high/medium/low"
        return True, "Optimized parameters valid"


@dataclass
class MonthlyProfitForecast:
    """
    P&L projection given optimized parameters.

    Provides statistical confidence intervals and probability of target achievement.

    Attributes:
        expected_monthly_profit: Expected profit in EUR/USD
        profit_confidence_interval: (5th percentile, 95th percentile)
        expected_monthly_trades: Estimated number of trades
        expected_win_rate: Probability of winning trade (0-1)
        expected_sharpe_ratio: Risk-adjusted return metric
        expected_max_drawdown: Expected maximum loss from peak
        probability_of_target: % chance of achieving profit goal
        percentile_5: 5th percentile P&L
        percentile_95: 95th percentile P&L
    """

    expected_monthly_profit: Decimal
    profit_confidence_interval: Tuple[Decimal, Decimal]
    expected_monthly_trades: int
    expected_win_rate: Decimal
    expected_sharpe_ratio: Decimal
    expected_max_drawdown: Decimal
    probability_of_target: Decimal  # 0-100%
    percentile_5: Decimal
    percentile_95: Decimal

    def validate(self) -> Tuple[bool, str]:
        """Validate profit forecast"""
        if self.expected_monthly_trades < 0:
            return False, "expected_monthly_trades must be >= 0"
        if not (Decimal("0") <= self.expected_win_rate <= Decimal("1")):
            return False, "expected_win_rate must be between 0-1"
        if self.expected_max_drawdown > Decimal("0"):
            return False, "expected_max_drawdown should be <= 0"
        if not (Decimal("0") <= self.probability_of_target <= Decimal("100")):
            return False, "probability_of_target must be between 0-100"
        return True, "Profit forecast valid"


@dataclass
class FeasibilityReport:
    """
    Is the profit goal achievable?

    Provides detailed assessment of goal feasibility with constraints and recommendations.

    Attributes:
        is_feasible: Can goal be achieved?
        confidence_level: "high" / "medium" / "low" / "not_feasible"
        required_alpha: Alpha needed for goal
        available_alpha: Alpha expected from backtesting
        gap: Shortfall (negative = need more alpha)
        tier: Account tier (micro/small/medium/large)
        constraints: Limiting factors preventing goal
        recommendations: Actions to improve feasibility
        deployment_status: APPROVED / RESTRICTED / REJECTED
    """

    is_feasible: bool
    confidence_level: str
    required_alpha: Decimal
    available_alpha: Decimal
    gap: Decimal
    tier: str
    constraints: List[str]
    recommendations: List[str]
    deployment_status: str  # APPROVED / RESTRICTED / REJECTED


# ============================================================================
# SPECIALIST COMPONENTS (Step 1 includes all component classes)
# ============================================================================


class AlphaTargetCalculator:
    """
    Calculate required alpha to achieve profit goal.

    Works backwards from profit goal:
    1. €800 profit goal (user specified)
    2. Apply tax rate (20%) → €1000 gross profit needed
    3. Apply execution costs → €1200+ alpha required
    4. Return AlphaTarget with confidence scoring
    """

    @staticmethod
    def calculate_required_alpha(
        monthly_profit_goal: Decimal,
        tax_rate: Decimal = Decimal("0.20"),
        commission_per_trade: Decimal = Decimal("10"),
        expected_trades_per_month: int = 10,
    ) -> AlphaTarget:
        """
        Calculate alpha required to achieve profit goal.

        Args:
            monthly_profit_goal: Target monthly profit (e.g., €800)
            tax_rate: Tax rate on profits (default 20%)
            commission_per_trade: Commission per trade (default $10)
            expected_trades_per_month: Estimated trades (for cost calculation)

        Returns:
            AlphaTarget with required alpha and confidence score

        Example:
            goal = €800/month
            → need €1000 gross (after tax)
            → need €1100+ alpha (after commissions)
        """
        if monthly_profit_goal <= Decimal("0"):
            raise ValueError("monthly_profit_goal must be > 0")

        # Step 1: Net goal is the input (after-tax target)
        net_profit_goal = monthly_profit_goal

        # Step 2: Calculate gross profit needed (before tax)
        # net = gross * (1 - tax_rate)
        # gross = net / (1 - tax_rate)
        gross_profit_needed = net_profit_goal / (Decimal("1") - tax_rate)

        # Step 3: Add execution costs
        total_trading_costs = commission_per_trade * Decimal(expected_trades_per_month)

        # Alpha = Gross Profit + Trading Costs
        monthly_alpha_needed = gross_profit_needed + total_trading_costs

        # Confidence scoring (how realistic is this goal?)
        # Lower goals = easier, higher confidence
        # Higher goals = harder, lower confidence
        # Factors: goal size and cost-to-goal ratio
        # €100/month = very conservative (high confidence ~90%)
        # €800/month = realistic (medium confidence ~70%)
        # €5000/month = aggressive (low confidence ~40%)
        goal_factor = (monthly_profit_goal / Decimal("1000")) * Decimal(
            "10"
        )  # Larger goals = less confidence
        cost_ratio = (monthly_alpha_needed - monthly_profit_goal) / (
            monthly_profit_goal + Decimal("1")
        )
        cost_factor = cost_ratio * Decimal("5")  # Higher costs relative to goal = less confidence
        confidence_score = Decimal("100") - goal_factor - cost_factor
        confidence_score = max(Decimal("10"), min(Decimal("100"), confidence_score))

        reasoning = (
            f"Goal €{monthly_profit_goal:,.0f}/month → "
            f"€{gross_profit_needed:,.0f} gross (after {tax_rate:.0%} tax) → "
            f"€{monthly_alpha_needed:,.0f} alpha needed (incl. €{total_trading_costs:,.0f} costs)"
        )

        return AlphaTarget(
            monthly_profit_goal=monthly_profit_goal,
            monthly_alpha_needed=monthly_alpha_needed,
            gross_profit_needed=gross_profit_needed,
            net_profit_expected=net_profit_goal,
            confidence_score=confidence_score,
            reasoning=reasoning,
        )


class CapacityFadeAnalyzer:
    """
    Estimate alpha decay as capital scales.

    Historical observation: Alpha decreases with capital due to:
    - Market impact (larger positions move markets)
    - Crowding (more capital following same strategy)
    - Liquidity constraints (harder to enter/exit large positions)
    - Slippage increases on larger orders

    Empirical decay: ~5-15% per 10x capital increase
    """

    # Empirical decay rates by tier and strategy type
    DECAY_RATE_BY_TIER = {
        AccountTier.MICRO: Decimal("0.05"),  # 5% per 10x (minimal impact at small scale)
        AccountTier.SMALL: Decimal("0.08"),  # 8% per 10x
        AccountTier.MEDIUM: Decimal("0.12"),  # 12% per 10x
        AccountTier.LARGE: Decimal("0.15"),  # 15% per 10x (more impact at large scale)
    }

    @staticmethod
    def estimate_capacity_fade(
        capital: Decimal,
        base_monthly_alpha: Decimal,
        tier: AccountTier = None,
        current_capital_reference: Decimal = Decimal("100000"),
    ) -> CapacityFadeEstimate:
        """
        Estimate alpha decay from current to target capital.

        Args:
            capital: Target capital level
            base_monthly_alpha: Alpha at reference capital level
            tier: Account tier (determines decay rate)
            current_capital_reference: Reference capital where base_alpha was achieved

        Returns:
            CapacityFadeEstimate with projections at 2x and 5x capital
        """
        if base_monthly_alpha <= Decimal("0"):
            raise ValueError("base_monthly_alpha must be > 0")

        # Determine decay rate based on tier
        if tier is None:
            tier = AccountConfiguration.get_tier(capital)

        decay_rate = CapacityFadeAnalyzer.DECAY_RATE_BY_TIER.get(tier, Decimal("0.10"))

        # Calculate capital scaling factor
        # If we're scaling from €100k reference to €250k actual
        capital_ratio = capital / current_capital_reference

        # Apply decay logarithmically (each 10x = decay_rate decay)
        # Using formula: alpha_final = alpha_base * ((1 - decay_rate) ^ log10(ratio))
        import math

        if capital_ratio > Decimal("1"):
            # Scaling up: apply decay
            log10_ratio = Decimal(math.log10(float(capital_ratio)))
            decay_multiplier = Decimal((1 - float(decay_rate)) ** float(log10_ratio))
        else:
            # Scaling down: slightly improve alpha (but cap at 1.0)
            decay_multiplier = min(Decimal("1"), Decimal("1") / capital_ratio)

        adjusted_alpha = base_monthly_alpha * decay_multiplier

        # Project at 2x and 5x capital (compute directly without recursion)
        capital_ratio_2x = (capital * Decimal("2")) / current_capital_reference
        capital_ratio_5x = (capital * Decimal("5")) / current_capital_reference

        if capital_ratio_2x > Decimal("1"):
            log10_ratio_2x = Decimal(math.log10(float(capital_ratio_2x)))
            decay_multiplier_2x = Decimal((1 - float(decay_rate)) ** float(log10_ratio_2x))
        else:
            decay_multiplier_2x = min(Decimal("1"), Decimal("1") / capital_ratio_2x)
        alpha_2x = base_monthly_alpha * decay_multiplier_2x

        if capital_ratio_5x > Decimal("1"):
            log10_ratio_5x = Decimal(math.log10(float(capital_ratio_5x)))
            decay_multiplier_5x = Decimal((1 - float(decay_rate)) ** float(log10_ratio_5x))
        else:
            decay_multiplier_5x = min(Decimal("1"), Decimal("1") / capital_ratio_5x)
        alpha_5x = base_monthly_alpha * decay_multiplier_5x

        reasoning = (
            f"Capital scaling {current_capital_reference:,.0f} → {capital:,.0f} "
            f"({float(capital_ratio):.1f}x) with {tier.value} decay rate ({decay_rate:.0%}/10x) "
            f"→ Alpha: {base_monthly_alpha:,.0f} → {adjusted_alpha:,.0f}"
        )

        return CapacityFadeEstimate(
            capital=capital,
            base_monthly_alpha=base_monthly_alpha,
            estimated_decay_rate=decay_rate,
            adjusted_alpha=adjusted_alpha,
            alpha_at_2x_capital=alpha_2x,
            alpha_at_5x_capital=alpha_5x,
            reasoning=reasoning,
        )


class ParameterScaler:
    """
    Scale position sizing and leverage to achieve monthly target.

    Ensures parameters stay within RiskProfile constraints while
    optimizing to hit the target return.
    """

    @staticmethod
    def scale_for_target(
        capital: Decimal,
        monthly_target_return: Decimal,
        expected_win_rate: Decimal,
        risk_profile: RiskProfile,
    ) -> OptimizedParameters:
        """
        Scale position sizing to achieve target return.

        Args:
            capital: Account capital
            monthly_target_return: Target monthly return % (e.g., 0.0032 for 0.32%)
            expected_win_rate: Expected win rate from backtesting
            risk_profile: Risk constraints from T1.1

        Returns:
            OptimizedParameters with position sizing scaled for target
        """
        if capital <= Decimal("0"):
            raise ValueError("capital must be > 0")
        if expected_win_rate <= Decimal("0") or expected_win_rate > Decimal("1"):
            raise ValueError("expected_win_rate must be between 0-1")

        # Determine confidence level based on target
        if monthly_target_return < Decimal("0.005"):  # < 0.5%
            confidence_level = "high"
            feasibility_score = Decimal("85")
        elif monthly_target_return < Decimal("0.01"):  # < 1%
            confidence_level = "medium"
            feasibility_score = Decimal("70")
        else:  # >= 1%
            confidence_level = "low"
            feasibility_score = Decimal("50")

        # Calculate position size needed for target
        # Position sizing = (Target Return * Capital) / (Win Rate * Avg Win)
        # Simplified: use fixed position size based on tier
        max_position = capital * risk_profile.max_position_size

        # Constraints
        constraints = []
        recommendations = []

        # Check leverage
        if risk_profile.leverage_allowed < Decimal("1.5"):
            constraints.append(f"Leverage limited to {risk_profile.leverage_allowed}x")

        # Check position size
        if max_position < Decimal("5000"):
            constraints.append(f"Position size limited to €{max_position:,.0f}")

        # Check daily loss limit
        daily_loss_limit = capital * risk_profile.max_daily_loss_pct
        if daily_loss_limit < capital * monthly_target_return / Decimal("20"):
            constraints.append(
                f"Daily loss limit (€{daily_loss_limit:,.0f}) may constrain positions"
            )

        required_alpha = capital * monthly_target_return

        return OptimizedParameters(
            position_size_pct=risk_profile.max_position_size,
            position_size_usd=max_position,
            leverage_multiplier=risk_profile.leverage_allowed,
            max_concurrent_trades=risk_profile.max_concurrent_trades,
            monthly_target_return=monthly_target_return,
            required_monthly_alpha=required_alpha,
            feasibility_score=feasibility_score,
            confidence_level=confidence_level,
            risk_level=risk_profile.tier,
            constraints=constraints,
            recommendations=recommendations,
        )


class ReturnDistributionValidator:
    """
    Validate that profit target is statistically realistic.

    Uses historical backtest statistics to assess likelihood of achieving target.
    """

    @staticmethod
    def validate_achievability(
        target_monthly_return: Decimal,
        expected_monthly_alpha: Decimal,
        historical_mean: Decimal = None,
        historical_std: Decimal = None,
    ) -> Tuple[bool, str]:
        """
        Check if target is statistically reasonable.

        Args:
            target_monthly_return: Target monthly return %
            expected_monthly_alpha: Expected alpha from backtesting
            historical_mean: Historical mean return (optional)
            historical_std: Historical std dev (optional)

        Returns:
            (is_achievable: bool, reasoning: str)
        """
        if expected_monthly_alpha <= Decimal("0"):
            return False, f"Expected alpha {expected_monthly_alpha:,.0f} insufficient"

        if target_monthly_return > expected_monthly_alpha:
            gap = target_monthly_return - expected_monthly_alpha
            return False, f"Target exceeds expected alpha by {gap:,.0f}"

        return (
            True,
            f"Target {target_monthly_return:,.0f} achievable with alpha {expected_monthly_alpha:,.0f}",
        )


class MonthlyProfitForecaster:
    """
    Forecast monthly P&L given optimized parameters.

    Provides confidence intervals and probability of achieving target.
    """

    @staticmethod
    def forecast_profit(
        position_size: Decimal,
        expected_win_rate: Decimal,
        avg_win_loss_ratio: Decimal = Decimal("1.5"),
        expected_monthly_trades: int = 15,
        sharpe_ratio: Decimal = Decimal("1.5"),
    ) -> MonthlyProfitForecast:
        """
        Forecast monthly profit given trading parameters.

        Args:
            position_size: Position size (USD)
            expected_win_rate: Expected win rate (0-1)
            avg_win_loss_ratio: Avg win / avg loss ratio
            expected_monthly_trades: Expected trades per month
            sharpe_ratio: Sharpe ratio from backtesting

        Returns:
            MonthlyProfitForecast with confidence intervals
        """
        if position_size <= Decimal("0"):
            raise ValueError("position_size must be > 0")

        # Simple profit calculation
        # Expected Profit = Position * Win Rate * Avg Win - Position * (1-Win Rate) * Avg Loss
        # Simplified: Expected Profit ≈ Position * Win Rate * 0.01 (rough estimate)
        expected_profit = position_size * expected_win_rate * Decimal("0.01")

        # Confidence interval (5th-95th percentile)
        # Rough approximation: ±1.96 * std_dev (95% confidence)
        std_dev = expected_profit * (Decimal("1") - expected_win_rate)
        percentile_5 = expected_profit - (Decimal("1.645") * std_dev)
        percentile_95 = expected_profit + (Decimal("1.645") * std_dev)

        # Probability of achieving any target (50% = break even)
        probability_of_target = (expected_win_rate * Decimal("100")).min(Decimal("95"))

        return MonthlyProfitForecast(
            expected_monthly_profit=expected_profit,
            profit_confidence_interval=(percentile_5, percentile_95),
            expected_monthly_trades=expected_monthly_trades,
            expected_win_rate=expected_win_rate,
            expected_sharpe_ratio=sharpe_ratio,
            expected_max_drawdown=-position_size
            * (Decimal("1") - expected_win_rate)
            * Decimal("0.10"),
            probability_of_target=probability_of_target,
            percentile_5=percentile_5,
            percentile_95=percentile_95,
        )


# ============================================================================
# CORE SERVICE CLASS
# ============================================================================


class AbsoluteReturnOptimizer:
    """
    Optimize trading parameters to achieve absolute return target.

    This service transforms a profit goal (€800/month) into operational
    parameters that balance target achievement with risk management.

    Workflow:
    1. Accept profit target (€800) + expected alpha from backtesting
    2. Calculate required alpha (accounting for costs and taxes)
    3. Estimate capacity fade (alpha decay with capital)
    4. Validate feasibility statistically
    5. Scale parameters to achieve target
    6. Return OptimizedParameters for deployment

    Integration:
    - Consumes: CapitalTierStrategySelector outputs (RiskProfile, StrategySelection)
    - Uses: AccountConfiguration for tier definitions
    - Calls: DeploymentValidator for final safety validation
    - Respects: Risk limits as hard constraints

    Usage:
        optimizer = AbsoluteReturnOptimizer(
            capital=Decimal("250000"),
            account_id="ACC_001"
        )
        result = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500")
        )
    """

    def __init__(self, capital: Decimal, account_id: str = None):
        """
        Initialize Absolute Return Optimizer.

        Args:
            capital: Account capital (EUR/USD)
            account_id: Account identifier for logging

        Raises:
            ValueError: If capital <= 0
        """
        if capital <= Decimal("0"):
            raise ValueError("Capital must be > 0")

        self.capital = capital
        self.account_id = account_id
        self.tier = AccountConfiguration.get_tier(capital)

        logger.info(
            f"[{account_id or 'UNKNOWN'}] Initialized AbsoluteReturnOptimizer: "
            f"capital={capital:,.0f}, tier={self.tier.value}"
        )

    def optimize_for_target(
        self,
        monthly_profit_goal: Decimal,
        expected_monthly_alpha: Decimal,
        risk_profile: Optional[RiskProfile] = None,
        tax_rate: Decimal = Decimal("0.20"),
        commission_per_trade: Decimal = Decimal("10"),
    ) -> Tuple[OptimizedParameters, FeasibilityReport]:
        """
        Optimize parameters to achieve monthly profit goal.

        Args:
            monthly_profit_goal: Target monthly profit (e.g., €800)
            expected_monthly_alpha: Expected alpha from backtesting
            risk_profile: Risk constraints from CapitalTierStrategySelector
            tax_rate: Tax rate on profits (default 20%)
            commission_per_trade: Commission per trade (default €10)

        Returns:
            (OptimizedParameters, FeasibilityReport) with optimization results

        Process:
        1. Calculate required alpha from goal
        2. Estimate capacity fade at current capital
        3. Validate feasibility
        4. Scale parameters within constraints
        5. Generate forecast
        """
        # If no risk profile provided, use safe defaults
        if risk_profile is None:
            config = AccountConfiguration.get_configuration(self.capital)
            risk_profile = RiskProfile(
                tier=self.tier.value,
                max_position_size=config.get("position_size_pct", Decimal("0.05")),
                max_concurrent_trades=config.get("max_concurrent_trades", 2),
                max_daily_loss_pct=Decimal(
                    str(getattr(get_config().trading, 'max_daily_loss_pct', 0.02))
                ),  # Use centralized config
                max_drawdown_pct=Decimal("0.10"),
                leverage_allowed=Decimal("1.5"),
                learning_enabled=config.get("learning_enabled", False),
                modules_enabled={},
                position_sizing_strategy="fixed_pct",
            )

        # Step 1: Calculate required alpha
        alpha_target = AlphaTargetCalculator.calculate_required_alpha(
            monthly_profit_goal=monthly_profit_goal,
            tax_rate=tax_rate,
            commission_per_trade=commission_per_trade,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Alpha target calculated: "
            f"goal={monthly_profit_goal:,.0f} → required_alpha={alpha_target.monthly_alpha_needed:,.0f}"
        )

        # Step 2: Estimate capacity fade
        capacity_fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=self.capital,
            base_monthly_alpha=expected_monthly_alpha,
            tier=self.tier,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Capacity fade estimated: "
            f"base_alpha={capacity_fade.base_monthly_alpha:,.0f} → "
            f"adjusted_alpha={capacity_fade.adjusted_alpha:,.0f}"
        )

        # Step 3: Calculate monthly target return
        monthly_target_return = monthly_profit_goal / self.capital

        # Step 4: Validate feasibility
        is_feasible, reason = ReturnDistributionValidator.validate_achievability(
            target_monthly_return=alpha_target.monthly_alpha_needed / self.capital,
            expected_monthly_alpha=capacity_fade.adjusted_alpha,
        )

        # Step 5: Scale parameters
        optimized = ParameterScaler.scale_for_target(
            capital=self.capital,
            monthly_target_return=monthly_target_return,
            expected_win_rate=Decimal("0.55"),  # Typical win rate
            risk_profile=risk_profile,
        )

        # Step 6: Generate feasibility report
        gap = capacity_fade.adjusted_alpha - alpha_target.monthly_alpha_needed

        if is_feasible and gap >= Decimal("0"):
            deployment_status = "APPROVED"
            confidence = "high"
            constraints = []
        elif gap >= Decimal("-100"):  # Small shortfall
            deployment_status = "RESTRICTED"
            confidence = "medium"
            constraints = [f"Alpha shortfall of €{abs(gap):,.0f}/month"]
        else:
            deployment_status = "REJECTED"
            confidence = "not_feasible"
            constraints = [f"Alpha shortfall of €{abs(gap):,.0f}/month - gap too large"]

        feasibility_report = FeasibilityReport(
            is_feasible=(deployment_status in ["APPROVED", "RESTRICTED"]),
            confidence_level=confidence,
            required_alpha=alpha_target.monthly_alpha_needed,
            available_alpha=capacity_fade.adjusted_alpha,
            gap=gap,
            tier=self.tier.value,
            constraints=constraints,
            recommendations=[],
            deployment_status=deployment_status,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Optimization complete: "
            f"status={deployment_status}, gap={gap:,.0f}, feasibility={confidence}"
        )

        return optimized, feasibility_report

    def validate_feasibility(
        self,
        monthly_profit_goal: Decimal,
        expected_monthly_alpha: Decimal,
    ) -> FeasibilityReport:
        """
        Check if profit goal is feasible without optimization.

        Args:
            monthly_profit_goal: Target monthly profit
            expected_monthly_alpha: Expected alpha from backtesting

        Returns:
            FeasibilityReport with assessment
        """
        alpha_target = AlphaTargetCalculator.calculate_required_alpha(
            monthly_profit_goal=monthly_profit_goal
        )

        capacity_fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=self.capital,
            base_monthly_alpha=expected_monthly_alpha,
            tier=self.tier,
        )

        gap = capacity_fade.adjusted_alpha - alpha_target.monthly_alpha_needed

        return FeasibilityReport(
            is_feasible=gap >= Decimal("0"),
            confidence_level="high" if gap >= Decimal("0") else "low",
            required_alpha=alpha_target.monthly_alpha_needed,
            available_alpha=capacity_fade.adjusted_alpha,
            gap=gap,
            tier=self.tier.value,
            constraints=[] if gap >= Decimal("0") else [f"Alpha shortfall: €{abs(gap):,.0f}"],
            recommendations=["Increase alpha" if gap < Decimal("0") else ["Goal achievable"]],
            deployment_status="APPROVED" if gap >= Decimal("0") else "REJECTED",
        )

    def forecast_monthly_profit(
        self,
        position_size: Decimal,
        expected_win_rate: Decimal,
        avg_win_loss_ratio: Decimal = Decimal("1.5"),
        expected_monthly_trades: int = 15,
    ) -> MonthlyProfitForecast:
        """
        Forecast monthly P&L given trading parameters.

        Args:
            position_size: Position size (EUR/USD)
            expected_win_rate: Expected win rate (0-1)
            avg_win_loss_ratio: Average win / average loss
            expected_monthly_trades: Expected trades per month

        Returns:
            MonthlyProfitForecast with confidence intervals
        """
        return MonthlyProfitForecaster.forecast_profit(
            position_size=position_size,
            expected_win_rate=expected_win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio,
            expected_monthly_trades=expected_monthly_trades,
        )
