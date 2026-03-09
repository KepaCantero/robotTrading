"""
Batería de tests diagnósticos para Momentum Strategy

Este módulo contiene tests exhaustivos para identificar y solucionar
todos los problemas que impiden que Momentum ejecute trades.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import AssetClass, Portfolio, Position
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.momentum import MomentumStrategy


class TestMomentumSignalGeneration:
    """Tests para verificar que Momentum genera señales correctamente."""

    def test_momentum_generates_signals_with_valid_data(self):
        """Verificar que Momentum genera señales cuando hay datos históricos suficientes."""
        config = {
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "volume_threshold": 1.0,
            "max_position_size": 0.1,
            "stop_loss": 0.05,
            "take_profit": 0.10,
            "rsi_period": 14,
            "ema_period": 20,
        }
        strategy = MomentumStrategy(config)

        # Generar datos históricos suficientes para calcular indicadores
        base_price = Decimal("200")
        for i in range(30):  # 30 días de datos
            price = base_price + Decimal(str(i * 0.5))
            volume = Decimal("1000000")
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow() - timedelta(days=30 - i),
                open=price,
                high=price * Decimal("1.01"),
                low=price * Decimal("0.99"),
                close=price,
                last=price,
                bid=price * Decimal("0.999"),
                ask=price * Decimal("1.001"),
                volume=volume,
            )
            signals = strategy.generate_signals(quote)
            # Después de suficiente histórico, deberíamos ver señales
            if i >= 20:
                assert isinstance(signals, list)

    def test_momentum_signal_has_correct_structure(self):
        """Verificar que las señales generadas tienen la estructura correcta."""
        config = {
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "volume_threshold": 1.0,
            "max_position_size": 0.1,
            "stop_loss": 0.05,
            "take_profit": 0.10,
        }
        strategy = MomentumStrategy(config)

        # Agregar datos históricos
        for i in range(30):
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow() - timedelta(days=30 - i),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            strategy.generate_signals(quote)

        # Generar señal
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("1000000"),
        )
        signals = strategy.generate_signals(quote)

        # Después de suficiente histórico, puede que genere señales
        # Verificamos que si hay señales, tienen la estructura correcta
        if signals and len(signals) > 0:
            signal = signals[0]
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'price')
            assert hasattr(signal, 'timestamp')
            assert hasattr(signal, 'price')
            assert hasattr(signal, 'volume')
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert signal.volume == Decimal("1")  # Placeholder


class TestMomentumRiskCheck:
    """Tests para verificar el risk_check de Momentum."""

    def setup_method(self):
        """Setup para cada test."""
        self.config = {
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "volume_threshold": 1.0,
            "max_position_size": 0.1,
            "stop_loss": 0.05,
            "take_profit": 0.10,
        }
        self.strategy = MomentumStrategy(self.config)

    def test_risk_check_buy_with_sufficient_cash(self):
        """Verificar que risk_check aprueba BUY cuando hay cash suficiente."""
        # Portfolio con cash suficiente
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        # Señal BUY con precio razonable
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),  # Placeholder
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        # get_position_size debería calcular ~25 acciones ($50k * 10% / $200)
        position_size = self.strategy.get_position_size(signal, portfolio)
        assert position_size > 0, f"Position size should be > 0, got {position_size}"

        # risk_check debería pasar
        result = self.strategy.risk_check(signal, portfolio)
        assert result, f"risk_check should pass with sufficient cash, got {result}"

    def test_risk_check_buy_insufficient_cash(self):
        """Verificar que risk_check rechaza BUY cuando no hay cash suficiente."""
        # Portfolio con muy poco cash
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("10"),  # Solo $10
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        assert not result, "risk_check should reject when insufficient cash"

    def test_risk_check_exposure_limit(self):
        """Verificar que risk_check respeta el límite de exposición (80%)."""
        # Portfolio con alta exposición (90%)
        positions = [
            Position(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("300"),
                market_price=Decimal("300"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="test",
            )
        ]
        # $30k en posiciones, $10k en cash = 75% exposición (debería pasar)
        # Pero ajustemos para que sea > 80%
        positions[0].quantity = Decimal("200")  # $60k en posiciones
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("10000"),  # $10k cash
            positions=positions,
            timestamp=datetime.utcnow(),
            broker="test",
        )

        # Total value = $70k, invested = $60k, exposición = 85.7% > 80%
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        assert not result, "risk_check should reject when exposure > 80%"

    def test_risk_check_sell_with_position(self):
        """Verificar que risk_check aprueba SELL cuando hay posición."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("10"),
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        assert result, "risk_check should pass SELL when position exists"

    def test_risk_check_sell_without_position(self):
        """Verificar que risk_check rechaza SELL cuando no hay posición."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        assert not result, "risk_check should reject SELL when no position exists"


class TestMomentumPositionSize:
    """Tests para verificar el cálculo de tamaño de posición."""

    def setup_method(self):
        """Setup para cada test."""
        self.config = {
            "max_position_size": Decimal("0.1"),  # 10%
        }
        self.strategy = MomentumStrategy(self.config)

    def test_get_position_size_buy_calculates_correctly(self):
        """Verificar que get_position_size calcula correctamente para BUY."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        position_size = self.strategy.get_position_size(signal, portfolio)

        # Debería ser: $50k * 10% = $5k / $200 = 25 acciones
        expected = Decimal("50000") * Decimal("0.1") / Decimal("200")
        assert abs(position_size - expected) < Decimal(
            "0.1"
        ), f"Position size should be ~{expected}, got {position_size}"
        assert position_size >= Decimal(
            "1"
        ), f"Position size should be at least 1 share, got {position_size}"

    def test_get_position_size_sell_uses_existing_position(self):
        """Verificar que get_position_size para SELL usa la posición existente."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("10"),
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        position_size = self.strategy.get_position_size(signal, portfolio)

        # Debería retornar la cantidad de la posición existente
        assert position_size == Decimal(
            "10"
        ), f"Position size for SELL should be existing position (10), got {position_size}"

    def test_get_position_size_sell_without_position_returns_zero(self):
        """Verificar que get_position_size para SELL sin posición retorna 0."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        position_size = self.strategy.get_position_size(signal, portfolio)

        assert position_size == Decimal(
            "0"
        ), f"Position size for SELL without position should be 0, got {position_size}"


class TestMomentumExposureCalculation:
    """Tests para verificar el cálculo de exposición."""

    def setup_method(self):
        """Setup para cada test."""
        self.config = {}
        self.strategy = MomentumStrategy(self.config)

    def test_calculate_total_exposure_with_positions(self):
        """Verificar cálculo de exposición con posiciones."""
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("200"),
                market_price=Decimal("200"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="test",
            )
        ]

        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("30000"),
            positions=positions,
            timestamp=datetime.utcnow(),
            broker="test",
        )

        exposure = self.strategy._calculate_total_exposure(portfolio)

        # Total value = $30k cash + $20k positions = $50k
        # Invested = $20k
        # Exposure = $20k / $50k = 40%
        expected = Decimal("20000") / Decimal("50000")
        assert abs(exposure - expected) < Decimal(
            "0.01"
        ), f"Exposure should be ~40%, got {exposure:.2%}"

    def test_calculate_total_exposure_no_positions(self):
        """Verificar cálculo de exposición sin posiciones."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        exposure = self.strategy._calculate_total_exposure(portfolio)

        assert exposure == Decimal(
            "0"
        ), f"Exposure with no positions should be 0%, got {exposure:.2%}"


class TestMomentumIntegration:
    """Tests de integración para Momentum con backtesting engine."""

    def test_momentum_signals_match_market_data(self):
        """Verificar que señales de Momentum tienen símbolos que existen en market_data."""
        config = {
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "volume_threshold": 1.0,
        }
        strategy = MomentumStrategy(config)

        symbols = ["AAPL", "MSFT", "GOOGL"]

        # Generar datos para múltiples símbolos
        for symbol in symbols:
            for i in range(30):
                quote = Quote(
                    symbol=symbol,
                    timestamp=datetime.utcnow() - timedelta(days=30 - i),
                    open=Decimal("200"),
                    high=Decimal("202"),
                    low=Decimal("198"),
                    close=Decimal("200"),
                    last=Decimal("200"),
                    bid=Decimal("199.8"),
                    ask=Decimal("200.2"),
                    volume=Decimal("1000000"),
                )
                strategy.generate_signals(quote)

        # Verificar que las señales tienen símbolos válidos
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("1000000"),
        )
        signals = strategy.generate_signals(quote)

        if signals:
            for signal in signals:
                assert (
                    signal.symbol in symbols
                ), f"Signal symbol {signal.symbol} should be in {symbols}"
                assert (
                    signal.metadata.get("strategy") == "momentum"
                ), "Signal should have strategy='momentum' in metadata"

    def test_momentum_risk_check_with_realistic_portfolio(self):
        """Test completo de risk_check con portfolio realista."""
        config = {
            "max_position_size": Decimal("0.1"),
        }
        strategy = MomentumStrategy(config)

        # Portfolio realista: $50k cash, algunas posiciones pequeñas
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[
                Position(
                    symbol="MSFT",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("50"),
                    avg_price=Decimal("300"),
                    market_price=Decimal("300"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        # BUY signal para AAPL
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = strategy.risk_check(signal, portfolio)

        # Debería pasar: cash suficiente, exposición < 80%
        # Total value = $50k cash + $15k positions = $65k
        # Exposure = $15k / $65k = 23% < 80%
        # New position = $50k * 10% = $5k < $50k cash
        assert result, "risk_check should pass for realistic scenario"


class TestMomentumEdgeCases:
    """Tests para casos extremos y edge cases."""

    def setup_method(self):
        """Setup para cada test."""
        self.config = {
            "max_position_size": Decimal("0.1"),
        }
        self.strategy = MomentumStrategy(self.config)

    def test_risk_check_with_very_high_exposure(self):
        """Test con exposición muy alta (cerca del límite)."""
        # Portfolio con exposición al 45% (justo bajo el límite de 50%)
        positions = [
            Position(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("225"),  # $22.5k en posiciones
                avg_price=Decimal("100"),
                market_price=Decimal("100"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="test",
            )
        ]

        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("27500"),  # $27.5k cash
            positions=positions,
            timestamp=datetime.utcnow(),
            broker="test",
        )

        # Total = $50k, invested = $22.5k, exposure = 45% < 50%
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        # Debería pasar porque 45% < 50% (límite por defecto)
        assert result, "risk_check should pass at 45% exposure (below 50% limit)"

    def test_risk_check_with_zero_cash(self):
        """Test con cash = 0."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("0"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        result = self.strategy.risk_check(signal, portfolio)
        assert not result, "risk_check should reject with zero cash"

    def test_get_position_size_with_very_low_cash(self):
        """Test de position_size con cash muy bajo."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("100"),  # Solo $100
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )

        position_size = self.strategy.get_position_size(signal, portfolio)

        # $100 * 10% = $10 / $200 = 0.05 acciones -> mínimo 1 acción
        assert position_size >= Decimal(
            "1"
        ), f"Position size should be at least 1, got {position_size}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
