"""
Crypto Momentum Strategy - Main Strategy Implementation

This module implements a momentum strategy optimized for cryptocurrency assets.

Key differences from stock momentum:
1. 24/7 trading - use continuous time
2. Higher volatility - use volatility-adjusted signals
3. BTC correlation - adjust for beta to BTC
4. Lower liquidity - position sizing limits
5. Social sentiment - optional integration

SOLID Principles:
- Single Responsibility: Strategy coordinates components
- Open/Closed: Extensible without modification
- Liskov Substitution: Compatible with BaseStrategy
- Interface Segregation: Minimal interfaces
- Dependency Inversion: Depends on abstractions
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

from .crypto_indicators import CryptoIndicators
from .crypto_portfolio import (
    CryptoAsset as PortfolioCryptoAsset,
    CryptoAssetType,
    CryptoMomentumConfig,
    CryptoMomentumScore,
    CryptoPortfolio,
    CryptoPortfolioConstructor,
)
from .crypto_screener import CryptoAsset, CryptoScreener

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote
    from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


@dataclass
class _AssetState:
    """Mutable runtime state tracked per asset by the strategy."""

    current_price: Decimal = Decimal("0")
    liquidity_score: Decimal = Decimal("100")
    volatility_90d: Decimal | None = None
    is_eligible: bool = False


def _convert_to_portfolio_asset(
    asset: CryptoAsset,
    state: _AssetState,
) -> PortfolioCryptoAsset:
    """Convert a screener CryptoAsset to a portfolio CryptoAsset."""
    return PortfolioCryptoAsset(
        symbol=asset.symbol,
        name=asset.name,
        asset_type=CryptoAssetType(asset.asset_type.value),
        current_price=state.current_price,
        market_cap=asset.market_cap,
        volume_24h=asset.avg_daily_volume,
        volatility_30d=asset.volatility_30d,
        volatility_90d=state.volatility_90d,
        liquidity_score=state.liquidity_score,
    )


class CryptoMomentumStrategy(BaseStrategy):
    """
    Momentum strategy optimized for crypto assets.

    Crypto markets have different dynamics than stocks:
    - 24/7 trading with no market close
    - Much higher volatility
    - Lower liquidity especially in smaller caps
    - Different momentum patterns due to retail dominance
    - Strong correlation with Bitcoin

    This strategy accounts for these differences with:
    - Volatility-adjusted momentum scores
    - BTC correlation adjustments
    - Liquidity-based position sizing
    - Continuous-time calculations

    Attributes:
        config: Strategy configuration
        screener: Crypto asset screener
        indicators: Crypto-specific indicators
        constructor: Portfolio constructor
        current_portfolio: Current crypto portfolio
        universe: Current universe of crypto assets
        momentum_scores: Cached momentum scores
        price_history: Price history for calculations
    """

    def __init__(self, config: dict[str, object]):
        """
        Initialize crypto momentum strategy.

        Args:
            config: Strategy configuration dictionary
        """
        super().__init__(config)

        # Parse configuration
        self.strategy_config = self._parse_config(config)

        # Initialize components
        self.screener = CryptoScreener(config)
        self.indicators = CryptoIndicators()
        self.constructor = CryptoPortfolioConstructor(self.strategy_config)

        # State
        self.current_portfolio: CryptoPortfolio | None = None
        self.universe: list[CryptoAsset] = []
        self.momentum_scores: dict[str, CryptoMomentumScore] = {}
        self.price_history: dict[str, deque[tuple]] = {}
        self.btc_price_history: deque[tuple] = deque(maxlen=365)

        # Per-asset mutable state not stored on CryptoAsset itself
        self._asset_state: dict[str, _AssetState] = {}

        # Confidence values computed alongside scores (CryptoMomentumScore has no confidence field)
        self._confidence: dict[str, Decimal] = {}

        # Metrics
        self.performance_history: deque[float] = deque(maxlen=252)

        logger.info(
            "CryptoMomentumStrategy initialized: portfolio_size=%d, btc_weight=%s, max_pos=%s",
            self.strategy_config.portfolio_size,
            f"{self.strategy_config.btc_weight:.1%}",
            f"{self.strategy_config.max_position_size:.1%}",
        )

    def _get_asset_state(self, symbol: str) -> _AssetState:
        """Return (creating if needed) the mutable state for a symbol."""
        if symbol not in self._asset_state:
            self._asset_state[symbol] = _AssetState()
        return self._asset_state[symbol]

    def _parse_config(self, config: dict[str, object]) -> CryptoMomentumConfig:
        """Parse configuration from dict."""
        try:
            return CryptoMomentumConfig(
                btc_weight=(
                    Decimal(str(config["btc_weight"])) if "btc_weight" in config else Decimal("0.5")
                ),
                portfolio_size=(
                    int(str(config["portfolio_size"])) if "portfolio_size" in config else 10
                ),
                rebalance_threshold=(
                    Decimal(str(config["rebalance_threshold"]))
                    if "rebalance_threshold" in config
                    else Decimal("0.05")
                ),
                max_position_weight=(
                    Decimal(str(config["max_position_weight"]))
                    if "max_position_weight" in config
                    else Decimal("0.15")
                ),
                max_position_size=(
                    Decimal(str(config["max_position_size"]))
                    if "max_position_size" in config
                    else Decimal("0.15")
                ),
                min_momentum_score=(
                    Decimal(str(config["min_momentum_score"]))
                    if "min_momentum_score" in config
                    else Decimal("0")
                ),
            )
        except Exception as e:
            logger.error("Error parsing config: %s", e)
            return CryptoMomentumConfig()

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        """
        Generate momentum signals for crypto assets.

        Process:
        1. Calculate momentum score for the asset
        2. Adjust for volatility
        3. Adjust for BTC correlation
        4. Generate signal if score meets threshold

        Args:
            market_data: Current market quote

        Returns:
            List of signals generated
        """
        if not self.is_active:
            logger.debug("Strategy inactive, no signals generated")
            return []

        symbol = market_data.symbol

        # Update price history
        self._update_price_history(symbol, market_data)

        # Store BTC prices separately
        if symbol == "BTC" or symbol == "BTCUSD":
            self.btc_price_history.append((market_data.timestamp, float(market_data.last)))

        # Check if symbol is in universe
        asset = None
        for a in self.universe:
            if a.symbol == symbol:
                asset = a
                break

        if asset is None:
            logger.debug("Symbol %s not in universe", symbol)
            return []

        # Update current price in local state
        state = self._get_asset_state(asset.symbol)
        state.current_price = market_data.last

        # Generate signals
        signals: list[Signal] = []

        # Buy signal: high momentum score
        if self._should_buy(asset):
            signal = self._create_buy_signal(asset, market_data)
            signals.append(signal)

        # Sell signal: momentum deteriorated
        elif self._should_sell(asset):
            signal = self._create_sell_signal(asset, market_data)
            signals.append(signal)

        return signals

    def _update_price_history(self, symbol: str, market_data: Quote) -> None:
        """Update price history for a symbol."""
        lookback = 90  # default lookback period in days
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=lookback)

        self.price_history[symbol].append((market_data.timestamp, float(market_data.last)))

    def _should_buy(self, asset: CryptoAsset) -> bool:
        """
        Determine if should generate buy signal.

        Criteria:
        - Asset is eligible (passed screening)
        - Momentum score > 70 (high momentum)
        - Not already at max position
        - Positive risk-adjusted return

        Args:
            asset: Crypto asset to evaluate

        Returns:
            True if should buy
        """
        # Check eligibility
        state = self._get_asset_state(asset.symbol)
        if not state.is_eligible:
            return False

        # Check if already at max position
        if self.current_portfolio:
            for pos in self.current_portfolio.positions:
                if (
                    pos.symbol == asset.symbol
                    and pos.weight >= self.strategy_config.max_position_size
                ):
                    return False

        # Get momentum score
        score = self.momentum_scores.get(asset.symbol)
        if score is None:
            return False

        # High momentum threshold (final_score > 70)
        if score.final_score < Decimal("70"):
            return False

        # Check confidence (confidence >= 60), tracked in _confidence dict
        confidence = self._confidence.get(asset.symbol, Decimal("0"))
        return confidence >= Decimal("60")

    def _should_sell(self, asset: CryptoAsset) -> bool:
        """
        Determine if should generate sell signal.

        Criteria:
        - Momentum score dropped below 40
        - Position exists
        - Significant loss (stop loss)

        Args:
            asset: Crypto asset to evaluate

        Returns:
            True if should sell
        """
        # Check if we have a position
        if not self.current_portfolio:
            return False

        position = None
        for pos in self.current_portfolio.positions:
            if pos.symbol == asset.symbol:
                position = pos
                break

        if position is None:
            return False

        # Check stop loss (unrealized_pnl_pct is a ratio, -0.15 = -15%)
        if position.unrealized_pnl_pct < Decimal("-0.15"):
            logger.warning("Stop loss triggered for %s", asset.symbol)
            return True

        # Check momentum deterioration (final_score < 40 means low momentum)
        score = self.momentum_scores.get(asset.symbol)
        if score and score.final_score < Decimal("40"):
            logger.info("Low momentum for %s: %s", asset.symbol, score.final_score)
            return True

        return False

    def _create_buy_signal(self, asset: CryptoAsset, market_data: Quote) -> Signal:
        """Create buy signal for crypto asset."""
        score = self.momentum_scores.get(asset.symbol)
        state = self._get_asset_state(asset.symbol)

        # Calculate confidence
        if score:
            confidence = float(self._confidence.get(asset.symbol, Decimal("65")))
            priority = float(score.final_score)
        else:
            confidence = 65.0
            priority = 70.0

        # Determine strength
        if priority > 85:
            strength = SignalStrength.STRONG
        elif priority > 70:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Liquidity score from local state
        liquidity_score = float(state.liquidity_score)

        signal = Signal(
            symbol=asset.symbol,
            signal_type=SignalType.BUY,
            strength=strength,
            confidence=confidence,
            liquidity_score=liquidity_score,
            priority_score=priority,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            metadata={
                "reason": "crypto_momentum",
                "momentum_score": float(score.final_score) if score else 0,
                "volatility": (
                    float(state.volatility_90d) if state.volatility_90d is not None else 0.0
                ),
                "btc_correlation": asset.btc_correlation,
                "liquidity_score": float(state.liquidity_score),
                "asset_type": asset.asset_type.value,
                "strategy": "crypto_momentum",
            },
        )

        logger.info(
            "BUY %s: Score %.1f, Confidence %.1f%%, Strength %s",
            asset.symbol,
            priority,
            confidence,
            strength.value,
        )

        return signal

    def _create_sell_signal(self, asset: CryptoAsset, market_data: Quote) -> Signal:
        """Create sell signal for crypto asset."""
        score = self.momentum_scores.get(asset.symbol)
        state = self._get_asset_state(asset.symbol)

        signal = Signal(
            symbol=asset.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=float(state.liquidity_score),
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            metadata={
                "reason": "momentum_deteriorated",
                "momentum_score": float(score.final_score) if score else 0,
                "strategy": "crypto_momentum",
            },
        )

        logger.warning("SELL %s: Momentum deteriorated", asset.symbol)

        return signal

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verify if signal passes risk criteria.

        Args:
            signal: Signal to verify
            portfolio: Current portfolio state

        Returns:
            True if signal passes risk check
        """
        # Position size check
        max_pos = self.strategy_config.max_position_size

        for pos in portfolio.positions:
            if pos.symbol == signal.symbol:
                if portfolio.total_value > 0:
                    current_weight = pos.market_value / portfolio.total_value
                else:
                    current_weight = Decimal("0")

                if current_weight >= max_pos:
                    logger.debug(
                        "Max position reached for %s: %.1f%% >= %.1f%%",
                        signal.symbol,
                        current_weight,
                        max_pos,
                    )
                    return False

        # Volatility check
        asset = None
        for a in self.universe:
            if a.symbol == signal.symbol:
                asset = a
                break

        if asset is not None:
            state = self._get_asset_state(asset.symbol)
            if state.volatility_90d is not None:
                cfg_max_vol = self.strategy_config.max_volatility
                if state.volatility_90d > cfg_max_vol:
                    logger.debug(
                        "Volatility too high for %s: %.1f%% > %.1f%%",
                        signal.symbol,
                        state.volatility_90d,
                        cfg_max_vol,
                    )
                    return False

        return True

    def calculate_momentum_score(
        self,
        prices: pd.Series,
        benchmark_prices: pd.Series | None = None,
    ) -> float:
        """
        Calculate volatility-adjusted momentum score.

        Score = (return / volatility) * beta_adjustment

        Where:
        - return: n-day return
        - volatility: annualized vol
        - beta_adjustment: reduce if high BTC correlation

        Args:
            prices: Asset price series
            benchmark_prices: Benchmark (BTC) price series

        Returns:
            Momentum score (0-100)
        """
        return self.indicators.calculate_momentum_score(
            prices=prices,
            benchmark_prices=benchmark_prices,
            lookback_days=90,
        )

    def calculate_crypto_beta(
        self,
        asset_returns: pd.Series,
        btc_returns: pd.Series,
    ) -> float:
        """
        Calculate beta to Bitcoin.

        Crypto assets with high BTC beta may not provide
        diversification benefits.

        Beta = Cov(asset, btc) / Var(btc)

        Args:
            asset_returns: Asset return series
            btc_returns: BTC return series

        Returns:
            Beta value
        """
        return self.indicators.calculate_crypto_beta(asset_returns, btc_returns)

    def update_momentum_scores(self) -> None:
        """Recalculate momentum scores for all assets in universe."""
        logger.info("Updating momentum scores for universe...")

        lookback = 90

        # Get BTC prices for correlation adjustment
        btc_prices: pd.Series | None = None
        if len(self.btc_price_history) > lookback:
            btc_data = list(self.btc_price_history)
            btc_series = pd.Series([p for _, p in btc_data])
            btc_prices = btc_series.tail(lookback)

        # Calculate score for each asset
        for asset in self.universe:
            if asset.symbol not in self.price_history:
                continue

            price_data = list(self.price_history[asset.symbol])
            if len(price_data) < lookback:
                continue

            prices = pd.Series([p for _, p in price_data])

            # Calculate raw momentum
            raw_momentum = self.calculate_momentum_score(prices, btc_prices)

            # Calculate volatility-adjusted momentum
            vol_adjusted: float | None = None
            returns = prices.pct_change().dropna()
            vol = returns.std() * np.sqrt(365)  # Annualized

            if vol > 0:
                # Adjust score by volatility (higher vol = lower score)
                vol_factor = max(0.5, min(1.5, 50 / vol))
                vol_adjusted = raw_momentum * vol_factor

            # Calculate BTC-adjusted momentum
            btc_adjusted: float | None = None
            if btc_prices is not None and len(btc_prices) > 0:
                asset_returns = prices.pct_change().dropna()
                btc_returns = btc_prices.pct_change().dropna()

                # Align series
                min_len = min(len(asset_returns), len(btc_returns))
                if min_len > 0:
                    asset_returns = asset_returns.tail(min_len)
                    btc_returns = btc_returns.tail(min_len)

                    beta = self.calculate_crypto_beta(asset_returns, btc_returns)

                    # Reduce score for high BTC correlation
                    if abs(beta) > 0.7:
                        btc_factor = 0.8
                    elif abs(beta) > 0.5:
                        btc_factor = 0.9
                    else:
                        btc_factor = 1.0

                    btc_adjusted = raw_momentum * btc_factor

            # Final score
            final_score = raw_momentum
            if vol_adjusted is not None:
                final_score = (final_score + vol_adjusted) / 2
            if btc_adjusted is not None:
                final_score = (final_score + btc_adjusted) / 2

            final_score = max(0, min(100, final_score))

            # Calculate confidence and store it separately
            data_points = len(price_data)
            confidence = min(100, (data_points / lookback) * 100)
            self._confidence[asset.symbol] = Decimal(str(confidence)).quantize(Decimal("0.01"))

            # Create score object
            score = CryptoMomentumScore(
                symbol=asset.symbol,
                score=Decimal(str(final_score)).quantize(Decimal("0.01")),
            )

            self.momentum_scores[asset.symbol] = score

        logger.info("Updated %d momentum scores", len(self.momentum_scores))

    def set_universe(self, assets: list[CryptoAsset]) -> None:
        """
        Set universe of crypto assets.

        Args:
            assets: List of crypto assets
        """
        self.universe = assets

        # Run screening
        result = self.screener.screen(
            universe=assets,
        )

        # Update universe with only passing assets
        self.universe = result.passed_assets

        # Mark assets as eligible in local state
        for asset in self.universe:
            state = self._get_asset_state(asset.symbol)
            state.is_eligible = True

        total_eval = result.total_evaluated
        passed_count = len(result.passed_assets)
        pass_rate = (passed_count / total_eval * 100) if total_eval > 0 else 0.0

        logger.info(
            "Universe set: %d assets (%.1f%% pass rate)",
            passed_count,
            pass_rate,
        )

    def construct_portfolio(self, total_capital: Decimal) -> CryptoPortfolio:
        """
        Construct crypto momentum portfolio.

        Args:
            total_capital: Total capital to invest

        Returns:
            Constructed portfolio
        """
        if not self.momentum_scores:
            self.update_momentum_scores()

        # Rank assets by momentum score
        ranked_assets = sorted(
            self.universe,
            key=lambda a: float(
                self.momentum_scores.get(
                    a.symbol,
                    CryptoMomentumScore(
                        symbol=a.symbol,
                        score=Decimal("50"),
                    ),
                ).final_score
            ),
            reverse=True,
        )

        # Select top N assets
        max_assets = min(len(ranked_assets), self.strategy_config.portfolio_size)
        ranked_assets = ranked_assets[:max_assets]

        # Convert screener CryptoAssets to portfolio CryptoAssets
        portfolio_assets: list[PortfolioCryptoAsset] = []
        for a in ranked_assets:
            state = self._get_asset_state(a.symbol)
            portfolio_assets.append(_convert_to_portfolio_asset(a, state))

        # Construct portfolio
        self.current_portfolio = self.constructor.construct_portfolio(
            ranked_assets=portfolio_assets,
            momentum_scores=self.momentum_scores,
            total_capital=total_capital,
        )

        return self.current_portfolio

    def rebalance_portfolio(self, total_capital: Decimal) -> CryptoPortfolio:
        """
        Rebalance existing portfolio.

        Args:
            total_capital: Current capital

        Returns:
            Rebalanced portfolio
        """
        if not self.current_portfolio:
            return self.construct_portfolio(total_capital)

        # Update momentum scores
        self.update_momentum_scores()

        # Reconstruct portfolio with updated scores
        return self.construct_portfolio(total_capital)

    def get_required_parameters(self) -> list[str]:
        """Get required strategy parameters."""
        return [
            "max_position_size",
            "btc_weight",
            "portfolio_size",
        ]

    def validate_config(self) -> bool:
        """Validate strategy configuration."""
        try:
            # dataclasses have __dataclass_fields__
            return hasattr(self.strategy_config, "__dataclass_fields__")
        except Exception:
            return False

    def get_portfolio_metrics(self) -> dict[str, object]:
        """Get current portfolio metrics."""
        if self.current_portfolio is None:
            return {}

        return self.constructor.get_portfolio_summary(self.current_portfolio)
