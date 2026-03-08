"""
Multi-Factor Strategy - Main Strategy Implementation

This module implements the complete Multi-Factor Strategy based on the
Fama-French 5-factor model plus Momentum factor.

Objective: BALANCED_GROWTH
- Combine multiple factor premiums for consistent returns
- Target positive exposure to profitable factors
- Maintain diversification and risk control

Strategy Overview:
1. Calculate factor scores for all stocks (Value, Size, Profitability, Investment, Momentum)
2. Select top stocks based on composite factor score
3. Optimize portfolio weights with factor tilt constraints
4. Rebalance quarterly or when drift exceeds threshold

References:
- Fama & French (2015): "A five-factor asset pricing model"
- Berkin & Swedroe: "The Incredible Shrinking Alpha"
- Factor investing principles

SOLID Principles:
- Single Responsibility: Coordinate components, not implement logic
- Open/Closed: Extensible strategy
- Liskov Substitution: Compatible with BaseStrategy
- Interface Segregation: Minimal interfaces
- Dependency Inversion: Depend on abstractions
"""

import logging
from collections import deque
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType

# Import both BaseStrategy classes - inherit from app's BaseStrategy
# but also be compatible with registry's BaseStrategy via async execute()
from app.domain.strategies.base import BaseStrategy
from app.shared.config.centralized_config import get_config

from .factor_calculator import FactorCalculator
from .factor_models import FactorModelManager
from .models import FactorPortfolio, FactorProfile, FactorStrategyConfig
from .portfolio_constructor import FactorPortfolioConstructor

logger = logging.getLogger(__name__)


class MultiFactorStrategy(BaseStrategy):
    """
    Multi-Factor Strategy implementing Fama-French 5-Factor + Momentum.

    This strategy constructs a diversified portfolio with targeted factor
    exposures based on the Fama-French 5-factor model plus Momentum.

    Objective: BALANCED_GROWTH
    - Target positive exposure to Value and Profitability factors
    - Moderate exposure to Momentum
    - Sector-neutral diversification
    - Quarterly rebalancing

    Factor Tilts:
    - Value (+20%): Overweight high book-to-market stocks
    - Profitability (+20%): Overweight high ROA/ROE stocks
    - Momentum (+10%): Overweight past winners
    - Size (0%): Market-neutral on size
    - Investment (0%): Market-neutral on investment

    Portfolio Construction:
    - 30-50 stocks for diversification
    - Max 25% per sector
    - Max 4% per position
    - Factor constraints to avoid extreme tilts

    Attributes:
        config: Strategy configuration
        calculator: Factor score calculator
        constructor: Portfolio constructor
        factor_manager: Factor model manager
        universe: Current stock universe
        current_portfolio: Current factor portfolio
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Multi-Factor Strategy.

        Args:
            config: Strategy configuration
        """
        super().__init__(config)

        # Load trading thresholds for history length
        trading_config = get_config()
        tt = trading_config.trading_thresholds

        # Parse configuration
        self.strategy_config = self._parse_config(config)

        # Initialize components
        self.calculator = FactorCalculator(min_samples=10)
        self.constructor = FactorPortfolioConstructor(self.strategy_config)
        self.factor_manager = FactorModelManager()

        # State
        self.universe: List[FactorProfile] = []
        self.current_portfolio: Optional[FactorPortfolio] = None
        self.factor_scores_dict: Dict[str, Any] = {}
        self.last_rebalance_date: Optional[date] = None
        self.rebalance_count = 0

        # Performance tracking - use config value
        self.return_history: deque = deque(maxlen=tt.multi_factor_history_length)
        self.factor_exposure_history: deque = deque(maxlen=tt.multi_factor_history_length)

        logger.info(
            f"✅ MultiFactorStrategy initialized: "
            f"objective={self.strategy_config.objetivo_inversion}, "
            f"portfolio_size={self.strategy_config.portfolio_size}, "
            f"value_tilt={self.strategy_config.value_tilt}, "
            f"profitability_tilt={self.strategy_config.profitability_tilt}"
        )

    def _parse_config(self, config: Dict[str, Any]) -> FactorStrategyConfig:
        """
        Parse strategy configuration.

        Args:
            config: Raw configuration dict

        Returns:
            Validated FactorStrategyConfig
        """
        try:
            # Default values
            defaults = {
                "name": "MultiFactorStrategy",
                "description": "Multi-factor strategy based on Fama-French 5-factor + Momentum",
                "version": "1.0.0",
                "objetivo_inversion": "BALANCED_GROWTH",
                "min_market_cap": None,
                "max_market_cap": None,
                "min_price": Decimal("5"),
                "min_daily_volume": None,
                "value_tilt": Decimal("0.2"),
                "size_tilt": Decimal("0"),
                "profitability_tilt": Decimal("0.2"),
                "investment_tilt": Decimal("0"),
                "momentum_tilt": Decimal("0.1"),
                "portfolio_size": 40,
                "max_sector_weight": Decimal("0.25"),
                "max_single_position": Decimal("0.04"),
                "min_position": Decimal("0.01"),
                "max_factor_exposure": Decimal("0.3"),
                "factor_neutral": False,
                "rebalance_frequency": "quarterly",
                "rebalance_threshold": Decimal("0.05"),
                "max_beta": None,
                "max_volatility": None,
                "stop_loss_factor": Decimal("0.15"),
                "value_weight": Decimal("0.25"),
                "profitability_weight": Decimal("0.25"),
                "momentum_weight": Decimal("0.20"),
                "size_weight": Decimal("0.15"),
                "investment_weight": Decimal("0.15"),
                "min_quality_score": Decimal("40"),
                "min_factor_score": Decimal("30"),
            }

            # Merge with provided config
            merged = {**defaults, **config}

            # Convert to Decimals where needed
            for key in [
                "min_market_cap",
                "max_market_cap",
                "min_price",
                "min_daily_volume",
                "value_tilt",
                "size_tilt",
                "profitability_tilt",
                "investment_tilt",
                "momentum_tilt",
                "max_sector_weight",
                "max_single_position",
                "min_position",
                "max_factor_exposure",
                "rebalance_threshold",
                "max_beta",
                "max_volatility",
                "stop_loss_factor",
                "value_weight",
                "profitability_weight",
                "momentum_weight",
                "size_weight",
                "investment_weight",
                "min_quality_score",
                "min_factor_score",
            ]:
                if key in merged and merged[key] is not None:
                    if not isinstance(merged[key], Decimal):
                        merged[key] = Decimal(str(merged[key]))

            return FactorStrategyConfig(**merged)

        except Exception as e:
            logger.error(f"Error parsing config: {e}")
            # Return default config
            return FactorStrategyConfig()

    def set_universe(self, profiles: List[FactorProfile]) -> None:
        """
        Set the stock universe for factor analysis.

        Args:
            profiles: List of factor profiles
        """
        self.universe = profiles
        logger.info(f"Universe set: {len(profiles)} stocks")

        # Calculate factor scores for the universe
        if len(profiles) >= 10:
            self.factor_scores_dict = self.calculator.calculate_factor_scores(profiles)
            logger.info(f"Factor scores calculated for {len(self.factor_scores_dict)} stocks")
        else:
            logger.warning("Insufficient stocks for factor calculation")

    def construct_initial_portfolio(
        self,
        total_capital: Decimal,
    ) -> FactorPortfolio:
        """
        Construct the initial portfolio.

        Args:
            total_capital: Total capital to invest

        Returns:
            Constructed factor portfolio
        """
        if not self.universe:
            raise ValueError("Universe not set. Call set_universe() first.")

        if not self.factor_scores_dict:
            raise ValueError("Factor scores not calculated.")

        self.current_portfolio = self.constructor.construct_portfolio(
            self.universe,
            self.factor_scores_dict,
            total_capital,
        )

        self.last_rebalance_date = date.today()
        self.rebalance_count = 1

        logger.info(
            f"Initial portfolio constructed: " f"{len(self.current_portfolio.positions)} positions"
        )

        return self.current_portfolio

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generate trading signals based on factor analysis.

        This method is called for each market data update.
        Signals are generated when:
        1. Stock should be added to portfolio (positive factor score)
        2. Stock should be removed (negative factor score or risk)

        Args:
            market_data: Current market quote

        Returns:
            List of trading signals
        """
        if not self.is_active:
            logger.debug("Strategy inactive, no signals generated")
            return []

        if not self.universe or not self.factor_scores_dict:
            logger.debug("Universe or factor scores not set")
            return []

        symbol = market_data.symbol

        # Find profile for this symbol
        profile = None
        for p in self.universe:
            if p.symbol == symbol:
                profile = p
                break

        if profile is None:
            return []

        # Update price in profile
        profile.current_price = (
            market_data.close if hasattr(market_data, "close") else market_data.price
        )

        signals = []

        # Check if should buy
        if self._should_buy(profile):
            signal = self._create_buy_signal(profile, market_data)
            signals.append(signal)

        # Check if should sell
        elif self._should_sell(profile):
            signal = self._create_sell_signal(profile, market_data)
            signals.append(signal)

        return signals

    def _should_buy(self, profile: FactorProfile) -> bool:
        """
        Determine if stock should be bought.

        Args:
            profile: Factor profile

        Returns:
            True if should buy
        """
        # Check if already in portfolio
        if self.current_portfolio:
            for pos in self.current_portfolio.positions:
                if pos.symbol == profile.symbol:
                    return False

        # Check factor scores
        if profile.symbol not in self.factor_scores_dict:
            return False

        factor_scores = self.factor_scores_dict[profile.symbol]

        # Check minimum scores
        if profile.quality_score and profile.quality_score < self.strategy_config.min_quality_score:
            return False

        # Check composite factor score
        composite_score = self._calculate_composite_score(factor_scores, profile)
        if composite_score < 50:
            return False

        # Check value tilt
        if self.strategy_config.value_tilt > 0:
            if factor_scores.value_score and factor_scores.value_score < -0.5:
                return False

        # Check profitability tilt
        if self.strategy_config.profitability_tilt > 0:
            if factor_scores.profitability_score and factor_scores.profitability_score < -0.5:
                return False

        return True

    def _should_sell(self, profile: FactorProfile) -> bool:
        """
        Determine if stock should be sold.

        Args:
            profile: Factor profile

        Returns:
            True if should sell
        """
        # Check if in portfolio
        if not self.current_portfolio:
            return False

        in_portfolio = False
        for pos in self.current_portfolio.positions:
            if pos.symbol == profile.symbol:
                in_portfolio = True
                break

        if not in_portfolio:
            return False

        # Check factor scores
        if profile.symbol not in self.factor_scores_dict:
            return False

        factor_scores = self.factor_scores_dict[profile.symbol]

        # Sell if quality deteriorated significantly
        if (
            profile.quality_score
            and profile.quality_score < self.strategy_config.min_quality_score * 0.7
        ):
            logger.warning(f"Quality deteriorated for {profile.symbol}: {profile.quality_score}")
            return True

        # Sell if momentum turned very negative
        if factor_scores.momentum_score and factor_scores.momentum_score < -2:
            logger.warning(
                f"Negative momentum for {profile.symbol}: {factor_scores.momentum_score}"
            )
            return True

        # Sell if value signal inverted (for value tilt strategy)
        if self.strategy_config.value_tilt > 0:
            if factor_scores.value_score and factor_scores.value_score < -1.5:
                logger.warning(
                    f"Value signal inverted for {profile.symbol}: {factor_scores.value_score}"
                )
                return True

        return False

    def _calculate_composite_score(self, factor_scores: Any, profile: FactorProfile) -> float:
        """Calculate composite score for ranking."""
        score = 0.0

        # Apply factor tilts
        if factor_scores.value_score is not None:
            score += float(factor_scores.value_score) * float(self.strategy_config.value_tilt) * 100

        if factor_scores.profitability_score is not None:
            score += (
                float(factor_scores.profitability_score)
                * float(self.strategy_config.profitability_tilt)
                * 100
            )

        if factor_scores.momentum_score is not None:
            score += (
                float(factor_scores.momentum_score)
                * float(self.strategy_config.momentum_tilt)
                * 100
            )

        # Base quality score
        if profile.quality_score is not None:
            score += float(profile.quality_score) * 0.3

        # Momentum
        if factor_scores.factor_momentum_score is not None:
            score += float(factor_scores.factor_momentum_score) * 0.2

        return score

    def _create_buy_signal(
        self,
        profile: FactorProfile,
        market_data: Quote,
    ) -> Signal:
        """Create buy signal."""
        factor_scores = self.factor_scores_dict.get(profile.symbol)

        # Calculate confidence
        confidence = float(profile.quality_score or 50)

        # Calculate strength
        composite_score = (
            self._calculate_composite_score(factor_scores, profile) if factor_scores else 50
        )

        if composite_score > 75:
            strength = SignalStrength.STRONG
        elif composite_score > 60:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Priority score
        priority = min(100, confidence * 0.5 + composite_score * 0.5)

        # Metadata
        metadata = {
            "strategy": "multi_factor",
            "composite_score": composite_score,
            "quality_score": float(profile.quality_score or 0),
        }

        if factor_scores:
            metadata.update(
                {
                    "value_score": float(factor_scores.value_score or 0),
                    "profitability_score": float(factor_scores.profitability_score or 0),
                    "momentum_score": float(factor_scores.momentum_score or 0),
                }
            )

        signal = Signal(
            symbol=profile.symbol,
            signal_type=SignalType.BUY,
            strength=strength,
            confidence=confidence,
            liquidity_score=80.0,
            priority_score=priority,
            source=SignalSource.FUNDAMENTAL,
            price=market_data.close if hasattr(market_data, "close") else market_data.price,
            volume=market_data.volume if hasattr(market_data, "volume") else Decimal("1000000"),
            metadata=metadata,
        )

        logger.info(
            f"📈 BUY {profile.symbol}: Composite={composite_score:.1f}, "
            f"Confidence={confidence:.1f}%, Strength={strength.value}"
        )

        return signal

    def _create_sell_signal(
        self,
        profile: FactorProfile,
        market_data: Quote,
    ) -> Signal:
        """Create sell signal."""
        signal = Signal(
            symbol=profile.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=60.0,
            source=SignalSource.FUNDAMENTAL,
            price=market_data.close if hasattr(market_data, "close") else market_data.price,
            volume=market_data.volume if hasattr(market_data, "volume") else Decimal("1000000"),
            metadata={
                "strategy": "multi_factor",
                "reason": "factor_deterioration",
            },
        )

        logger.warning(f"📉 SELL {profile.symbol}: Factor deterioration")

        return signal

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Perform risk check on signal.

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            True if signal passes risk check
        """
        # Check position size
        max_pos = Decimal(str(self.strategy_config.max_single_position))
        current_allocation = Decimal("0")

        for pos in portfolio.positions:
            if pos.symbol == signal.symbol:
                # Position uses market_value property, not value
                current_allocation = pos.market_value / portfolio.total_value

        if current_allocation > 0 and current_allocation >= max_pos:
            logger.debug(f"Position max reached for {signal.symbol}: {current_allocation:.1%}")
            return False

        # Check sector exposure
        if self.current_portfolio and signal.signal_type == SignalType.BUY:
            sector = self._get_sector_for_symbol(signal.symbol)
            if sector and sector in self.current_portfolio.sector_weights:
                sector_weight = self.current_portfolio.sector_weights[sector]
                max_sector = self.strategy_config.max_sector_weight

                if sector_weight >= max_sector:
                    logger.debug(f"Sector max reached for {sector}: {sector_weight:.1%}")
                    return False

        return True

    def _get_sector_for_symbol(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol."""
        for profile in self.universe:
            if profile.symbol == symbol:
                return profile.sector
        return None

    def get_required_parameters(self) -> List[str]:
        """Get required configuration parameters."""
        return [
            "portfolio_size",
            "value_tilt",
            "profitability_tilt",
            "momentum_tilt",
            "max_sector_weight",
            "max_single_position",
        ]

    def validate_config(self) -> bool:
        """Validate strategy configuration."""
        try:
            # Get config for thresholds
            cfg = get_config()
            weights_tolerance = Decimal(str(getattr(cfg.trading, 'factor_weights_tolerance', 0.05)))
            max_single_position_limit = Decimal(
                str(getattr(cfg.trading, 'max_single_position_limit', 0.5))
            )

            # Validate weights sum
            total_weight = (
                self.strategy_config.value_weight
                + self.strategy_config.profitability_weight
                + self.strategy_config.momentum_weight
                + self.strategy_config.size_weight
                + self.strategy_config.investment_weight
            )

            if abs(total_weight - Decimal("1.0")) > weights_tolerance:
                logger.error(f"Factor weights must sum to 1.0, sum to {total_weight}")
                return False

            # Validate portfolio size
            if not (10 <= self.strategy_config.portfolio_size <= 100):
                logger.error("portfolio_size must be between 10 and 100")
                return False

            # Validate position limits
            if self.strategy_config.max_single_position > max_single_position_limit:
                logger.error(f"max_single_position cannot exceed {max_single_position_limit}")
                return False

            return True

        except Exception as e:
            logger.error(f"Config validation error: {e}")
            return False

    # ==========================================================================
    # ASYNC EXECUTION
    # ==========================================================================

    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the strategy (async interface from registry).

        This method provides the async interface required by the strategy registry.
        It wraps the synchronous portfolio construction and signal generation.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Portfolio or signals depending on execution mode
        """
        execution_mode = kwargs.get("mode", "signals")

        if execution_mode == "construct_portfolio":
            # Construct/return current portfolio
            total_capital = Decimal(str(kwargs.get("capital", 100000)))
            if self.current_portfolio is None:
                return self.construct_initial_portfolio(total_capital)
            return self.current_portfolio

        elif execution_mode == "rebalance":
            # Rebalance portfolio
            if self.current_portfolio:
                profiles = kwargs.get("profiles", self.universe)
                total_capital = Decimal(str(kwargs.get("capital", 100000)))
                return self.constructor.rebalance(
                    self.current_portfolio,
                    profiles,
                    self.factor_scores_dict,
                    total_capital,
                )
            return None

        else:  # mode == "signals"
            # Generate signals for a symbol
            market_data = kwargs.get("market_data")
            if market_data:
                return self.generate_signals(market_data)
            return []

    # ==========================================================================
    # PORTFOLIO MANAGEMENT
    # ==========================================================================

    def rebalance_portfolio(
        self,
        total_capital: Optional[Decimal] = None,
    ) -> FactorPortfolio:
        """
        Rebalance the portfolio.

        Args:
            total_capital: Current total capital (optional)

        Returns:
            Rebalanced portfolio
        """
        if not self.current_portfolio:
            raise ValueError("No portfolio to rebalance. Construct initial portfolio first.")

        if total_capital is None:
            total_capital = self.current_portfolio.total_value

        self.current_portfolio = self.constructor.rebalance(
            self.current_portfolio,
            self.universe,
            self.factor_scores_dict,
            total_capital,
        )

        self.last_rebalance_date = date.today()
        self.rebalance_count += 1

        logger.info(f"Portfolio rebalanced (#{self.rebalance_count})")

        return self.current_portfolio

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Get current portfolio metrics.

        Returns:
            Dictionary of portfolio metrics
        """
        if not self.current_portfolio:
            return {}

        return self.constructor.get_portfolio_metrics(self.current_portfolio)

    def get_factor_exposures(self) -> Dict[str, float]:
        """
        Get current portfolio factor exposures.

        Returns:
            Dictionary of factor exposures
        """
        if not self.current_portfolio:
            return {}

        return {k: float(v) for k, v in self.current_portfolio.factor_exposures.items()}

    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get comprehensive strategy status.

        Returns:
            Dictionary with strategy status information
        """
        status = {
            "name": self.name,
            "objective": self.strategy_config.objetivo_inversion,
            "is_active": self.is_active,
            "universe_size": len(self.universe),
            "portfolio_positions": (
                len(self.current_portfolio.positions) if self.current_portfolio else 0
            ),
            "last_rebalance": (
                self.last_rebalance_date.isoformat() if self.last_rebalance_date else None
            ),
            "rebalance_count": self.rebalance_count,
            "factor_tilts": {
                "value": float(self.strategy_config.value_tilt),
                "size": float(self.strategy_config.size_tilt),
                "profitability": float(self.strategy_config.profitability_tilt),
                "investment": float(self.strategy_config.investment_tilt),
                "momentum": float(self.strategy_config.momentum_tilt),
            },
            "config_description": self.strategy_config.get_config_description(),
        }

        if self.current_portfolio:
            status["portfolio_metrics"] = self.get_portfolio_metrics()
            status["factor_exposures"] = self.get_factor_exposures()

        return status
