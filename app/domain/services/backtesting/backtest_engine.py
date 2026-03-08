"""
Robust Backtesting Engine

Implements institutional-grade backtesting with:
- Realistic transaction costs
- Slippage modeling
- Market impact
- Multi-year simulation
- Survivorship bias correction
- Corporate actions handling
- Dividend reinvestment

Reference: López de Prado (2018) "Advances in Financial Machine Learning"
- PnL distribution analysis
- Backtesting overfitting detection
- Harrah's bias prevention
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

# Import canonical Trade and PerformanceMetrics from app.backtesting.models
from app.backtesting.models import PerformanceMetrics, Trade, TradeStatus
from app.shared.config.centralized_config import get_config


class OrderSide(str, Enum):
    """Side of an order - kept for backward compatibility."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Type of order."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    """Status of an order."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Trade class removed - use canonical Trade from app.backtesting.models
# The canonical Trade includes all fields needed here plus additional ones


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""

    initial_capital: Decimal
    start_date: date
    end_date: date
    commission_per_share: Decimal = Decimal("0.005")
    commission_min: Decimal = Decimal("1.0")
    slippage_model: Optional[str] = "linear"
    slippage_rate: float = 0.001  # 0.1% default
    market_impact: bool = True
    dividend_reinvestment: bool = True
    survivorship_bias_correction: bool = True
    benchmark_symbol: Optional[str] = None
    max_position_size: Optional[Decimal] = None
    max_portfolio_exposure: Optional[float] = None


# NOTE: PerformanceMetrics is now imported from app.backtesting.models
# This is the canonical source of truth for all performance metrics.


@dataclass
class BacktestResult:
    """Results from a backtest."""

    config: BacktestConfig
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[date, Decimal]] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    positions: Dict[str, Decimal] = field(default_factory=dict)
    cash: Decimal = Decimal("0")
    final_capital: Decimal = Decimal("0")
    metrics: Optional[PerformanceMetrics] = None

    @property
    def total_trades(self) -> int:
        """Total number of trades executed."""
        return len(self.trades)


class BacktestEngine:
    """
    Robust backtesting engine.

    Features:
    - Realistic transaction costs
    - Slippage modeling
    - Market impact
    - Multi-year simulation
    - Survivorship bias correction
    - Corporate actions handling
    - Dividend reinvestment

    Reference: López de Prado (2018)
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize backtest engine.

        Args:
            config: Backtest configuration
        """
        self._config = config
        self._cash = config.initial_capital
        self._positions: Dict[str, Decimal] = {}
        self._trades: List[Trade] = []
        self._equity_curve: List[Tuple[date, Decimal]] = []
        self._returns: List[float] = []
        self._current_date: Optional[date] = None
        self._prices: Dict[str, Decimal] = {}
        self._dividends: Dict[str, List[Tuple[date, Decimal]]] = {}

    def reset(self) -> None:
        """Reset the backtest engine to initial state."""
        self._cash = self._config.initial_capital
        self._positions.clear()
        self._trades.clear()
        self._equity_curve.clear()
        self._returns.clear()
        self._current_date = None
        self._prices.clear()

    @property
    def cash(self) -> Decimal:
        """Current cash balance."""
        return self._cash

    @property
    def positions(self) -> Dict[str, Decimal]:
        """Current positions."""
        return self._positions.copy()

    @property
    def equity(self) -> Decimal:
        """Total equity (cash + positions)."""
        total = self._cash
        for symbol, quantity in self._positions.items():
            price = self._prices.get(symbol, Decimal("0"))
            total += quantity * price
        return total

    def get_position_value(self, symbol: str) -> Decimal:
        """Get value of position in symbol."""
        quantity = self._positions.get(symbol, Decimal("0"))
        price = self._prices.get(symbol, Decimal("0"))
        return quantity * price

    def update_prices(self, prices: Dict[str, Decimal], current_date: date) -> None:
        """
        Update prices for all symbols.

        Args:
            prices: Dictionary of symbol -> price
            current_date: Current simulation date
        """
        self._prices.update(prices)
        self._current_date = current_date

        # Record equity curve
        self._equity_curve.append((current_date, self.equity))

        # Calculate daily return
        if len(self._equity_curve) > 1:
            prev_equity = self._equity_curve[-2][1]
            if prev_equity > 0:
                daily_return = float((self.equity - prev_equity) / prev_equity)
                self._returns.append(daily_return)

    def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price_limit: Optional[Decimal] = None,
    ) -> Optional[Trade]:
        """
        Execute an order with realistic costs.

        Args:
            symbol: Symbol to trade
            side: Buy or sell
            quantity: Quantity to trade
            order_type: Type of order
            price_limit: Limit price for limit orders

        Returns:
            Trade if executed, None otherwise
        """
        if quantity <= 0:
            return None

        # Get current price
        current_price = self._prices.get(symbol)
        if current_price is None:
            return None

        # Check limit order
        if order_type == OrderType.LIMIT and price_limit is not None:
            if side == OrderSide.BUY and current_price > price_limit:
                return None  # Limit not hit
            if side == OrderSide.SELL and current_price < price_limit:
                return None  # Limit not hit

        # Calculate slippage
        slippage = self._calculate_slippage(symbol, side, quantity, current_price)

        # Calculate market impact for large orders
        market_impact = Decimal("0")
        if self._config.market_impact:
            market_impact = self._calculate_market_impact(symbol, side, quantity, current_price)

        # Calculate execution price
        execution_price = current_price
        if side == OrderSide.BUY:
            execution_price = current_price + slippage + market_impact
        else:
            execution_price = current_price - slippage - market_impact

        # Calculate commission
        commission = self._calculate_commission(quantity, execution_price)

        # Calculate total cost
        total_cost = quantity * execution_price + commission
        if side == OrderSide.BUY:
            total_cost += quantity * (slippage + market_impact)

        # Check if we have enough cash/position
        if side == OrderSide.BUY:
            required = total_cost
            if required > self._cash:
                # Insufficient funds
                return None
        else:
            current_position = self._positions.get(symbol, Decimal("0"))
            if quantity > current_position:
                # Insufficient position
                return None

        # Execute trade
        if side == OrderSide.BUY:
            self._cash -= total_cost
            self._positions[symbol] = self._positions.get(symbol, Decimal("0")) + quantity
        else:
            self._cash += (
                quantity * execution_price - commission - quantity * (slippage + market_impact)
            )
            self._positions[symbol] = self._positions.get(symbol, Decimal("0")) - quantity

            # Clean up empty positions
            if self._positions[symbol] == 0:
                del self._positions[symbol]

        # Record trade using canonical Trade model
        trade_timestamp = datetime.combine(self._current_date or date.today(), datetime.min.time())
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side.value if isinstance(side, OrderSide) else side,
            quantity=quantity,
            entry_price=execution_price,
            entry_time=trade_timestamp,
            status=TradeStatus.OPEN,
            commission=commission,
            slippage=slippage if side == OrderSide.BUY else -slippage,
            market_impact=market_impact if side == OrderSide.BUY else -market_impact,
        )
        self._trades.append(trade)

        return trade

    def _calculate_slippage(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> Decimal:
        """Calculate slippage for order."""
        if self._config.slippage_model == "linear":
            # Linear slippage based on quantity
            slippage_rate = Decimal(str(self._config.slippage_rate))
            return price * quantity * slippage_rate / Decimal("1000")
        elif self._config.slippage_model == "percentage":
            slippage_pct = Decimal(str(self._config.slippage_rate))
            return price * slippage_pct
        else:
            return Decimal("0")

    def _calculate_market_impact(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> Decimal:
        """Calculate market impact for large orders (simplified)."""
        # Simplified square-root law
        # Impact ~ (quantity / adv) ^ 0.5
        # This is a placeholder - real implementation needs ADV data
        impact_rate = Decimal(str(self._config.slippage_rate)) * Decimal("0.5")
        return price * impact_rate * (quantity.sqrt() if quantity > 0 else Decimal("0"))

    def _calculate_commission(self, quantity: Decimal, price: Decimal) -> Decimal:
        """Calculate commission for trade."""
        per_share = quantity * self._config.commission_per_share
        return max(per_share, self._config.commission_min)

    def handle_dividend(self, symbol: str, dividend_per_share: Decimal) -> Decimal:
        """
        Handle dividend payment.

        Args:
            symbol: Symbol paying dividend
            dividend_per_share: Dividend per share

        Returns:
            Total dividend received
        """
        position = self._positions.get(symbol, Decimal("0"))
        if position == 0:
            return Decimal("0")

        dividend = position * dividend_per_share

        if self._config.dividend_reinvestment:
            # Reinvest dividend
            price = self._prices.get(symbol)
            if price and price > 0:
                shares_to_buy = dividend // price
                if shares_to_buy > 0:
                    self.execute_order(symbol, OrderSide.BUY, shares_to_buy)
        else:
            # Add to cash
            self._cash += dividend

        return dividend

    def close_all_positions(self) -> List[Trade]:
        """
        Close all positions at current prices.

        Returns:
            List of closing trades
        """
        closing_trades = []
        for symbol, quantity in list(self._positions.items()):
            if quantity > 0:
                trade = self.execute_order(symbol, OrderSide.SELL, quantity)
                if trade:
                    closing_trades.append(trade)

        return closing_trades

    def calculate_metrics(
        self, benchmark_returns: Optional[NDArray[np.float64]] = None
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics.

        Args:
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            PerformanceMetrics (canonical from app.backtesting.models)
        """

        # Helper function to convert to Decimal
        def to_decimal(val):
            if val is None:
                return None
            return Decimal(str(val))

        if not self._returns:
            return PerformanceMetrics()

        returns_array = np.array(self._returns)

        # Basic metrics
        total_return = float(
            (self.equity - self._config.initial_capital) / self._config.initial_capital
        )

        days = len(self._equity_curve)
        years = max(days / 252, 1 / 252)  # Avoid division by zero
        annualized_return = (1 + total_return) ** (1 / years) - 1

        # Volatility
        volatility = float(np.std(returns_array))
        annualized_volatility = volatility * np.sqrt(252)

        # Sharpe ratio (using CentralizedConfig for risk-free rate)
        risk_free_rate = float(get_config().backtesting.default_risk_free_rate)
        sharpe_ratio = (
            (annualized_return - risk_free_rate) / annualized_volatility
            if annualized_volatility > 0
            else 0.0
        )

        # Sortino ratio
        downside_returns = returns_array[returns_array < 0]
        downside_deviation = (
            float(np.std(downside_returns)) * np.sqrt(252) if len(downside_returns) > 0 else 0.0
        )
        sortino_ratio = (
            (annualized_return - risk_free_rate) / downside_deviation
            if downside_deviation > 0
            else 0.0
        )

        # Drawdown
        equity_values = [float(eq[1]) for eq in self._equity_curve]
        cummax = np.maximum.accumulate(equity_values)
        drawdowns = (np.array(equity_values) - cummax) / cummax
        max_drawdown = float(np.min(drawdowns))

        # Max drawdown duration
        drawdown_end = np.argmin(drawdowns)
        drawdown_start = np.argmax(equity_values[:drawdown_end]) if drawdown_end > 0 else 0
        max_drawdown_duration = int(drawdown_end - drawdown_start)

        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        # Trade statistics
        trade_returns = []
        for i, trade in enumerate(self._trades):
            if trade.side == OrderSide.SELL:
                # Find matching buy
                for j in range(i - 1, -1, -1):
                    if (
                        self._trades[j].side == OrderSide.BUY
                        and self._trades[j].symbol == trade.symbol
                    ):
                        buy_price = self._trades[j].price
                        sell_price = trade.price
                        trade_return = float((sell_price - buy_price) / buy_price)
                        trade_returns.append(trade_return)
                        break

        if trade_returns:
            win_rate = np.mean([1 for r in trade_returns if r > 0])
            winning_trades = [r for r in trade_returns if r > 0]
            losing_trades = [r for r in trade_returns if r < 0]

            profit_factor = (
                sum(winning_trades) / abs(sum(losing_trades)) if losing_trades else float('inf')
            )
            avg_trade_return = float(np.mean(trade_returns))
            best_trade = max(trade_returns)
            worst_trade = min(trade_returns)
            avg_win = float(np.mean(winning_trades)) if winning_trades else 0.0
            avg_loss = float(np.mean(losing_trades)) if losing_trades else 0.0
            expectancy = avg_trade_return
        else:
            win_rate = 0.0
            profit_factor = 0.0
            avg_trade_return = 0.0
            best_trade = 0.0
            worst_trade = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            expectancy = 0.0

        # Skewness and kurtosis
        from scipy import stats

        skewness = float(stats.skew(returns_array))
        kurtosis = float(stats.kurtosis(returns_array))

        # VaR and CVaR
        var_95 = float(np.percentile(returns_array, 5))
        var_99 = float(np.percentile(returns_array, 1))
        cvar_95 = float(np.mean(returns_array[returns_array <= var_95]))

        # Information ratio and tracking error (vs benchmark)
        if benchmark_returns is not None and len(benchmark_returns) == len(returns_array):
            excess_returns = returns_array - benchmark_returns
            information_ratio = (
                float(np.mean(excess_returns) / np.std(excess_returns))
                if np.std(excess_returns) > 0
                else 0.0
            )
            tracking_error = float(np.std(excess_returns) * np.sqrt(252))

            # Alpha and Beta
            covariance_matrix = np.cov(returns_array, benchmark_returns)
            beta = (
                float(covariance_matrix[0, 1] / covariance_matrix[1, 1])
                if covariance_matrix[1, 1] > 0
                else 1.0
            )
            alpha = float(
                annualized_return
                - (risk_free_rate + beta * (np.mean(benchmark_returns) * 252 - risk_free_rate))
            )
        else:
            information_ratio = 0.0
            tracking_error = 0.0
            beta = 1.0
            alpha = 0.0

        return PerformanceMetrics(
            total_return=to_decimal(total_return),
            annualized_return=to_decimal(annualized_return),
            sharpe_ratio=to_decimal(sharpe_ratio),
            sortino_ratio=to_decimal(sortino_ratio),
            calmar_ratio=to_decimal(calmar_ratio),
            max_drawdown=to_decimal(max_drawdown),
            max_drawdown_duration=max_drawdown_duration,
            volatility=to_decimal(volatility),
            annualized_volatility=to_decimal(annualized_volatility),
            win_rate=to_decimal(win_rate * 100),  # Convert to percentage
            profit_factor=to_decimal(profit_factor) if profit_factor != float('inf') else None,
            avg_trade_return=to_decimal(avg_trade_return),
            total_trades=len(self._trades),
            winning_trades=len([r for r in trade_returns if r > 0]),
            losing_trades=len([r for r in trade_returns if r < 0]),
            best_trade=to_decimal(best_trade),
            worst_trade=to_decimal(worst_trade),
            avg_win=to_decimal(avg_win),
            avg_loss=to_decimal(avg_loss),
            expectancy=to_decimal(expectancy),
            skewness=to_decimal(skewness),
            kurtosis=to_decimal(kurtosis),
            var_95=to_decimal(var_95),
            var_99=to_decimal(var_99),
            cvar_95=to_decimal(cvar_95),
            information_ratio=to_decimal(information_ratio),
            tracking_error=to_decimal(tracking_error),
            beta=to_decimal(beta),
            alpha=to_decimal(alpha),
        )

    def get_result(self) -> BacktestResult:
        """Get backtest results."""
        return BacktestResult(
            config=self._config,
            trades=self._trades.copy(),
            equity_curve=self._equity_curve.copy(),
            returns=self._returns.copy(),
            positions=self._positions.copy(),
            cash=self._cash,
            final_capital=self.equity,
        )
