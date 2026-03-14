"""
Multi-Asset Portfolio Rebalancing.

This module provides comprehensive rebalancing functionality for multi-asset
portfolios, including trade calculation, prioritization, and cost estimation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List

from app.backtesting.models import Trade
from app.shared.config.centralized_config import get_config

from .asset_class import AssetClass, AssetClassType
from .models import MultiAssetAllocation, MultiAssetPortfolio

logger = logging.getLogger(__name__)


class RebalancePriority(str, Enum):
    """Priority levels for rebalancing trades."""

    CRITICAL = "critical"  # Must rebalance immediately
    HIGH = "high"  # Should rebalance soon
    MEDIUM = "medium"  # Normal priority
    LOW = "low"  # Can defer
    DEFER = "defer"  # Skip this rebalance


@dataclass
class CostEstimate:
    """
    Estimated trading costs for rebalancing.

    Attributes:
        commission: Trading commissions
        spread_cost: Bid-ask spread cost
        market_impact: Market impact cost
        tax_cost: Estimated tax cost
        total_cost: Total estimated cost
        cost_as_percentage: Cost as percentage of portfolio value
    """

    commission: Decimal
    spread_cost: Decimal
    market_impact: Decimal
    tax_cost: Decimal
    total_cost: Decimal
    cost_as_percentage: Decimal

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "commission": float(self.commission),
            "spread_cost": float(self.spread_cost),
            "market_impact": float(self.market_impact),
            "tax_cost": float(self.tax_cost),
            "total_cost": float(self.total_cost),
            "cost_as_percentage": float(self.cost_as_percentage),
        }


@dataclass
class RebalanceTrade:
    """
    Trade generated for rebalancing.

    Attributes:
        symbol: Asset symbol
        asset_class: Asset class
        quantity: Quantity to trade
        current_price: Current market price
        target_value: Target value in portfolio
        current_value: Current value in portfolio
        deviation: Deviation from target (as decimal)
        priority: Execution priority
        estimated_cost: Estimated trading cost
        reason: Reason for this trade
        urgency: Trade urgency level
    """

    symbol: str
    asset_class: str
    quantity: Decimal
    current_price: Decimal
    target_value: Decimal
    current_value: Decimal
    deviation: Decimal
    priority: int
    estimated_cost: Decimal
    reason: str
    urgency: RebalancePriority = RebalancePriority.MEDIUM

    def to_trade(self) -> Trade:
        """Convert to Trade object."""
        return Trade(
            symbol=self.symbol,
            asset_class=self.asset_class,
            quantity=self.quantity,
            price=self.current_price,
            value=abs(self.quantity * self.current_price),
            reason=self.reason,
            priority=self.priority,
            estimated_cost=self.estimated_cost,
        )

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.quantity > 0

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.quantity < 0


@dataclass
class RebalancePlan:
    """
    Complete rebalancing plan.

    Attributes:
        trades: List of trades to execute
        total_cost: Total estimated cost
        pre_rebalance_portfolio: Portfolio state before rebalancing
        post_rebalance_portfolio: Target portfolio state
        deviations: Deviations that triggered rebalancing
        warnings: List of warnings
        created_at: When the plan was created
        priority: Overall plan priority
    """

    trades: List[RebalanceTrade]
    total_cost: CostEstimate
    pre_rebalance_portfolio: MultiAssetPortfolio
    post_rebalance_portfolio: MultiAssetPortfolio
    deviations: Dict[str, Decimal]
    warnings: List[str]
    created_at: datetime
    priority: RebalancePriority = RebalancePriority.MEDIUM

    @property
    def n_trades(self) -> int:
        """Number of trades in the plan."""
        return len(self.trades)

    @property
    def total_value_to_trade(self) -> Decimal:
        """Total value of all trades."""
        return Decimal(sum(abs(t.quantity * t.current_price) for t in self.trades))

    @property
    def buys(self) -> List[RebalanceTrade]:
        """Get all buy trades."""
        return [t for t in self.trades if t.is_buy]

    @property
    def sells(self) -> List[RebalanceTrade]:
        """Get all sell trades."""
        return [t for t in self.trades if t.is_sell]

    @property
    def net_cash_flow(self) -> Decimal:
        """Net cash flow from all trades (positive = inflow)."""
        buy_value = Decimal(sum(t.quantity * t.current_price for t in self.buys))
        sell_value = Decimal(sum(abs(t.quantity * t.current_price) for t in self.sells))
        return sell_value - buy_value


class MultiAssetRebalancer:
    """
    Rebalance multi-asset portfolio.

    This class handles all aspects of portfolio rebalancing:
    - Detecting when rebalancing is needed
    - Calculating optimal trades
    - Prioritizing trades for execution
    - Estimating trading costs
    - Optimizing for tax efficiency
    - Managing different rebalance frequencies per asset class

    Considerations:
    - Different rebalance frequencies per asset class
    - Trading costs vary by asset class
    - Tax implications (short-term vs long-term)
    - Market impact
    - Liquidity constraints

    Example:
        >>> rebalancer = MultiAssetRebalancer(config)
        >>>
        >>> # Create rebalancing plan
        >>> plan = rebalancer.create_rebalance_plan(
        ...     current_portfolio=portfolio,
        ...     target_weights=target_weights,
        ...     current_prices=prices,
        ...     portfolio_value=value
        ... )
        >>>
        >>> # Execute trades
        >>> for trade in plan.trades:
        ...     execute_trade(trade)
    """

    def __init__(
        self,
        trading_cost_bps: Decimal = Decimal("10"),
        rebalance_threshold: Decimal = Decimal("0.05"),
        min_trade_size: Decimal = Decimal("1000"),
    ):
        """
        Initialize rebalancer.

        Args:
            trading_cost_bps: Trading cost in basis points
            rebalance_threshold: Deviation threshold for rebalancing
            min_trade_size: Minimum trade size in currency units
        """
        self.trading_cost_bps = trading_cost_bps
        self.rebalance_threshold = rebalance_threshold
        self.min_trade_size = min_trade_size

        # Asset class-specific cost multipliers
        self.cost_multipliers = {
            AssetClassType.EQUITY: Decimal("1.0"),
            AssetClassType.CRYPTO: Decimal("0.5"),  # Lower costs
            AssetClassType.FOREX: Decimal("0.3"),  # Lower costs
            AssetClassType.FIXED_INCOME: Decimal("1.2"),  # Higher costs for corporates
            AssetClassType.COMMODITY: Decimal("1.0"),
            AssetClassType.REAL_ESTATE: Decimal("1.0"),
            AssetClassType.CASH: Decimal("0.0"),
        }

    def create_rebalance_plan(
        self,
        current_portfolio: MultiAssetPortfolio,
        target_weights: Dict[str, Decimal],
        current_prices: Dict[str, Decimal],
        portfolio_value: Decimal,
        asset_classes: Dict[str, AssetClass],
    ) -> RebalancePlan:
        """
        Create comprehensive rebalancing plan.

        Args:
            current_portfolio: Current portfolio state
            target_weights: Target weights for each asset class
            current_prices: Current market prices
            portfolio_value: Current portfolio value
            asset_classes: Asset class definitions

        Returns:
            RebalancePlan with all necessary trades
        """
        warnings: List[str] = []
        deviations: Dict[str, Decimal] = {}

        # Detect deviations
        for class_name, target_weight in target_weights.items():
            current_weight = current_portfolio.allocations.get(class_name)
            if current_weight is None:
                current_alloc = Decimal("0")
            else:
                current_alloc = current_weight.weight

            deviation = target_weight - current_alloc
            deviations[class_name] = deviation

        # Calculate trades for each asset class
        trades: List[RebalanceTrade] = []

        for class_name, target_weight in target_weights.items():
            class_trades = self._calculate_asset_class_trades(
                class_name=class_name,
                target_weight=target_weight,
                current_portfolio=current_portfolio,
                current_prices=current_prices,
                portfolio_value=portfolio_value,
                asset_classes=asset_classes,
            )
            trades.extend(class_trades)

        # Prioritize trades
        prioritized_trades = self.prioritize_trades(trades)

        # Estimate costs
        cost_estimate = self.estimate_costs(prioritized_trades, portfolio_value)

        # Create target portfolio (what portfolio will look like after rebalancing)
        target_portfolio = self._create_target_portfolio(
            current_portfolio, target_weights, asset_classes
        )

        # Determine overall priority
        plan_priority = self._determine_plan_priority(deviations, cost_estimate)

        return RebalancePlan(
            trades=prioritized_trades,
            total_cost=cost_estimate,
            pre_rebalance_portfolio=current_portfolio,
            post_rebalance_portfolio=target_portfolio,
            deviations=deviations,
            warnings=warnings,
            created_at=datetime.utcnow(),
            priority=plan_priority,
        )

    def prioritize_trades(self, trades: List[RebalanceTrade]) -> List[RebalanceTrade]:
        """
        Prioritize trades for execution.

        Priority factors:
        - Deviation from target (larger = higher priority)
        - Trading cost (lower cost = higher priority)
        - Market impact (lower impact = higher priority)
        - Asset class liquidity

        Args:
            trades: List of trades to prioritize

        Returns:
            Sorted list of trades by priority
        """
        if not trades:
            return []

        # Calculate priority score for each trade
        scored_trades = []
        for trade in trades:
            score = self._calculate_trade_priority_score(trade)
            scored_trades.append((score, trade))

        # Sort by score (higher = higher priority)
        scored_trades.sort(key=lambda x: x[0], reverse=True)

        # Assign priority values (100 = highest, 0 = lowest)
        prioritized = []
        for i, (score, trade) in enumerate(scored_trades):
            # Map score to 0-100 priority
            priority = int(min(100, max(0, score * 100)))
            trade.priority = priority

            # Set urgency based on priority
            if priority >= 80:
                trade.urgency = RebalancePriority.CRITICAL
            elif priority >= 60:
                trade.urgency = RebalancePriority.HIGH
            elif priority >= 40:
                trade.urgency = RebalancePriority.MEDIUM
            elif priority >= 20:
                trade.urgency = RebalancePriority.LOW
            else:
                trade.urgency = RebalancePriority.DEFER

            prioritized.append(trade)

        return prioritized

    def estimate_costs(
        self, trades: List[RebalanceTrade], portfolio_value: Decimal
    ) -> CostEstimate:
        """
        Calculate anticipated trading costs by asset class.

        Cost components:
        - Commission: Fixed per-trade or per-share cost
        - Spread: Bid-ask spread cost
        - Market impact: Price movement due to trade size
        - Tax: Short-term vs long-term capital gains

        Args:
            trades: List of trades
            portfolio_value: Total portfolio value

        Returns:
            CostEstimate with detailed cost breakdown
        """
        total_commission = Decimal("0")
        total_spread = Decimal("0")
        total_impact = Decimal("0")
        total_tax = Decimal("0")

        for trade in trades:
            # Commission (fixed bps + asset class multiplier)
            # Use default multiplier if asset_class is a name rather than type
            multiplier = self._get_cost_multiplier_for_asset_class(trade.asset_class)
            commission = (
                abs(trade.target_value) * self.trading_cost_bps * multiplier / Decimal("10000")
            )
            total_commission += commission

            # Spread cost (typically 0.01% - 0.1% depending on asset)
            spread_rate = self._get_spread_rate(trade.asset_class)
            spread = abs(trade.target_value) * spread_rate
            total_spread += spread

            # Market impact (increases with trade size)
            impact = self._calculate_market_impact(trade)
            total_impact += impact

            # Tax estimate (simplified - assumes short-term for all)
            if trade.is_sell:  # Only sales trigger tax
                tax_rate = self._get_tax_rate(trade.asset_class)
                # Estimate gains as 50% of sale value (conservative)
                estimated_gain = abs(trade.quantity * trade.current_price) * Decimal("0.5")
                tax = estimated_gain * tax_rate
                total_tax += tax

        total_cost = total_commission + total_spread + total_impact + total_tax
        # Use config percentage multiplier
        tt = get_config().trading_thresholds
        cost_pct = (
            (total_cost / portfolio_value * tt.percentage_multiplier)
            if portfolio_value > 0
            else Decimal("0")
        )

        return CostEstimate(
            commission=total_commission,
            spread_cost=total_spread,
            market_impact=total_impact,
            tax_cost=total_tax,
            total_cost=total_cost,
            cost_as_percentage=cost_pct,
        )

    def _get_cost_multiplier_for_asset_class(self, asset_class: str) -> Decimal:
        """
        Get cost multiplier for an asset class.

        Args:
            asset_class: Asset class name or type

        Returns:
            Cost multiplier
        """
        # Try to convert to AssetClassType
        try:
            asset_type = AssetClassType(asset_class)
            return self.cost_multipliers.get(asset_type, Decimal("1.0"))
        except ValueError:
            # If it's a name, use default multiplier
            return Decimal("1.0")

    def _calculate_asset_class_trades(
        self,
        class_name: str,
        target_weight: Decimal,
        current_portfolio: MultiAssetPortfolio,
        current_prices: Dict[str, Decimal],
        portfolio_value: Decimal,
        asset_classes: Dict[str, AssetClass],
    ) -> List[RebalanceTrade]:
        """Calculate trades to rebalance a single asset class."""
        trades: List[RebalanceTrade] = []

        # Get current allocation
        current_alloc = current_portfolio.allocations.get(class_name)

        if current_alloc is None:
            # New asset class - need to buy target allocation
            target_value = portfolio_value * target_weight
            # This is simplified - would need to know specific assets
            # For now, skip new asset classes
            return trades

        current_weight = current_alloc.weight
        weight_diff = target_weight - current_weight

        if abs(weight_diff) < self.rebalance_threshold:
            # No rebalancing needed for this class
            return trades

        # Calculate target value for this class
        target_value = portfolio_value * target_weight
        current_value = portfolio_value * current_weight
        target_value - current_value

        # Create trades for each asset in the class
        for symbol, within_weight in current_alloc.assets.items():
            if symbol == "CASH":
                continue

            current_price = current_prices.get(symbol, Decimal("100"))
            current_asset_value = current_value * within_weight
            target_asset_value = target_value * within_weight
            asset_diff = target_asset_value - current_asset_value

            if abs(asset_diff) < self.min_trade_size:
                continue

            # Calculate quantity
            quantity = (asset_diff / current_price).quantize(Decimal("1"))

            if quantity == 0:
                continue

            # Calculate deviation
            deviation = weight_diff

            # Estimate cost
            cost = abs(asset_diff) * self.trading_cost_bps / Decimal("10000")

            trade = RebalanceTrade(
                symbol=symbol,
                asset_class=class_name,
                quantity=quantity,
                current_price=current_price,
                target_value=target_asset_value,
                current_value=current_asset_value,
                deviation=deviation,
                priority=0,  # Will be set by prioritize_trades
                estimated_cost=cost,
                reason=f"Rebalance {class_name} from {current_weight:.2%} to {target_weight:.2%}",
            )
            trades.append(trade)

        return trades

    def _calculate_trade_priority_score(self, trade: RebalanceTrade) -> float:
        """
        Calculate priority score for a trade.

        Higher score = higher priority.

        Factors:
        - Deviation magnitude (larger = more important)
        - Trade value (larger = more important)
        - Asset class (some classes are more time-sensitive)
        - Cost efficiency (lower cost = higher priority)

        Returns:
            Priority score between 0 and 1
        """
        # Deviation score (0-1)
        deviation_score = min(1.0, abs(float(trade.deviation)) / 0.2)

        # Value score (0-1)
        value_score = min(1.0, float(abs(trade.target_value)) / 100000)

        # Asset class multiplier (some are more time-sensitive)
        class_priority = {
            AssetClassType.CRYPTO: 1.2,  # Time-sensitive due to volatility
            AssetClassType.FOREX: 1.1,
            AssetClassType.EQUITY: 1.0,
            AssetClassType.FIXED_INCOME: 0.8,
            AssetClassType.COMMODITY: 0.9,
            AssetClassType.REAL_ESTATE: 0.7,
            AssetClassType.CASH: 0.5,
        }
        try:
            class_multiplier = class_priority.get(AssetClassType(trade.asset_class), 1.0)
        except ValueError:
            class_multiplier = 1.0

        # Cost efficiency (higher cost = lower priority)
        cost_ratio = (
            float(trade.estimated_cost) / float(abs(trade.target_value))
            if trade.target_value != 0
            else 0
        )
        cost_score = max(0, 1 - cost_ratio * 10)

        # Combine scores
        combined_score = (
            deviation_score * 0.5 + value_score * 0.2 + cost_score * 0.2
        ) * class_multiplier

        return min(1.0, combined_score)

    def _get_spread_rate(self, asset_class_identifier: str) -> Decimal:
        """Get typical spread rate for asset class from config."""
        # Get transaction costs from config
        config = get_config()
        tt = config.trading

        # Default rate from config
        default_rate = Decimal(str(getattr(tt, 'tx_cost_equity', 0.0005)))

        # Try to convert to AssetClassType
        try:
            asset_type = AssetClassType(asset_class_identifier)
        except ValueError:
            # If it's a name, use default rate
            return default_rate

        # Get spread rates from config
        spread_rates = {
            AssetClassType.EQUITY: Decimal(str(getattr(tt, 'tx_cost_equity', 0.0005))),
            AssetClassType.CRYPTO: Decimal(str(getattr(tt, 'tx_cost_crypto', 0.001))),
            AssetClassType.FOREX: Decimal(str(getattr(tt, 'tx_cost_forex', 0.0001))),
            AssetClassType.FIXED_INCOME: Decimal(str(getattr(tt, 'tx_cost_fixed_income', 0.001))),
            AssetClassType.COMMODITY: Decimal(str(getattr(tt, 'tx_cost_commodity', 0.0005))),
            AssetClassType.REAL_ESTATE: Decimal(str(getattr(tt, 'tx_cost_real_estate', 0.001))),
            AssetClassType.CASH: Decimal("0"),
        }
        return spread_rates.get(asset_type, default_rate)

    def _calculate_market_impact(self, trade: RebalanceTrade) -> Decimal:
        """
        Calculate market impact cost.

        Simplified model: impact = (trade_size / avg_daily_volume) ^ 0.5 * price
        For now, use a percentage-based estimate.
        """
        # Assume impact increases with square root of trade size
        trade_value = abs(trade.target_value)
        # Assume avg daily volume of $1M for simplicity
        impact_ratio = (float(trade_value) / 1000000) ** 0.5

        # Impact is typically 1-5 bps per 1% of daily volume
        impact_bps = impact_ratio * 5
        return trade_value * Decimal(str(impact_bps)) / Decimal("10000")

    def _get_tax_rate(self, asset_class_identifier: str) -> Decimal:
        """Get tax rate for asset class from config."""
        # Get tax rate from config
        config = get_config()
        tt = config.trading

        # Simplified - use same rate for all (short-term capital gains)
        # Could be made asset-class specific in the future
        return Decimal(str(getattr(tt, 'portfolio_tax_rate', 0.25)))

    def _create_target_portfolio(
        self,
        current_portfolio: MultiAssetPortfolio,
        target_weights: Dict[str, Decimal],
        asset_classes: Dict[str, AssetClass],
    ) -> MultiAssetPortfolio:
        """Create target portfolio representation."""
        # Create new allocations with target weights
        target_allocations = {}

        for class_name, target_weight in target_weights.items():
            if class_name in current_portfolio.allocations:
                # Keep same within-class weights, just update class weight
                current_alloc = current_portfolio.allocations[class_name]
                target_allocations[class_name] = MultiAssetAllocation(
                    asset_class=current_alloc.asset_class,
                    weight=target_weight,
                    assets=current_alloc.assets.copy(),
                    expected_return=current_alloc.expected_return,
                    risk=current_alloc.risk,
                )
            elif class_name in asset_classes:
                # New allocation with equal weights
                asset_class = asset_classes[class_name]
                # Use default allocation
                target_allocations[class_name] = MultiAssetAllocation(
                    asset_class=asset_class,
                    weight=target_weight,
                    assets={"CASH": Decimal("1")},
                    expected_return=asset_class.expected_return * target_weight,
                    risk=asset_class.volatility * target_weight,
                )

        return MultiAssetPortfolio(
            name=f"{current_portfolio.name} (Target)",
            allocations=target_allocations,
            total_value=current_portfolio.total_value,
            last_rebalanced=datetime.utcnow(),
            rebalance_threshold=current_portfolio.rebalance_threshold,
            currency=current_portfolio.currency,
        )

    def _determine_plan_priority(
        self, deviations: Dict[str, Decimal], cost_estimate: CostEstimate
    ) -> RebalancePriority:
        """Determine overall priority for rebalancing plan."""
        # Calculate maximum deviation
        max_deviation = max(abs(d) for d in deviations.values()) if deviations else Decimal("0")

        # Get config for cost efficiency threshold
        cfg = get_config()
        cost_threshold = Decimal(str(getattr(cfg.trading, 'max_cost_impact_ratio', 0.30)))

        # Check cost efficiency
        cost_too_high = cost_estimate.cost_as_percentage > cost_threshold

        # Get rebalance thresholds from config
        rebalance_threshold_high = Decimal(
            str(getattr(cfg.trading, 'portfolio_max_deviation_high', 0.10))
        )
        rebalance_threshold_medium = Decimal(
            str(getattr(cfg.trading, 'portfolio_max_deviation_moderate', 0.05))
        )

        if max_deviation > Decimal("0.15"):
            # More than 15% deviation - critical
            return RebalancePriority.CRITICAL
        elif max_deviation > rebalance_threshold_high:
            # More than 10% deviation - high
            return RebalancePriority.HIGH
        elif cost_too_high:
            # Costs too high - defer
            return RebalancePriority.DEFER
        elif max_deviation > rebalance_threshold_medium:
            # More than 5% deviation - medium
            return RebalancePriority.MEDIUM
        else:
            # Low deviation - low priority
            return RebalancePriority.LOW

    def calculate_rebalance_trades(
        self,
        current_portfolio: MultiAssetPortfolio,
        target_portfolio: MultiAssetPortfolio,
        current_prices: Dict[str, Decimal],
        portfolio_value: Decimal,
    ) -> List[Trade]:
        """
        Calculate trades needed to rebalance.

        Optimizes for:
        - Minimizing trading costs
        - Respecting rebalance frequency
        - Tax efficiency

        Args:
            current_portfolio: Current portfolio state
            target_portfolio: Target portfolio state
            current_prices: Current market prices
            portfolio_value: Current portfolio value

        Returns:
            List of Trade objects
        """
        trades: List[Trade] = []

        # Get target weights
        target_weights = target_portfolio.get_asset_class_weights()

        # Calculate trades for each asset class
        for class_name, target_weight in target_weights.items():
            class_trades = self._calculate_asset_class_trades(
                class_name=class_name,
                target_weight=target_weight,
                current_portfolio=current_portfolio,
                current_prices=current_prices,
                portfolio_value=portfolio_value,
                asset_classes={},  # Not needed for trade calculation
            )

            # Convert RebalanceTrade to Trade
            for rebalance_trade in class_trades:
                trades.append(rebalance_trade.to_trade())

        return trades
