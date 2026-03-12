"""
Market Depth and Liquidity Analysis Module

This module implements market depth measurement and liquidity estimation concepts
from Maureen O'Hara's "Market Microstructure Theory" (Chapter 5-6).

Key Concepts:
- Market depth measurement and interpretation
- Liquidity estimation across different dimensions
- Spread component analysis (order processing, inventory, adverse selection)
- Liquidity risk assessment

References:
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 5-6
- Stoll, H.R. (2000) "Friction"
- Kyle, A.S. (1985) "Continuous Auctions and Insider Trading"
"""
from __future__ import annotations  # Enable Python 3.10+ union syntax in Python 3.9

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# mypy: ignore-errors
# pylint: disable=unsupported-binary-operation  # For Python 3.10+ union syntax


class LiquidityDimension(Enum):
    """Dimensions of liquidity"""

    DEPTH = "DEPTH"  # Volume available at prices
    TIGHTNESS = "TIGHTNESS"  # Bid-ask spread
    RESILIENCE = "RESILIENCE"  # Speed of recovery from shocks
    IMMEDIACY = "IMMEDIACY"  # Speed of execution


class SpreadComponent(Enum):
    """Components of the bid-ask spread"""

    ORDER_PROCESSING = "ORDER_PROCESSING"  # Fixed costs of trading
    INVENTORY_HOLDING = "INVENTORY_HOLDING"  # Inventory risk premium
    ADVERSE_SELECTION = "ADVERSE_SELECTION"  # Information asymmetry cost


@dataclass
class LiquidityMetrics:
    """
    Comprehensive liquidity metrics

    Attributes:
        timestamp: Measurement time
        bid_ask_spread_bps: Current spread in basis points
        quoted_depth: Total depth at best bid/ask
        effective_spread: Effective spread for trade size
        depth_slope: Slope of order book
        liquidity_score: Composite liquidity score (0-100)
        liquidity_regime: Classification (HIGH/NORMAL/LOW)
    """

    timestamp: datetime
    bid_ask_spread_bps: float
    quoted_depth: Decimal
    effective_spread_bps: float
    depth_slope: float
    liquidity_score: float
    liquidity_regime: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'bid_ask_spread_bps': self.bid_ask_spread_bps,
            'quoted_depth': str(self.quoted_depth),
            'effective_spread_bps': self.effective_spread_bps,
            'depth_slope': self.depth_slope,
            'liquidity_score': self.liquidity_score,
            'liquidity_regime': self.liquidity_regime,
        }


@dataclass
class SpreadDecomposition:
    """
    Decomposition of bid-ask spread into components

    Based on Stoll (2000) and O'Hara analysis:
    Spread = Order Processing + Inventory Holding + Adverse Selection

    Attributes:
        timestamp: Decomposition time
        total_spread_bps: Total spread
        order_processing_bps: Fixed costs portion
        inventory_holding_bps: Inventory risk portion
        adverse_selection_bps: Information asymmetry portion
        dominant_component: Largest component
    """

    timestamp: datetime
    total_spread_bps: float
    order_processing_bps: float
    inventory_holding_bps: float
    adverse_selection_bps: float
    dominant_component: SpreadComponent

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_spread_bps': self.total_spread_bps,
            'order_processing_bps': self.order_processing_bps,
            'inventory_holding_bps': self.inventory_holding_bps,
            'adverse_selection_bps': self.adverse_selection_bps,
            'dominant_component': self.dominant_component.value,
        }


@dataclass
class DepthProfile:
    """
    Market depth profile at multiple price levels

    Attributes:
        timestamp: Profile time
        bid_levels: List of (price, cumulative_volume) for bids
        ask_levels: List of (price, cumulative_volume) for asks
        total_bid_depth: Total volume on bid side
        total_ask_depth: Total volume on ask side
        imbalance_ratio: Ratio of bid to ask depth
    """

    timestamp: datetime
    bid_levels: list[tuple[Decimal, Decimal]]
    ask_levels: list[tuple[Decimal, Decimal]]
    total_bid_depth: Decimal
    total_ask_depth: Decimal
    imbalance_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'bid_levels': [(str(p), str(v)) for p, v in self.bid_levels],
            'ask_levels': [(str(p), str(v)) for p, v in self.ask_levels],
            'total_bid_depth': str(self.total_bid_depth),
            'total_ask_depth': str(self.total_ask_depth),
            'imbalance_ratio': self.imbalance_ratio,
        }


@dataclass
class LiquidityRisk:
    """
    Liquidity risk assessment

    Attributes:
        timestamp: Assessment time
        liquidity_gap: Gap between available and needed liquidity
    """

    timestamp: datetime
    liquidity_gap: Decimal
    execution_shortfall_risk: float
    market_impact_estimate: float
    risk_level: str
    recommendations: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'liquidity_gap': str(self.liquidity_gap),
            'execution_shortfall_risk': self.execution_shortfall_risk,
            'market_impact_estimate': self.market_impact_estimate,
            'risk_level': self.risk_level,
            'recommendations': self.recommendations,
        }


class LiquidityAnalyzer:
    """
    Analyzes market depth and liquidity characteristics

    Implements O'Hara Chapter 5 concepts on liquidity measurement
    """

    def __init__(
        self,
        lookback_periods: int = 20,
        depth_levels: int = 5,
    ):
        """
        Initialize liquidity analyzer

        Args:
            lookback_periods: Number of periods for historical analysis
            depth_levels: Number of order book levels to analyze
        """
        logger.debug(
            "Initializing LiquidityAnalyzer",
            extra={
                "lookback_periods": lookback_periods,
                "depth_levels": depth_levels,
            },
        )
        self.lookback_periods = lookback_periods
        self.depth_levels = depth_levels
        self._historical_metrics: list[LiquidityMetrics] = []

    def measure_market_depth(
        self,
        order_book: dict[str, list[tuple[Decimal, Decimal]]],
        target_size: Decimal | None = None,
    ) -> DepthProfile:
        """
        Measure market depth at multiple price levels

        Depth is a key dimension of liquidity (O'Hara 5.2)

        Args:
            order_book: Dictionary with 'bids' and 'asks'
                Each is a list of (price, size) tuples
            target_size: Size to calculate depth for

        Returns:
            DepthProfile with depth information
        """
        logger.debug(
            "Measuring market depth",
            extra={
                "bid_levels": len(order_book.get('bids', [])),
                "ask_levels": len(order_book.get('asks', [])),
                "target_size": str(target_size) if target_size else None,
            },
        )
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])

        timestamp = datetime.now()

        # Calculate cumulative depth
        bid_levels = []
        ask_levels = []
        cumulative_bid = Decimal('0')
        cumulative_ask = Decimal('0')

        # Process bids (descending price)
        for price, size in bids[: self.depth_levels]:
            cumulative_bid += size
            bid_levels.append((price, cumulative_bid))

        # Process asks (ascending price)
        for price, size in asks[: self.depth_levels]:
            cumulative_ask += size
            ask_levels.append((price, cumulative_ask))

        # Total depth
        total_bid_depth = sum(size for _, size in bids)
        total_ask_depth = sum(size for _, size in asks)

        # Imbalance ratio
        total_depth = total_bid_depth + total_ask_depth
        if total_depth > 0:
            imbalance_ratio = float((total_bid_depth - total_ask_depth) / total_depth)
        else:
            imbalance_ratio = 0.0

        logger.info(
            "Market depth measured",
            extra={
                "total_bid_depth": float(total_bid_depth),
                "total_ask_depth": float(total_ask_depth),
                "imbalance_ratio": imbalance_ratio,
            },
        )
        return DepthProfile(
            timestamp=timestamp,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            total_bid_depth=total_bid_depth,
            total_ask_depth=total_ask_depth,
            imbalance_ratio=imbalance_ratio,
        )

    def calculate_liquidity_score(
        self,
        spread_bps: float,
        depth: Decimal,
        volatility: float,
        volume: float,
    ) -> float:
        """
        Calculate composite liquidity score

        Combines multiple liquidity dimensions into single score (0-100)

        Args:
            spread_bps: Current bid-ask spread in bps
            depth: Available depth
            volatility: Price volatility
            volume: Trading volume

        Returns:
            Liquidity score from 0 (illiquid) to 100 (highly liquid)
        """
        # Tightness score (inverse of spread)
        # Lower spread = higher tightness
        tightness_score = max(0, min(100, 100 - spread_bps * 2))

        # Depth score (log scale)
        # More depth = higher score
        depth_value = float(depth)
        depth_score = min(100, np.log1p(depth_value / 1000) * 20)

        # Immediacy score (volume)
        # Higher volume = better immediacy
        volume_score = min(100, np.log1p(volume / 10000) * 15)

        # Resilience score (inverse of volatility)
        # Lower volatility = better resilience
        resilience_score = max(0, min(100, 100 - volatility * 500))

        # Composite score (weighted average)
        # Weights: Tightness (30%), Depth (30%), Immediacy (20%), Resilience (20%)
        composite = (
            tightness_score * 0.30
            + depth_score * 0.30
            + volume_score * 0.20
            + resilience_score * 0.20
        )

        return round(composite, 2)

    def classify_liquidity_regime(self, liquidity_score: float) -> str:
        """
        Classify liquidity regime based on score

        Args:
            liquidity_score: Composite liquidity score

        Returns:
            Regime classification
        """
        config = get_config()
        high_threshold = getattr(config.market_microstructure, 'liquidity_high_threshold', 80.0)
        normal_threshold = getattr(config.market_microstructure, 'liquidity_normal_threshold', 60.0)
        low_threshold = getattr(config.market_microstructure, 'liquidity_low_threshold', 40.0)

        if liquidity_score >= high_threshold:
            return 'HIGH'
        elif liquidity_score >= normal_threshold:
            return 'NORMAL'
        elif liquidity_score >= low_threshold:
            return 'LOW'
        else:
            return 'POOR'

    def decompose_spread(
        self,
        spread_bps: float,
        price_variance: float,
        order_flow_imbalance: float,
        volume: float,
        volatility: float,
    ) -> SpreadDecomposition:
        """
        Decompose bid-ask spread into components

        Based on Stoll (2000) and O'Hara analysis:
        - Order processing: Fixed costs
        - Inventory holding: Risk premium for holding inventory
        - Adverse selection: Cost of trading with informed traders

        Args:
            spread_bps: Total spread in bps
            price_variance: Variance of returns
            order_flow_imbalance: Current order imbalance
            volume: Trading volume
            volatility: Price volatility

        Returns:
            SpreadDecomposition with component breakdown
        """
        # Order processing component (fixed costs)
        # Typically 30-50% of spread for liquid stocks
        order_processing = spread_bps * 0.35

        # Inventory holding component (inventory risk)
        # Proportional to volatility and order imbalance
        # From Amihud-Mendelson (1980) model
        inventory_risk = volatility * np.sqrt(price_variance) * 10000
        inventory_holding = min(spread_bps * 0.4, inventory_risk)

        # Adverse selection component (information asymmetry)
        # Proportional to order flow imbalance and inversely to volume
        # From Glosten-Milgrom (1985) model
        adverse_selection = (
            spread_bps * abs(order_flow_imbalance) * 0.5 * min(1.0, 100000 / max(volume, 1))
        )

        # Ensure components sum to total spread
        total_components = order_processing + inventory_holding + adverse_selection
        if total_components > 0:
            scaling_factor = spread_bps / total_components
            order_processing *= scaling_factor
            inventory_holding *= scaling_factor
            adverse_selection *= scaling_factor
        else:
            order_processing = spread_bps * 0.5
            inventory_holding = spread_bps * 0.3
            adverse_selection = spread_bps * 0.2

        # Determine dominant component
        components = {
            SpreadComponent.ORDER_PROCESSING: order_processing,
            SpreadComponent.INVENTORY_HOLDING: inventory_holding,
            SpreadComponent.ADVERSE_SELECTION: adverse_selection,
        }
        dominant = max(components, key=components.get)

        return SpreadDecomposition(
            timestamp=datetime.now(),
            total_spread_bps=spread_bps,
            order_processing_bps=order_processing,
            inventory_holding_bps=inventory_holding,
            adverse_selection_bps=adverse_selection,
            dominant_component=dominant,
        )

    def calculate_effective_spread(
        self,
        execution_price: float,
        bid_price: float,
        ask_price: float,
        side: str,
    ) -> float:
        """
        Calculate effective spread for a trade

        Effective spread measures actual execution cost relative to midpoint

        Args:
            execution_price: Price at which trade was executed
            bid_price: Best bid at execution time
            ask_price: Best ask at execution time
            side: Trade side ('BUY' or 'SELL')

        Returns:
            Effective spread in bps
        """
        midpoint = (bid_price + ask_price) / 2

        if side.upper() == 'BUY':
            # Buyer pays more than midpoint
            effective_spread = 2 * (execution_price - midpoint) / midpoint
        else:
            # Seller receives less than midpoint
            effective_spread = 2 * (midpoint - execution_price) / midpoint

        return effective_spread * 10000  # Convert to bps

    def measure_market_resilience(
        self,
        price_history: pd.DataFrame,
        shock_times: list[datetime],
        recovery_window_seconds: int = 60,
    ) -> float:
        """
        Measure market resilience (speed of recovery from shocks)

        Resilience is how quickly prices return to equilibrium after a shock
        (O'Hara 5.4)

        Args:
            price_history: Price history with timestamps
            shock_times: List of times when shocks occurred
            recovery_window_seconds: Window to measure recovery

        Returns:
            Resilience score (higher = faster recovery)
        """
        if price_history.empty or not shock_times:
            return 0.0

        recovery_times = []

        for shock_time in shock_times:
            # Find price at shock
            shock_prices = price_history[price_history.index == shock_time]['close']

            if shock_prices.empty:
                continue

            shock_prices.iloc[0]

            # Find recovery time (return to pre-shock level or within 1%)
            pre_shock_window = price_history[
                (price_history.index >= shock_time - timedelta(seconds=30))
                & (price_history.index < shock_time)
            ]

            if pre_shock_window.empty:
                continue

            reference_price = pre_shock_window['close'].mean()
            target_price = reference_price * 0.99  # Allow 1% tolerance

            # Search for recovery
            recovery_window = price_history[
                (price_history.index > shock_time)
                & (price_history.index <= shock_time + timedelta(seconds=recovery_window_seconds))
            ]

            if recovery_window.empty:
                continue

            # Check if recovered
            recovered = recovery_window[recovery_window['close'] >= target_price]

            if not recovered.empty:
                recovery_time = (recovered.index[0] - shock_time).total_seconds()
                recovery_times.append(recovery_time)

        if not recovery_times:
            return 0.0

        # Resilience score: faster recovery = higher score
        avg_recovery_time = np.mean(recovery_times)
        resilience_score = max(0, min(100, 100 - avg_recovery_time))

        return resilience_score

    def assess_liquidity_risk(
        self,
        required_size: Decimal,
        available_depth: Decimal,
        volatility: float,
        average_daily_volume: float,
        urgency: str = 'NORMAL',
    ) -> LiquidityRisk:
        """
        Assess liquidity risk for a trade

        Args:
            required_size: Size needed to trade
            available_depth: Available depth in order book
            volatility: Price volatility
            average_daily_volume: Average daily volume
            urgency: Trade urgency (LOW/NORMAL/HIGH)

        Returns:
            LiquidityRisk with assessment
        """
        timestamp = datetime.now()

        # Liquidity gap
        liquidity_gap = max(Decimal('0'), required_size - available_depth)

        # Execution shortfall risk
        # Probability of not executing at desired price
        depth_ratio = float(available_depth / max(required_size, Decimal('1')))
        shortfall_risk = max(0, min(1, 1 - depth_ratio))

        # Adjust for volatility
        shortfall_risk *= 1 + volatility * 10

        # Market impact estimate (Almgren-Chriss style)
        participation_rate = float(required_size / max(average_daily_volume, 1))
        market_impact = volatility * np.sqrt(participation_rate) * 10000

        # Determine risk level
        if shortfall_risk > 0.5 or liquidity_gap > required_size * Decimal('0.5'):
            risk_level = 'HIGH'
        elif shortfall_risk > 0.2 or liquidity_gap > required_size * Decimal('0.2'):
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Generate recommendations
        recommendations = []

        if risk_level == 'HIGH':
            recommendations.append(
                "Significant liquidity gap - reduce order size or use algorithmic execution"
            )
            recommendations.append("Consider executing over multiple days")

        if urgency == 'HIGH' and risk_level != 'LOW':
            recommendations.append("High urgency with liquidity risk - expect significant slippage")

        if market_impact > 50:  # More than 50 bps
            recommendations.append(f"High expected market impact ({market_impact:.1f} bps)")

        if volatility > 0.03:
            recommendations.append("High volatility - consider waiting for better conditions")

        return LiquidityRisk(
            timestamp=timestamp,
            liquidity_gap=liquidity_gap,
            execution_shortfall_risk=shortfall_risk,
            market_impact_estimate=market_impact,
            risk_level=risk_level,
            recommendations=list(recommendations),
        )

    def calculate_liquidity_metrics(
        self,
        symbol: str,
        order_book: dict[str, list[tuple[Decimal, Decimal]]],
        price_history: pd.DataFrame,
        volume: float,
        target_size: Decimal | None = None,
    ) -> LiquidityMetrics:
        """
        Calculate comprehensive liquidity metrics

        Args:
            symbol: Trading symbol
            order_book: Current order book
            price_history: Price history
            volume: Current volume
            target_size: Target size for effective spread

        Returns:
            LiquidityMetrics with complete analysis
        """
        timestamp = datetime.now()

        # Get best bid and ask
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])

        if not bids or not asks:
            # Default values if no book data
            return LiquidityMetrics(
                timestamp=timestamp,
                bid_ask_spread_bps=0.0,
                quoted_depth=Decimal('0'),
                effective_spread_bps=0.0,
                depth_slope=0.0,
                liquidity_score=0.0,
                liquidity_regime='UNKNOWN',
            )

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        midpoint = (best_bid + best_ask) / 2

        # Calculate spread in bps
        spread_bps = (best_ask - best_bid) / midpoint * 10000

        # Calculate quoted depth
        quoted_depth = sum(size for _, size in bids[:5]) + sum(size for _, size in asks[:5])

        # Calculate effective spread for target size
        if target_size:
            effective_spread = self._calculate_effective_spread_for_size(
                order_book, target_size, midpoint
            )
        else:
            effective_spread = spread_bps

        # Calculate depth slope
        depth_slope = self._calculate_depth_slope(order_book)

        # Calculate volatility
        if len(price_history) >= 20:
            returns = price_history['close'].pct_change().dropna()
            volatility = returns.tail(20).std()
        else:
            config = get_config()
            volatility = getattr(
                config.market_microstructure, 'default_volatility', 0.02
            )  # Default from config

        # Calculate composite liquidity score
        liquidity_score = self.calculate_liquidity_score(
            spread_bps=spread_bps,
            depth=quoted_depth,
            volatility=volatility,
            volume=volume,
        )

        # Classify regime
        regime = self.classify_liquidity_regime(liquidity_score)

        metrics = LiquidityMetrics(
            timestamp=timestamp,
            bid_ask_spread_bps=spread_bps,
            quoted_depth=quoted_depth,
            effective_spread_bps=effective_spread,
            depth_slope=depth_slope,
            liquidity_score=liquidity_score,
            liquidity_regime=regime,
        )

        # Store in history
        self._historical_metrics.append(metrics)
        if len(self._historical_metrics) > self.lookback_periods:
            self._historical_metrics.pop(0)

        return metrics

    def _calculate_effective_spread_for_size(
        self,
        order_book: dict[str, list[tuple[Decimal, Decimal]]],
        target_size: Decimal,
        midpoint: float,
    ) -> float:
        """Calculate effective spread for executing target_size"""
        order_book.get('bids', [])
        asks = order_book.get('asks', [])

        # For buys, walk through ask side
        remaining_size = target_size
        total_cost = Decimal('0')

        for price, size in asks:
            if remaining_size <= 0:
                break

            fill_size = min(size, remaining_size)
            total_cost += price * fill_size
            remaining_size -= fill_size

        if target_size > 0:
            avg_price = float(total_cost / target_size)
            effective_spread = 2 * (avg_price - midpoint) / midpoint * 10000
        else:
            effective_spread = 0.0

        return effective_spread

    def _calculate_depth_slope(
        self,
        order_book: Dict[str, List[Tuple[Decimal, Decimal]]],
    ) -> float:
        """
        Calculate order book depth slope

        Steeper slope = less liquidity at better prices
        """
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])

        if len(bids) < 2 or len(asks) < 2:
            return 0.0

        # Calculate slope on ask side
        ask_prices = [float(p) for p, _ in asks[:5]]
        ask_volumes = [float(v) for _, v in asks[:5]]

        # Normalize volumes relative to best level
        if ask_volumes[0] > 0:
            relative_volumes = [v / ask_volumes[0] for v in ask_volumes]
        else:
            relative_volumes = ask_volumes

        # Linear regression of volume vs price level
        if len(ask_prices) >= 2:
            slope, _ = np.polyfit(range(len(ask_prices)), relative_volumes, 1)
            return float(slope)
        else:
            return 0.0

    def get_liquidity_trend(self) -> str:
        """
        Get liquidity trend based on historical metrics

        Returns:
            Trend direction ('IMPROVING', 'STABLE', 'DETERIORATING')
        """
        if len(self._historical_metrics) < 5:
            return 'UNKNOWN'

        recent_scores = [m.liquidity_score for m in self._historical_metrics[-5:]]
        older_scores = [m.liquidity_score for m in self._historical_metrics[:-5]]

        if not older_scores:
            return 'STABLE'

        recent_avg = np.mean(recent_scores)
        older_avg = np.mean(older_scores)

        change = (recent_avg - older_avg) / max(older_avg, 1)

        if change > 0.05:
            return 'IMPROVING'
        elif change < -0.05:
            return 'DETERIORATING'
        else:
            return 'STABLE'

    def generate_liquidity_report(
        self,
        symbol: str,
        order_book: dict[str, list[tuple[Decimal, Decimal]]],
        price_history: pd.DataFrame,
        volume: float,
        required_size: Decimal | None = None,
    ) -> dict:
        """
        Generate comprehensive liquidity report

        Args:
            symbol: Trading symbol
            order_book: Current order book
            price_history: Price history
            volume: Trading volume
            required_size: Size to assess risk for

        Returns:
            Dictionary with complete liquidity analysis
        """
        # Calculate metrics
        metrics = self.calculate_liquidity_metrics(
            symbol, order_book, price_history, volume, required_size
        )

        # Measure depth
        depth_profile = self.measure_market_depth(order_book, required_size)

        # Decompose spread
        config = get_config()
        default_vol = getattr(config.market_microstructure, 'default_volatility', 0.02)
        spread_decomp = self.decompose_spread(
            spread_bps=metrics.bid_ask_spread_bps,
            price_variance=(
                price_history['close'].pct_change().var() if len(price_history) > 1 else 0.0001
            ),
            order_flow_imbalance=depth_profile.imbalance_ratio,
            volume=volume,
            volatility=(
                price_history['close'].pct_change().std() if len(price_history) > 1 else default_vol
            ),
        )

        # Assess liquidity risk
        risk = self.assess_liquidity_risk(
            required_size=required_size or Decimal('1000'),
            available_depth=metrics.quoted_depth,
            volatility=(
                price_history['close'].pct_change().std() if len(price_history) > 1 else default_vol
            ),
            average_daily_volume=volume,
        )

        # Get trend
        trend = self.get_liquidity_trend()

        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics.to_dict(),
            'depth_profile': depth_profile.to_dict(),
            'spread_decomposition': spread_decomp.to_dict(),
            'liquidity_risk': risk.to_dict(),
            'trend': trend,
            'recommendations': self._generate_liquidity_recommendations(
                metrics, spread_decomp, risk
            ),
        }

    def _generate_liquidity_recommendations(
        self,
        metrics: LiquidityMetrics,
        spread_decomp: SpreadDecomposition,
        risk: LiquidityRisk,
    ) -> list[str]:
        """Generate trading recommendations based on liquidity analysis"""
        recommendations = []

        # Regime-based recommendations
        if metrics.liquidity_regime == 'POOR':
            recommendations.append("POOR liquidity - avoid trading or use extreme caution")
        elif metrics.liquidity_regime == 'LOW':
            recommendations.append("LOW liquidity - reduce order sizes")

        # Spread component recommendations
        if spread_decomp.dominant_component == SpreadComponent.ADVERSE_SELECTION:
            recommendations.append("High adverse selection - use limit orders")
        elif spread_decomp.dominant_component == SpreadComponent.INVENTORY_HOLDING:
            recommendations.append("High inventory risk - consider splitting orders")

        # Risk-based recommendations
        recommendations.extend(risk.recommendations)

        # Effective spread recommendations
        if metrics.effective_spread_bps > metrics.bid_ask_spread_bps * 2:
            recommendations.append("High effective spread - consider smaller orders")

        if not recommendations:
            recommendations.append("Normal liquidity conditions")

        return recommendations


class LiquidityMonitor:
    """
    Monitors liquidity conditions in real-time

    Tracks liquidity across multiple dimensions and alerts on degradation
    """

    def __init__(
        self,
        liquidity_threshold: float = 50.0,
        alert_window_minutes: int = 5,
    ):
        """
        Initialize liquidity monitor

        Args:
            liquidity_threshold: Alert threshold for liquidity score
            alert_window_minutes: Time window for trend analysis
        """
        self.liquidity_threshold = liquidity_threshold
        self.alert_window_minutes = alert_window_minutes
        self._alerts: list[dict] = []

    def check_liquidity_alert(
        self,
        current_metrics: LiquidityMetrics,
    ) -> dict | None:
        """
        Check if liquidity alert should be triggered

        Args:
            current_metrics: Current liquidity metrics

        Returns:
            Alert dictionary or None if no alert
        """
        alerts = []
        config = get_config()
        wide_spread_threshold = getattr(config.market_microstructure, 'wide_spread_bps', 10.0)

        # Low liquidity score alert
        if current_metrics.liquidity_score < self.liquidity_threshold:
            alerts.append(
                {
                    'type': 'LOW_LIQUIDITY',
                    'severity': 'HIGH' if current_metrics.liquidity_score < 30 else 'MEDIUM',
                    'message': f"Liquidity score ({current_metrics.liquidity_score:.1f}) below threshold ({self.liquidity_threshold})",
                    'timestamp': datetime.now().isoformat(),
                }
            )

        # Wide spread alert
        if current_metrics.bid_ask_spread_bps > wide_spread_threshold:
            alerts.append(
                {
                    'type': 'WIDE_SPREAD',
                    'severity': 'MEDIUM',
                    'message': f"Bid-ask spread ({current_metrics.bid_ask_spread_bps:.2f} bps) unusually wide",
                    'timestamp': datetime.now().isoformat(),
                }
            )

        # Store alerts
        self._alerts.extend(alerts)

        return alerts[0] if alerts else None


# Singleton instances
_liquidity_analyzer: LiquidityAnalyzer | None = None
_liquidity_monitor: LiquidityMonitor | None = None


def get_liquidity_analyzer(
    lookback_periods: int = 20,
    depth_levels: int = 5,
) -> LiquidityAnalyzer:
    """Get or create singleton LiquidityAnalyzer instance"""
    global _liquidity_analyzer
    if _liquidity_analyzer is None:
        _liquidity_analyzer = LiquidityAnalyzer(
            lookback_periods=lookback_periods,
            depth_levels=depth_levels,
        )
    return _liquidity_analyzer


def get_liquidity_monitor(
    liquidity_threshold: float = 50.0,
    alert_window_minutes: int = 5,
) -> LiquidityMonitor:
    """Get or create singleton LiquidityMonitor instance"""
    global _liquidity_monitor
    if _liquidity_monitor is None:
        _liquidity_monitor = LiquidityMonitor(
            liquidity_threshold=liquidity_threshold,
            alert_window_minutes=alert_window_minutes,
        )
    return _liquidity_monitor


__all__ = [
    "LiquidityDimension",
    "SpreadComponent",
    "LiquidityMetrics",
    "SpreadDecomposition",
    "DepthProfile",
    "LiquidityRisk",
    "LiquidityAnalyzer",
    "LiquidityMonitor",
    "get_liquidity_analyzer",
    "get_liquidity_monitor",
]
