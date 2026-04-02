"""
Realistic Market Data Generator for Backtesting

Generates realistic market data using advanced statistical models:
- Geometric Brownian Motion with volatility clustering (GARCH-like)
- Markov Regime-Switching Model (bull/bear/sideways markets)
- Volume correlated with volatility and price movements
- Realistic OHLC generation with intraday patterns
- Jump-diffusion for extreme events

This replaces the simplistic linear/random data generation that was
previously used, providing much more realistic test scenarios.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar

import numpy as np

from app.domain.models.market_data import Quote
from app.shared.utils.decimal_utils import round_price, to_decimal

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime types for regime-switching model."""

    BULL = "bull"  # Uptrend, moderate volatility
    BEAR = "bear"  # Downtrend, high volatility
    SIDEWAYS = "sideways"  # Range-bound, low volatility
    VOLATILE = "volatile"  # High volatility, no clear trend


@dataclass
class RegimeParameters:
    """Parameters for a market regime."""

    name: MarketRegime
    drift: float  # Daily return (annualized / 252)
    volatility: float  # Daily volatility (annual / sqrt(252))
    volume_multiplier: float  # Volume relative to baseline
    jump_probability: float  # Probability of price jump
    jump_mean: float  # Mean jump size (as decimal, e.g., 0.02 = 2%)
    transition_prob: dict  # Probability of transitioning to other regimes


class RealisticDataGenerator:
    """
    Generate realistic market data for backtesting.

    Uses:
    1. Markov Regime-Switching Model for realistic market cycles
    2. GARCH-like volatility clustering
    3. Volume correlated with volatility and price movements
    4. Jump-diffusion for extreme events (crashes, rallies)

    This replaces simplistic linear/random models with statistically
    realistic market behavior.
    """

    # Default regime parameters (calibrated from historical equity data)
    DEFAULT_REGIMES: ClassVar[dict] = {
        MarketRegime.BULL: RegimeParameters(
            name=MarketRegime.BULL,
            drift=0.0005,  # ~12.6% annually
            volatility=0.012,  # ~19% annually
            volume_multiplier=1.2,
            jump_probability=0.005,  # 0.5% chance per day
            jump_mean=0.01,  # +1% average jump
            transition_prob={
                MarketRegime.BULL: 0.96,  # 96% stay in bull
                MarketRegime.BEAR: 0.02,  # 2% transition to bear
                MarketRegime.SIDEWAYS: 0.02,  # 2% transition to sideways
            },
        ),
        MarketRegime.BEAR: RegimeParameters(
            name=MarketRegime.BEAR,
            drift=-0.0003,  # ~-7.5% annually
            volatility=0.025,  # ~40% annually
            volume_multiplier=1.8,
            jump_probability=0.02,  # 2% chance per day
            jump_mean=-0.03,  # -3% average jump
            transition_prob={
                MarketRegime.BEAR: 0.94,  # 94% stay in bear
                MarketRegime.BULL: 0.04,  # 4% transition to bull
                MarketRegime.SIDEWAYS: 0.02,  # 2% transition to sideways
            },
        ),
        MarketRegime.SIDEWAYS: RegimeParameters(
            name=MarketRegime.SIDEWAYS,
            drift=0.0001,  # ~2.5% annually
            volatility=0.008,  # ~13% annually
            volume_multiplier=0.9,
            jump_probability=0.002,  # 0.2% chance per day
            jump_mean=0.0,
            transition_prob={
                MarketRegime.SIDEWAYS: 0.95,  # 95% stay sideways
                MarketRegime.BULL: 0.03,  # 3% transition to bull
                MarketRegime.BEAR: 0.02,  # 2% transition to bear
            },
        ),
        MarketRegime.VOLATILE: RegimeParameters(
            name=MarketRegime.VOLATILE,
            drift=0.0,  # No trend
            volatility=0.035,  # ~55% annually
            volume_multiplier=2.5,
            jump_probability=0.05,  # 5% chance per day
            jump_mean=0.0,
            transition_prob={
                MarketRegime.VOLATILE: 0.85,  # 85% stay volatile
                MarketRegime.BULL: 0.10,  # 10% transition to bull
                MarketRegime.BEAR: 0.05,  # 5% transition to bear
            },
        ),
    }

    def __init__(
        self,
        seed: int | None = None,
        base_price: float = 100.0,
        base_volume: int = 50_000_000,
        regimes: dict | None = None,
        asset_class: str = "equity",
    ):
        """
        Initialize realistic data generator.

        Args:
            seed: Random seed for reproducibility
            base_price: Starting price
            base_volume: Base daily volume
            regimes: Custom regime parameters (uses DEFAULT_REGIMES if None)
            asset_class: Asset class for price precision (equity, forex, crypto, etc.)
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.base_price = base_price
        self.base_volume = base_volume
        self.regimes = regimes or self.DEFAULT_REGIMES
        self.asset_class = asset_class

        # GARCH-like parameters for volatility clustering
        self.garch_omega = 0.00002  # Long-term variance
        self.garch_alpha = 0.08  # ARCH coefficient (past shocks)
        self.garch_beta = 0.90  # GARCH coefficient (past variance)
        self.volatility_clustering = True

    def generate_realistic_quotes(
        self,
        symbol: str,
        n_days: int,
        start_date: datetime,
        use_regime_switching: bool = True,
        initial_regime: MarketRegime = MarketRegime.BULL,
    ) -> list[Quote]:
        """
        Generate realistic market data quotes.

        Uses regime-switching GBM with volatility clustering and
        volume-price correlation.

        Args:
            symbol: Trading symbol
            n_days: Number of days to generate
            start_date: Start date
            use_regime_switching: Whether to use regime-switching model
            initial_regime: Starting regime

        Returns:
            List of Quote objects with realistic OHLCV data
        """
        logger.info(
            f"Generating {n_days} days of realistic data for {symbol} "
            f"starting {start_date.strftime('%Y-%m-%d')}"
        )

        # Initialize arrays
        dates = [start_date + timedelta(days=i) for i in range(n_days)]
        prices = np.empty(n_days)
        volumes = np.empty(n_days)

        # Generate regime sequence if using regime-switching
        if use_regime_switching:
            regime_sequence = self._generate_regime_sequence(n_days, initial_regime)
        else:
            regime_sequence = [initial_regime] * n_days

        # Initialize GARCH-like volatility
        current_variance = self.regimes[initial_regime].volatility ** 2

        # Generate prices with regime-switching and volatility clustering
        prices[0] = self.base_price

        for i in range(n_days - 1):
            regime = self.regimes[regime_sequence[i]]

            # Update volatility (GARCH-like)
            if self.volatility_clustering:
                # Past return shock
                past_return = np.log(prices[i] / max(prices[i - 1], prices[i])) if i > 0 else 0
                # Update variance: omega + alpha * shock^2 + beta * past_variance
                current_variance = (
                    self.garch_omega
                    + self.garch_alpha * past_return**2
                    + self.garch_beta * current_variance
                )
                # Bounds check
                current_variance = max(current_variance, regime.volatility**2 * 0.5)
                current_variance = min(current_variance, regime.volatility**2 * 2.0)
            else:
                current_variance = regime.volatility**2

            current_vol = np.sqrt(current_variance)

            # Generate price with regime-specific parameters
            dW = self.rng.standard_normal()

            # Check for jump
            if self.rng.random() < regime.jump_probability:
                # Poisson jump
                jump_size = self.rng.normal(regime.jump_mean, regime.volatility * 2)
                log_return = regime.drift + jump_size
            else:
                # Standard GBM return
                log_return = regime.drift - 0.5 * current_variance + current_vol * dW

            prices[i + 1] = prices[i] * np.exp(log_return)
            prices[i + 1] = max(prices[i + 1], 0.01)  # Floor at 1 cent

            # Generate volume correlated with volatility and price movement
            price_change_pct = abs(log_return)
            base_vol = self.base_volume * regime.volume_multiplier

            # Volume increases with:
            # 1. Higher volatility
            # 2. Larger price movements
            # 3. Random lognormal noise
            vol_multiplier = (
                1.0  # Base
                + (current_vol / regime.volatility - 1.0) * 2.0  # Volatility effect
                + price_change_pct * 10.0  # Price movement effect
            )

            volume_noise = self.rng.lognormal(0, 0.3)  # 30% std lognormal
            volumes[i] = int(base_vol * vol_multiplier * volume_noise)
            volumes[i] = max(volumes[i], 1000)  # Minimum volume

        volumes[-1] = volumes[-2] if n_days > 1 else int(self.base_volume)

        # Convert prices to quotes with realistic OHLC
        quotes = self._prices_to_realistic_quotes(
            prices.tolist(),
            volumes.tolist(),
            dates,
            symbol,
            regime_sequence if use_regime_switching else None,
        )

        logger.info(
            f"Generated {len(quotes)} quotes. "
            f"Price range: ${min(quotes, key=lambda q: float(q.close)).close:.2f} - "
            f"${max(quotes, key=lambda q: float(q.close)).close:.2f}"
        )

        return quotes

    def _generate_regime_sequence(
        self, n_days: int, initial_regime: MarketRegime
    ) -> list[MarketRegime]:
        """
        Generate regime sequence using Markov chain.

        Args:
            n_days: Number of days
            initial_regime: Starting regime

        Returns:
            List of regimes for each day
        """
        regimes = [initial_regime]
        current_regime = initial_regime

        for _ in range(n_days - 1):
            # Get transition probabilities
            trans_probs = self.regimes[current_regime].transition_prob

            # Sample next regime
            rand = self.rng.random()
            cumulative = 0.0

            for regime, prob in trans_probs.items():
                cumulative += prob
                if rand <= cumulative:
                    current_regime = regime
                    break

            regimes.append(current_regime)

        return regimes

    def _prices_to_realistic_quotes(
        self,
        prices: list[float],
        volumes: list[int],
        dates: list[datetime],
        symbol: str,
        regimes: list[MarketRegime] | None = None,
    ) -> list[Quote]:
        """
        Convert price list to realistic Quote objects with proper OHLC.

        Generates realistic intraday price movements:
        - Open != Close (gap from previous close)
        - High and Low reflect intraday volatility
        - Bid-ask spread correlates with volatility

        Args:
            prices: List of close prices
            volumes: List of volumes
            dates: List of timestamps
            symbol: Trading symbol
            regimes: Optional regime sequence for logging

        Returns:
            List of Quote objects
        """
        quotes = []

        for i, (close_price, volume, date) in enumerate(zip(prices, volumes, dates)):
            # Calculate intraday volatility (higher for more volatile stocks)
            daily_volatility = 0.015 if i > 0 else 0.01  # Base 1.5% daily range

            # Generate OHLC with realistic patterns
            if i == 0:
                # First day
                open_price = close_price
            else:
                # Gap from previous close (realistic overnight gap)
                # Typical overnight gap: 0.1% to 0.5% in either direction
                gap = self.rng.normal(0, 0.002)  # 0.2% std
                gap = max(min(gap, 0.01), -0.01)  # Clamp to ±1%
                open_price = prices[i - 1] * (1 + gap)

            # Intraday movement (open to close)
            # High and Low reflect intraday trading range
            intraday_range = close_price * daily_volatility * self.rng.uniform(0.5, 2.0)

            # Determine if up or down day
            if close_price >= open_price:
                # Up day
                high = max(close_price, open_price) + abs(self.rng.normal(0, intraday_range * 0.3))
                low = min(open_price, close_price) - abs(self.rng.normal(0, intraday_range * 0.5))
            else:
                # Down day
                high = max(open_price, close_price) + abs(self.rng.normal(0, intraday_range * 0.5))
                low = min(open_price, close_price) - abs(self.rng.normal(0, intraday_range * 0.3))

            # Ensure OHLC consistency
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            high = max(high, low * 1.0001)  # Ensure bid-ask spread
            low = min(low, high * 0.9999)

            # Round using proper precision based on asset class
            # This handles equity (2 decimals), forex (4-5 decimals), crypto (8 decimals)
            open_price_rounded = round_price(open_price, self.asset_class, symbol)
            high_rounded = round_price(high, self.asset_class, symbol)
            low_rounded = round_price(low, self.asset_class, symbol)
            close_price_rounded = round_price(close_price, self.asset_class, symbol)

            # Generate bid-ask spread (correlates with volatility)
            spread_bps = 3 + daily_volatility * 1000 * self.rng.uniform(0.5, 2.0)  # 3-15 bps
            spread_bps = min(spread_bps, 50)  # Max 50 bps

            # Calculate bid/ask and round with proper precision
            bid = round_price(close_price * (1 - spread_bps / 10000), self.asset_class, symbol)
            ask = round_price(close_price * (1 + spread_bps / 10000), self.asset_class, symbol)

            # Ensure bid < ask < close or close < bid < ask
            # Use appropriate minimum spread based on asset class
            min_spreads = {
                "equity": 0.01,
                "forex": 0.00001,
                "crypto": 0.00000001,
                "commodity": 0.01,
                "bond": 0.0001,
                "index": 0.01,
            }
            min_spread = min_spreads.get(self.asset_class, 0.01)

            if float(bid) >= float(ask):
                ask = to_decimal(float(bid) + min_spread)

            # Last is usually close or between bid/ask
            last = close_price_rounded

            # Create Quote
            quote = Quote(
                symbol=symbol,
                timestamp=date,
                bid=bid,
                ask=ask,
                last=last,
                volume=to_decimal(volume),
                open=open_price_rounded,
                high=high_rounded,
                low=low_rounded,
                close=close_price_rounded,
            )

            quotes.append(quote)

        return quotes

    def generate_monte_carlo_scenario(
        self,
        base_quotes: list[Quote],
        n_simulations: int = 100,
        volatility_adjustment: float = 1.0,
    ) -> list[list[Quote]]:
        """
        Generate Monte Carlo scenarios from base quotes.

        Creates realistic alternative price paths using the same
        statistical models as generate_realistic_quotes, but
        preserving the overall price trend of the base data.

        Args:
            base_quotes: Original quotes to use as baseline
            n_simulations: Number of Monte Carlo paths
            volatility_adjustment: Multiplier for volatility (1.0 = same)

        Returns:
            List of quote lists (one per simulation)
        """
        if not base_quotes:
            return []

        n_days = len(base_quotes)
        base_prices = np.array([float(q.close) for q in base_quotes])
        base_volumes = np.array([int(q.volume) for q in base_quotes])

        # Calculate base statistics
        returns = np.diff(np.log(base_prices))
        base_drift = np.mean(returns)
        base_vol = np.std(returns) * volatility_adjustment

        simulations = []

        for sim_idx in range(n_simulations):
            # Use simulation-specific seed for reproducibility
            sim_seed = self.seed + sim_idx if self.seed else None
            sim_rng = np.random.RandomState(sim_seed)

            # Generate price path with same drift but realistic volatility
            sim_prices = np.empty(n_days)
            sim_prices[0] = base_prices[0]

            # GARCH-like volatility for simulation
            current_variance = base_vol**2

            for i in range(n_days - 1):
                # Update volatility with GARCH
                if i > 0:
                    past_return = np.log(sim_prices[i] / sim_prices[i - 1])
                    current_variance = (
                        self.garch_omega
                        + self.garch_alpha * past_return**2
                        + self.garch_beta * current_variance
                    )
                    current_variance = max(current_variance, base_vol**2 * 0.5)
                    current_variance = min(current_variance, base_vol**2 * 2.0)

                sim_vol = np.sqrt(current_variance)

                # Generate return
                dW = sim_rng.standard_normal()
                log_return = base_drift - 0.5 * current_variance + sim_vol * dW

                sim_prices[i + 1] = sim_prices[i] * np.exp(log_return)
                sim_prices[i + 1] = max(sim_prices[i + 1], 0.01)

            # Convert to quotes
            sim_quotes = self._prices_to_realistic_quotes(
                sim_prices.tolist(),
                base_volumes.tolist(),
                [q.timestamp for q in base_quotes],
                base_quotes[0].symbol,
                regimes=None,
            )

            simulations.append(sim_quotes)

        logger.info(f"Generated {n_simulations} Monte Carlo simulations")

        return simulations
