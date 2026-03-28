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

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

from .crypto_indicators import CryptoIndicators
from .crypto_portfolio import CryptoPortfolioConstructor
from .crypto_screener import CryptoAsset, CryptoScreener
from .models import CryptoMomentumConfig, CryptoMomentumScore, CryptoPortfolio

logger = logging.getLogger(__name__)


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

    def __init__(self, config: Dict[str, Any]):
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
        self.current_portfolio: Optional[CryptoPortfolio] = None
        self.universe: List[CryptoAsset] = []
        self.momentum_scores: Dict[str, CryptoMomentumScore] = {}
        self.price_history: Dict[str, deque] = {}
        self.btc_price_history: deque = deque(maxlen=365)

        # Metrics
        self.performance_history: deque = deque(maxlen=252)

        logger.info(
            f"CryptoMomentumStrategy initialized: "
            f"lookback={self.strategy_config.lookback_days}d, "
            f"btc_weight={self.strategy_config.btc_weight:.1%}, "
            f"max_pos={self.strategy_config.max_position_size:.1%}, "
            f"portfolio_size={self.strategy_config.portfolio_size}"
        )

    def _parse_config(self, config: Dict[str, Any]) -> CryptoMomentumConfig:
        """Parse configuration from dict."""
        try:
            return CryptoMomentumConfig(**config)
        except Exception as e:
            logger.error(f"Error parsing config: {e}")
            return CryptoMomentumConfig()

    def generate_signals(self, market_data: Quote) -> List[Signal]:
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
            logger.debug(f"Symbol {symbol} not in universe")
            return []

        # Update current price
        asset.current_price = market_data.last

        # Generate signals
        signals = []

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
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.strategy_config.lookback_days)

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
        if not asset.is_eligible:
            return False

        # Check if already at max position
        if self.current_portfolio:
            for pos in self.current_portfolio.positions:
                if pos.symbol == asset.symbol and pos.weight >= self.strategy_config.max_position_size:
                    return False

        # Get momentum score
        score = self.momentum_scores.get(asset.symbol)
        if score is None:
            return False

        # High momentum threshold
        if not score.is_high_momentum:
            return False

        # Check confidence
        if score.confidence < 60:
            return False

        return True

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

        # Check stop loss
        if position.unrealized_pnl_pct < -15:  # 15% stop loss
            logger.warning(f"Stop loss triggered for {asset.symbol}")
            return True

        # Check momentum deterioration
        score = self.momentum_scores.get(asset.symbol)
        if score and score.is_low_momentum:
            logger.info(f"Low momentum for {asset.symbol}: {score.final_score:.1f}")
            return True

        return False

    def _create_buy_signal(self, asset: CryptoAsset, market_data: Quote) -> Signal:
        """Create buy signal for crypto asset."""
        score = self.momentum_scores.get(asset.symbol)

        # Calculate confidence
        if score:
            confidence = float(score.confidence)
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

        # Liquidity score based on asset liquidity
        liquidity_score = float(asset.liquidity_score)

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
                "volatility": float(asset.volatility_90d),
                "btc_correlation": asset.btc_correlation,
                "liquidity_score": float(asset.liquidity_score),
                "asset_type": asset.asset_type.value,
                "strategy": "crypto_momentum",
            },
        )

        logger.info(
            f"BUY {asset.symbol}: Score {priority:.1f}, "
            f"Confidence {confidence:.1f}%, Strength {strength.value}"
        )

        return signal

    def _create_sell_signal(self, asset: CryptoAsset, market_data: Quote) -> Signal:
        """Create sell signal for crypto asset."""
        score = self.momentum_scores.get(asset.symbol)

        signal = Signal(
            symbol=asset.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=float(asset.liquidity_score),
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

        logger.warning(f"SELL {asset.symbol}: Momentum deteriorated")

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
                current_weight = pos.value / portfolio.total_value

                if current_weight >= max_pos:
                    logger.debug(
                        f"Max position reached for {signal.symbol}: "
                        f"{current_weight:.1%} >= {max_pos:.1%}"
                    )
                    return False

        # Volatility check
        asset = None
        for a in self.universe:
            if a.symbol == signal.symbol:
                asset = a
                break

        if asset and self.strategy_config.max_volatility and asset.volatility_90d > self.strategy_config.max_volatility:
            logger.debug(
                f"Volatility too high for {signal.symbol}: "
                f"{asset.volatility_90d:.1f}% > "
                f"{self.strategy_config.max_volatility:.1f}%"
            )
            return False

        return True

    def calculate_momentum_score(
        self,
        prices: pd.Series,
        benchmark_prices: Optional[pd.Series] = None,
    ) -> float:
        """
        Calculate volatility-adjusted momentum score.

        Score = (return / volatility) × beta_adjustment

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
            lookback_days=self.strategy_config.lookback_days,
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

        # Get BTC prices for correlation adjustment
        btc_prices = None
        if len(self.btc_price_history) > self.strategy_config.lookback_days:
            btc_data = list(self.btc_price_history)
            btc_series = pd.Series([p for _, p in btc_data])
            btc_prices = btc_series.tail(self.strategy_config.lookback_days)

        # Calculate score for each asset
        for asset in self.universe:
            if asset.symbol not in self.price_history:
                continue

            price_data = list(self.price_history[asset.symbol])
            if len(price_data) < self.strategy_config.lookback_days:
                continue

            prices = pd.Series([p for _, p in price_data])

            # Calculate raw momentum
            raw_momentum = self.calculate_momentum_score(prices, btc_prices)

            # Calculate volatility-adjusted momentum
            vol_adjusted = None
            if self.strategy_config.volatility_adjustment:
                returns = prices.pct_change().dropna()
                vol = returns.std() * np.sqrt(365)  # Annualized

                if vol > 0:
                    # Adjust score by volatility (higher vol = lower score)
                    vol_factor = max(0.5, min(1.5, 50 / vol))
                    vol_adjusted = raw_momentum * vol_factor

            # Calculate BTC-adjusted momentum
            btc_adjusted = None
            if self.strategy_config.btc_adjustment and btc_prices is not None:
                asset_returns = prices.pct_change().dropna()
                btc_returns = btc_prices.pct_change().dropna()

                # Align series
                min_len = min(len(asset_returns), len(btc_returns))
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

            # Calculate confidence
            data_points = len(price_data)
            confidence = min(100, (data_points / self.strategy_config.lookback_days) * 100)

            # Create score object
            score = CryptoMomentumScore(
                symbol=asset.symbol,
                raw_momentum=Decimal(str(raw_momentum)).quantize(Decimal("0.01")),
                volatility_adjusted_momentum=(
                    Decimal(str(vol_adjusted)).quantize(Decimal("0.01"))
                    if vol_adjusted is not None
                    else None
                ),
                btc_adjusted_momentum=(
                    Decimal(str(btc_adjusted)).quantize(Decimal("0.01"))
                    if btc_adjusted is not None
                    else None
                ),
                final_score=Decimal(str(final_score)).quantize(Decimal("0.01")),
                confidence=Decimal(str(confidence)).quantize(Decimal("0.01")),
            )

            self.momentum_scores[asset.symbol] = score

        logger.info(f"Updated {len(self.momentum_scores)} momentum scores")

    def set_universe(self, assets: List[CryptoAsset]) -> None:
        """
        Set universe of crypto assets.

        Args:
            assets: List of crypto assets
        """
        self.universe = assets

        # Run screening
        result = self.screener.screen(
            universe=assets,
            min_market_cap=self.strategy_config.min_market_cap,
            min_daily_volume=self.strategy_config.min_daily_volume,
            min_liquidity_score=self.strategy_config.min_liquidity_score,
            max_volatility=self.strategy_config.max_volatility,
        )

        # Update universe with only passing assets
        self.universe = result.passed_assets

        # Mark assets as eligible
        for asset in self.universe:
            asset.is_eligible = True

        logger.info(
            f"Universe set: {len(self.universe)} assets " f"({result.pass_rate:.1f}% pass rate)"
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
                        raw_momentum=Decimal("50"),
                        final_score=Decimal("50"),
                        confidence=Decimal("50"),
                    ),
                ).final_score
            ),
            reverse=True,
        )

        # Select top N assets
        max_assets = min(len(ranked_assets), self.strategy_config.portfolio_size)
        ranked_assets = ranked_assets[:max_assets]

        # Construct portfolio
        self.current_portfolio = self.constructor.construct_portfolio(
            ranked_assets=ranked_assets,
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

    def get_required_parameters(self) -> List[str]:
        """Get required strategy parameters."""
        return [
            "lookback_days",
            "max_position_size",
            "btc_weight",
            "portfolio_size",
        ]

    def validate_config(self) -> bool:
        """Validate strategy configuration."""
        try:
            return self.strategy_config.model_dump() is not None
        except Exception:
            return False

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get current portfolio metrics."""
        if self.current_portfolio is None:
            return {}

        return self.constructor.get_portfolio_summary(self.current_portfolio)
