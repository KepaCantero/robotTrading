"""
Ernest Chan - Quantitative Trading: Execution Algorithms Implementation

This module implements execution algorithms as described in Ernest Chan's
"Quantitative Trading: How to Build Your Own Algorithmic Trading Business".

Key Concepts:
- VWAP (Volume-Weighted Average Price) execution
- TWAP (Time-Weighted Average Price) execution
- Implementation Shortfall minimization
- Market impact modeling and minimization
- Optimal execution scheduling
- Arrival price vs. Decision price
- Almgren-Chriss optimal execution framework

Based on:
- Almgren, R., & Chriss, N. (2001). Optimal execution of portfolio transactions.
- Kissell, R., & Glantz, M. (2003). Optimal Trading Strategies.
- Chan, E. P. (2013). Algorithmic Trading: Winning Strategies and Their Rationale.

Author: Algorithmic Trading System
Date: 2026-01-28
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """Execution plan for an order."""

    symbol: str
    side: str  # 'buy' or 'sell'
    total_quantity: float
    execution_slices: List['ExecutionSlice']
    algorithm: str
    urgency: float  # 0 to 1, where 1 is most urgent
    expected_market_impact: float
    expected_timing_risk: float
    estimated_slippage: float
    start_time: datetime
    end_time: datetime


@dataclass
class ExecutionSlice:
    """Single execution slice/tranche."""

    slice_number: int
    quantity: float
    target_time: datetime
    limit_price: Optional[float]
    execution_algorithm: str
    participation_rate: Optional[float] = None  # For POV/PoV algorithms


@dataclass
class MarketImpactModel:
    """
    Market Impact Model.

    Models the market impact of trading based on:
    - Permanent impact (information leakage)
    - Temporary impact (liquidity consumption)
    - Volatility effects
    """

    permanent_impact_coef: float  # Coefficient for permanent impact
    temporary_impact_coef: float  # Coefficient for temporary impact
    volatility_impact_coef: float  # Volatility scaling
    daily_volume: float  # Average daily volume
    spread: float  # Current bid-ask spread


class VWAPExecutor:
    """
    Volume-Weighted Average Price (VWAP) Execution Algorithm.

    Executes orders throughout the day to match the VWAP price.
    Slices orders proportionally to historical volume patterns.

    Advantages:
    - Good benchmark for execution quality
    - Minimizes market impact by spreading execution
    - Easy to implement and understand

    Disadvantages:
    - Predictable execution pattern (can be gamed)
    - May underperform in trending markets
    - Doesn't adapt to real-time market conditions

    Based on: Implementation of standard VWAP algorithms as described in
    "Algorithmic Trading" by Ernest Chan.

    Usage:
        >>> executor = VWAPExecutor()
        >>> plan = executor.create_execution_plan(symbol="AAPL", quantity=10000, side="buy")
    """

    def __init__(
        self,
        typical_volume_profile: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize VWAP Executor.

        Args:
            typical_volume_profile: Volume profile by time period (% of daily volume)
        """
        # Default US equity market volume profile
        self.typical_volume_profile = typical_volume_profile or {
            "09:30-10:00": 0.12,  # Opening
            "10:00-11:00": 0.10,
            "11:00-12:00": 0.08,
            "12:00-13:00": 0.06,  # Lunch lull
            "13:00-14:00": 0.10,
            "14:00-15:00": 0.12,
            "15:00-16:00": 0.22,  # Close
            "16:00-20:00": 0.20,  # After hours
        }

        logger.info("VWAPExecutor initialized")

    def create_execution_plan(
        self,
        symbol: str,
        quantity: float,
        side: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_slices: int = 20,
        min_slice_pct: float = getattr(config.trading, 'max_risk_per_trade', 0.02),  # Minimum 2% per slice
        custom_volume_profile: Optional[Dict[str, float]] = None,
    ) -> ExecutionPlan:
        """
        Create VWAP execution plan.

        Args:
            symbol: Trading symbol
            quantity: Total quantity to trade
            side: 'buy' or 'sell'
            start_time: Execution start time (default: now)
            end_time: Execution end time (default: 1 day from start)
            max_slices: Maximum number of slices
            min_slice_pct: Minimum percentage per slice
            custom_volume_profile: Custom volume profile

        Returns:
            ExecutionPlan with VWAP slices
        """
        try:
            # Set times
            start_time = start_time or datetime.now()
            end_time = end_time or (start_time + timedelta(days=1))

            # Use custom profile if provided
            volume_profile = custom_volume_profile or self.typical_volume_profile

            # Create execution slices
            slices = []
            remaining_qty = quantity
            slice_num = 0

            for time_period, vol_pct in volume_profile.items():
                if remaining_qty <= 0 or slice_num >= max_slices:
                    break

                # Calculate slice quantity based on volume profile
                slice_qty = min(
                    remaining_qty,
                    quantity * vol_pct,
                    quantity * min_slice_pct * 5,  # Cap at 5x minimum
                )

                if slice_qty > 0:
                    # Parse time period
                    start_str, end_str = time_period.split("-")

                    # Calculate target time (middle of period)
                    target_time = self._parse_target_time(start_time, start_str, end_str)

                    # Create slice
                    slices.append(
                        ExecutionSlice(
                            slice_number=slice_num,
                            quantity=slice_qty,
                            target_time=target_time,
                            limit_price=None,  # Market order
                            execution_algorithm="vwap",
                        )
                    )

                    remaining_qty -= slice_qty
                    slice_num += 1

            # Add any remaining quantity to last slice
            if remaining_qty > 0 and slices:
                slices[-1].quantity += remaining_qty

            # Calculate expected market impact
            expected_impact = self._calculate_market_impact(quantity, symbol, side)

            # Calculate timing risk
            timing_risk = self._calculate_timing_risk(quantity, start_time, end_time)

            # Estimate slippage
            estimated_slippage = expected_impact + timing_risk

            plan = ExecutionPlan(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
                execution_slices=slices,
                algorithm="vwap",
                urgency=0.5,  # Medium urgency
                expected_market_impact=expected_impact,
                expected_timing_risk=timing_risk,
                estimated_slippage=estimated_slippage,
                start_time=start_time,
                end_time=end_time,
            )

            logger.info(
                f"VWAP plan created for {symbol}: {quantity} shares, "
                f"{len(slices)} slices, expected_impact={expected_impact:.4f}"
            )

            return plan

        except (ValueError, TypeError) as e:
            logger.error(f"VWAP plan creation failed: {e}")
            raise

    def _parse_target_time(
        self,
        base_date: datetime,
        start_str: str,
        end_str: str,
    ) -> datetime:
        """Parse target time from time period string."""
        try:
            # Parse start time
            start_hour, start_min = map(int, start_str.split(":"))

            # Create target time (middle of period)
            target_time = base_date.replace(
                hour=start_hour,
                minute=start_min,
                second=0,
                microsecond=0,
            )

            return target_time

        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse time period: {e}")
            return base_date + timedelta(hours=1)

    def _calculate_market_impact(
        self,
        quantity: float,
        symbol: str,
        side: str,
        daily_volume: float = 1_000_000,
        price: float = 100.0,
    ) -> float:
        """
        Calculate expected market impact.

        Uses Almgren-Chriss model approximation.

        Args:
            quantity: Order quantity
            symbol: Trading symbol
            side: Order side
            daily_volume: Average daily volume
            price: Current price

        Returns:
            Expected market impact (bps)
        """
        # Market participation rate
        participation_rate = quantity / daily_volume

        # Permanent impact: proportional to participation rate
        # Typical coefficient: 0.1 to 1.0 bps per 1% participation
        permanent_impact = 0.5 * participation_rate * 100  # bps

        # Temporary impact: proportional to square root of participation
        temporary_impact = 1.0 * np.sqrt(participation_rate) * 100  # bps

        total_impact = permanent_impact + temporary_impact

        return total_impact

    def _calculate_timing_risk(
        self,
        quantity: float,
        start_time: datetime,
        end_time: datetime,
        daily_volatility: float = getattr(config.trading, 'max_risk_per_trade', 0.02),  # 2% daily vol
    ) -> float:
        """
        Calculate timing risk (uncertainty from delayed execution).

        Args:
            quantity: Order quantity
            start_time: Start time
            end_time: End time
            daily_volatility: Daily volatility

        Returns:
            Expected timing risk (bps)
        """
        # Execution duration (in days)
        duration = (end_time - start_time).total_seconds() / (24 * 3600)

        # Timing risk scales with sqrt(duration) * volatility
        timing_risk = daily_volatility * np.sqrt(duration) * 100  # bps

        return timing_risk


class TWAPExecutor:
    """
    Time-Weighted Average Price (TWAP) Execution Algorithm.

    Executes orders evenly over a specified time period.
    Simpler than VWAP but less effective at minimizing impact.

    Advantages:
    - Very simple to implement
    - Unpredictable execution pattern (harder to game)
    - Good for illiquid securities

    Disadvantages:
    - May execute during high-impact periods
    - Doesn't account for volume patterns

    Usage:
        >>> executor = TWAPExecutor()
        >>> plan = executor.create_execution_plan(symbol="AAPL", quantity=10000, duration_minutes=60)
    """

    def __init__(self):
        """Initialize TWAP Executor."""
        logger.info("TWAPExecutor initialized")

    def create_execution_plan(
        self,
        symbol: str,
        quantity: float,
        side: str,
        start_time: Optional[datetime] = None,
        duration_minutes: int = 60,
        num_slices: int = 12,
        randomize_timing: bool = True,
        randomization_pct: float = 0.2,  # 20% timing randomization
    ) -> ExecutionPlan:
        """
        Create TWAP execution plan.

        Args:
            symbol: Trading symbol
            quantity: Total quantity to trade
            side: 'buy' or 'sell'
            start_time: Execution start time
            duration_minutes: Total execution duration
            num_slices: Number of time slices
            randomize_timing: Whether to randomize slice timings
            randomization_pct: Percentage of timing randomization

        Returns:
            ExecutionPlan with TWAP slices
        """
        try:
            start_time = start_time or datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)

            # Calculate quantity per slice
            base_slice_qty = quantity / num_slices

            # Calculate time interval
            interval_seconds = (duration_minutes * 60) / num_slices

            slices = []
            remaining_qty = quantity

            for i in range(num_slices):
                if remaining_qty <= 0:
                    break

                # Calculate slice quantity (last slice gets remainder)
                slice_qty = (
                    min(base_slice_qty, remaining_qty) if i < num_slices - 1 else remaining_qty
                )

                # Calculate target time
                base_target_time = start_time + timedelta(
                    seconds=i * interval_seconds + interval_seconds / 2
                )

                # Add randomization if requested
                if randomize_timing:
                    random_offset = (
                        np.random.uniform(-randomization_pct, randomization_pct) * interval_seconds
                    )
                    target_time = base_target_time + timedelta(seconds=random_offset)
                else:
                    target_time = base_target_time

                slices.append(
                    ExecutionSlice(
                        slice_number=i,
                        quantity=slice_qty,
                        target_time=target_time,
                        limit_price=None,
                        execution_algorithm="twap",
                    )
                )

                remaining_qty -= slice_qty

            # Calculate metrics
            vwap_executor = VWAPExecutor()  # Reuse VWAP methods
            expected_impact = vwap_executor._calculate_market_impact(quantity, symbol, side)
            timing_risk = vwap_executor._calculate_timing_risk(quantity, start_time, end_time)

            plan = ExecutionPlan(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
                execution_slices=slices,
                algorithm="twap",
                urgency=0.5,
                expected_market_impact=expected_impact,
                expected_timing_risk=timing_risk,
                estimated_slippage=expected_impact + timing_risk,
                start_time=start_time,
                end_time=end_time,
            )

            logger.info(
                f"TWAP plan created for {symbol}: {quantity} shares, "
                f"{len(slices)} slices over {duration_minutes} minutes"
            )

            return plan

        except (ValueError, TypeError) as e:
            logger.error(f"TWAP plan creation failed: {e}")
            raise


class ImplementationShortfallExecutor:
    """
    Implementation Shortfall (Arrival Price) Executor.

    Minimizes implementation shortfall, which is the difference between
    the decision price and the final execution price.

    Implementation Shortfall = Market Impact + Timing Risk
    - Market Impact: Cost from moving the market
    - Timing Risk: Cost from price movement during execution

    Optimizes the trade-off between:
    - Executing quickly (high impact, low timing risk)
    - Executing slowly (low impact, high timing risk)

    Based on:
    - Almgren, R., & Chriss, N. (2001). Optimal execution of portfolio transactions.
    - Perold, A. F. (1988). The implementation shortfall: Paper versus reality.

    Usage:
        >>> executor = ImplementationShortfallExecutor()
        >>> plan = executor.create_execution_plan(symbol="AAPL", quantity=10000, urgency=0.5)
    """

    def __init__(
        self,
        impact_model: Optional[MarketImpactModel] = None,
    ):
        """
        Initialize Implementation Shortfall Executor.

        Args:
            impact_model: Market impact model parameters
        """
        # Default market impact model
        self.impact_model = impact_model or MarketImpactModel(
            permanent_impact_coef=0.1,  # bps per 1% participation
            temporary_impact_coef=1.0,  # bps per sqrt(1% participation)
            volatility_impact_coef=1.0,
            daily_volume=1_000_000,
            spread=0.01,  # 1 cent
        )

        logger.info("ImplementationShortfallExecutor initialized")

    def create_execution_plan(
        self,
        symbol: str,
        quantity: float,
        side: str,
        start_time: Optional[datetime] = None,
        urgency: float = 0.5,  # 0 to 1
        price: float = 100.0,
        daily_volume: float = 1_000_000,
        daily_volatility: float = getattr(config.trading, 'max_risk_per_trade', 0.02),
        max_duration_minutes: int = 240,
    ) -> ExecutionPlan:
        """
        Create optimal execution plan minimizing implementation shortfall.

        Args:
            symbol: Trading symbol
            quantity: Total quantity to trade
            side: 'buy' or 'sell'
            start_time: Execution start time
            urgency: Urgency level (0=patient, 1=urgent)
            price: Current price
            daily_volume: Average daily volume
            daily_volatility: Daily volatility
            max_duration_minutes: Maximum execution duration

        Returns:
            Optimized ExecutionPlan
        """
        try:
            start_time = start_time or datetime.now()

            # Calculate optimal execution duration
            optimal_duration = self._calculate_optimal_duration(
                quantity, urgency, daily_volume, daily_volatility
            )

            # Cap at maximum duration
            duration_minutes = min(optimal_duration, max_duration_minutes)
            end_time = start_time + timedelta(minutes=duration_minutes)

            # Calculate optimal execution trajectory (Almgren-Chriss)
            n_slices = max(5, int(duration_minutes / 10))  # One slice per 10 minutes
            trajectory = self._calculate_optimal_trajectory(
                quantity, duration_minutes, n_slices, urgency
            )

            # Create execution slices
            slices = []
            interval_seconds = (duration_minutes * 60) / n_slices

            for i, slice_qty in enumerate(trajectory):
                target_time = start_time + timedelta(seconds=i * interval_seconds)

                slices.append(
                    ExecutionSlice(
                        slice_number=i,
                        quantity=slice_qty,
                        target_time=target_time,
                        limit_price=None,
                        execution_algorithm="implementation_shortfall",
                    )
                )

            # Calculate expected costs
            expected_impact = self._calculate_total_impact(
                quantity, duration_minutes, daily_volume, daily_volatility
            )

            timing_risk = self._calculate_timing_risk_optimized(
                quantity, duration_minutes, daily_volatility
            )

            shortfall = expected_impact + timing_risk

            plan = ExecutionPlan(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
                execution_slices=slices,
                algorithm="implementation_shortfall",
                urgency=urgency,
                expected_market_impact=expected_impact,
                expected_timing_risk=timing_risk,
                estimated_slippage=shortfall,
                start_time=start_time,
                end_time=end_time,
            )

            logger.info(
                f"Implementation shortfall plan created for {symbol}: "
                f"{quantity} shares, duration={duration_minutes}min, "
                f"expected_shortfall={shortfall:.2f}bps"
            )

            return plan

        except (ValueError, TypeError) as e:
            logger.error(f"Implementation shortfall plan creation failed: {e}")
            raise

    def _calculate_optimal_duration(
        self,
        quantity: float,
        urgency: float,
        daily_volume: float,
        daily_volatility: float,
    ) -> float:
        """
        Calculate optimal execution duration.

        Based on Almgren-Chriss model: minimize (Impact^2 + TimingRisk^2).

        Args:
            quantity: Order quantity
            urgency: Urgency parameter (0 to 1)
            daily_volume: Average daily volume
            daily_volatility: Daily volatility

        Returns:
            Optimal duration in minutes
        """
        # Market participation rate
        participation = quantity / daily_volume

        # Impact cost scales with participation
        # Faster execution = higher impact
        impact_coef = 100  # bps coefficient

        # Timing risk scales with sqrt(duration)
        # Slower execution = higher timing risk
        timing_coef = daily_volatility * 100  # Convert to bps

        # Optimize: minimize (impact_coef * participation / T)^2 + (timing_coef * sqrt(T))^2
        # where T is duration in days

        # Analytical solution (approximate)
        # T_opt = (impact_coef * participation / timing_coef)^(2/3)

        if urgency >= 0.9:
            # Very urgent: execute quickly
            optimal_duration_days = 0.01  # ~15 minutes
        elif urgency <= 0.1:
            # Very patient: execute slowly
            optimal_duration_days = 1.0  # 1 day
        else:
            # Calculate optimal duration
            ratio = (impact_coef * participation) / timing_coef
            optimal_duration_days = ratio ** (2 / 3)

            # Adjust by urgency
            optimal_duration_days = optimal_duration_days * (1 - urgency * 0.9)

        # Convert to minutes
        return float(max(10, min(optimal_duration_days * 1440, 1440)))  # 10 min to 1 day

    def _calculate_optimal_trajectory(
        self,
        quantity: float,
        duration_minutes: float,
        n_slices: int,
        urgency: float,
    ) -> np.ndarray:
        """
        Calculate optimal execution trajectory.

        Uses Almgren-Chriss optimal liquidation strategy.

        Args:
            quantity: Total quantity
            duration_minutes: Execution duration
            n_slices: Number of slices
            urgency: Urgency parameter

        Returns:
            Array of slice quantities
        """
        # For simplicity, use exponential decay trajectory
        # More urgent = faster decay (front-loaded)
        # Less urgent = linear trajectory

        if urgency > 0.7:
            # Front-loaded execution
            decay_rate = 2.0
        elif urgency < 0.3:
            # Back-loaded execution
            decay_rate = 0.5
        else:
            # Linear execution
            decay_rate = 1.0

        times = np.linspace(0, 1, n_slices)

        if decay_rate == 1.0:
            # Linear trajectory
            trajectory = np.ones(n_slices) * quantity / n_slices
        else:
            # Exponential trajectory
            weights = np.exp(-decay_rate * times)
            weights = weights / weights.sum() * quantity
            trajectory = weights

        return trajectory

    def _calculate_total_impact(
        self,
        quantity: float,
        duration_minutes: float,
        daily_volume: float,
        daily_volatility: float,
    ) -> float:
        """Calculate total expected market impact."""
        # Average participation rate
        avg_participation = (quantity / daily_volume) / (duration_minutes / 1440)

        # Permanent impact
        permanent = self.impact_model.permanent_impact_coef * avg_participation * 100

        # Temporary impact (with volatility adjustment)
        temporary = self.impact_model.temporary_impact_coef * np.sqrt(avg_participation) * 100
        temporary *= 1 + daily_volatility * self.impact_model.volatility_impact_coef

        return permanent + temporary

    def _calculate_timing_risk_optimized(
        self,
        quantity: float,
        duration_minutes: float,
        daily_volatility: float,
    ) -> float:
        """Calculate timing risk for optimized execution."""
        duration_days = duration_minutes / 1440
        timing_risk = daily_volatility * np.sqrt(duration_days / 2) * 100  # bps

        return timing_risk


class POVExecutor:
    """
    Percentage of Volume (POV) / Participation Rate Executor.

    Executes orders at a specified percentage of market volume.
    Automatically adjusts to real-time market conditions.

    Advantages:
    - Automatically adapts to market conditions
    - Limits market impact by capping participation
    - Good for large orders

    Disadvantages:
    - Execution time uncertain
    - Requires real-time volume data

    Usage:
        >>> executor = POVExecutor()
        >>> plan = executor.create_execution_plan(symbol="AAPL", quantity=10000, participation_rate=0.10)
    """

    def __init__(self):
        """Initialize POV Executor."""
        logger.info("POVExecutor initialized")

    def create_execution_plan(
        self,
        symbol: str,
        quantity: float,
        side: str,
        participation_rate: float,  # e.g., 0.10 for 10% POV
        start_time: Optional[datetime] = None,
        max_duration_minutes: int = 240,
        min_slice_quantity: float = 100,
    ) -> ExecutionPlan:
        """
        Create POV execution plan.

        Args:
            symbol: Trading symbol
            quantity: Total quantity to trade
            side: 'buy' or 'sell'
            participation_rate: Target participation rate (0 to 1)
            start_time: Execution start time
            max_duration_minutes: Maximum execution duration
            min_slice_quantity: Minimum quantity per slice

        Returns:
            ExecutionPlan with POV slices
        """
        try:
            start_time = start_time or datetime.now()

            # Create slices with dynamic participation
            # Since we don't have real-time volume, create template slices
            n_slices = max(10, int(max_duration_minutes / 10))

            slices = []
            remaining_qty = quantity

            for i in range(n_slices):
                if remaining_qty <= 0:
                    break

                # Estimate slice quantity based on participation rate
                # This will be adjusted during execution based on actual volume
                estimated_slice_qty = max(min_slice_quantity, remaining_qty / (n_slices - i))

                slice_qty = min(estimated_slice_qty, remaining_qty)

                target_time = start_time + timedelta(minutes=i * 10)

                slices.append(
                    ExecutionSlice(
                        slice_number=i,
                        quantity=slice_qty,
                        target_time=target_time,
                        limit_price=None,
                        execution_algorithm="pov",
                        participation_rate=participation_rate,
                    )
                )

                remaining_qty -= slice_qty

            # Calculate metrics (rough estimates)
            duration_estimate = self._estimate_duration(
                quantity, participation_rate, max_duration_minutes
            )

            vwap_executor = VWAPExecutor()
            expected_impact = vwap_executor._calculate_market_impact(
                quantity, symbol, side, daily_volume=1_000_000
            )

            timing_risk = vwap_executor._calculate_timing_risk(
                quantity, start_time, start_time + timedelta(minutes=duration_estimate)
            )

            plan = ExecutionPlan(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
                execution_slices=slices,
                algorithm="pov",
                urgency=0.3,  # Low urgency (adaptive)
                expected_market_impact=expected_impact,
                expected_timing_risk=timing_risk,
                estimated_slippage=expected_impact + timing_risk,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=duration_estimate),
            )

            logger.info(
                f"POV plan created for {symbol}: {quantity} shares, "
                f"participation_rate={participation_rate:.1%}"
            )

            return plan

        except (ValueError, TypeError) as e:
            logger.error(f"POV plan creation failed: {e}")
            raise

    def _estimate_duration(
        self,
        quantity: float,
        participation_rate: float,
        max_duration_minutes: int,
        daily_volume: float = 1_000_000,
    ) -> float:
        """Estimate execution duration for POV."""
        # Time to complete at given participation rate
        # T = Q / (ADV * POV)

        required_days = quantity / (daily_volume * participation_rate)
        required_minutes = required_days * 1440

        return min(required_minutes, max_duration_minutes)


def create_execution_plan(
    symbol: str,
    quantity: float,
    side: str,
    algorithm: str = "vwap",
    **kwargs,
) -> ExecutionPlan:
    """
    High-level function to create execution plans.

    Args:
        symbol: Trading symbol
        quantity: Quantity to trade
        side: 'buy' or 'sell'
        algorithm: Execution algorithm ('vwap', 'twap', 'is', 'pov')
        **kwargs: Algorithm-specific parameters

    Returns:
        ExecutionPlan

    Example:
        >>> plan = create_execution_plan("AAPL", 10000, "buy", algorithm="vwap")
        >>> print(plan.execution_slices)
    """
    if algorithm == "vwap":
        executor = VWAPExecutor()
    elif algorithm == "twap":
        executor = TWAPExecutor()
    elif algorithm == "is":
        executor = ImplementationShortfallExecutor()
    elif algorithm == "pov":
        executor = POVExecutor()
    else:
        raise ValueError(f"Unknown execution algorithm: {algorithm}")

    return executor.create_execution_plan(symbol, quantity, side, **kwargs)
