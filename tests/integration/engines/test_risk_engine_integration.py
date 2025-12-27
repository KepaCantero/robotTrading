"""
Integration Tests: Risk Engine (Fase 3, Módulo 6)

Tests para verificar que Risk Engine funciona correctamente:
- RiskEngine básico
- VaR Calculators (Historical, Parametric, Monte Carlo, GARCH)
- Stress Testing
- Drawdown Controller
- Exposure Manager
- Correlation Analyzer
- Risk Attribution
- Alert System
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.risk_engine import RiskEngine
from app.engines.risk_engine.alert_system import AlertSystem
from app.engines.risk_engine.correlation_analyzers import CorrelationAnalyzer
from app.engines.risk_engine.drawdown_controllers import DrawdownController
from app.engines.risk_engine.exposure_managers import ExposureManager
from app.engines.risk_engine.risk_attribution import RiskAttributor
from app.engines.risk_engine.stress_testers import StressTester
from app.engines.risk_engine.var_calculators import (
    HistoricalVaRCalculator,
    MonteCarloVaRCalculator,
    ParametricVaRCalculator,
)
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
        ),
        Position(
            symbol="GOOGL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("2000.00"),
            market_price=Decimal("2050.00"),
            unrealized_pnl=Decimal("2500.00"),
            broker="paper",
        ),
    ]

    return Portfolio(
        portfolio_id=str(uuid4()), cash=Decimal("50000.00"), positions=positions, broker="paper"
    )


class TestRiskEngine:
    """Tests básicos de RiskEngine."""

    def test_risk_engine_initialization(self):
        """Test inicialización de RiskEngine."""
        config = {'enabled': True}
        engine = RiskEngine(config)

        assert engine.enabled
        assert not engine._initialized

        engine.initialize()
        assert engine._initialized

    def test_assess_risk(self):
        """Test evaluación de riesgo básica."""
        config = {'enabled': True}
        engine = RiskEngine(config)
        engine.initialize()

        portfolio = create_test_portfolio()
        assessment = engine.assess_risk(portfolio)

        assert 'risk_level' in assessment or 'status' in assessment
        assert 'timestamp' in assessment

    def test_set_components(self):
        """Test configurar componentes."""
        config = {'enabled': True}
        engine = RiskEngine(config)

        var_calculator = HistoricalVaRCalculator({'confidence_level': 0.95})
        engine.set_var_calculator(var_calculator)

        stress_tester = StressTester({'n_monte_carlo_scenarios': 100})
        engine.set_stress_tester(stress_tester)

        assert engine.var_calculator is not None
        assert engine.stress_tester is not None


class TestVaRCalculators:
    """Tests de calculadores de VaR."""

    def test_historical_var_calculator(self):
        """Test Historical VaR Calculator."""
        config = {'confidence_level': 0.95}
        calculator = HistoricalVaRCalculator(config)

        # Retornos históricos de prueba
        returns = np.random.normal(0.001, 0.02, 100)

        result = calculator.calculate_var(returns, portfolio_value=100000)

        assert 'var' in result
        assert 'cvar' in result
        assert 'confidence_level' in result
        assert result['confidence_level'] == 0.95

    def test_parametric_var_calculator(self):
        """Test Parametric VaR Calculator."""
        config = {'confidence_level': 0.95}
        calculator = ParametricVaRCalculator(config)

        returns = np.random.normal(0.001, 0.02, 100)

        result = calculator.calculate_var(returns, portfolio_value=100000)

        assert 'var' in result
        assert 'cvar' in result
        assert 'mean_return' in result
        assert 'std_return' in result

    def test_monte_carlo_var_calculator(self):
        """Test Monte Carlo VaR Calculator."""
        config = {'confidence_level': 0.95, 'n_simulations': 1000}
        calculator = MonteCarloVaRCalculator(config)

        returns = np.random.normal(0.001, 0.02, 100)

        result = calculator.calculate_var(returns, portfolio_value=100000)

        assert 'var' in result
        assert 'cvar' in result
        assert 'n_simulations' in result


class TestStressTesting:
    """Tests de stress testing."""

    def test_stress_tester_initialization(self):
        """Test inicialización de StressTester."""
        config = {'n_monte_carlo_scenarios': 100}
        tester = StressTester(config)

        assert len(tester.historical_scenarios) > 0
        assert '2008_crisis' in tester.historical_scenarios

    def test_run_historical_stress_tests(self):
        """Test ejecutar stress tests históricos."""
        config = {'n_monte_carlo_scenarios': 100}
        tester = StressTester(config)

        portfolio = create_test_portfolio()
        results = tester.run_stress_tests(portfolio, scenario_types=['historical'])

        assert 'historical' in results
        assert 'summary' in results
        assert '2008_crisis' in results['historical']


class TestDrawdownController:
    """Tests de drawdown controller."""

    def test_drawdown_controller_initialization(self):
        """Test inicialización de DrawdownController."""
        config = {'max_drawdown_limit': 0.20}
        controller = DrawdownController(config)

        assert controller.max_drawdown_limit == 0.20
        assert not controller.circuit_breaker_active

    def test_assess_drawdown(self):
        """Test evaluación de drawdown."""
        config = {'max_drawdown_limit': 0.20}
        controller = DrawdownController(config)

        portfolio = create_test_portfolio()

        # Simular historial
        controller.portfolio_value_history = [
            {'timestamp': datetime.now(), 'portfolio_value': Decimal("100000")},
            {'timestamp': datetime.now(), 'portfolio_value': Decimal("95000")},
        ]

        result = controller.assess_drawdown(portfolio)

        assert 'portfolio_drawdown' in result
        assert 'circuit_breaker_status' in result


class TestExposureManager:
    """Tests de exposure manager."""

    def test_exposure_manager_initialization(self):
        """Test inicialización de ExposureManager."""
        config = {'max_asset_exposure': 0.20}
        manager = ExposureManager(config)

        assert manager.max_asset_exposure == 0.20

    def test_analyze_exposure(self):
        """Test análisis de exposición."""
        config = {'max_asset_exposure': 0.20}
        manager = ExposureManager(config)

        portfolio = create_test_portfolio()
        result = manager.analyze_exposure(portfolio)

        assert 'asset_exposure' in result
        assert 'leverage' in result
        assert 'concentration' in result
        assert 'violations' in result


class TestCorrelationAnalyzer:
    """Tests de correlation analyzer."""

    def test_correlation_analyzer_initialization(self):
        """Test inicialización de CorrelationAnalyzer."""
        config = {'max_correlation': 0.8}
        analyzer = CorrelationAnalyzer(config)

        assert analyzer.max_correlation == 0.8

    def test_analyze_correlations(self):
        """Test análisis de correlaciones."""
        config = {'max_correlation': 0.8}
        analyzer = CorrelationAnalyzer(config)

        portfolio = create_test_portfolio()

        # Precios históricos simulados
        prices_history = {
            'AAPL': [150 + i * 0.1 for i in range(100)],
            'GOOGL': [2000 + i * 2 for i in range(100)],
        }

        result = analyzer.analyze_correlations(portfolio, prices_history)

        assert 'correlation_matrix' in result
        assert 'diversification_score' in result


class TestRiskAttribution:
    """Tests de risk attribution."""

    def test_risk_attributor_initialization(self):
        """Test inicialización de RiskAttributor."""
        config = {'use_factor_models': True}
        attributor = RiskAttributor(config)

        assert attributor.use_factor_models

    def test_attribute_risk(self):
        """Test atribución de riesgo."""
        config = {'use_factor_models': False}
        attributor = RiskAttributor(config)

        portfolio = create_test_portfolio()

        returns_history = {
            'AAPL': [0.01 * (i % 2 - 0.5) for i in range(100)],
            'GOOGL': [0.01 * (i % 2 - 0.5) for i in range(100)],
        }

        result = attributor.attribute_risk(portfolio, returns_history=returns_history)

        assert 'by_asset' in result or 'summary' in result


class TestAlertSystem:
    """Tests de alert system."""

    def test_alert_system_initialization(self):
        """Test inicialización de AlertSystem."""
        config = {
            'thresholds': {'drawdown_limit': 0.15},
            'enable_email': False,
            'enable_slack': False,
        }
        alert_system = AlertSystem(config)

        assert alert_system.thresholds['drawdown_limit'] == 0.15

    def test_check_thresholds(self):
        """Test verificación de umbrales."""
        config = {'thresholds': {'drawdown_limit': 0.15}}
        alert_system = AlertSystem(config)

        portfolio = create_test_portfolio()
        risk_assessment = {
            'drawdown': {
                'portfolio_drawdown': {'current_drawdown': 0.20},  # Excede límite
                'circuit_breaker_status': {'global_circuit_breaker_active': False},
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, portfolio)

        assert isinstance(alerts, list)
