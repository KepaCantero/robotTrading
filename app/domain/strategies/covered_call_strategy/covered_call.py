"""
Covered Call Strategy Domain Service

Implements covered call strategy for income generation.
Sells call options against owned stock positions to generate premium income.

Reference: Rule 42-kissell-algorithmic-trading-portfolio-management.md
Paper: Kissell, M., & Posament, S. (2017). "Options Trading and Hedging"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class CallSignal(str, Enum):
    """Signal for covered call strategy."""

    SELL_CALL = "sell_call"  # Sell call option (open covered call)
    BUY_BACK_CALL = "buy_back_call"  # Buy back call (close position)
    ROLL_CALL = "roll_call"  # Roll to next expiration/strike
    HOLD = "hold"  # Hold current position
    NO_ACTION = "no_action"


@dataclass
class OptionData:
    """Data for a call option."""

    symbol: str
    strike: float  # Strike price
    expiration_date: str  # YYYY-MM-DD
    days_to_expiration: int
    implied_volatility: float  # IV
    bid: float  # Bid price
    ask: float  # Ask price
    mid_price: float  # Mid price
    delta: float  # Option delta
    theta: float  # Time decay per day

    @property
    def is_itm(self) -> bool:
        """Check if option is in-the-money."""
        return self.delta > 0.5

    @property
    def is_otm(self) -> bool:
        """Check if option is out-of-the-money."""
        return self.delta < 0.5

    @property
    def time_value(self) -> float:
        """Get time value of option."""
        return self.mid_price - max(0, self.delta)  # Simplified


@dataclass
class CoveredCallPosition:
    """A covered call position."""

    stock_symbol: str
    stock_quantity: int  # Number of shares owned
    stock_cost_basis: float  # Cost basis per share
    call_option: OptionData  # Short call option
    call_premium_received: float  # Premium received
    open_date: str  # Position open date

    @property
    def break_even_price(self) -> float:
        """Calculate break-even price at expiration."""
        return self.stock_cost_basis - self.call_premium_received

    @property
    def max_profit(self) -> float:
        """Calculate maximum profit."""
        return self.call_option.strike - self.stock_cost_basis + self.call_premium_received

    @property
    def max_loss(self) -> float:
        """Calculate maximum loss (stock goes to zero)."""
        return self.stock_cost_basis - self.call_premium_received

    @property
    def assignment_probability(self) -> float:
        """Estimate probability of assignment (simplified)."""
        if self.call_option.is_itm:
            # Higher delta = higher probability
            return min(1.0, self.call_option.delta * 2)
        return self.call_option.delta


@dataclass
class CoveredCallPortfolio:
    """Portfolio of covered call positions."""

    positions: List[CoveredCallPosition]
    total_premium_collected: float
    assigned_positions: int  # Number of positions assigned
    avg_monthly_income: float  # Average monthly income from premiums

    @property
    def annualized_yield(self) -> float:
        """Calculate annualized yield from premiums."""
        if len(self.positions) == 0:
            return 0.0
        return self.avg_monthly_income * 12

    @property
    def capital_at_risk(self) -> float:
        """Calculate total capital at risk."""
        return sum(pos.stock_quantity * pos.stock_cost_basis for pos in self.positions)


class CoveredCallStrategy:
    """
    Covered call strategy for income generation.

    Strategy:
    1. Own underlying stock
    2. Sell call options against stock
    3. Collect premium income
    4. Manage assignment risk

    This is a pure domain service that can be used with any data source.

    Reference: Kissell, M., & Posament, S. (2017)
    """

    def __init__(
        self,
        target_otm_percentage: float = 0.05,  # Target 5% OTM
        min_days_to_expiration: int = 30,  # Minimum days to expiration
        max_days_to_expiration: int = 45,  # Maximum days (monthly cycle)
        min_premium_threshold: float = 0.01,  # Minimum 1% premium
        max_iv_percentile: float = 0.8,  # Max IV percentile (avoid expensive options)
        roll_threshold: float = 0.5,  # Roll when delta > 0.5 (ITM)
        assignment_threshold: float = 0.8,  # Close when assignment probability > 80%
    ):
        """
        Initialize covered call strategy.

        Args:
            target_otm_percentage: Target percentage OTM for strikes
            min_days_to_expiration: Minimum days to expiration
            max_days_to_expiration: Maximum days to expiration
            min_premium_threshold: Minimum premium threshold (% of stock price)
            max_iv_percentile: Maximum IV percentile
            roll_threshold: Delta threshold for rolling calls
            assignment_threshold: Assignment probability threshold
        """
        self._target_otm = target_otm_percentage
        self._min_dte = min_days_to_expiration
        self._max_dte = max_days_to_expiration
        self._min_premium = min_premium_threshold
        self._max_iv = max_iv_percentile
        self._roll_threshold = roll_threshold
        self._assign_threshold = assignment_threshold

        # Load trading thresholds from config
        trading_config = get_config()
        self._tt = trading_config.trading_thresholds

    def select_optimal_call(
        self,
        stock_price: float,
        available_calls: List[OptionData],
        stock_quantity: int,
    ) -> Optional[OptionData]:
        """
        Select optimal call option to sell.

        Args:
            stock_price: Current stock price
            available_calls: Available call options
            stock_quantity: Number of shares owned

        Returns:
            Best option to sell, or None if none suitable
        """
        # Input validation
        if not np.isfinite(stock_price) or stock_price <= 0:
            logger.warning(f"Invalid stock_price: {stock_price}")
            return None

        if stock_quantity <= 0:
            logger.warning(f"Invalid stock_quantity: {stock_quantity}")
            return None

        if not available_calls:
            logger.warning("No available calls provided")
            return None

        # Filter by expiration and validate option data
        valid_calls = []
        for opt in available_calls:
            # Validate option data
            if not all(
                [
                    np.isfinite(opt.strike) and opt.strike > 0,
                    np.isfinite(opt.days_to_expiration) and opt.days_to_expiration >= 0,
                    np.isfinite(opt.mid_price) and opt.mid_price >= 0,
                    np.isfinite(opt.delta) and opt.delta >= 0 and opt.delta <= 1,
                    np.isfinite(opt.implied_volatility) and opt.implied_volatility >= 0,
                ]
            ):
                logger.warning(f"Invalid option data for {opt.symbol}, skipping")
                continue

            if self._min_dte <= opt.days_to_expiration <= self._max_dte:
                valid_calls.append(opt)

        if not valid_calls:
            logger.warning("No valid calls within DTE range")
            return None

        # Calculate target strike (OTM)
        target_strike = stock_price * (1 + self._target_otm)

        if not np.isfinite(target_strike) or target_strike <= 0:
            target_strike = stock_price * 1.05  # Fallback

        # Find closest strike to target
        best_call = None
        best_score = -float('inf')

        for call in valid_calls:
            # Check premium threshold
            if stock_price > 0:
                premium_pct = call.mid_price / stock_price
            else:
                continue

            if premium_pct < self._min_premium:
                continue

            # Calculate score (prefer closest to target strike with good premium)
            if stock_price > 0:
                strike_distance = abs(call.strike - target_strike) / stock_price
            else:
                continue

            premium_score = premium_pct  # Higher premium better

            # Combined score (prefer near target with good premium)
            score = premium_score - strike_distance

            if not np.isfinite(score):
                continue

            if score > best_score:
                best_score = score
                best_call = call

        return best_call

    def generate_signal(
        self,
        covered_position: Optional[CoveredCallPosition],
        stock_price: float,
        available_calls: List[OptionData],
    ) -> CallSignal:
        """
        Generate trading signal for covered call position.

        Args:
            covered_position: Current covered call position (if exists)
            stock_price: Current stock price
            available_calls: Available call options

        Returns:
            CallSignal with action
        """
        if covered_position is None:
            # No position - check if should open
            optimal_call = self.select_optimal_call(stock_price, available_calls, 100)
            if optimal_call:
                return CallSignal.SELL_CALL
            return CallSignal.NO_ACTION

        # Check current position
        option = covered_position.call_option

        # Check if close to expiration or high assignment probability
        if (
            option.days_to_expiration <= 7
            or covered_position.assignment_probability > self._assign_threshold
        ):
            # Close to expiration or high assignment risk
            if option.is_itm and option.delta > self._roll_threshold:
                # Roll to next month
                next_month_call = self._find_next_month_call(
                    stock_price, available_calls, option.strike
                )
                if next_month_call:
                    return CallSignal.ROLL_CALL
            return CallSignal.BUY_BACK_CALL

        # Check if should roll early for better premium
        if option.is_otm and option.delta < 0.3:
            # Very OTM - could roll up for more premium
            roll_up_call = self._find_roll_up_call(stock_price, available_calls, option)
            if roll_up_call:
                return CallSignal.ROLL_CALL

        return CallSignal.HOLD

    def _find_next_month_call(
        self,
        stock_price: float,
        available_calls: List[OptionData],
        current_strike: float,
    ) -> Optional[OptionData]:
        """Find call option for next month with similar strike."""
        # Filter for later expirations
        future_calls = [
            opt for opt in available_calls if opt.days_to_expiration > self._min_dte + 7
        ]

        # Find closest strike to current
        best_call = None
        min_strike_diff = float('inf')

        for call in future_calls:
            strike_diff = abs(call.strike - current_strike)
            if strike_diff < min_strike_diff:
                min_strike_diff = strike_diff
                best_call = call

        return best_call

    def _find_roll_up_call(
        self,
        stock_price: float,
        available_calls: List[OptionData],
        current_option: OptionData,
    ) -> Optional[OptionData]:
        """Find call option with higher strike for more premium."""
        # Look for higher strike with similar expiration
        target_strike = stock_price * (
            1 + self._target_otm * self._tt.covered_call_otm_multiplier
        )  # More OTM

        best_call = None
        min_distance = float('inf')

        for call in available_calls:
            # Must be higher strike
            if call.strike <= current_option.strike:
                continue

            # Similar expiration
            if abs(call.days_to_expiration - current_option.days_to_expiration) > 7:
                continue

            # Find closest to target
            distance = abs(call.strike - target_strike)
            if distance < min_distance:
                min_distance = distance
                best_call = call

        return best_call

    def calculate_position_size(
        self,
        capital: float,
        stock_price: float,
        max_position_pct: float = 0.05,
    ) -> int:
        """
        Calculate number of shares for covered call position.

        Args:
            capital: Available capital
            stock_price: Current stock price
            max_position_pct: Maximum position as % of capital

        Returns:
            Number of shares (in lots of 100)
        """
        # Input validation
        if not np.isfinite(capital) or capital <= 0:
            logger.warning(f"Invalid capital: {capital}")
            return 100  # Minimum

        if not np.isfinite(stock_price) or stock_price <= 0:
            logger.warning(f"Invalid stock_price: {stock_price}")
            return 100  # Minimum

        if not np.isfinite(max_position_pct) or max_position_pct <= 0 or max_position_pct > 1:
            logger.warning(f"Invalid max_position_pct: {max_position_pct}, using 0.05")
            max_position_pct = 0.05

        max_investment = capital * max_position_pct
        max_shares = int(max_investment / stock_price)

        # Round down to nearest 100 (option contract multiplier)
        shares = (max_shares // 100) * 100

        return max(100, shares)  # Minimum 1 contract

    def calculate_expected_return(
        self,
        covered_position: CoveredCallPosition,
        days_to_expiration: int,
    ) -> float:
        """
        Calculate expected annualized return.

        Args:
            covered_position: Covered call position
            days_to_expiration: Days until option expiration

        Returns:
            Annualized return (0-1)
        """
        # Input validation
        if (
            not np.isfinite(covered_position.call_premium_received)
            or covered_position.call_premium_received < 0
        ):
            logger.warning("Invalid premium received")
            return 0.0

        if (
            not np.isfinite(covered_position.stock_cost_basis)
            or covered_position.stock_cost_basis <= 0
        ):
            logger.warning("Invalid stock cost basis")
            return 0.0

        if covered_position.stock_quantity <= 0:
            logger.warning("Invalid stock quantity")
            return 0.0

        if not np.isfinite(days_to_expiration) or days_to_expiration < 0:
            logger.warning("Invalid days to expiration")
            return 0.0

        # Premium income
        premium = covered_position.call_premium_received

        # Calculate return
        investment = covered_position.stock_cost_basis * covered_position.stock_quantity

        if investment <= 0:
            return 0.0

        # Annualized return
        days = max(1, days_to_expiration)
        annual_return = (premium / investment) * (365 / days)

        # Validate and clamp
        if not np.isfinite(annual_return):
            return 0.0

        return min(1.0, max(0.0, annual_return))

    def create_covered_call_position(
        self,
        stock_symbol: str,
        stock_quantity: int,
        stock_cost_basis: float,
        call_option: OptionData,
        open_date: str,
    ) -> CoveredCallPosition:
        """
        Create a new covered call position.

        Args:
            stock_symbol: Stock symbol
            stock_quantity: Number of shares
            stock_cost_basis: Cost basis per share
            call_option: Call option to sell
            open_date: Position open date

        Returns:
            CoveredCallPosition
        """
        premium = call_option.bid  # Use bid for conservative estimate

        return CoveredCallPosition(
            stock_symbol=stock_symbol,
            stock_quantity=stock_quantity,
            stock_cost_basis=stock_cost_basis,
            call_option=call_option,
            call_premium_received=premium,
            open_date=open_date,
        )

    def manage_position(
        self,
        position: CoveredCallPosition,
        current_stock_price: float,
        current_date: str,
    ) -> Tuple[CallSignal, Optional[OptionData]]:
        """
        Manage existing covered call position.

        Args:
            position: Current position
            current_stock_price: Current stock price
            current_date: Current date (YYYY-MM-DD)

        Returns:
            Tuple of (signal, new_option if rolling)
        """
        option = position.call_option

        # Check for assignment scenarios
        if option.is_itm and current_stock_price > option.strike:
            # In-the-money near expiration
            if option.days_to_expiration <= 7:
                # Close to expiration - expect assignment
                return CallSignal.BUY_BACK_CALL, None

            # Early roll consideration
            if option.delta > self._roll_threshold:
                # Roll to next month
                roll_call = OptionData(  # Placeholder - would come from market data
                    symbol=option.symbol,
                    strike=option.strike,
                    expiration_date="next_month",
                    days_to_expiration=option.days_to_expiration + 30,
                    implied_volatility=option.implied_volatility,
                    bid=option.bid,
                    ask=option.ask,
                    mid_price=option.mid_price,
                    delta=option.delta * 0.8,  # Lower delta for further OTM
                    theta=option.theta,
                )
                return CallSignal.ROLL_CALL, roll_call

        # Check time decay opportunity
        if option.days_to_expiration <= 14 and option.is_otm:
            # Close to expiration OTM - buy back for profit
            return CallSignal.BUY_BACK_CALL, None

        return CallSignal.HOLD, None

    def calculate_portfolio_metrics(
        self,
        positions: List[CoveredCallPosition],
    ) -> Dict[str, float]:
        """
        Calculate portfolio-level metrics.

        Args:
            positions: List of covered call positions

        Returns:
            Dictionary of metrics
        """
        if not positions:
            return {
                "total_capital": 0.0,
                "total_premium": 0.0,
                "annualized_yield": 0.0,
                "avg_days_to_expiration": 0.0,
                "positions_at_risk": 0,
            }

        total_capital = sum(pos.stock_quantity * pos.stock_cost_basis for pos in positions)
        total_premium = sum(pos.call_premium_received for pos in positions)

        # Calculate weighted average days to expiration
        total_dte = sum(pos.call_option.days_to_expiration for pos in positions)
        avg_dte = total_dte / len(positions)

        # Positions at risk (ITM)
        at_risk = sum(1 for pos in positions if pos.call_option.is_itm)

        # Annualized yield estimate
        if total_capital > 0:
            # Assume 30-day average cycle
            monthly_yield = total_premium / total_capital
            annual_yield = monthly_yield * 12
        else:
            annual_yield = 0.0

        return {
            "total_capital": total_capital,
            "total_premium": total_premium,
            "annualized_yield": annual_yield,
            "avg_days_to_expiration": avg_dte,
            "positions_at_risk": at_risk,
            "total_positions": len(positions),
        }
