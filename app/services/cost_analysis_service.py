"""
Cost Analysis Service for AlgoTrading system.

This module provides comprehensive cost analysis functionality including
transaction costs, slippage analysis, infrastructure costs, and profitability validation.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Tuple

from app.backtesting.models import Trade, TradeStatus
from app.models.order import OrderType


class CostType(str, Enum):
    """Types of trading costs."""

    COMMISSION = "commission"
    SLIPPAGE = "slippage"
    INFRASTRUCTURE = "infrastructure"
    MARKET_IMPACT = "market_impact"
    BORROWING_COST = "borrowing_cost"


@dataclass
class CostBreakdown:
    """Breakdown of trading costs for a single trade."""

    trade_id: str
    symbol: str
    order_type: OrderType
    quantity: Decimal
    execution_price: Decimal

    # Cost components
    commission: Decimal
    slippage: Decimal
    market_impact: Decimal
    infrastructure_cost: Decimal
    borrowing_cost: Decimal

    # Calculated metrics
    total_cost: Decimal
    cost_percentage: Decimal
    cost_impact_ratio: Decimal

    timestamp: datetime


@dataclass
class CostAnalysisResult:
    """Result of cost analysis for a trading strategy."""

    strategy_name: str
    analysis_period: Tuple[datetime, datetime]
    total_trades: int

    # Cost metrics
    total_commission: Decimal
    total_slippage: Decimal
    total_market_impact: Decimal
    total_infrastructure: Decimal
    total_borrowing: Decimal
    total_costs: Decimal

    # Profitability metrics
    gross_profit: Decimal
    net_profit: Decimal
    cost_impact_ratio: Decimal
    profitability_threshold: Decimal

    # Cost breakdown by trade
    cost_breakdowns: List[CostBreakdown]

    # Validation results
    is_profitable: bool
    exceeds_cost_threshold: bool
    recommendations: List[str]


class CostAnalysisService:
    """Service for analyzing trading costs and profitability."""

    def __init__(self):
        """Initialize the cost analysis service."""
        # Default cost parameters
        self.commission_rates = {
            "equity": Decimal("0.005"),  # 0.5% per trade
            "crypto": Decimal("0.001"),  # 0.1% per trade
            "forex": Decimal("0.0002"),  # 0.02% per trade
        }

        self.slippage_rates = {
            "equity": Decimal("0.001"),  # 0.1% slippage
            "crypto": Decimal("0.0005"),  # 0.05% slippage
            "forex": Decimal("0.0001"),  # 0.01% slippage
        }

        self.infrastructure_cost_per_trade = Decimal("0.50")  # $0.50 per trade
        self.borrowing_cost_rate = Decimal("0.05")  # 5% annual borrowing cost

        # Profitability thresholds
        self.min_profitability_threshold = Decimal("0.02")  # 2% minimum profit
        self.max_cost_impact_ratio = Decimal("0.30")  # 30% max cost impact

    def analyze_trade_costs(self, trade: Trade, market_data: Dict[str, Any]) -> CostBreakdown:
        """Analyze costs for a single trade."""
        try:
            # Determine asset class for cost calculation
            asset_class = self._determine_asset_class(trade.symbol)

            # Calculate commission
            commission = self._calculate_commission(trade, asset_class)

            # Calculate slippage (real per-trade, not average)
            slippage = self._calculate_real_slippage(trade, market_data, asset_class)

            # Calculate market impact
            market_impact = self._calculate_market_impact(trade, market_data)

            # Calculate infrastructure cost
            infrastructure_cost = self.infrastructure_cost_per_trade

            # Calculate borrowing cost (for short positions)
            borrowing_cost = self._calculate_borrowing_cost(trade)

            # Calculate total cost
            total_cost = (
                commission + slippage + market_impact + infrastructure_cost + borrowing_cost
            )

            # Calculate cost percentage
            trade_value = trade.quantity * trade.entry_price
            cost_percentage = (total_cost / trade_value) * 100 if trade_value > 0 else Decimal("0")

            # Calculate Cost Impact Ratio (CIR)
            gross_profit = trade.pnl if trade.pnl else Decimal("0")
            cost_impact_ratio = (
                (total_cost / gross_profit) * 100 if gross_profit > 0 else Decimal("0")
            )

            return CostBreakdown(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                order_type=OrderType.MARKET,  # Default to MARKET for Trade model
                quantity=trade.quantity,
                execution_price=trade.entry_price,
                commission=commission,
                slippage=slippage,
                market_impact=market_impact,
                infrastructure_cost=infrastructure_cost,
                borrowing_cost=borrowing_cost,
                total_cost=total_cost,
                cost_percentage=cost_percentage,
                cost_impact_ratio=cost_impact_ratio,
                timestamp=trade.entry_time,
            )

        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            # Return zero costs if calculation fails
            return CostBreakdown(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                order_type=OrderType.MARKET,
                quantity=trade.quantity,
                execution_price=trade.entry_price,
                commission=Decimal("0"),
                slippage=Decimal("0"),
                market_impact=Decimal("0"),
                infrastructure_cost=Decimal("0"),
                borrowing_cost=Decimal("0"),
                total_cost=Decimal("0"),
                cost_percentage=Decimal("0"),
                cost_impact_ratio=Decimal("0"),
                timestamp=trade.entry_time,
            )

    def analyze_strategy_costs(
        self, trades: List[Trade], strategy_name: str, market_data: Dict[str, Any]
    ) -> CostAnalysisResult:
        """Analyze costs for an entire trading strategy."""
        try:
            if not trades:
                return self._create_empty_analysis_result(strategy_name)

            # Analyze costs for each trade
            cost_breakdowns = []
            for trade in trades:
                if trade.status == TradeStatus.CLOSED:
                    breakdown = self.analyze_trade_costs(trade, market_data)
                    cost_breakdowns.append(breakdown)

            if not cost_breakdowns:
                return self._create_empty_analysis_result(strategy_name)

            # Calculate aggregate metrics
            total_commission = sum(bd.commission for bd in cost_breakdowns)
            total_slippage = sum(bd.slippage for bd in cost_breakdowns)
            total_market_impact = sum(bd.market_impact for bd in cost_breakdowns)
            total_infrastructure = sum(bd.infrastructure_cost for bd in cost_breakdowns)
            total_borrowing = sum(bd.borrowing_cost for bd in cost_breakdowns)
            total_costs = (
                total_commission
                + total_slippage
                + total_market_impact
                + total_infrastructure
                + total_borrowing
            )

            # Calculate profitability metrics
            gross_profit = sum(trade.pnl for trade in trades if trade.pnl)
            net_profit = gross_profit - total_costs

            # Calculate Cost Impact Ratio (CIR)
            cost_impact_ratio = (
                (total_costs / gross_profit) * 100 if gross_profit > 0 else Decimal("0")
            )

            # Validation
            is_profitable = net_profit > 0
            exceeds_cost_threshold = cost_impact_ratio > self.max_cost_impact_ratio

            # Generate recommendations
            recommendations = self._generate_recommendations(
                cost_impact_ratio,
                is_profitable,
                exceeds_cost_threshold,
                cost_breakdowns,
            )

            return CostAnalysisResult(
                strategy_name=strategy_name,
                analysis_period=(
                    min(t.entry_time for t in trades),
                    max(t.exit_time for t in trades),
                ),
                total_trades=len(cost_breakdowns),
                total_commission=total_commission,
                total_slippage=total_slippage,
                total_market_impact=total_market_impact,
                total_infrastructure=total_infrastructure,
                total_borrowing=total_borrowing,
                total_costs=total_costs,
                gross_profit=gross_profit,
                net_profit=net_profit,
                cost_impact_ratio=cost_impact_ratio,
                profitability_threshold=self.min_profitability_threshold,
                cost_breakdowns=cost_breakdowns,
                is_profitable=is_profitable,
                exceeds_cost_threshold=exceeds_cost_threshold,
                recommendations=recommendations,
            )

        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return self._create_empty_analysis_result(strategy_name)

    def validate_profitability(self, analysis_result: CostAnalysisResult) -> bool:
        """Validate that strategy is profitable after all costs."""
        return analysis_result.is_profitable and not analysis_result.exceeds_cost_threshold

    def _determine_asset_class(self, symbol: str) -> str:
        """Determine asset class from symbol."""
        if any(crypto in symbol.upper() for crypto in ["BTC", "ETH", "USDT", "USDC"]):
            return "crypto"
        elif any(forex in symbol.upper() for forex in ["USD", "EUR", "GBP", "JPY"]):
            return "forex"
        else:
            return "equity"

    def _calculate_commission(self, trade: Trade, asset_class: str) -> Decimal:
        """Calculate commission for a trade."""
        commission_rate = self.commission_rates.get(asset_class, self.commission_rates["equity"])
        trade_value = trade.quantity * trade.entry_price
        return trade_value * commission_rate

    def _calculate_real_slippage(
        self, trade: Trade, market_data: Dict[str, Any], asset_class: str
    ) -> Decimal:
        """Calculate real slippage per trade (not average)."""
        try:
            # Get market data for the trade
            symbol_data = market_data.get(trade.symbol, {})

            # Calculate slippage based on order type and market conditions
            # Since Trade model doesn't have order_type, we'll assume MARKET
            # orders
            base_slippage = self.slippage_rates.get(asset_class, self.slippage_rates["equity"])

            # Adjust for market volatility
            volatility = symbol_data.get("volatility", 0.02)
            volatility_multiplier = Decimal(str(1 + volatility))

            # Adjust for order size
            order_size_impact = min(Decimal("2.0"), Decimal(str(trade.quantity)) / Decimal("1000"))

            slippage = base_slippage * volatility_multiplier * order_size_impact

            # Calculate slippage in dollar terms
            trade_value = trade.quantity * trade.entry_price
            slippage_amount = trade_value * slippage

            return slippage_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            # Fallback to base slippage rate
            base_slippage = self.slippage_rates.get(asset_class, self.slippage_rates["equity"])
            trade_value = trade.quantity * trade.entry_price
            return (trade_value * base_slippage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_market_impact(self, trade: Trade, market_data: Dict[str, Any]) -> Decimal:
        """Calculate market impact cost."""
        try:
            symbol_data = market_data.get(trade.symbol, {})
            avg_volume = symbol_data.get("avg_volume", Decimal("1000000"))

            # Market impact is proportional to order size relative to average
            # volume
            volume_ratio = trade.quantity / avg_volume if avg_volume > 0 else Decimal("0")

            # Market impact increases with order size
            # Large order (>10% of avg volume)
            if volume_ratio > Decimal("0.1"):
                impact_rate = Decimal("0.005")  # 0.5%
            # Medium order (>5% of avg volume)
            elif volume_ratio > Decimal("0.05"):
                impact_rate = Decimal("0.002")  # 0.2%
            else:  # Small order
                impact_rate = Decimal("0.0005")  # 0.05%

            trade_value = trade.quantity * trade.entry_price
            return (trade_value * impact_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return Decimal("0")

    def _calculate_borrowing_cost(self, trade: Trade) -> Decimal:
        """Calculate borrowing cost for short positions."""
        try:
            # Only short positions have borrowing costs
            if trade.side.lower() == "sell" and trade.quantity > 0:
                # Calculate borrowing cost based on position duration
                duration_days = (trade.exit_time - trade.entry_time).days
                if duration_days <= 0:
                    duration_days = 1

                # Annual rate converted to daily rate
                daily_rate = self.borrowing_cost_rate / Decimal("365")

                # Calculate borrowing cost
                position_value = trade.quantity * trade.entry_price
                borrowing_cost = position_value * daily_rate * Decimal(str(duration_days))

                return borrowing_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            return Decimal("0")

        except (ValueError, TypeError, KeyError, AttributeError):
            return Decimal("0")

    def _generate_recommendations(
        self,
        cost_impact_ratio: Decimal,
        is_profitable: bool,
        exceeds_threshold: bool,
        cost_breakdowns: List[CostBreakdown],
    ) -> List[str]:
        """Generate recommendations based on cost analysis."""
        recommendations = []

        if not is_profitable:
            recommendations.append(
                "Strategy is not profitable after costs. Consider reducing trade frequency or improving entry/exit timing."
            )

        if exceeds_threshold:
            recommendations.append(
                f"Cost Impact Ratio ({cost_impact_ratio:.1f}%) exceeds threshold ({self.max_cost_impact_ratio:.1f}%). Focus on reducing costs."
            )

        # Analyze cost components
        avg_slippage = (
            sum(bd.slippage for bd in cost_breakdowns) / len(cost_breakdowns)
            if cost_breakdowns
            else Decimal("0")
        )
        avg_commission = (
            sum(bd.commission for bd in cost_breakdowns) / len(cost_breakdowns)
            if cost_breakdowns
            else Decimal("0")
        )

        if avg_slippage > avg_commission * Decimal("2"):
            recommendations.append(
                "Slippage costs are high relative to commissions. Consider using limit orders or trading during high-liquidity periods."
            )

        if avg_commission > Decimal("10"):
            recommendations.append(
                "Commission costs are high. Consider negotiating better rates with broker or reducing trade frequency."
            )

        # Check for high-cost trades
        high_cost_trades = [bd for bd in cost_breakdowns if bd.cost_percentage > Decimal("5")]
        if len(high_cost_trades) > len(cost_breakdowns) * Decimal("0.2"):
            recommendations.append(
                "More than 20% of trades have high costs (>5%). Review execution strategy."
            )

        return recommendations

    def _create_empty_analysis_result(self, strategy_name: str) -> CostAnalysisResult:
        """Create empty analysis result for strategies with no trades."""
        return CostAnalysisResult(
            strategy_name=strategy_name,
            analysis_period=(datetime.utcnow(), datetime.utcnow()),
            total_trades=0,
            total_commission=Decimal("0"),
            total_slippage=Decimal("0"),
            total_market_impact=Decimal("0"),
            total_infrastructure=Decimal("0"),
            total_borrowing=Decimal("0"),
            total_costs=Decimal("0"),
            gross_profit=Decimal("0"),
            net_profit=Decimal("0"),
            cost_impact_ratio=Decimal("0"),
            profitability_threshold=self.min_profitability_threshold,
            cost_breakdowns=[],
            is_profitable=False,
            exceeds_cost_threshold=True,
            recommendations=["No trades to analyze. Strategy needs more trading activity."],
        )
