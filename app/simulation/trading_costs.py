"""
Trading Costs Analysis - Larry Harris's Trading Cost Framework

This module implements the trading costs analysis framework from Harris,
Chapter 8: "Trading Costs" and Chapter 9: "Trading Cost Evaluation."

Key concepts implemented:
1. Bid-ask spread impact
2. Market impact modeling
3. Timing risk
4. Execution cost breakdown
5. Cost-benefit analysis of trading decisions

Reference:
    Harris, L. (2003). Trading and Exchanges, Chapters 8-9.
"""
# mypy: ignore-errors

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CostComponent(Enum):
    """Components of trading costs."""

    COMMISSION = "COMMISSION"
    SPREAD = "SPREAD"
    MARKET_IMPACT = "MARKET_IMPACT"
    TIMING_RISK = "TIMING_RISK"
    TIMING_COST = "TIMING_COST"
    DELAY_COST = "DELAY_COST"
    OPPORTUNITY_COST = "OPPORTUNITY_COST"
    PRICE_IMPACT = "PRICE_IMPACT"


class ImpactModel(Enum):
    """Market impact model types."""

    LINEAR = "LINEAR"  # Impact = k * participation_rate
    SQUARE_ROOT = "SQUARE_ROOT"  # Impact = k * sqrt(participation_rate)
    POWER_LAW = "POWER_LAW"  # Impact = k * participation_rate^alpha
    ALMGREN_CHRISS = "ALMGREN_CHRISS"  # Almgren-Chriss model
    STATIC = "STATIC"  # Fixed impact per share


@dataclass
class CostBreakdown:
    """
    Detailed breakdown of trading costs.

    Attributes:
        symbol: Trading symbol
        side: Buy or sell
        quantity: Order quantity
        execution_price: Average execution price
        benchmark_price: Benchmark price (arrival, decision, etc.)
        components: Cost components by type
        total_cost: Total cost in currency
        total_cost_bps: Total cost in basis points
        effective_spread: Effective half-spread
        realized_spread: Realized spread after reversal
        implementation_shortfall: Implementation shortfall
        saving_vs_benchmark: Savings relative to benchmark
    """

    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal
    benchmark_price: Decimal
    components: Dict[CostComponent, Decimal] = field(default_factory=dict)
    total_cost: Decimal = Decimal("0")
    total_cost_bps: Decimal = Decimal("0")
    effective_spread: Decimal = Decimal("0")
    realized_spread: Optional[Decimal] = None
    implementation_shortfall: Decimal = Decimal("0")
    saving_vs_benchmark: Decimal = Decimal("0")

    @property
    def cost_percentage(self) -> Decimal:
        """Total cost as percentage of notional value."""
        notional = self.quantity * self.benchmark_price
        if notional == 0:
            return Decimal("0")
        return (self.total_cost / notional) * Decimal("100")


@dataclass
class ExecutionQualityMetrics:
    """
    Execution quality metrics.

    Attributes:
        symbol: Trading symbol
        execution_id: Execution identifier
        fill_rate: Percentage of order filled
        avg_fill_price: Average fill price
        benchmark_prices: Various benchmark prices
        effective_spread_bps: Effective spread in bps
        price_improvement_bps: Price improvement in bps
        timing_cost_bps: Timing cost in bps
        market_impact_bps: Market impact in bps
        implementation_shortfall_bps: Implementation shortfall in bps
        execution_score: Overall execution score (0-100)
    """

    symbol: str
    execution_id: str
    fill_rate: Decimal
    avg_fill_price: Decimal
    benchmark_prices: Dict[str, Decimal]
    effective_spread_bps: Decimal
    price_improvement_bps: Decimal = Decimal("0")
    timing_cost_bps: Decimal = Decimal("0")
    market_impact_bps: Decimal = Decimal("0")
    implementation_shortfall_bps: Optional[Decimal] = None
    execution_score: float = 0.0

    @property
    def excellent_execution(self) -> bool:
        """Check if execution quality is excellent (score >= 80)."""
        return self.execution_score >= 80

    @property
    def poor_execution(self) -> bool:
        """Check if execution quality is poor (score < 50)."""
        return self.execution_score < 50


class MarketImpactModel:
    """
    Market Impact Model.

    Models the price impact of trading based on order size and market conditions.
    Implements Harris's discussion of market impact in Chapter 8.

    Impact models:
    1. Linear: Impact proportional to participation rate
    2. Square root: Impact proportional to sqrt(participation)
    3. Power law: Impact = k * participation^alpha
    4. Almgren-Chriss: Temporary + permanent impact

    Reference:
        Harris, L. (2003). Trading and Exchanges, Chapter 8,
        "Liquidity and Market Depth"
        Almgren, R., & Chriss, N. (2001). "Optimal Execution of
        Portfolio Transactions."
    """

    def __init__(
        self,
        model_type: ImpactModel = ImpactModel.SQUARE_ROOT,
        daily_volume: Optional[float] = None,
        alpha: float = 0.5,
        k_temporary: float = 0.1,
        k_permanent: float = 0.05,
    ):
        """
        Initialize market impact model.

        Args:
            model_type: Type of impact model
            daily_volume: Average daily volume (for participation calculation)
            alpha: Power law exponent (default 0.5 for square root)
            k_temporary: Temporary impact coefficient
            k_permanent: Permanent impact coefficient
        """
        self.model_type = model_type
        self.daily_volume = daily_volume
        self.alpha = alpha
        self.k_temporary = k_temporary
        self.k_permanent = k_permanent

    def calculate_impact(
        self,
        order_quantity: float,
        current_price: float,
        adv: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Calculate market impact for an order.

        Returns:
            (temporary_impact, permanent_impact) as fractions of price

        Args:
            order_quantity: Order quantity
            current_price: Current price
            adv: Average daily volume (overrides default)
            volatility: Price volatility (for some models)
        """
        adv_to_use = adv or self.daily_volume

        if adv_to_use is None or adv_to_use == 0:
            return 0.0, 0.0

        # Calculate participation rate
        participation_rate = order_quantity / adv_to_use

        if self.model_type == ImpactModel.LINEAR:
            # Linear impact
            impact = self.k_permanent * participation_rate
            return impact * 0.3, impact  # 30% temporary, 70% permanent

        elif self.model_type == ImpactModel.SQUARE_ROOT:
            # Square root impact
            impact = self.k_permanent * np.sqrt(participation_rate)
            return impact * 0.4, impact * 0.6  # 40% temporary, 60% permanent

        elif self.model_type == ImpactModel.POWER_LAW:
            # Power law impact
            impact = self.k_permanent * (participation_rate**self.alpha)
            return impact * 0.35, impact * 0.65  # Split between temp/permanent

        elif self.model_type == ImpactModel.ALMGREN_CHRISS:
            # Almgren-Chriss model
            # Temporary impact: decays with time
            # Permanent impact: depends on total order size
            temporary = self.k_temporary * participation_rate
            permanent = self.k_permanent * participation_rate
            return temporary, permanent

        else:  # STATIC
            # Fixed impact
            return 0.001, 0.002  # 10 bps temporary, 20 bps permanent


class BidAskSpreadAnalyzer:
    """
    Bid-Ask Spread Analyzer.

    Analyzes the bid-ask spread and its components as described in Harris Chapter 8.

    Spread components:
    1. Order processing costs
    2. Inventory holding costs
    3. Adverse selection costs
    4. Profit margin for market makers

    Attributes:
        spread_history: History of spread observations
    """

    def __init__(self):
        """Initialize the spread analyzer."""
        self._spread_history: List[Tuple[datetime, Decimal, Decimal]] = []

    def add_spread_observation(
        self,
        timestamp: datetime,
        bid: Decimal,
        ask: Decimal,
    ) -> None:
        """Add a spread observation."""
        spread = ask - bid
        self._spread_history.append((timestamp, spread, (bid + ask) / 2))

    def get_average_spread(self, window: Optional[int] = None) -> Optional[Decimal]:
        """Get average spread over window."""
        if not self._spread_history:
            return None

        observations = self._spread_history[-window:] if window else self._spread_history

        if not observations:
            return None

        total = sum(spread for _, spread, _ in observations)
        return total / Decimal(str(len(observations)))

    def get_spread_statistics(self) -> Dict[str, float]:
        """Get spread statistics."""
        if not self._spread_history:
            return {}

        spreads = [float(spread) for _, spread, _ in self._spread_history]
        mids = [float(mid) for _, _, mid in self._spread_history]

        # Calculate relative spreads (as % of mid price)
        relative_spreads = [s / m * 100 for s, m in zip(spreads, mids) if m > 0]

        return {
            "mean_spread": np.mean(spreads),
            "std_spread": np.std(spreads),
            "median_spread": np.median(spreads),
            "mean_relative_spread_bps": np.mean(relative_spreads) * 100,
            "min_spread": np.min(spreads),
            "max_spread": np.max(spreads),
            "spread_volatility": np.std(relative_spreads) * 100 if relative_spreads else 0,
        }

    def estimate_adverse_selection_cost(
        self,
        trade_price: Decimal,
        subsequent_mid_price: Decimal,
        is_buy: bool,
    ) -> Decimal:
        """
        Estimate adverse selection cost.

        Adverse selection occurs when prices move against the trader
        after execution, indicating information asymmetry.

        For buys: cost = mid_price_after - execution_price
        For sells: cost = execution_price - mid_price_after

        Args:
            trade_price: Execution price
            subsequent_mid_price: Mid price after execution
            is_buy: Whether trade was a buy

        Returns:
            Adverse selection cost (positive if unfavorable)
        """
        if is_buy:
            return subsequent_mid_price - trade_price
        else:
            return trade_price - subsequent_mid_price


class TimingRiskCalculator:
    """
    Timing Risk Calculator.

    Calculates the risk associated with execution timing as described
    in Harris Chapter 8.

    Timing risk arises from:
    1. Price volatility during execution period
    2. Delay between decision and execution
    3. Market movements during the execution window

    Attributes:
        confidence_level: Confidence level for risk calculation (default 95%)
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize the timing risk calculator.

        Args:
            confidence_level: Confidence level for VaR calculation
        """
        self.confidence_level = confidence_level

    def calculate_timing_risk(
        self,
        target_quantity: Decimal,
        execution_price: Decimal,
        volatility: float,
        execution_period_hours: float,
        arrival_price: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate timing risk for an execution.

        Args:
            target_quantity: Target quantity to trade
            execution_price: Actual execution price
            volatility: Price volatility (annualized)
            execution_period_hours: Time spent executing (hours)
            arrival_price: Price at arrival/decision (optional)

        Returns:
            Dictionary with timing risk metrics

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 8,
            "The Timing Risk of Market Orders"
        """
        # Convert annual volatility to execution period
        trading_days_per_year = 252
        hours_per_day = 6.5  # Assuming 6.5 hour trading day
        period_volatility = volatility * np.sqrt(
            execution_period_hours / (hours_per_day * trading_days_per_year)
        )

        # Calculate timing risk as price uncertainty
        timing_risk_abs = float(execution_price) * period_volatility
        timing_risk_bps = period_volatility * 10000

        # Calculate cost relative to arrival price if provided
        arrival_cost = None
        arrival_cost_bps = None
        if arrival_price:
            arrival_cost = execution_price - arrival_price
            arrival_cost_bps = (arrival_cost / arrival_price) * 10000

        return {
            "timing_risk_absolute": Decimal(str(timing_risk_abs)),
            "timing_risk_bps": Decimal(str(timing_risk_bps)),
            "period_volatility": Decimal(str(period_volatility * 100)),
            "arrival_cost": arrival_cost,
            "arrival_cost_bps": arrival_cost_bps,
        }

    def calculate_implicit_cost(
        self,
        execution_price: Decimal,
        decision_price: Decimal,
        is_buy: bool,
    ) -> Decimal:
        """
        Calculate implicit cost of delay.

        The cost from the time the decision was made to execution.

        Args:
            execution_price: Actual execution price
            decision_price: Price at decision time
            is_buy: Whether trade was a buy

        Returns:
            Implicit cost (positive for unfavorable)
        """
        if is_buy:
            return execution_price - decision_price
        else:
            return decision_price - execution_price


class TradingCostAnalyzer:
    """
    Comprehensive Trading Cost Analyzer.

    Implements Harris's framework for analyzing trading costs from Chapter 9.

    Cost components analyzed:
    1. Explicit costs: commissions, fees
    2. Implicit costs: spread, market impact, timing risk
    3. Opportunity costs: missed trades, unfilled quantities
    4. Implementation shortfall

    Attributes:
        market_impact_model: Market impact model
        spread_analyzer: Spread analyzer
        timing_risk_calculator: Timing risk calculator
    """

    def __init__(
        self,
        market_impact_model: Optional[MarketImpactModel] = None,
        spread_analyzer: Optional[BidAskSpreadAnalyzer] = None,
    ):
        """
        Initialize the trading cost analyzer.

        Args:
            market_impact_model: Market impact model
            spread_analyzer: Spread analyzer
        """
        self.market_impact_model = market_impact_model or MarketImpactModel()
        self.spread_analyzer = spread_analyzer or BidAskSpreadAnalyzer()
        self.timing_risk_calculator = TimingRiskCalculator()

        logger.debug("Initialized TradingCostAnalyzer")

    def analyze_execution(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        benchmark_price: Decimal,
        arrival_price: Optional[Decimal] = None,
        decision_price: Optional[Decimal] = None,
        commission: Optional[Decimal] = None,
        fees: Optional[Decimal] = None,
        adv: Optional[float] = None,
        volatility: Optional[float] = None,
        bid_at_arrival: Optional[Decimal] = None,
        ask_at_arrival: Optional[Decimal] = None,
        execution_period_hours: float = 0.5,
    ) -> CostBreakdown:
        """
        Analyze trading costs for an execution.

        Args:
            symbol: Trading symbol
            side: Buy or sell
            quantity: Executed quantity
            execution_price: Average execution price
            benchmark_price: Benchmark price (e.g., VWAP, arrival mid)
            arrival_price: Price at arrival (optional)
            decision_price: Price at decision (optional)
            commission: Commission paid
            fees: Additional fees
            adv: Average daily volume
            volatility: Price volatility (annualized)
            bid_at_arrival: Bid at arrival (for spread calculation)
            ask_at_arrival: Ask at arrival (for spread calculation)
            execution_period_hours: Time from decision to execution

        Returns:
            CostBreakdown with detailed cost analysis

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 9,
            "The Cost of Trading"
        """
        if commission is None:
            commission = Decimal("0")
        if fees is None:
            fees = Decimal("0")
        components = {}
        is_buy = side.upper() == "BUY"

        # 1. Explicit costs
        if commission > 0:
            components[CostComponent.COMMISSION] = commission
        if fees > 0:
            components[CostComponent.COMMISSION] = (
                components.get(CostComponent.COMMISSION, Decimal("0")) + fees
            )

        # 2. Spread cost (half spread paid)
        if bid_at_arrival and ask_at_arrival:
            half_spread = (ask_at_arrival - bid_at_arrival) / 2
            spread_cost = half_spread * quantity
            components[CostComponent.SPREAD] = spread_cost

        # 3. Market impact
        if adv and volatility:
            temp_impact, perm_impact = self.market_impact_model.calculate_impact(
                order_quantity=float(quantity),
                current_price=float(benchmark_price),
                adv=adv,
                volatility=volatility,
            )
            # Combine impacts
            total_impact_bps = (temp_impact + perm_impact) * 10000
            impact_cost = float(execution_price) * float(quantity) * (total_impact_bps / 10000)
            components[CostComponent.MARKET_IMPACT] = Decimal(str(impact_cost))

        # 4. Timing risk
        if decision_price and execution_period_hours > 0 and volatility:
            self.timing_risk_calculator.calculate_timing_risk(
                target_quantity=quantity,
                execution_price=execution_price,
                volatility=volatility,
                execution_period_hours=execution_period_hours,
                arrival_price=arrival_price,
            )
            # Add timing cost (difference between decision and arrival)
            if arrival_price and decision_price:
                timing_cost = abs(arrival_price - decision_price) * quantity
                components[CostComponent.TIMING_COST] = timing_cost

        # 5. Calculate total cost
        total_cost = Decimal(sum(components.values())) if components else Decimal("0")

        # 6. Calculate effective spread
        notional = quantity * benchmark_price
        effective_spread = abs(execution_price - benchmark_price)
        effective_spread_bps = (
            (effective_spread / benchmark_price) * 10000 if benchmark_price > 0 else Decimal("0")
        )

        # 7. Implementation shortfall
        # IS = (decision_price - execution_price) / decision_price
        if decision_price:
            if is_buy:
                shortfall = (execution_price - decision_price) / decision_price
            else:
                shortfall = (decision_price - execution_price) / decision_price
            implementation_shortfall = shortfall * Decimal("10000")
        else:
            implementation_shortfall = Decimal("0")

        # 8. Savings vs benchmark
        if is_buy:
            saving = (benchmark_price - execution_price) * quantity
        else:
            saving = (execution_price - benchmark_price) * quantity

        return CostBreakdown(
            symbol=symbol,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
            benchmark_price=benchmark_price,
            components=components,
            total_cost=total_cost,
            total_cost_bps=(
                (total_cost / notional * Decimal("10000")) if notional > 0 else Decimal("0")
            ),
            effective_spread=effective_spread_bps,
            implementation_shortfall=implementation_shortfall,
            saving_vs_benchmark=saving,
        )

    def evaluate_execution_quality(
        self,
        cost_breakdown: CostBreakdown,
        fill_rate: Optional[Decimal] = None,
        peer_fill_rate: Optional[Decimal] = None,
        market_conditions: Optional[Dict[str, float]] = None,
    ) -> ExecutionQualityMetrics:
        """
        Evaluate execution quality on a 0-100 scale.

        Args:
            cost_breakdown: Cost breakdown from analysis
            fill_rate: Percentage of order filled
            peer_fill_rate: Average peer fill rate (for benchmarking)
            market_conditions: Market condition metrics

        Returns:
            ExecutionQualityMetrics with quality assessment

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 9,
            "Execution Quality"
        """
        if fill_rate is None:
            fill_rate = Decimal("100")
        # Calculate effective spread in bps
        effective_spread_bps = abs(cost_breakdown.effective_spread)

        # Price improvement (negative effective spread = improvement)
        price_improvement_bps = -effective_spread_bps if effective_spread_bps < 0 else Decimal("0")

        # Market impact from breakdown
        market_impact_bps = Decimal("0")
        if CostComponent.MARKET_IMPACT in cost_breakdown.components:
            impact_cost = cost_breakdown.components[CostComponent.MARKET_IMPACT]
            notional = cost_breakdown.quantity * cost_breakdown.benchmark_price
            if notional > 0:
                market_impact_bps = (impact_cost / notional) * Decimal("10000")

        # Timing cost
        timing_cost_bps = Decimal("0")
        if CostComponent.TIMING_COST in cost_breakdown.components:
            timing_cost = cost_breakdown.components[CostComponent.TIMING_COST]
            notional = cost_breakdown.quantity * cost_breakdown.benchmark_price
            if notional > 0:
                timing_cost_bps = (timing_cost / notional) * Decimal("10000")

        # Implementation shortfall
        implementation_shortfall_bps = cost_breakdown.implementation_shortfall

        # Calculate execution score (0-100)
        # Penalizes: high costs, low fill rate, high shortfall
        # Rewards: price improvement, high fill rate

        # Base score starts at 100
        score = 100.0

        # Penalty for total cost (every 10 bps costs 5 points)
        cost_penalty = float(cost_breakdown.total_cost_bps) / 10 * 5
        score -= cost_penalty

        # Penalty for implementation shortfall (every 10 bps costs 3 points)
        shortfall_penalty = float(abs(implementation_shortfall_bps)) / 10 * 3
        score -= shortfall_penalty

        # Reward for price improvement (every 5 bps improvement gains 2 points)
        improvement_reward = float(price_improvement_bps) / 5 * 2
        score += improvement_reward

        # Penalty for low fill rate
        fill_penalty = (100 - float(fill_rate)) / 5
        score -= fill_penalty

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        return ExecutionQualityMetrics(
            symbol=cost_breakdown.symbol,
            execution_id=f"{cost_breakdown.symbol}_{datetime.utcnow().timestamp()}",
            fill_rate=fill_rate,
            avg_fill_price=cost_breakdown.execution_price,
            benchmark_prices={
                "arrival": cost_breakdown.benchmark_price,
            },
            effective_spread_bps=effective_spread_bps,
            price_improvement_bps=price_improvement_bps,
            timing_cost_bps=timing_cost_bps,
            market_impact_bps=market_impact_bps,
            implementation_shortfall_bps=implementation_shortfall_bps,
            execution_score=score,
        )


def create_trading_cost_analyzer(
    impact_model: ImpactModel = ImpactModel.SQUARE_ROOT,
    daily_volume: Optional[float] = None,
) -> TradingCostAnalyzer:
    """
    Factory function to create a TradingCostAnalyzer.

    Args:
        impact_model: Type of market impact model
        daily_volume: Average daily volume for impact calculation

    Returns:
        Configured TradingCostAnalyzer instance

    Example:
        >>> analyzer = create_trading_cost_analyzer(
        ...     impact_model=ImpactModel.SQUARE_ROOT,
        ...     daily_volume=1_000_000,
        ... )
        >>> cost = analyzer.analyze_execution(
        ...     symbol="AAPL",
        ...     side="BUY",
        ...     quantity=Decimal("1000"),
        ...     execution_price=Decimal("150.50"),
        ...     benchmark_price=Decimal("150.00"),
        ...     adv=1_000_000,
        ...     volatility=0.2,
        ... )
        >>> print(f"Total cost: {cost.total_cost_bps:.2f} bps")
    """
    impact = MarketImpactModel(
        model_type=impact_model,
        daily_volume=daily_volume,
    )

    return TradingCostAnalyzer(market_impact_model=impact)
