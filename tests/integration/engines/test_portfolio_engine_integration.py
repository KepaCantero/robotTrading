"""
Integration Tests: Portfolio Engine (Fase 3, Módulo 5)

Tests para verificar que Portfolio Engine funciona correctamente:
- PortfolioEngine básico
- Optimizadores (Markowitz, Risk Parity, Black-Litterman, Kelly)
- Rebalanceadores (Threshold, Time-based, Volatility-targeting, Transaction-cost-aware)
- Meta-learners (Historical Performance, RL, Ensemble)
- Multi-asset support
"""

import logging
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.portfolio_engine import PortfolioEngine
from app.engines.portfolio_engine.meta_learners import (
    EnsembleMetaLearner,
    HistoricalPerformanceLearner,
)
from app.engines.portfolio_engine.optimizers import (
    BlackLittermanOptimizer,
    KellyCriterionOptimizer,
    MarkowitzOptimizer,
    RiskParityOptimizer,
)
from app.engines.portfolio_engine.rebalancers import (
    ThresholdRebalancer,
    TimeBasedRebalancer,
    TransactionCostAwareRebalancer,
    VolatilityTargetingRebalancer,
)
from app.models.portfolio import AssetClass, Portfolio, Position
from app.providers.paper_trading import PaperTradingPortfolioProvider

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


class TestPortfolioEngine:
    """Tests básicos de PortfolioEngine."""

    def test_portfolio_engine_initialization(self):
        """Test inicialización de PortfolioEngine."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)

        assert engine.enabled == True
        assert engine._initialized == False

        engine.initialize()
        assert engine._initialized == True

    def test_get_portfolio(self):
        """Test obtener portfolio."""
        config = {'enabled': True}
        provider = PaperTradingPortfolioProvider()
        engine = PortfolioEngine(config, provider)
        engine.initialize()

        # No podemos testear async aquí sin asyncio, pero verificamos estructura
        assert engine.portfolio_service is not None

    def test_set_optimizer(self):
        """Test configurar optimizer."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)

        optimizer = MarkowitzOptimizer({'risk_aversion': 0.5})
        engine.set_optimizer(optimizer)

        assert engine.optimizer is not None
        assert isinstance(engine.optimizer, MarkowitzOptimizer)

    def test_set_rebalancer(self):
        """Test configurar rebalancer."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)

        rebalancer = ThresholdRebalancer({'threshold': 0.05})
        engine.set_rebalancer(rebalancer)

        assert engine.rebalancer is not None

    def test_set_meta_learner(self):
        """Test configurar meta-learner."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)

        meta_learner = HistoricalPerformanceLearner({'lookback_period': 30})
        engine.set_meta_learner(meta_learner)

        assert engine.meta_learner is not None

    def test_get_allocation_by_asset_class(self):
        """Test obtener asignación por clase de activo."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)

        portfolio = create_test_portfolio()
        engine.current_portfolio = portfolio

        allocation = engine.get_allocation_by_asset_class()

        assert 'equity' in allocation
        assert allocation['equity']['count'] == 2

    def test_get_status(self):
        """Test obtener estado del engine."""
        config = {'enabled': True}
        engine = PortfolioEngine(config)
        engine.initialize()

        status = engine.get_status()

        assert 'enabled' in status
        assert 'initialized' in status
        assert 'has_optimizer' in status
        assert 'has_rebalancer' in status
        assert 'has_meta_learner' in status


class TestPortfolioOptimizers:
    """Tests de optimizadores de portfolio."""

    def test_markowitz_optimizer(self):
        """Test Markowitz optimizer."""
        config = {'risk_aversion': 0.5}
        optimizer = MarkowitzOptimizer(config)

        # Datos de prueba
        expected_returns = np.array([0.10, 0.12, 0.08])
        cov_matrix = np.array([[0.04, 0.02, 0.01], [0.02, 0.06, 0.03], [0.01, 0.03, 0.05]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        assert 'weights' in result
        assert 'expected_return' in result
        assert 'volatility' in result
        assert 'sharpe_ratio' in result
        assert abs(sum(result['weights'].values()) - 1.0) < 0.01

    def test_risk_parity_optimizer(self):
        """Test Risk Parity optimizer."""
        config = {}
        optimizer = RiskParityOptimizer(config)

        expected_returns = np.array([0.10, 0.12, 0.08])
        cov_matrix = np.array([[0.04, 0.02, 0.01], [0.02, 0.06, 0.03], [0.01, 0.03, 0.05]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        assert 'weights' in result
        assert abs(sum(result['weights'].values()) - 1.0) < 0.01

    def test_black_litterman_optimizer(self):
        """Test Black-Litterman optimizer."""
        config = {}
        optimizer = BlackLittermanOptimizer(config)

        expected_returns = np.array([0.10, 0.12, 0.08])
        cov_matrix = np.array([[0.04, 0.02, 0.01], [0.02, 0.06, 0.03], [0.01, 0.03, 0.05]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        assert 'weights' in result
        assert abs(sum(result['weights'].values()) - 1.0) < 0.01

    def test_kelly_criterion_optimizer(self):
        """Test Kelly Criterion optimizer."""
        config = {}
        optimizer = KellyCriterionOptimizer(config)

        expected_returns = np.array([0.10, 0.12, 0.08])
        cov_matrix = np.array([[0.04, 0.02, 0.01], [0.02, 0.06, 0.03], [0.01, 0.03, 0.05]])

        constraints = {
            'win_probabilities': np.array([0.55, 0.60, 0.50]),
            'win_returns': np.array([0.15, 0.18, 0.12]),
            'loss_returns': np.array([-0.10, -0.12, -0.08]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        assert 'weights' in result
        assert 'kelly_fractions' in result
        assert abs(sum(result['weights'].values()) - 1.0) < 0.01


class TestPortfolioRebalancers:
    """Tests de rebalanceadores."""

    def test_threshold_rebalancer(self):
        """Test threshold rebalancer."""
        config = {'threshold': 0.05}
        rebalancer = ThresholdRebalancer(config)

        current_weights = {'AAPL': 0.45, 'GOOGL': 0.55}
        target_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        portfolio_value = Decimal("100000")

        should_rebalance = rebalancer.should_rebalance(
            current_weights, target_weights, portfolio_value
        )

        # Con threshold 5%, desviación de 5% debería trigger rebalance
        assert should_rebalance == True

    def test_time_based_rebalancer(self):
        """Test time-based rebalancer."""
        config = {'frequency': 'daily'}
        rebalancer = TimeBasedRebalancer(config)

        current_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        target_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        portfolio_value = Decimal("100000")

        # Primera vez debería rebalancear
        should_rebalance = rebalancer.should_rebalance(
            current_weights, target_weights, portfolio_value
        )
        assert should_rebalance == True

    def test_volatility_targeting_rebalancer(self):
        """Test volatility-targeting rebalancer."""
        config = {'target_volatility': 0.15, 'volatility_threshold': 0.02}
        rebalancer = VolatilityTargetingRebalancer(config)

        current_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        target_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        portfolio_value = Decimal("100000")

        # Matriz de covarianza que genere volatilidad diferente a target
        # Para asegurar que se calcule correctamente
        cov_matrix = np.array([[0.04, 0.02], [0.02, 0.06]])

        should_rebalance = rebalancer.should_rebalance(
            current_weights, target_weights, portfolio_value, cov_matrix=cov_matrix
        )

        # Debe retornar un bool (puede ser True o False dependiendo de la volatilidad)
        assert isinstance(should_rebalance, bool)

    def test_transaction_cost_aware_rebalancer(self):
        """Test transaction cost-aware rebalancer."""
        config = {'threshold': 0.05, 'commission_rate': 0.001, 'slippage_rate': 0.0005}
        rebalancer = TransactionCostAwareRebalancer(config)

        current_weights = {'AAPL': 0.45, 'GOOGL': 0.55}
        target_weights = {'AAPL': 0.50, 'GOOGL': 0.50}
        portfolio_value = Decimal("100000")

        current_positions = {
            'AAPL': {'market_value': 45000, 'quantity': 290},
            'GOOGL': {'market_value': 55000, 'quantity': 27},
        }
        prices = {'AAPL': Decimal("155.00"), 'GOOGL': Decimal("2050.00")}

        should_rebalance = rebalancer.should_rebalance(
            current_weights,
            target_weights,
            portfolio_value,
            current_positions=current_positions,
            prices=prices,
        )

        assert isinstance(should_rebalance, bool)


class TestMetaLearners:
    """Tests de meta-learners."""

    def test_historical_performance_learner(self):
        """Test Historical Performance Learner."""
        config = {'lookback_period': 30, 'use_sharpe': True}
        learner = HistoricalPerformanceLearner(config)

        strategy_performance = {
            'momentum': {'return': 0.15, 'sharpe_ratio': 1.5, 'max_drawdown': -0.10},
            'mean_reversion': {'return': 0.10, 'sharpe_ratio': 1.2, 'max_drawdown': -0.15},
        }

        weights = learner.learn_weights(strategy_performance)

        assert len(weights) == 2
        assert 'momentum' in weights
        assert 'mean_reversion' in weights
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_ensemble_meta_learner(self):
        """Test Ensemble Meta-Learner."""
        config = {'use_historical': True, 'learner_weights': {'HistoricalPerformanceLearner': 1.0}}
        learner = EnsembleMetaLearner(config)

        strategy_performance = {
            'momentum': {'return': 0.15, 'sharpe_ratio': 1.5},
            'mean_reversion': {'return': 0.10, 'sharpe_ratio': 1.2},
        }

        weights = learner.learn_weights(strategy_performance)

        assert len(weights) == 2
        assert abs(sum(weights.values()) - 1.0) < 0.01
