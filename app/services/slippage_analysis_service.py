"""
Dynamic Slippage Analysis Service
TASK-11: Análisis Dinámico de Slippage

Servicio para calcular slippage dinámico basado en volatilidad del mercado y liquidez.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)

from app.domain.models.slippage_analysis import (
    DynamicSlippageAnalysis,
    LiquidityMetrics,
    MarketCondition,
    OrderSizeImpact,
    SlippageCalculationParams,
    SlippageComponent,
    SlippageHistory,
    SlippageType,
    VolatilityMetrics,
)
from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote


class VolatilityCalculator:
    """Calculadora de volatilidad del mercado."""

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        # Load trading thresholds for volatility trend thresholds
        self._tt = get_config().trading_thresholds

    def calculate_volatility(self, price_history: list[Decimal]) -> VolatilityMetrics:
        """Calcular métricas de volatilidad."""
        logger.debug(
            "Calculating volatility metrics", extra={"price_history_length": len(price_history)}
        )
        if len(price_history) < 2:
            logger.error(
                "Insufficient price history for volatility calculation",
                extra={"price_history_length": len(price_history)},
            )
            raise ValueError("Insufficient price history for volatility calculation")

        # Convertir a numpy para cálculos
        prices = np.array([float(p) for p in price_history])

        # Calcular returns
        returns = np.diff(np.log(prices))

        # Volatilidad actual (últimos 5 días) - use config values
        recent_returns = returns[-5:] if len(returns) >= 5 else returns
        tt = get_config().trading_thresholds
        current_volatility = Decimal(
            str(np.std(recent_returns) * np.sqrt(tt.annual_trading_days) * tt.percentage_multiplier)
        )

        # Volatilidad histórica (todo el período)
        historical_volatility = Decimal(
            str(np.std(returns) * np.sqrt(tt.annual_trading_days) * tt.percentage_multiplier)
        )

        # Percentil de volatilidad
        volatility_percentile = self._calculate_percentile(
            current_volatility, historical_volatility
        )

        # Tendencia de volatilidad
        volatility_trend = self._calculate_trend(returns)

        # Regimen de volatilidad
        volatility_regime = self._determine_volatility_regime(current_volatility)

        logger.debug(
            "Volatility metrics calculated",
            extra={
                "current_volatility": float(current_volatility),
                "historical_volatility": float(historical_volatility),
                "regime": str(volatility_regime.value),
            },
        )
        return VolatilityMetrics(
            current_volatility=current_volatility,
            historical_volatility=historical_volatility,
            volatility_percentile=volatility_percentile,
            volatility_trend=volatility_trend,
            volatility_regime=volatility_regime,
        )

    def _calculate_percentile(self, current: Decimal, historical: Decimal) -> float:
        """Calcular percentil de volatilidad actual."""
        if historical == 0:
            return 50.0
        tt = get_config().trading_thresholds
        return float((current / historical) * tt.percentage_multiplier)

    def _calculate_trend(self, returns: np.ndarray) -> str:
        """Calcular tendencia de volatilidad - use config thresholds."""
        if len(returns) < 10:
            return "insufficient_data"

        # Calcular volatilidad móvil
        window_size = min(10, len(returns) // 2)
        recent_vol = np.std(returns[-window_size:])
        previous_vol = np.std(returns[-window_size * 2 : -window_size])

        if recent_vol > previous_vol * self._tt.volatility_trend_increasing_threshold:
            return "increasing"
        elif recent_vol < previous_vol * self._tt.volatility_trend_decreasing_threshold:
            return "decreasing"
        else:
            return "stable"

    def _determine_volatility_regime(self, volatility: Decimal) -> MarketCondition:
        """Determinar régimen de volatilidad."""
        config = get_config()
        high_threshold = config.trading.volatility_threshold_high
        extreme_threshold = config.trading.volatility_threshold_extreme

        if volatility >= extreme_threshold:
            return MarketCondition.EXTREME_EVENTS
        elif volatility >= high_threshold:
            return MarketCondition.HIGH_VOLATILITY
        else:
            return MarketCondition.NORMAL


class LiquidityCalculator:
    """Calculadora de liquidez del mercado."""

    def __init__(self):
        # Load trading thresholds for liquidity calculation
        self._tt = get_config().trading_thresholds

    def calculate_liquidity(
        self, quote: Quote, volume_24h: Decimal, order_book_depth: Decimal
    ) -> LiquidityMetrics:
        """Calcular métricas de liquidez."""
        logger.debug(
            "Calculating liquidity metrics",
            extra={"symbol": quote.symbol, "volume_24h": str(volume_24h)},
        )
        # Calcular spread bid-ask
        if quote.bid and quote.ask and quote.bid > 0:
            spread = ((quote.ask - quote.bid) / quote.bid) * Decimal("100")
        else:
            spread = Decimal("1.0")  # Spread por defecto

        # Calcular score de liquidez
        liquidity_score = self._calculate_liquidity_score(spread, volume_24h, order_book_depth)

        # Determinar régimen de liquidez
        liquidity_regime = self._determine_liquidity_regime(liquidity_score, spread)

        logger.debug(
            "Liquidity metrics calculated",
            extra={
                "spread": float(spread),
                "liquidity_score": liquidity_score,
                "regime": str(liquidity_regime.value),
            },
        )
        return LiquidityMetrics(
            bid_ask_spread=spread,
            volume_24h=volume_24h,
            order_book_depth=order_book_depth,
            liquidity_score=liquidity_score,
            liquidity_regime=liquidity_regime,
        )

    def _calculate_liquidity_score(self, spread: Decimal, volume: Decimal, depth: Decimal) -> float:
        """Calcular score de liquidez (0-1) - use config values."""
        # Normalizar spread (menor es mejor) - use config
        spread_score = max(0, 1 - float(spread) / self._tt.liquidity_max_spread_percent)

        # Normalizar volumen (mayor es mejor) - use config
        volume_score = min(1.0, float(volume) / self._tt.liquidity_volume_normalization)

        # Normalizar profundidad (mayor es mejor) - use config
        depth_score = min(1.0, float(depth) / self._tt.liquidity_depth_normalization)

        # Score combinado con pesos - use config weights
        return float(
            spread_score * self._tt.liquidity_spread_weight
            + volume_score * self._tt.liquidity_volume_weight
            + depth_score * self._tt.liquidity_depth_weight
        )

    def _determine_liquidity_regime(
        self, liquidity_score: float, spread: Decimal
    ) -> MarketCondition:
        """Determinar régimen de liquidez - use config multiplier."""
        config = get_config()
        min_liquidity = config.trading.min_liquidity_score
        max_spread = config.trading.max_spread_threshold

        if liquidity_score < min_liquidity or spread > max_spread:
            return MarketCondition.LOW_LIQUIDITY
        elif liquidity_score < min_liquidity * self._tt.liquidity_stress_multiplier:
            return MarketCondition.MARKET_STRESS
        else:
            return MarketCondition.NORMAL


class OrderSizeCalculator:
    """Calculadora de impacto del tamaño de orden."""

    def __init__(self):
        # Load trading thresholds for order size thresholds
        self._tt = get_config().trading_thresholds

    def calculate_order_impact(
        self, order_size: Decimal, market_cap: Decimal, current_price: Decimal
    ) -> OrderSizeImpact:
        """Calcular impacto del tamaño de orden."""
        logger.debug(
            "Calculating order impact",
            extra={"order_size": str(order_size), "market_cap": str(market_cap)},
        )
        # Calcular ratio orden/capitalización
        market_cap_ratio = order_size / market_cap if market_cap > 0 else Decimal("0")

        # Calcular multiplicador de impacto
        impact_multiplier = self._calculate_impact_multiplier(market_cap_ratio)

        logger.debug(
            "Order impact calculated",
            extra={
                "market_cap_ratio": float(market_cap_ratio),
                "impact_multiplier": impact_multiplier,
            },
        )
        return OrderSizeImpact(
            order_size=order_size,
            market_cap_ratio=market_cap_ratio,
            impact_multiplier=impact_multiplier,
        )

    def _calculate_impact_multiplier(self, market_cap_ratio: Decimal) -> float:
        """Calcular multiplicador de impacto basado en el ratio - use config thresholds."""
        # Función exponencial para capturar impacto no lineal - use config
        ratio = float(market_cap_ratio)
        if ratio <= self._tt.order_size_tiny_threshold:
            return 1.0
        elif ratio <= self._tt.order_size_small_threshold:
            return float(1.0 + ratio * self._tt.order_size_small_multiplier)
        else:
            return float(1.0 + ratio * self._tt.order_size_large_multiplier)


class DynamicSlippageService:
    """Servicio principal para análisis de slippage dinámico."""

    def __init__(self, params: SlippageCalculationParams | None = None):
        logger.debug("Initializing DynamicSlippageService")
        self.params = params or SlippageCalculationParams()
        self.volatility_calculator = VolatilityCalculator(self.params.volatility_lookback_days)
        self.liquidity_calculator = LiquidityCalculator()
        self.order_size_calculator = OrderSizeCalculator()
        self.slippage_history: dict[str, SlippageHistory] = {}
        logger.info(
            "DynamicSlippageService initialized",
            extra={"volatility_lookback_days": self.params.volatility_lookback_days},
        )

    def calculate_dynamic_slippage(
        self,
        asset_symbol: str,
        base_price: Decimal,
        order_side: str,
        order_size: Decimal,
        quote: Quote,
        price_history: list[Decimal],
        volume_24h: Decimal,
        order_book_depth: Decimal,
        market_cap: Decimal,
    ) -> DynamicSlippageAnalysis:
        """Calcular slippage dinámico completo."""
        logger.debug(
            "calculate_dynamic_slippage called",
            extra={
                "asset_symbol": asset_symbol,
                "order_side": order_side,
                "order_size": str(order_size),
            },
        )

        # Calcular métricas de entrada
        volatility_metrics = self.volatility_calculator.calculate_volatility(price_history)
        liquidity_metrics = self.liquidity_calculator.calculate_liquidity(
            quote, volume_24h, order_book_depth
        )
        order_size_impact = self.order_size_calculator.calculate_order_impact(
            order_size, market_cap, base_price
        )

        # Calcular componentes de slippage
        slippage_components = self._calculate_slippage_components(
            volatility_metrics, liquidity_metrics, order_size_impact
        )

        # Calcular slippage total
        total_slippage = self._calculate_total_slippage(slippage_components)

        # Determinar condición del mercado
        market_condition = self._determine_market_condition(volatility_metrics, liquidity_metrics)

        # Calcular confianza
        confidence = self._calculate_confidence(slippage_components)

        # Crear análisis
        analysis = DynamicSlippageAnalysis(
            asset_symbol=asset_symbol,
            base_price=base_price,
            order_side=order_side,
            order_size=order_size,
            volatility_metrics=volatility_metrics,
            liquidity_metrics=liquidity_metrics,
            order_size_impact=order_size_impact,
            slippage_components=slippage_components,
            total_slippage=total_slippage,
            slippage_confidence=confidence,
            market_condition=market_condition,
        )

        # Guardar en historial
        self._add_to_history(analysis)

        logger.info(
            "Dynamic slippage calculated",
            extra={
                "asset_symbol": asset_symbol,
                "total_slippage": float(total_slippage),
                "market_condition": str(market_condition.value),
                "confidence": confidence,
            },
        )
        return analysis

    def _calculate_slippage_components(
        self,
        volatility_metrics: VolatilityMetrics,
        liquidity_metrics: LiquidityMetrics,
        order_size_impact: OrderSizeImpact,
    ) -> list[SlippageComponent]:
        """Calcular componentes individuales de slippage."""
        components = []

        # 1. Market Impact (impacto del tamaño de orden)
        market_impact = self._calculate_market_impact(order_size_impact, liquidity_metrics)
        components.append(market_impact)

        # 2. Timing Delay (delay en ejecución)
        timing_delay = self._calculate_timing_delay(volatility_metrics)
        components.append(timing_delay)

        # 3. Liquidity Cost (costo de liquidez)
        liquidity_cost = self._calculate_liquidity_cost(liquidity_metrics)
        components.append(liquidity_cost)

        # 4. Volatility Adjustment (ajuste por volatilidad)
        volatility_adjustment = self._calculate_volatility_adjustment(volatility_metrics)
        components.append(volatility_adjustment)

        return components

    def _calculate_market_impact(
        self, order_size_impact: OrderSizeImpact, liquidity_metrics: LiquidityMetrics
    ) -> SlippageComponent:
        """Calcular impacto del mercado usando config."""
        # Get market stress threshold from config
        config = get_config()
        market_stress_threshold = Decimal(
            str(getattr(config.trading, "slippage_market_stress_threshold", 0.01))
        )

        base_impact = float(order_size_impact.market_cap_ratio) * 100
        liquidity_adjustment = 1 / max(0.1, liquidity_metrics.liquidity_score)
        impact_value = Decimal(str(base_impact * liquidity_adjustment))

        # Determinar condición del mercado basada en el impacto
        if order_size_impact.market_cap_ratio > market_stress_threshold:
            market_condition = MarketCondition.MARKET_STRESS
        else:
            market_condition = MarketCondition.NORMAL

        return SlippageComponent(
            slippage_type=SlippageType.MARKET_IMPACT,
            value=impact_value,
            confidence=0.8,
            market_condition=market_condition,
            calculation_method="market_impact_v1",
        )

    def _calculate_timing_delay(self, volatility_metrics: VolatilityMetrics) -> SlippageComponent:
        """Calcular delay de timing."""
        delay_value = Decimal(str(float(volatility_metrics.current_volatility) * 0.01))

        return SlippageComponent(
            slippage_type=SlippageType.TIMING_DELAY,
            value=delay_value,
            confidence=0.7,
            market_condition=volatility_metrics.volatility_regime,
            calculation_method="timing_delay_v1",
        )

    def _calculate_liquidity_cost(self, liquidity_metrics: LiquidityMetrics) -> SlippageComponent:
        """Calcular costo de liquidez."""
        cost_value = liquidity_metrics.bid_ask_spread / Decimal("2")  # Mitad del spread

        return SlippageComponent(
            slippage_type=SlippageType.LIQUIDITY_COST,
            value=cost_value,
            confidence=0.9,
            market_condition=liquidity_metrics.liquidity_regime,
            calculation_method="liquidity_cost_v1",
        )

    def _calculate_volatility_adjustment(
        self, volatility_metrics: VolatilityMetrics
    ) -> SlippageComponent:
        """Calcular ajuste por volatilidad usando config."""
        # Get volatility adjustment factors from config
        config = get_config()
        adj_extreme = Decimal(str(getattr(config.trading, "slippage_vol_adjustment_extreme", 2.0)))
        adj_high = Decimal(str(getattr(config.trading, "slippage_vol_adjustment_high", 1.0)))
        adj_normal = Decimal(str(getattr(config.trading, "slippage_vol_adjustment_normal", 0.2)))

        if volatility_metrics.volatility_regime == MarketCondition.EXTREME_EVENTS:
            adjustment = adj_extreme
        elif volatility_metrics.volatility_regime == MarketCondition.HIGH_VOLATILITY:
            adjustment = adj_high
        else:
            adjustment = adj_normal

        return SlippageComponent(
            slippage_type=SlippageType.VOLATILITY_ADJUSTMENT,
            value=adjustment,
            confidence=0.6,
            market_condition=volatility_metrics.volatility_regime,
            calculation_method="volatility_adjustment_v1",
        )

    def _calculate_total_slippage(self, components: list[SlippageComponent]) -> Decimal:
        """Calcular slippage total."""
        # Sumar componentes con pesos
        total = Decimal("0")
        weights = {
            SlippageType.MARKET_IMPACT: 0.4,
            SlippageType.TIMING_DELAY: 0.2,
            SlippageType.LIQUIDITY_COST: 0.3,
            SlippageType.VOLATILITY_ADJUSTMENT: 0.1,
        }

        for component in components:
            weight = weights.get(component.slippage_type, 0.1)
            total += component.value * Decimal(str(weight))

        # Aplicar slippage base
        base_slippage = self.params.base_slippage
        total += base_slippage

        return Decimal(total)

    def _determine_market_condition(
        self, volatility_metrics: VolatilityMetrics, liquidity_metrics: LiquidityMetrics
    ) -> MarketCondition:
        """Determinar condición general del mercado."""
        if (
            volatility_metrics.volatility_regime == MarketCondition.EXTREME_EVENTS
            or liquidity_metrics.liquidity_regime == MarketCondition.LOW_LIQUIDITY
        ):
            return MarketCondition.MARKET_STRESS
        elif (
            volatility_metrics.volatility_regime == MarketCondition.HIGH_VOLATILITY
            or liquidity_metrics.liquidity_regime == MarketCondition.MARKET_STRESS
        ):
            return MarketCondition.HIGH_VOLATILITY
        else:
            return MarketCondition.NORMAL

    def _calculate_confidence(self, components: list[SlippageComponent]) -> float:
        """Calcular confianza en el cálculo."""
        if not components:
            return 0.5

        # Promedio ponderado de confianzas
        total_confidence = sum(c.confidence for c in components)
        return float(total_confidence / len(components))

    def _add_to_history(self, analysis: DynamicSlippageAnalysis):
        """Agregar análisis al historial."""
        if analysis.asset_symbol not in self.slippage_history:
            self.slippage_history[analysis.asset_symbol] = SlippageHistory(
                asset_symbol=analysis.asset_symbol
            )

        self.slippage_history[analysis.asset_symbol].add_analysis(analysis)

    def get_slippage_history(self, asset_symbol: str) -> SlippageHistory | None:
        """Obtener historial de slippage para un activo."""
        logger.debug("Getting slippage history", extra={"asset_symbol": asset_symbol})
        return self.slippage_history.get(asset_symbol)

    def get_average_slippage(self, asset_symbol: str, days: int = 7) -> Decimal | None:
        """Obtener slippage promedio para un activo."""
        logger.debug("Getting average slippage", extra={"asset_symbol": asset_symbol, "days": days})
        history = self.get_slippage_history(asset_symbol)
        if history:
            raw_avg = history.get_average_slippage(days)
            avg_slippage: Decimal | None = Decimal(str(raw_avg)) if raw_avg is not None else None
            logger.debug(
                "Average slippage retrieved",
                extra={
                    "asset_symbol": asset_symbol,
                    "days": days,
                    "average_slippage": str(avg_slippage) if avg_slippage else None,
                },
            )
            return avg_slippage
        return None
