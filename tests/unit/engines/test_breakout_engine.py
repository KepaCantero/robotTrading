"""
Unit tests for BreakoutStrategyEngine.

Estos tests usan datos sintéticos sencillos y un portfolio dummy para
verificar la lógica principal sin depender de datos históricos reales.
"""

from decimal import Decimal
from datetime import datetime

import pytest

from app.engines.strategy_engines import BreakoutStrategyEngine
from app.models.market_data import Quote
from app.models.portfolio import AssetClass, Position, Portfolio


class DummyPortfolio:
    """Portfolio dummy minimal para probar risk_check sin depender de Portfolio real."""

    def __init__(self, exposure: float = 0.0):
        self._exposure = exposure

    def get_total_exposure(self) -> float:
        return self._exposure


def make_quote(price: float, high: float = None, low: float = None, volume: float = 1_000_000) -> Quote:
    """Helper para crear Quote sencillo."""
    high_val = high if high is not None else price
    low_val = low if low is not None else price
    return Quote(
        symbol="TEST",
        timestamp=datetime.utcnow(),
        bid=Decimal(str(price)),
        ask=Decimal(str(price)),
        last=Decimal(str(price)),
        close=Decimal(str(price)),
        open=Decimal(str(price)),
        high=Decimal(str(high_val)),
        low=Decimal(str(low_val)),
        volume=Decimal(str(volume)),
    )


class TestBreakoutStrategyEngineUnit:
    """Unit tests básicos para BreakoutStrategyEngine."""

    def test_breakout_engine_initialization_defaults(self):
        """El engine se inicializa con parámetros por defecto razonables."""
        engine = BreakoutStrategyEngine({})

        assert engine.get_strategy_type() == "breakout"
        assert engine.lookback_period == 20
        assert engine.breakout_threshold_pct == Decimal("0.01")
        assert engine.min_volume_ratio == Decimal("1.5")
        assert engine.max_exposure == Decimal("0.60")
        assert engine.min_signal_confidence == 60.0
        # Learning deshabilitado por defecto
        assert not engine.learning_enabled

    def test_breakout_engine_no_signal_without_breakout(self):
        """No debe generar señales si el precio no rompe el rango."""
        config = {
            "lookback_period": 5,
            "breakout_threshold_pct": 0.01,
            "min_volume_ratio": 1.0,
        }
        engine = BreakoutStrategyEngine(config)

        # Precios dentro de un rango estrecho sin breakout
        prices = [100, 101, 99, 100.5, 100.2]
        for p in prices:
            quote = make_quote(price=p, high=p, low=p, volume=1_000_000)
            engine.generate_signals(quote)

        # Otro punto dentro del rango
        quote = make_quote(price=100.3, high=100.5, low=99.5, volume=1_200_000)
        signals = engine.generate_signals(quote)

        assert signals == []

    def test_breakout_engine_generates_buy_signal_on_up_breakout(self):
        """Genera señal BUY cuando hay breakout alcista con volumen suficiente."""
        config = {
            "lookback_period": 5,
            "breakout_threshold_pct": 0.01,  # 1%
            "min_volume_ratio": 1.0,
        }
        engine = BreakoutStrategyEngine(config)

        # Rango reciente ~ [99, 101]
        base_prices = [100, 101, 100.5, 99.5, 100.2]
        for p in base_prices:
            quote = make_quote(price=p, high=p, low=p, volume=1_000_000)
            engine.generate_signals(quote)

        # Breakout alcista: precio por encima del máximo * (1 + threshold)
        breakout_price = 102.5  # suficiente por encima de 101 * 1.01 ≈ 102.01
        breakout_quote = make_quote(
            price=breakout_price,
            high=breakout_price,
            low=101.5,
            volume=2_000_000,  # volumen alto para volume_ratio >= 1
        )

        signals = engine.generate_signals(breakout_quote)

        assert len(signals) == 1
        signal = signals[0]
        assert signal.signal_type == "buy"
        assert signal.metadata.get("breakout_direction") == "up"
        assert signal.metadata.get("breakout_level") is not None
        assert signal.confidence >= 60.0  # debería ser una señal razonablemente fuerte

    def test_breakout_engine_risk_check_respects_exposure_and_confidence(self):
        """risk_check debe filtrar por exposición y confianza mínima."""
        engine = BreakoutStrategyEngine(
            {
                "max_exposure": 0.50,
                "min_signal_confidence": 70.0,
            }
        )

        # Señal con alta confianza
        quote = make_quote(price=100.0)
        signals = engine._generate_signals_impl(quote)
        # Si _generate_signals_impl no genera nada (por falta de histórico),
        # creamos una señal sintética para probar solo risk_check.
        from app.models.signal import Signal, SignalStrength, SignalSource

        if not signals:
            signal = Signal(
                symbol="TEST",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=80.0,
                priority_score=80.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("100"),
                volume=Decimal("1"),
                timestamp=datetime.utcnow(),
                metadata={},
            )
        else:
            signal = signals[0]

        # Portfolio con baja exposición
        low_exposure_portfolio = DummyPortfolio(exposure=0.20)
        assert engine.risk_check(signal, low_exposure_portfolio) is True

        # Portfolio con exposición alta
        high_exposure_portfolio = DummyPortfolio(exposure=0.80)
        assert engine.risk_check(signal, high_exposure_portfolio) is False

        # Señal con confianza baja
        low_conf_signal = signal.model_copy(update={"confidence": 50.0})
        assert engine.risk_check(low_conf_signal, low_exposure_portfolio) is False


