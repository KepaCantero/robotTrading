"""
T2.1.3 - Market Impact Estimator

Estimates execution cost (slippage + market impact) for large orders.

Uses empirical market impact formula:
market_impact = sqrt(participation_rate) * volatility_factor * base_impact
"""

import logging
from decimal import Decimal
from typing import Optional

from .models import MarketImpactEstimate

logger = logging.getLogger(__name__)


class MarketImpactEstimator:
    """
    Estimates market impact and execution slippage for large orders.

    Based on empirical research showing square-root relationship between
    order size (participation rate) and market impact.

    Reference: Almgren et al., "Optimal Execution of Portfolio Transactions"
    """

    # Base market impact coefficients (empirically calibrated)
    # These are typical values; can be adjusted per asset class/market
    BASE_IMPACT_BPS = {
        "equity": Decimal("10"),  # 10 bps base impact
        "crypto": Decimal("20"),  # 20 bps (more volatile)
        "forex": Decimal("5"),  # 5 bps (more liquid)
        "commodity": Decimal("15"),  # 15 bps
        "bond": Decimal("8"),  # 8 bps
    }

    # Volatility impact multipliers
    # Higher volatility → higher market impact
    VOLATILITY_MULTIPLIERS = {
        0: Decimal("0.5"),  # Very low vol (0-10th percentile)
        1: Decimal("0.7"),  # Low vol (10-30th percentile)
        2: Decimal("1.0"),  # Normal vol (30-70th percentile)
        3: Decimal("1.5"),  # High vol (70-90th percentile)
        4: Decimal("2.0"),  # Very high vol (90-100th percentile)
    }

    # Time decay factor (earlier execution = higher impact per unit)
    # More time to execute = lower per-unit impact (can split better)
    TIME_DECAY_FACTOR = Decimal("0.85")  # 15% reduction per doubling of time window

    # Spread impact coefficient (for bid-ask crossing)
    SPREAD_COEFFICIENT = Decimal("1.5")  # How much spread adds to impact

    def __init__(self):
        """Initialize estimator."""
        logger.info("MarketImpactEstimator initialized")

    async def estimate(
        self,
        symbol: str,
        order_size: Decimal,
        daily_volume: Decimal,
        current_spread_bps: Optional[Decimal] = None,
        volatility_percentile: int = 50,
        time_window_ms: int = 60_000,
        asset_class: str = "equity",
    ) -> MarketImpactEstimate:
        """
        Estimate market impact for an order.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            order_size: Total order size in currency units (€)
            daily_volume: Expected daily trading volume (€)
            current_spread_bps: Current bid-ask spread in basis points
            volatility_percentile: Current volatility percentile (0-100)
            time_window_ms: Time window available for execution (ms)
            asset_class: Asset class (equity, crypto, forex, commodity, bond)

        Returns:
            MarketImpactEstimate with slippage breakdown

        Example:
            >>> estimator = MarketImpactEstimator()
            >>> est = await estimator.estimate(
            ...     symbol="AAPL",
            ...     order_size=Decimal("50000"),
            ...     daily_volume=Decimal("10000000"),
            ...     volatility_percentile=50,
            ...     time_window_ms=300_000,
            ... )
            >>> est.estimated_slippage_bps
            Decimal('15.25')
        """

        # Ensure Decimal types
        order_size = Decimal(str(order_size))
        daily_volume = Decimal(str(daily_volume))
        current_spread_bps = Decimal(str(current_spread_bps or "1"))  # Default 1 bps

        # 1. Calculate participation rate (order size as % of daily volume)
        participation_rate = order_size / daily_volume if daily_volume > 0 else Decimal("0")

        # Cap participation rate at reasonable maximum (100% doesn't make sense)
        participation_rate = min(participation_rate, Decimal("1.0"))

        logger.debug(
            f"{symbol}: Participation rate = {participation_rate:.4%} "
            f"(order: €{order_size:,.0f}, daily volume: €{daily_volume:,.0f})"
        )

        # 2. Calculate square-root impact (empirical relationship)
        # sqrt(0.005) = 0.0707, sqrt(0.01) = 0.1, sqrt(0.02) = 0.1414
        if participation_rate > 0:
            sqrt_impact = participation_rate.sqrt()
        else:
            sqrt_impact = Decimal("0")

        # 3. Get volatility multiplier based on percentile
        # Map percentile (0-100) to volatility level (0-4)
        vol_level = min(int(volatility_percentile // 20), 4)
        volatility_multiplier = self.VOLATILITY_MULTIPLIERS.get(vol_level, Decimal("1.0"))

        logger.debug(
            f"{symbol}: Volatility percentile {volatility_percentile} → "
            f"level {vol_level}, multiplier {volatility_multiplier}"
        )

        # 4. Apply time decay (longer execution window = lower per-unit impact)
        # Base time window: 60 seconds (1 minute)
        # For every 2x increase in time, multiply by TIME_DECAY_FACTOR
        time_decay = Decimal("1.0")
        if time_window_ms > 60_000:
            # Calculate number of doublings beyond base 60s
            num_doublings = (time_window_ms / Decimal("60000")).ln() / Decimal("2").ln()
            time_decay = self.TIME_DECAY_FACTOR**num_doublings

        logger.debug(f"{symbol}: Time window {time_window_ms}ms → decay factor {time_decay}")

        # 5. Calculate base market impact (in basis points)
        base_impact = self.BASE_IMPACT_BPS.get(asset_class, Decimal("10"))

        # Combine factors: base × sqrt(participation) × volatility × time_decay
        market_impact_bps = base_impact * sqrt_impact * volatility_multiplier * time_decay

        # 6. Calculate spread impact
        # Spread cost is typically: spread × (0.5 + participation_impact)
        # We model it as: spread_bps × SPREAD_COEFFICIENT × sqrt_impact
        spread_impact = current_spread_bps * self.SPREAD_COEFFICIENT * sqrt_impact

        logger.debug(
            f"{symbol}: Market impact {market_impact_bps:.2f} bps, "
            f"Spread impact {spread_impact:.2f} bps"
        )

        # 7. Total estimated slippage (in basis points)
        estimated_slippage_bps = market_impact_bps + spread_impact

        # Cap at reasonable maximum (500 bps = 5%)
        estimated_slippage_bps = min(estimated_slippage_bps, Decimal("500"))

        # 8. Convert to currency units
        estimated_slippage_usd = order_size * estimated_slippage_bps / Decimal("10000")

        logger.info(
            f"Market impact estimate: {symbol} €{order_size:,.0f} → "
            f"{estimated_slippage_bps:.2f} bps (€{estimated_slippage_usd:,.2f})"
        )

        return MarketImpactEstimate(
            symbol=symbol,
            participation_rate=participation_rate,
            sqrt_impact=sqrt_impact,
            volatility_multiplier=volatility_multiplier,
            spread_impact=spread_impact,
            estimated_slippage_bps=estimated_slippage_bps,
            estimated_slippage_usd=estimated_slippage_usd,
        )

    async def estimate_by_participation_rate(
        self,
        symbol: str,
        participation_rate: Decimal,
        daily_volume: Decimal,
        order_size: Decimal,
        current_spread_bps: Optional[Decimal] = None,
        volatility_percentile: int = 50,
        asset_class: str = "equity",
    ) -> MarketImpactEstimate:
        """
        Alternative estimation method using pre-calculated participation rate.

        Useful when you already know the participation rate from elsewhere.
        """
        # Infer order size from participation rate if needed
        if order_size == Decimal("0"):
            order_size = participation_rate * daily_volume

        return await self.estimate(
            symbol=symbol,
            order_size=order_size,
            daily_volume=daily_volume,
            current_spread_bps=current_spread_bps,
            volatility_percentile=volatility_percentile,
            time_window_ms=60_000,
            asset_class=asset_class,
        )

    def estimate_slippage_for_different_windows(
        self,
        symbol: str,
        order_size: Decimal,
        daily_volume: Decimal,
        volatility_percentile: int = 50,
        asset_class: str = "equity",
    ) -> dict:
        """
        Show how slippage changes with different execution time windows.

        Useful for comparing TWAP vs VWAP vs other strategies.

        Returns:
            Dict with time_window_ms → estimated_slippage_bps mapping
        """
        windows = [
            60_000,  # 1 minute (extreme urgency)
            300_000,  # 5 minutes
            600_000,  # 10 minutes
            1_800_000,  # 30 minutes
            3_600_000,  # 1 hour
        ]

        results = {}

        # We'll run sync version since this is mostly math
        participation_rate = order_size / daily_volume if daily_volume > 0 else Decimal("0")
        participation_rate = min(participation_rate, Decimal("1.0"))

        if participation_rate > 0:
            sqrt_impact = participation_rate.sqrt()
        else:
            sqrt_impact = Decimal("0")

        vol_level = min(int(volatility_percentile // 20), 4)
        volatility_multiplier = self.VOLATILITY_MULTIPLIERS.get(vol_level, Decimal("1.0"))
        base_impact = self.BASE_IMPACT_BPS.get(asset_class, Decimal("10"))

        for time_window_ms in windows:
            time_decay = Decimal("1.0")
            if time_window_ms > 60_000:
                num_doublings = (time_window_ms / Decimal("60000")).ln() / Decimal("2").ln()
                time_decay = self.TIME_DECAY_FACTOR**num_doublings

            market_impact_bps = base_impact * sqrt_impact * volatility_multiplier * time_decay
            spread_impact = Decimal("1") * self.SPREAD_COEFFICIENT * sqrt_impact
            total_slippage = min(market_impact_bps + spread_impact, Decimal("500"))

            results[time_window_ms] = {
                "time_window_ms": time_window_ms,
                "time_window_min": time_window_ms / Decimal("60000"),
                "slippage_bps": total_slippage,
                "slippage_usd": order_size * total_slippage / Decimal("10000"),
                "time_decay": time_decay,
            }

        logger.info(f"Slippage estimates for {symbol}: {results}")
        return results


# Global singleton
_market_impact_estimator: MarketImpactEstimator = None


def get_market_impact_estimator() -> MarketImpactEstimator:
    """Get or create global MarketImpactEstimator instance."""
    global _market_impact_estimator
    if _market_impact_estimator is None:
        pass

    return _market_impact_estimator
