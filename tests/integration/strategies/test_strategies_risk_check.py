"""
Tests para verificar que risk_check funciona correctamente en todas las estrategias.

Problemas identificados:
- risk_check rechaza señales válidas
- risk_check no verifica correctamente posiciones para SELL
- Insufficient cash para BUY cuando debería haber suficiente
"""
import unittest
from datetime import datetime
from decimal import Decimal

from app.models.market_data import Quote
from app.models.portfolio import AssetClass, Portfolio, Position
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTradingStrategy


class TestStrategiesRiskCheck(unittest.TestCase):
    """Tests para verificar risk_check en estrategias."""

    def setUp(self):
        """Configurar estrategias para tests."""
        self.momentum = MomentumStrategy({"name": "momentum"})
        self.mean_reversion = MeanReversionStrategy({"name": "mean_reversion"})
        self.pairs_trading = PairsTradingStrategy(
            {"name": "pairs_trading", "pair_symbols": ["AAPL", "MSFT"]}
        )

    def _create_quote(self, symbol: str, price: Decimal, timestamp: datetime = None) -> Quote:
        """Crear Quote de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
        return Quote(
            symbol=symbol,
            timestamp=timestamp,
            open=price,
            high=price * Decimal("1.01"),
            low=price * Decimal("0.99"),
            close=price,
            last=price,
            bid=price * Decimal("0.999"),
            ask=price * Decimal("1.001"),
            volume=Decimal("1000000"),
        )

    def _create_portfolio(self, cash: Decimal, positions: list = None) -> Portfolio:
        """Crear Portfolio de prueba."""
        if positions is None:
            positions = []
        return Portfolio(
            portfolio_id="test",
            cash=cash,
            positions=positions,
            timestamp=datetime(2024, 1, 1),
            broker="test",
            currency="USD",
        )

    def _create_signal(
        self, symbol: str, signal_type: SignalType, price: Decimal, timestamp: datetime = None
    ) -> Signal:
        """Crear señal de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=price,
            timestamp=timestamp,
            volume=Decimal("1"),
            metadata={"strategy": "test"},
        )

    def test_momentum_buy_with_sufficient_cash_should_pass(self):
        """Test: BUY con suficiente cash debe pasar risk_check."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")  # Suficiente para comprar

        signal = self._create_signal(symbol, SignalType.BUY, price)
        portfolio = self._create_portfolio(cash)

        # Risk check debe pasar
        result = self.momentum.risk_check(signal, portfolio)

        self.assertTrue(result, "Risk check debe pasar cuando hay suficiente cash para BUY")

    def test_momentum_buy_with_insufficient_cash_should_fail(self):
        """Test: BUY sin suficiente cash debe fallar risk_check."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10")  # Insuficiente

        signal = self._create_signal(symbol, SignalType.BUY, price)
        portfolio = self._create_portfolio(cash)

        # Risk check debe fallar
        result = self.momentum.risk_check(signal, portfolio)

        self.assertFalse(result, "Risk check debe fallar cuando no hay suficiente cash para BUY")

    def test_momentum_sell_with_position_should_pass(self):
        """Test: SELL con posición existente debe pasar risk_check."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")
        position = Position(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("90"),
            market_price=price,
            unrealized_pnl=Decimal("1000"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="test",
        )

        signal = self._create_signal(symbol, SignalType.SELL, price)
        portfolio = self._create_portfolio(cash, [position])

        # Risk check debe pasar
        result = self.momentum.risk_check(signal, portfolio)

        self.assertTrue(result, "Risk check debe pasar cuando hay posición para SELL")

    def test_momentum_sell_without_position_should_fail(self):
        """Test: SELL sin posición debe fallar risk_check."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")

        signal = self._create_signal(symbol, SignalType.SELL, price)
        portfolio = self._create_portfolio(cash)

        # Risk check debe fallar
        result = self.momentum.risk_check(signal, portfolio)

        self.assertFalse(result, "Risk check debe fallar cuando no hay posición para SELL")

    def test_mean_reversion_buy_with_sufficient_cash_should_pass(self):
        """Test: Mean Reversion BUY con suficiente cash debe pasar."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")

        signal = self._create_signal(symbol, SignalType.BUY, price)
        portfolio = self._create_portfolio(cash)

        result = self.mean_reversion.risk_check(signal, portfolio)

        self.assertTrue(result, "Mean Reversion risk check debe pasar con suficiente cash")

    def test_mean_reversion_sell_with_position_should_pass(self):
        """Test: Mean Reversion SELL con posición debe pasar."""
        symbol = "AAPL"
        price = Decimal("100")
        position = Position(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("90"),
            market_price=price,
            unrealized_pnl=Decimal("1000"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="test",
        )

        signal = self._create_signal(symbol, SignalType.SELL, price)
        portfolio = self._create_portfolio(Decimal("10000"), [position])

        result = self.mean_reversion.risk_check(signal, portfolio)

        self.assertTrue(result, "Mean Reversion risk check debe pasar con posición existente")

    def test_pairs_trading_buy_with_sufficient_cash_should_pass(self):
        """Test: Pairs Trading BUY con suficiente cash debe pasar."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")

        signal = self._create_signal(symbol, SignalType.BUY, price)
        portfolio = self._create_portfolio(cash)

        result = self.pairs_trading.risk_check(signal, portfolio)

        self.assertTrue(result, "Pairs Trading risk check debe pasar con suficiente cash")

    def test_pairs_trading_sell_with_position_should_pass(self):
        """Test: Pairs Trading SELL con posición debe pasar."""
        symbol = "AAPL"
        price = Decimal("100")
        position = Position(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("90"),
            market_price=price,
            unrealized_pnl=Decimal("1000"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="test",
        )

        signal = self._create_signal(symbol, SignalType.SELL, price)
        # Increase cash to ensure pair exposure is not too high
        # Position value = 100 * 100 = $10,000
        # Total value = $10k cash + $10k position = $20k
        # Pair exposure = $10k / $20k = 50% (may exceed max_pair_exposure default of 20%)
        # Increase cash to reduce pair exposure
        portfolio = self._create_portfolio(Decimal("70000"), [position])
        # Now: Total = $70k cash + $10k position = $80k
        # Pair exposure = $10k / $80k = 12.5% < 15% ✅ (config has max_pair_exposure = 0.15)

        result = self.pairs_trading.risk_check(signal, portfolio)

        self.assertTrue(result, "Pairs Trading risk check debe pasar con posición existente")

    def test_all_strategies_reject_sell_without_position(self):
        """Test: Todas las estrategias deben rechazar SELL sin posición."""
        symbol = "AAPL"
        price = Decimal("100")

        strategies = [self.momentum, self.mean_reversion, self.pairs_trading]
        signal = self._create_signal(symbol, SignalType.SELL, price)
        portfolio = self._create_portfolio(Decimal("10000"))

        for strategy in strategies:
            result = strategy.risk_check(signal, portfolio)
            self.assertFalse(
                result, f"{strategy.__class__.__name__} debe rechazar SELL sin posición"
            )

    def test_position_size_calculation_is_reasonable(self):
        """Test: Position size calculado debe ser razonable."""
        symbol = "AAPL"
        price = Decimal("100")
        cash = Decimal("10000")

        signal = self._create_signal(symbol, SignalType.BUY, price)
        portfolio = self._create_portfolio(cash)

        # Verificar que risk_check pasa
        result = self.momentum.risk_check(signal, portfolio)
        self.assertTrue(result, "Risk check debe pasar")

        # Calcular position size
        position_size = self.momentum.get_position_size(signal, portfolio)

        # Position size debe ser razonable
        self.assertGreater(position_size, Decimal("0"), "Position size debe ser > 0")
        self.assertLess(
            position_size * price,
            cash * Decimal("1.1"),
            "Position size no debe exceder cash disponible",
        )


if __name__ == "__main__":
    unittest.main()
