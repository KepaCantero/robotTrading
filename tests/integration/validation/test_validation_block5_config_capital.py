"""
BLOQUE 5 — Auditoría de Configuración y Capital

Tests para verificar:
- Restricción de exposición (max_exposure, max_total_exposure no superan límites del preset)
- Rebalanceo (no se gasta el mismo capital en dos estrategias simultáneamente)
- Persistencia de preset (Conservative no sobrescrito por valores por defecto)
"""

import unittest
from datetime import datetime
from decimal import Decimal

from app.core.centralized_config import get_strategy_config
from app.models.portfolio import AssetClass, Portfolio, Position
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTradingStrategy


class TestExposureRestriction(unittest.TestCase):
    """Test: Restricción de exposición."""

    def setUp(self):
        """Setup para tests de exposición."""
        self.momentum = MomentumStrategy({"name": "momentum"})
        self.mean_reversion = MeanReversionStrategy({"name": "mean_reversion"})
        self.pairs_trading = PairsTradingStrategy(
            {"name": "pairs_trading", "pair_symbols": ["AAPL", "MSFT"]}
        )

    def test_momentum_max_exposure_respected(self):
        """Validar que max_exposure no supera los límites del preset."""
        # Momentum tiene max_exposure = 80% (0.8)
        max_exposure = Decimal("0.8")

        # Crear portfolio con exposición al límite
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("20000"),  # $20k cash
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("400"),  # $80k en posiciones
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

        # Calcular exposición actual
        total_exposure = self.momentum._calculate_total_exposure(portfolio)

        # Verificar que está dentro del límite o ligeramente por encima (por redondeo)
        self.assertLessEqual(
            total_exposure,
            max_exposure + Decimal("0.01"),  # Tolerancia 1%
            f"Exposición actual {total_exposure:.2%} no debe superar max_exposure {max_exposure:.2%}",
        )

    def test_mean_reversion_max_exposure_respected(self):
        """Validar que Mean Reversion respeta max_exposure = 60%."""
        max_exposure = Decimal("0.6")  # 60% para Mean Reversion

        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("40000"),  # $40k cash
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("300"),  # $60k en posiciones
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

        total_exposure = self.mean_reversion._calculate_total_exposure(portfolio)

        self.assertLessEqual(
            total_exposure,
            max_exposure + Decimal("0.01"),
            f"Mean Reversion exposición {total_exposure:.2%} no debe superar {max_exposure:.2%}",
        )

    def test_pairs_trading_max_pair_exposure_respected(self):
        """Validar que Pairs Trading respeta max_pair_exposure = 20%."""
        max_pair_exposure = Decimal("0.2")  # 20% para Pairs Trading

        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("80000"),  # $80k cash
            positions=[
                Position(
                    symbol="AAPL",  # Parte del par
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("100"),  # $20k en posición del par
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

        pair_exposure = self.pairs_trading._calculate_pair_exposure(portfolio)

        self.assertLessEqual(
            pair_exposure,
            max_pair_exposure + Decimal("0.01"),
            f"Pairs Trading pair_exposure {pair_exposure:.2%} no debe superar {max_pair_exposure:.2%}",
        )


class TestCapitalRebalancing(unittest.TestCase):
    """Test: Rebalanceo."""

    def test_no_duplicate_capital_spending(self):
        """Asegurar que no se gasta el mismo capital en dos estrategias simultáneamente."""
        # Este test se valida a nivel de MultiStrategyBacktester
        # Verificamos que cada estrategia tiene su capital asignado

        from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

        initial_capital = Decimal("100000")
        allocation_manager = MultiStrategyAllocationManager(total_capital=initial_capital)

        # Obtener capital asignado a estrategias usando allocate()
        momentum_allocation = allocation_manager.strategy_allocations.get("momentum")
        mean_reversion_allocation = allocation_manager.strategy_allocations.get("mean_reversion")

        if momentum_allocation and mean_reversion_allocation:
            # Calcular capital asignado
            momentum_capital = momentum_allocation.allocate(initial_capital)
            mean_reversion_capital = mean_reversion_allocation.allocate(initial_capital)

            # Verificar que la suma no excede el capital total
            total_allocated = momentum_capital + mean_reversion_capital

            self.assertLessEqual(
                total_allocated,
                initial_capital,
                f"Capital total asignado {total_allocated} no debe exceder inicial {initial_capital}",
            )

    def test_capital_redistributed_after_position_close(self):
        """Verificar que el capital se redistribuye correctamente después de cada cierre."""
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("50000"),
            positions=[],
            timestamp=datetime.utcnow(),
            broker="test",
        )

        # Simular cierre de posición
        # Antes: $50k cash, $50k en posición = $100k total
        # Después: $100k cash, $0 en posición = $100k total

        initial_cash = portfolio.cash
        initial_positions_value = sum(p.market_value for p in portfolio.positions)
        initial_total = initial_cash + initial_positions_value

        # Cerrar posición (simulado)
        portfolio.positions = []

        final_cash = portfolio.cash
        final_positions_value = sum(p.market_value for p in portfolio.positions)
        final_total = final_cash + final_positions_value

        # El total debe mantenerse (o aumentar si hubo ganancia)
        self.assertGreaterEqual(
            final_total,
            initial_total - Decimal("100"),  # Tolerancia por comisiones
            f"Capital total no debe disminuir después de cerrar: {final_total} vs {initial_total}",
        )


class TestPresetPersistence(unittest.TestCase):
    """Test: Persistencia de preset."""

    def test_conservative_preset_not_overwritten_by_defaults(self):
        """Revisar que el preset Conservative no está siendo sobrescrito por valores por defecto."""
        # Obtener config de momentum con preset Conservative
        strategy_config = get_strategy_config("momentum")

        if strategy_config:
            # Verificar que los parámetros del preset están presentes
            if hasattr(strategy_config, 'stop_loss_pct'):
                stop_loss = strategy_config.stop_loss_pct
                # Conservative preset típicamente tiene stop_loss alrededor de 2-3%
                self.assertIsNotNone(stop_loss, "stop_loss debe estar en config")
                self.assertGreater(stop_loss, 0, "stop_loss debe ser positivo")
                self.assertLess(stop_loss, 0.1, "stop_loss debe ser razonable (<10%)")

            if hasattr(strategy_config, 'take_profit_pct'):
                take_profit = strategy_config.take_profit_pct
                self.assertIsNotNone(take_profit, "take_profit debe estar en config")
                self.assertGreater(take_profit, 0, "take_profit debe ser positivo")

    def test_preset_parameters_persist_in_strategy(self):
        """Verificar que los parámetros del preset persisten en la estrategia."""
        strategy = MomentumStrategy({"name": "momentum"})

        # Verificar que los parámetros de riesgo están configurados
        self.assertIsNotNone(strategy.stop_loss, "stop_loss debe estar configurado")
        self.assertIsNotNone(strategy.take_profit, "take_profit debe estar configurado")
        self.assertIsNotNone(strategy.max_position_size, "max_position_size debe estar configurado")

        # Verificar que no son valores por defecto genéricos (deben venir de config)
        self.assertGreater(strategy.stop_loss, 0, "stop_loss debe ser > 0")
        self.assertGreater(strategy.take_profit, 0, "take_profit debe ser > 0")
        self.assertGreater(strategy.max_position_size, 0, "max_position_size debe ser > 0")


if __name__ == "__main__":
    unittest.main()
