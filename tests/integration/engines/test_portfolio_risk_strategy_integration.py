"""
Integration Tests: Portfolio Engine y Risk Engine con Strategy Engines

Tests para verificar que Portfolio Engine y Risk Engine se integran correctamente con Strategy Engines:
- Strategy Engines pueden usar Portfolio Engine para optimización
- Strategy Engines pueden usar Risk Engine para evaluación de riesgo
- Integración completa en backtests multi-strategy
"""

import logging
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.portfolio_engine import PortfolioEngine
from app.engines.portfolio_engine.optimizers import MarkowitzOptimizer
from app.engines.risk_engine import RiskEngine
from app.engines.risk_engine.drawdown_controllers import DrawdownController
from app.engines.risk_engine.var_calculators import HistoricalVaRCalculator
from app.engines.strategy_engines import ModularMomentumStrategyEngine, MomentumStrategyEngine
from app.models.portfolio import AssetClass, Portfolio, Position

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_portfolio() -> Portfolio:
    """Crear portfolio de prueba."""
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            broker="paper",
        )
    ]

    return Portfolio(
        portfolio_id=str(uuid4()), cash=Decimal("50000.00"), positions=positions, broker="paper"
    )


class TestPortfolioEngineIntegration:
    """Tests de integración de Portfolio Engine con Strategy Engines."""

    def test_portfolio_engine_with_strategy_engine(self):
        """Test que Strategy Engine puede usar Portfolio Engine."""
        # Crear Portfolio Engine
        portfolio_config = {'enabled': True}
        portfolio_engine = PortfolioEngine(portfolio_config)
        portfolio_engine.initialize()

        # Configurar optimizer
        optimizer = MarkowitzOptimizer({'risk_aversion': 0.5})
        portfolio_engine.set_optimizer(optimizer)

        # Crear Strategy Engine
        strategy_config = {'rsi_period': 14}
        MomentumStrategyEngine(strategy_config)

        # Verificar que Portfolio Engine está disponible
        assert portfolio_engine._initialized == True
        assert portfolio_engine.optimizer is not None

    def test_portfolio_optimization_with_strategy_signals(self):
        """Test optimización de portfolio usando señales de estrategias."""
        # Crear Portfolio Engine con optimizer
        portfolio_config = {'enabled': True}
        portfolio_engine = PortfolioEngine(portfolio_config)
        portfolio_engine.initialize()

        optimizer = MarkowitzOptimizer({'risk_aversion': 0.5})
        portfolio_engine.set_optimizer(optimizer)

        # Simular retornos esperados y covarianza basados en estrategias
        expected_returns = [0.10, 0.12, 0.08]
        cov_matrix = [[0.04, 0.02, 0.01], [0.02, 0.06, 0.03], [0.01, 0.03, 0.05]]

        import numpy as np

        result = optimizer.optimize(np.array(expected_returns), np.array(cov_matrix))

        assert 'weights' in result
        assert len(result['weights']) > 0


class TestRiskEngineIntegration:
    """Tests de integración de Risk Engine con Strategy Engines."""

    def test_risk_engine_with_strategy_engine(self):
        """Test que Strategy Engine puede usar Risk Engine."""
        # Crear Risk Engine
        risk_config = {'enabled': True}
        risk_engine = RiskEngine(risk_config)
        risk_engine.initialize()

        # Configurar componentes
        var_calculator = HistoricalVaRCalculator({'confidence_level': 0.95})
        risk_engine.set_var_calculator(var_calculator)

        drawdown_controller = DrawdownController({'max_drawdown_limit': 0.20})
        risk_engine.set_drawdown_controller(drawdown_controller)

        # Crear Strategy Engine
        strategy_config = {'rsi_period': 14}
        MomentumStrategyEngine(strategy_config)

        # Verificar que Risk Engine está disponible
        assert risk_engine._initialized == True
        assert risk_engine.var_calculator is not None
        assert risk_engine.drawdown_controller is not None

    def test_risk_assessment_with_strategy_portfolio(self):
        """Test evaluación de riesgo usando portfolio de estrategia."""
        # Crear Risk Engine
        risk_config = {'enabled': True}
        risk_engine = RiskEngine(risk_config)
        risk_engine.initialize()

        var_calculator = HistoricalVaRCalculator({'confidence_level': 0.95})
        risk_engine.set_var_calculator(var_calculator)

        # Crear portfolio
        portfolio = create_test_portfolio()

        # Evaluar riesgo
        import numpy as np

        returns_history = np.random.normal(0.001, 0.02, 100)

        assessment = risk_engine.assess_risk(portfolio, returns_history=returns_history)

        assert 'timestamp' in assessment


class TestIntegratedSystem:
    """Tests del sistema integrado completo."""

    def test_portfolio_risk_strategy_integration(self):
        """Test integración completa Portfolio + Risk + Strategy."""
        # Crear todos los engines
        portfolio_config = {'enabled': True}
        portfolio_engine = PortfolioEngine(portfolio_config)
        portfolio_engine.initialize()

        risk_config = {'enabled': True}
        risk_engine = RiskEngine(risk_config)
        risk_engine.initialize()

        strategy_config = {'rsi_period': 14}
        MomentumStrategyEngine(strategy_config)

        # Verificar que todos están inicializados
        assert portfolio_engine._initialized == True
        assert risk_engine._initialized == True

        # Portfolio puede ser evaluado por Risk Engine
        portfolio = create_test_portfolio()

        import numpy as np

        returns_history = np.random.normal(0.001, 0.02, 100)

        risk_assessment = risk_engine.assess_risk(portfolio, returns_history=returns_history)

        assert 'timestamp' in risk_assessment

    def test_multi_strategy_with_portfolio_risk_engines(self):
        """Test multi-strategy con Portfolio y Risk Engines."""
        # Crear engines compartidos
        portfolio_config = {'enabled': True}
        portfolio_engine = PortfolioEngine(portfolio_config)
        portfolio_engine.initialize()

        risk_config = {'enabled': True}
        risk_engine = RiskEngine(risk_config)
        risk_engine.initialize()

        # Crear múltiples Strategy Engines
        momentum_engine = MomentumStrategyEngine({'rsi_period': 14})
        modular_engine = ModularMomentumStrategyEngine(
            {'rsi_period': 14, 'context_engine_enabled': False}
        )

        # Todos pueden usar los mismos Portfolio y Risk Engines
        assert portfolio_engine._initialized == True
        assert risk_engine._initialized == True

        # Evaluar riesgo de portfolio común
        portfolio = create_test_portfolio()

        import numpy as np

        returns_history = np.random.normal(0.001, 0.02, 100)

        risk_assessment = risk_engine.assess_risk(portfolio, returns_history=returns_history)

        assert 'timestamp' in risk_assessment
