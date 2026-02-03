"""
FX Intermarket Strategy Implementation.

This module implements an FX trading strategy based on intermarket
relationships and correlations between currency pairs and external
asset classes.

Strategy Logic:
1. Monitor correlations between FX pairs and external assets
2. Detect significant moves in external assets
3. Generate trading signals based on expected FX responses
4. Apply risk management and position sizing

Key Intermarket Relationships:
- Safe Haven: JPY/CHF appreciate when equities decline
- Commodity Link: AUD/CAD/NZD track commodity prices
- Carry Trade: High-yield currencies correlate with risk assets
- Yield Differential: Interest rate differentials drive movements

Reference:
    Ilmanen, Antti. "Expected Returns: An Investor's Guide"
    Chapters on currency markets and intermarket relationships
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

from app.models.signal import Signal, SignalSource, SignalType, SignalStrength
from app.strategies.base import BaseStrategy
from app.strategies.fx_intermarket.correlation_analyzer import (
    CorrelationAnalyzer,
)
from app.strategies.fx_intermarket.models import (
    AssetClass,
    FXIntermarketConfig,
    IntermarketRelationship,
    IntermarketSignal,
    RelationshipType,
)

logger = logging.getLogger(__name__)


@dataclass
class FXIntermarketState:
    """
    Current state of the FX intermarket strategy.

    Attributes:
        active_relationships: Dictionary of tracked relationships
        historical_correlations: Historical correlation data
        current_signals: Active trading signals
        last_correlation_update: Last time correlations were updated
        total_trades: Total number of trades executed
    """

    active_relationships: dict[str, IntermarketRelationship] = field(
        default_factory=dict
    )
    historical_correlations: dict[str, list[Decimal]] = field(default_factory=dict)
    current_signals: list[IntermarketSignal] = field(default_factory=list)
    last_correlation_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_trades: int = 0


class FXIntermarketStrategy(BaseStrategy):
    """
    FX Intermarket strategy based on cross-asset relationships.

    This strategy exploits known intermarket relationships to generate
    trading signals when significant moves occur in related assets.

    Signal Generation Process:
    1. Calculate correlations between FX pairs and external assets
    2. Monitor external assets for significant moves
    3. Generate signals when expected FX response meets threshold
    4. Apply risk filters and position sizing

    Attributes:
        config: Strategy configuration (FXIntermarketConfig)
        analyzer: Correlation analysis engine
        state: Current strategy state

    Examples:
        >>> from app.strategies.fx_intermarket import (
        ...     FXIntermarketStrategy,
        ...     FXIntermarketConfig,
        ... )
        >>> config = FXIntermarketConfig(
        ...     correlation_lookback=60,
        ...     min_correlation=Decimal("0.7")
        ... )
        >>> strategy = FXIntermarketStrategy(config=config)
    """

    def __init__(
        self,
        config: dict[str, Any] | FXIntermarketConfig,
    ) -> None:
        """
        Initialize the FX Intermarket strategy.

        Args:
            config: Strategy configuration (dict or FXIntermarketConfig)

        Raises:
            ValueError: If config is invalid
        """
        # Handle dict config for BaseStrategy compatibility
        if isinstance(config, dict):
            # Extract known parameters or use defaults
            strategy_config = FXIntermarketConfig(
                correlation_lookback=config.get("correlation_lookback", 60),
                min_correlation=Decimal(str(config.get("min_correlation", "0.6"))),
                min_significance=Decimal(str(config.get("min_significance", "70"))),
                signal_threshold=Decimal(str(config.get("signal_threshold", "60"))),
                min_signal_strength=Decimal(str(config.get("min_signal_strength", "65"))),
                max_positions=config.get("max_positions", 5),
                stop_loss=Decimal(str(config.get("stop_loss", "0.03"))),
                take_profit=Decimal(str(config.get("take_profit", "0.08"))),
                position_size=Decimal(str(config.get("position_size", "0.1"))),
            )
            super().__init__(config)
        else:
            strategy_config = config
            # Convert to dict for BaseStrategy
            super().__init__({
                "name": "FXIntermarket",
                "description": "FX Intermarket strategy based on cross-asset relationships",
                "version": "1.0.0",
                "correlation_lookback": strategy_config.correlation_lookback,
                "min_correlation": str(strategy_config.min_correlation),
                "min_significance": str(strategy_config.min_significance),
                "signal_threshold": str(strategy_config.signal_threshold),
                "min_signal_strength": str(strategy_config.min_signal_strength),
                "max_positions": strategy_config.max_positions,
                "stop_loss": str(strategy_config.stop_loss),
                "take_profit": str(strategy_config.take_profit),
                "position_size": str(strategy_config.position_size),
            })

        self.config = strategy_config

        # Initialize correlation analyzer
        self.analyzer = CorrelationAnalyzer(
            lookback_days=strategy_config.correlation_lookback,
            min_correlation=strategy_config.min_correlation,
            min_significance=strategy_config.min_significance,
        )

        # Initialize strategy state
        self.state = FXIntermarketState()

        # Pre-define common relationship mappings
        self._setup_default_relationships()

        logger.info(
            f"FXIntermarketStrategy initialized with "
            f"{len(self.config.monitored_pairs)} pairs, "
            f"{len(self.config.monitored_assets)} assets"
        )

    def _setup_default_relationships(self) -> None:
        """Setup default relationship mappings for known pairs."""
        self.default_relationships = {
            # Safe haven relationships
            "USD/JPY_SPX": RelationshipType.SAFE_HAVEN,
            "USD/CHF_SPX": RelationshipType.SAFE_HAVEN,
            "USD/JPY_VIX": RelationshipType.POSITIVE_CORRELATION,
            # Commodity link relationships
            "AUD/USD_GOLD": RelationshipType.COMMODITY_LINK,
            "AUD/USD_OIL": RelationshipType.COMMODITY_LINK,
            "USD/CAD_OIL": RelationshipType.COMMODITY_LINK,
            "NZD/USD_GOLD": RelationshipType.COMMODITY_LINK,
            # Carry trade relationships
            "AUD/USD_SPX": RelationshipType.CARRY_TRADE,
            "NZD/USD_SPX": RelationshipType.CARRY_TRADE,
            # Yield differential relationships
            "EUR/USD_US10Y": RelationshipType.YIELD_DIFFERENTIAL,
            "USD/JPY_US10Y": RelationshipType.YIELD_DIFFERENTIAL,
        }

    def generate_signals(self, market_data: Any) -> list[Signal]:
        """
        Generate trading signals based on intermarket analysis.

        This is the main entry point for signal generation. It:
        1. Updates correlations if needed
        2. Analyzes current relationships
        3. Detects significant moves in external assets
        4. Generates signals for expected FX responses

        Args:
            market_data: Market data (dict with returns for FX and assets)

        Returns:
            List of Signal objects for trading

        Raises:
            ValueError: If market_data is invalid

        Examples:
            >>> signals = strategy.generate_signals({
            ...     "EUR/USD": pd.Series([...]),
            ...     "SPX": pd.Series([...])
            ... })
        """
        if not isinstance(market_data, dict):
            raise ValueError(
                f"market_data must be a dict, got {type(market_data)}"
            )

        signals = []
        as_of = datetime.now(timezone.utc)

        try:
            # Update correlations periodically
            self.update_correlations(as_of)

            # Analyze current intermarket relationships
            relationships = self.analyze_intermarket_relationships(as_of)

            # Detect significant moves in external assets
            significant_moves = self.detect_significant_moves(
                market_data, threshold_std=2.0
            )

            # Generate signals for each significant move
            for asset, move_info in significant_moves.items():
                # Find FX pairs related to this asset
                related_pairs = self._find_related_pairs(asset, relationships)

                for fx_pair, relationship in related_pairs:
                    # Generate intermarket signal
                    intermarket_signal = self.generate_intermarket_signal(
                        fx_pair=fx_pair,
                        trigger_asset=asset,
                        relationship=relationship,
                        asset_move=move_info,
                    )

                    if intermarket_signal and intermarket_signal.is_actionable:
                        # Convert to base Signal type
                        base_signal = self._convert_to_base_signal(
                            intermarket_signal, market_data.get(fx_pair)
                        )
                        if base_signal:
                            signals.append(base_signal)

            # Limit to max positions
            if len(signals) > self.config.max_positions:
                # Sort by confidence and keep top signals
                signals.sort(key=lambda s: s.confidence, reverse=True)
                signals = signals[: self.config.max_positions]

            logger.info(
                f"Generated {len(signals)} intermarket signals "
                f"from {len(significant_moves)} significant asset moves"
            )

        except Exception as e:
            logger.error(f"Error generating signals: {e}")

        return signals

    def analyze_intermarket_relationships(
        self, as_of: datetime
    ) -> list[IntermarketRelationship]:
        """
        Analyze current intermarket relationships.

        Calculates correlations between monitored FX pairs and external
        assets to identify active relationships.

        Args:
            as_of: Analysis timestamp

        Returns:
            List of active IntermarketRelationship objects

        Examples:
            >>> relationships = strategy.analyze_intermarket_relationships(
            ...     datetime.utcnow()
            ... )
        """
        # This would typically use historical data
        # For now, return tracked relationships from state
        return list(self.state.active_relationships.values())

    def detect_significant_moves(
        self,
        returns_data: dict[str, pd.Series],
        threshold_std: float = 2.0,
    ) -> dict[str, dict[str, Any]]:
        """
        Detect significant moves in external assets.

        Identifies assets that have moved more than the specified
        standard deviation threshold.

        Args:
            returns_data: Dictionary of return series by asset
            threshold_std: Standard deviation threshold for significance

        Returns:
            Dictionary mapping asset symbols to move information

        Examples:
            >>> moves = strategy.detect_significant_moves(
            ...     returns_data,
            ...     threshold_std=2.0
            ... )
        """
        significant_moves = {}

        for asset, returns in returns_data.items():
            # Only check external assets, not FX pairs
            if asset in self.config.monitored_assets:
                if len(returns) < 2:
                    continue

                # Get latest return
                latest_return = Decimal(str(returns.iloc[-1]))

                # Calculate rolling statistics
                if len(returns) >= 20:
                    mean_return = returns.tail(20).mean()
                    std_return = returns.tail(20).std()
                else:
                    mean_return = returns.mean()
                    std_return = returns.std()

                if std_return == 0:
                    continue

                # Calculate z-score
                z_score = float((latest_return - Decimal(str(mean_return))) / Decimal(str(std_return)))

                # Check if exceeds threshold
                if abs(z_score) >= threshold_std:
                    significant_moves[asset] = {
                        "return": latest_return,
                        "z_score": Decimal(str(z_score)),
                        "mean": Decimal(str(mean_return)),
                        "std": Decimal(str(std_return)),
                        "direction": "up" if latest_return > 0 else "down",
                    }

        return significant_moves

    def generate_intermarket_signal(
        self,
        fx_pair: str,
        trigger_asset: str,
        relationship: IntermarketRelationship,
        asset_move: dict[str, Any],
    ) -> IntermarketSignal | None:
        """
        Generate an intermarket trading signal.

        Creates a signal based on the expected FX response to a move
        in an external asset, given their historical relationship.

        Args:
            fx_pair: Currency pair to trade
            trigger_asset: External asset that moved
            relationship: Intermarket relationship details
            asset_move: Information about the asset move

        Returns:
            IntermarketSignal if signal meets criteria, None otherwise

        Examples:
            >>> signal = strategy.generate_intermarket_signal(
            ...     fx_pair="USD/JPY",
            ...     trigger_asset="SPX",
            ...     relationship=rel,
            ...     asset_move={"return": Decimal("-0.02"), ...}
            ... )
        """
        try:
            # Calculate expected move in FX pair
            expected_move = self.calculate_expected_move(
                asset_move["return"],
                relationship.correlation,
                relationship.beta,
            )

            # Calculate signal strength
            strength = self.calculate_signal_strength(
                expected_move,
                relationship.correlation,
                relationship.significance,
            )

            # Calculate confidence
            confidence = self.calculate_confidence(
                relationship.correlation,
                relationship.significance,
                self._get_relationship_stability(relationship),
            )

            # Determine signal type
            signal_type = self._determine_signal_type(
                expected_move, relationship.relationship_type
            )

            # Check if signal meets threshold
            if strength < self.config.min_signal_strength:
                return None

            # Build rationale
            rationale = self._build_signal_rationale(
                fx_pair,
                trigger_asset,
                relationship,
                asset_move,
                expected_move,
            )

            signal = IntermarketSignal(
                fx_pair=fx_pair,
                signal_type=signal_type,
                strength=strength,
                trigger_asset=trigger_asset,
                relationship_type=relationship.relationship_type,
                expected_move=expected_move,
                confidence=confidence,
                rationale=rationale,
            )

            logger.info(
                f"Generated intermarket signal: {fx_pair} {signal_type} "
                f"strength={strength:.0f} confidence={confidence:.0f}"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating intermarket signal: {e}")
            return None

    def calculate_expected_move(
        self,
        asset_move: Decimal,
        correlation: Decimal,
        beta: Decimal,
    ) -> Decimal:
        """
        Calculate expected move in FX pair based on asset move.

        Expected Move = Asset Move * Correlation * Beta

        Args:
            asset_move: Move in external asset (decimal)
            correlation: Correlation coefficient
            beta: Beta coefficient

        Returns:
            Expected move in FX pair as Decimal

        Examples:
            >>> expected = strategy.calculate_expected_move(
            ...     Decimal("0.02"),
            ...     Decimal("-0.75"),
            ...     Decimal("-0.5")
            ... )
        """
        # Expected move = asset move * correlation * beta
        expected = asset_move * correlation * beta
        return expected

    def calculate_signal_strength(
        self,
        expected_move: Decimal,
        correlation: Decimal,
        significance: Decimal,
    ) -> Decimal:
        """
        Calculate signal strength score (0-100).

        Combines magnitude of expected move with correlation strength
        and statistical significance.

        Args:
            expected_move: Expected price move
            correlation: Correlation coefficient
            significance: Statistical significance (0-100)

        Returns:
            Signal strength score (0-100)

        Examples:
            >>> strength = strategy.calculate_signal_strength(
            ...     Decimal("0.015"),
            ...     Decimal("0.8"),
            ...     Decimal("90")
            ... )
        """
        # Magnitude component (larger expected move = higher strength)
        magnitude_score = min(abs(expected_move) * Decimal("1000"), Decimal("50"))

        # Correlation component
        correlation_score = abs(correlation) * Decimal("40")

        # Significance component
        significance_score = significance * Decimal("0.1")

        # Combine components
        strength = magnitude_score + correlation_score + significance_score

        return min(strength, Decimal("100"))

    def calculate_confidence(
        self,
        correlation: Decimal,
        significance: Decimal,
        relationship_stability: Decimal,
    ) -> Decimal:
        """
        Calculate signal confidence score (0-100).

        Args:
            correlation: Correlation coefficient
            significance: Statistical significance (0-100)
            relationship_stability: Stability score (0-100)

        Returns:
            Confidence score (0-100)

        Examples:
            >>> confidence = strategy.calculate_confidence(
            ...     Decimal("-0.75"),
            ...     Decimal("95"),
            ...     Decimal("80")
            ... )
        """
        # Correlation strength (higher absolute = more confident)
        corr_confidence = abs(correlation) * Decimal("40")

        # Statistical significance
        sig_confidence = significance * Decimal("0.4")

        # Stability bonus
        stability_bonus = relationship_stability * Decimal("0.2")

        confidence = corr_confidence + sig_confidence + stability_bonus

        return min(confidence, Decimal("100"))

    def _get_relationship_stability(
        self, relationship: IntermarketRelationship
    ) -> Decimal:
        """
        Get relationship stability score.

        Args:
            relationship: Intermarket relationship

        Returns:
            Stability score (0-100)
        """
        # Check if we have historical correlation data
        key = f"{relationship.fx_pair}_{relationship.external_asset}"

        if key not in self.state.historical_correlations:
            # No history, use significance as proxy
            return relationship.significance

        historical = self.state.historical_correlations[key]

        if len(historical) < 5:
            return relationship.significance

        # Calculate stability (1 - std/mean)
        import numpy as np

        values = [float(c) for c in historical]
        std = np.std(values)
        mean = np.mean(np.abs(values))

        if mean == 0:
            return Decimal("50")

        stability = 1 - (std / mean)
        return Decimal(str(max(0, min(100, stability * 100))))

    def _determine_signal_type(
        self, expected_move: Decimal, relationship_type: RelationshipType
    ) -> str:
        """
        Determine signal type (buy/sell) from expected move.

        Args:
            expected_move: Expected price move
            relationship_type: Type of relationship

        Returns:
            "buy" or "sell"
        """
        # For safe haven, negative expected move means buy (appreciate)
        if relationship_type == RelationshipType.SAFE_HAVEN:
            return "sell" if expected_move > 0 else "buy"

        # For commodity link and carry trade
        if relationship_type in (
            RelationshipType.COMMODITY_LINK,
            RelationshipType.CARRY_TRADE,
            RelationshipType.POSITIVE_CORRELATION,
        ):
            return "buy" if expected_move > 0 else "sell"

        # For negative correlation
        if relationship_type == RelationshipType.NEGATIVE_CORRELATION:
            return "sell" if expected_move > 0 else "buy"

        # Default
        return "buy" if expected_move > 0 else "sell"

    def _build_signal_rationale(
        self,
        fx_pair: str,
        trigger_asset: str,
        relationship: IntermarketRelationship,
        asset_move: dict[str, Any],
        expected_move: Decimal,
    ) -> str:
        """
        Build signal rationale explanation.

        Args:
            fx_pair: Currency pair
            trigger_asset: Triggering asset
            relationship: Intermarket relationship
            asset_move: Asset move information
            expected_move: Expected FX move

        Returns:
            Rationale string
        """
        direction = asset_move["direction"]
        move_pct = float(asset_move["return"]) * 100

        rationale = (
            f"{trigger_asset} moved {direction} {abs(move_pct):.2f}%. "
            f"Based on {relationship.relationship_type.value} relationship "
            f"(corr={relationship.correlation:.2f}, "
            f"sig={relationship.significance:.0f}), "
            f"expecting {fx_pair} to move {expected_move*100:.2f}%."
        )

        return rationale

    def _find_related_pairs(
        self,
        asset: str,
        relationships: list[IntermarketRelationship],
    ) -> list[tuple[str, IntermarketRelationship]]:
        """
        Find FX pairs related to an external asset.

        Args:
            asset: External asset symbol
            relationships: List of relationships

        Returns:
            List of (fx_pair, relationship) tuples
        """
        related = []

        for rel in relationships:
            if rel.external_asset == asset and rel.is_active:
                related.append((rel.fx_pair, rel))

        return related

    def _convert_to_base_signal(
        self,
        intermarket_signal: IntermarketSignal,
        fx_price: Any = None,
    ) -> Signal | None:
        """
        Convert IntermarketSignal to base Signal type.

        Args:
            intermarket_signal: Intermarket signal
            fx_price: Current FX price (if available)

        Returns:
            Signal object or None
        """
        try:
            # Determine signal strength category
            strength_val = float(intermarket_signal.strength)
            if strength_val >= 80:
                strength = SignalStrength.VERY_STRONG
            elif strength_val >= 65:
                strength = SignalStrength.STRONG
            elif strength_val >= 50:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # Determine signal type
            signal_type = SignalType.BUY if intermarket_signal.is_buy else SignalType.SELL

            # Use provided price or default
            price = fx_price if isinstance(fx_price, Decimal) else Decimal("1.0")

            signal = Signal(
                symbol=intermarket_signal.fx_pair,
                signal_type=signal_type,
                strength=strength,
                confidence=float(intermarket_signal.confidence),
                liquidity_score=75.0,  # FX generally liquid
                priority_score=float(intermarket_signal.strength),
                source=SignalSource.FUNDAMENTAL,
                price=price,
                volume=Decimal("1000000"),  # Default FX volume
                metadata={
                    "strategy": "fx_intermarket",
                    "trigger_asset": intermarket_signal.trigger_asset,
                    "relationship_type": intermarket_signal.relationship_type.value,
                    "expected_move": str(intermarket_signal.expected_move),
                    "rationale": intermarket_signal.rationale,
                },
            )

            return signal

        except Exception as e:
            logger.error(f"Error converting signal: {e}")
            return None

    def update_correlations(self, as_of: datetime) -> None:
        """
        Update correlation calculations.

        Args:
            as_of: Current timestamp

        Examples:
            >>> strategy.update_correlations(datetime.now(timezone.utc))
        """
        # Check if update is needed (once per day)
        if (as_of - self.state.last_correlation_update).days < 1:
            return

        # In a real implementation, this would:
        # 1. Fetch historical return data
        # 2. Recalculate correlations using analyzer
        # 3. Update active_relationships in state
        # 4. Store historical correlations for stability analysis

        self.state.last_correlation_update = as_of

        logger.info("Correlations updated")

    def get_monitored_pairs(self) -> list[str]:
        """
        Get list of monitored FX pairs.

        Returns:
            List of currency pair symbols

        Examples:
            >>> pairs = strategy.get_monitored_pairs()
        """
        return self.config.get_fx_pairs()

    def get_monitored_assets(self) -> dict[str, AssetClass]:
        """
        Get dictionary of monitored external assets.

        Returns:
            Dictionary mapping asset symbols to asset classes

        Examples:
            >>> assets = strategy.get_monitored_assets()
        """
        return self.config.get_external_assets()

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """
        Check if signal passes risk management criteria.

        Args:
            signal: Trading signal to check
            portfolio: Current portfolio state

        Returns:
            True if signal passes risk checks

        Examples:
            >>> passes = strategy.risk_check(signal, portfolio)
        """
        # Check confidence threshold
        if signal.confidence < float(self.config.signal_threshold):
            logger.warning(
                f"Signal rejected: confidence {signal.confidence} "
                f"below threshold {self.config.signal_threshold}"
            )
            return False

        # Check if we're at max positions
        # (This would need actual position count from portfolio)
        # For now, always pass if confidence is sufficient

        return True

    def get_required_parameters(self) -> list[str]:
        """
        Get required strategy parameters.

        Returns:
            List of required parameter names

        Examples:
            >>> params = strategy.get_required_parameters()
        """
        return [
            "correlation_lookback",
            "min_correlation",
            "min_significance",
            "signal_threshold",
            "max_positions",
            "stop_loss",
            "take_profit",
        ]

    def get_portfolio_summary(self) -> dict[str, Any]:
        """
        Get summary of current strategy state.

        Returns:
            Dictionary with strategy metrics

        Examples:
            >>> summary = strategy.get_portfolio_summary()
        """
        return {
            "active_relationships": len(self.state.active_relationships),
            "current_signals": len(self.state.current_signals),
            "total_trades": self.state.total_trades,
            "monitored_pairs": len(self.config.monitored_pairs),
            "monitored_assets": len(self.config.monitored_assets),
            "last_correlation_update": self.state.last_correlation_update.isoformat(),
        }

    def __str__(self) -> str:
        """Return string representation of strategy."""
        return (
            f"FXIntermarketStrategy("
            f"pairs={len(self.config.monitored_pairs)}, "
            f"assets={len(self.config.monitored_assets)}, "
            f"min_corr={self.config.min_correlation})"
        )

    def __repr__(self) -> str:
        """Return detailed representation of strategy."""
        return (
            f"FXIntermarketStrategy("
            f"config={self.config}, "
            f"active_relationships={len(self.state.active_relationships)}, "
            f"signals={len(self.state.current_signals)})"
        )
