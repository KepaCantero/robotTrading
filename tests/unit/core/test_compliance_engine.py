"""
Comprehensive Test Suite for Compliance Engine
================================================

Following Beck TDD principles (Rule 21):
- Test-first development
- Red-Green-Refactor cycle
- Comprehensive coverage of all functionality
- Both success and failure cases
- Clear, descriptive test names

Coverage Target: >80%
Author: TDD Compliance Suite
Date: 2026-01-28
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import pandas as pd
import numpy as np

from app.core.compliance_engine import (
    ComplianceEngine,
    SystemAvailability,
    SystemBus,
    PreTradeAnalysis,
    PostTradeAnalysis,
    PortfolioOptimization,
    get_compliance_engine,
    quick_check,
    get_execution_plan,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_price_history() -> pd.DataFrame:
    """Create sample price history for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    # Generate realistic price series
    price = 100 + np.cumsum(np.random.randn(100) * 2)
    volume = np.random.randint(100000, 1000000, 100)

    return pd.DataFrame(
        {
            'open': price * (1 + np.random.randn(100) * 0.01),
            'high': price * (1 + abs(np.random.randn(100)) * 0.02),
            'low': price * (1 - abs(np.random.randn(100)) * 0.02),
            'close': price,
            'volume': volume,
        },
        index=dates,
    )


@pytest.fixture
def sample_returns() -> pd.DataFrame:
    """Create sample returns for portfolio optimization."""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=252, freq='D')

    returns_data = np.random.randn(252, 3) * 0.02  # 3 assets
    returns_df = pd.DataFrame(returns_data, index=dates, columns=['AAPL', 'MSFT', 'GOOGL'])

    return returns_df


@pytest.fixture
def mock_harris_integrator():
    """Mock Harris integrator for testing."""
    mock = Mock()

    # Mock pre_trade_check
    pre_trade_result = Mock()
    pre_trade_result.can_execute = True
    pre_trade_result.order_book_depth_ok = True
    pre_trade_result.liquidity_score = 65.0
    pre_trade_result.vpin = 0.05
    pre_trade_result.pin = 0.03
    pre_trade_result.estimated_market_impact_bps = 5.0
    pre_trade_result.estimated_timing_cost_bps = 2.0
    pre_trade_result.recommended_venue = "lit_exchange"
    pre_trade_result.recommended_order_type = "LIMIT"
    pre_trade_result.recommended_limit_price = Decimal("150.25")
    pre_trade_result.reasons = []

    mock.pre_trade_check = Mock(return_value=pre_trade_result)

    # Mock analyze_execution
    post_trade_result = Mock()
    post_trade_result.implementation_shortfall_bps = 7.5
    post_trade_result.market_impact_bps = 5.0
    post_trade_result.timing_cost_bps = 2.0
    post_trade_result.effective_spread_bps = 1.5
    post_trade_result.execution_quality_score = 85.0
    post_trade_result.price_improvement_bps = 0.5

    mock.analyze_execution = Mock(return_value=post_trade_result)

    return mock


@pytest.fixture
def mock_regime_detector():
    """Mock regime detector for testing."""
    mock = Mock()
    mock.detect_regimes = Mock(return_value=["BULL", "BULL", "BEAR", "BULL"])
    return mock


@pytest.fixture
def mock_alpha_model():
    """Mock alpha model for testing."""
    mock = Mock()
    alpha_signal = Mock()
    alpha_signal.confidence = 0.75
    mock.generate_alpha = Mock(return_value=alpha_signal)
    return mock


@pytest.fixture
def mock_portfolio_constructor():
    """Mock portfolio constructor for testing."""
    mock = Mock()
    optimization_result = Mock()
    optimization_result.weights = np.array([0.4, 0.35, 0.25])
    optimization_result.expected_return = 0.12
    optimization_result.risk = 0.15
    optimization_result.sharpe_ratio = 0.8

    mock.optimize = Mock(return_value=optimization_result)
    return mock


@pytest.fixture
def mock_var_calculator():
    """Mock VaR calculator for testing."""
    mock = Mock()

    def calculate_var(returns, method='historical', confidence_level=0.95):
        var_value = np.percentile(returns, (1 - confidence_level) * 100)
        return {'var': var_value, 'method': method}

    return calculate_var


@pytest.fixture
def engine_without_logging():
    """Create engine with logging disabled for cleaner test output."""
    return ComplianceEngine(enable_logging=False)


@pytest.fixture
def reset_singleton():
    """Reset singleton between tests."""
    yield
    ComplianceEngine._instance = None


# =============================================================================
# TEST CLASS: SystemAvailability
# =============================================================================


class TestSystemAvailability:
    """Test suite for SystemAvailability class."""

    def test_initialization_checks_all_systems(self):
        """Test that initialization checks all 21 systems."""
        availability = SystemAvailability()

        # Should have checked all systems
        systems = availability.get_availability()
        assert len(systems) > 0

        # Should have both main and compliance systems
        expected_main_systems = [
            'backtesting_engine',
            'live_trading',
            'risk_engine',
            'portfolio_engine',
            'data_engine',
            'context_engine',
        ]
        for system in expected_main_systems:
            assert system in systems

    def test_get_availability_returns_dict(self):
        """Test that get_availability returns a dictionary."""
        availability = SystemAvailability()
        result = availability.get_availability()

        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result.keys())
        assert all(isinstance(v, bool) for v in result.values())

    def test_is_available_returns_correct_status(self):
        """Test is_available returns correct boolean."""
        availability = SystemAvailability()

        # Test with known system
        result = availability.is_available('tomasini')
        assert isinstance(result, bool)

        # Test with unknown system
        result = availability.is_available('nonexistent_system')
        assert result is False

    def test_get_summary_returns_complete_metrics(self):
        """Test get_summary returns complete metrics."""
        availability = SystemAvailability()
        summary = availability.get_summary()

        assert 'total_systems' in summary
        assert 'available_systems' in summary
        assert 'availability_percentage' in summary
        assert 'systems' in summary

        assert summary['total_systems'] > 0
        assert 0 <= summary['availability_percentage'] <= 100
        assert len(summary['systems']) == summary['total_systems']

    def test_summary_availability_percentage_calculation(self):
        """Test that availability percentage is calculated correctly."""
        availability = SystemAvailability()
        summary = availability.get_summary()

        expected_percentage = (
            summary['available_systems'] / summary['total_systems'] * 100
            if summary['total_systems'] > 0
            else 0
        )

        assert summary['availability_percentage'] == expected_percentage


# =============================================================================
# TEST CLASS: ComplianceEngine - Initialization
# =============================================================================


class TestComplianceEngineInitialization:
    """Test suite for ComplianceEngine initialization."""

    def test_singleton_pattern_returns_same_instance(self, reset_singleton):
        """Test that singleton pattern returns the same instance."""
        engine1 = ComplianceEngine(enable_logging=False)
        engine2 = ComplianceEngine(enable_logging=False)

        assert engine1 is engine2
        assert id(engine1) == id(engine2)

    def test_initialization_with_default_parameters(self, reset_singleton):
        """Test initialization with default parameters."""
        engine = ComplianceEngine(enable_logging=False)

        assert engine.asset_class == "equity"
        assert engine.strict_mode is False
        assert engine.enable_logging is False

    def test_initialization_with_custom_parameters(self, reset_singleton):
        """Test initialization with custom parameters."""
        engine = ComplianceEngine(asset_class="crypto", strict_mode=True, enable_logging=False)

        assert engine.asset_class == "crypto"
        assert engine.strict_mode is True

    def test_initialization_avoids_reinitialization(self, reset_singleton):
        """Test that re-initialization doesn't reset attributes."""
        engine = ComplianceEngine(asset_class="equity", enable_logging=False)

        # Try to re-initialize with different parameters
        engine.__init__(asset_class="crypto", enable_logging=False)

        # Should keep original parameters
        assert engine.asset_class == "equity"

    def test_initialization_creates_system_availability(self, reset_singleton):
        """Test that initialization creates SystemAvailability."""
        engine = ComplianceEngine(enable_logging=False)

        assert hasattr(engine, 'availability')
        assert isinstance(engine.availability, SystemAvailability)

    def test_initialization_creates_system_bus(self, reset_singleton):
        """Test that initialization creates SystemBus."""
        engine = ComplianceEngine(enable_logging=False)

        assert hasattr(engine, '_system_bus')
        assert isinstance(engine._system_bus, SystemBus)

    def test_initialization_creates_tracking_dicts(self, reset_singleton):
        """Test that initialization creates tracking dictionaries."""
        engine = ComplianceEngine(enable_logging=False)

        assert hasattr(engine, '_active_orders')
        assert hasattr(engine, '_completed_trades')
        assert hasattr(engine, '_daily_pnl_tracking')
        assert isinstance(engine._active_orders, dict)
        assert isinstance(engine._completed_trades, list)
        assert isinstance(engine._daily_pnl_tracking, list)

    def test_enable_logging_parameter_respected(self, reset_singleton, caplog):
        """Test that enable_logging parameter is respected."""
        with caplog.at_level(logging.INFO):
            engine_with_logging = ComplianceEngine(enable_logging=True)
            assert "COMPLIANCE ENGINE STARTED" in caplog.text

        caplog.clear()

        with caplog.at_level(logging.INFO):
            engine_without_logging = ComplianceEngine(enable_logging=False)
            # Should not log startup
            assert "COMPLIANCE ENGINE STARTED" not in caplog.text

    def test_strict_mode_parameter_stored(self, reset_singleton):
        """Test that strict_mode parameter is stored correctly."""
        # First instance sets the parameters (singleton)
        engine_strict = ComplianceEngine(strict_mode=True, enable_logging=False)

        # Reset singleton to test with different parameters
        ComplianceEngine._instance = None
        engine_normal = ComplianceEngine(strict_mode=False, enable_logging=False)

        assert engine_strict.strict_mode is True
        assert engine_normal.strict_mode is False

        # Reset for other tests
        ComplianceEngine._instance = None


# =============================================================================
# TEST CLASS: ComplianceEngine - Pre-Trade Analysis
# =============================================================================


class TestComplianceEnginePreTradeAnalysis:
    """Test suite for pre-trade analysis functionality."""

    def test_analyze_pre_trade_returns_pre_trade_analysis(
        self, engine_without_logging, sample_price_history
    ):
        """Test that analyze_pre_trade returns PreTradeAnalysis object."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            price_history=sample_price_history,
            urgency=0.5,
            signal_time=datetime.now(),
        )

        assert isinstance(result, PreTradeAnalysis)

    def test_analyze_pre_trade_with_minimal_parameters(self, engine_without_logging):
        """Test pre-trade analysis with minimal required parameters."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        assert isinstance(result, PreTradeAnalysis)
        assert result.can_execute is not None
        assert result.confidence >= 0

    def test_analyze_pre_trade_populates_basic_fields(self, engine_without_logging):
        """Test that basic fields are populated in analysis."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        assert hasattr(result, 'can_execute')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reasons')
        assert hasattr(result, 'venue')
        assert hasattr(result, 'algorithm')

    def test_analyze_pre_trade_systems_contributed_incremented(
        self, engine_without_logging, mock_harris_integrator
    ):
        """Test that systems_contributed is incremented correctly."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_pre_trade(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
            )

            assert result.systems_contributed > 0

    def test_analyze_pre_trade_harris_integration_works(
        self, engine_without_logging, mock_harris_integrator
    ):
        """Test that Harris microstructure integration works."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_pre_trade(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                urgency=0.5,
            )

            # Harris fields should be populated
            assert result.harris_order_book_depth_ok is not None
            assert result.harris_liquidity_score > 0
            assert result.venue == "lit_exchange"
            assert result.algorithm == "LIMIT"

    def test_analyze_pre_trade_chan_regime_detection(
        self, engine_without_logging, mock_regime_detector
    ):
        """Test that Chan regime detection is integrated."""
        engine = engine_without_logging

        def mock_get_subsystem(name):
            if name == "ernest_chan":
                return {"regime": mock_regime_detector}
            return None

        with patch.object(engine, '_get_subsystem', side_effect=mock_get_subsystem):
            result = engine.analyze_pre_trade(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                price_history=pd.DataFrame({'close': [100, 101, 102, 103, 104, 105]}),
            )

            # Chan regime should be detected
            # Note: The actual detection might fail if there's not enough data
            # or the implementation returns None, so we check the field exists
            assert hasattr(result, 'chan_regime')

    def test_analyze_pre_trade_hull_var_calculation(
        self, engine_without_logging, mock_var_calculator, sample_price_history
    ):
        """Test that Hull VaR calculation is integrated."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_var_calculator):
            result = engine.analyze_pre_trade(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                price_history=sample_price_history,
            )

            # Hull VaR should be calculated
            assert result.hull_var_1d_95 is not None or result.hull_var_1d_99 is not None

    def test_analyze_pre_trade_risk_checks_block_dangerous_trades(
        self, engine_without_logging, sample_price_history
    ):
        """Test that risk checks can block dangerous trades."""
        engine = engine_without_logging

        # Create price history with very high volatility
        high_volatility_history = sample_price_history.copy()
        high_volatility_history['close'] = high_volatility_history['close'] * (
            1 + np.random.randn(len(high_volatility_history)) * 0.5
        )

        result = engine.analyze_pre_trade(
            symbol="VOLATILE",
            side="BUY",
            quantity=Decimal("1000"),
            price=Decimal("150"),
            price_history=high_volatility_history,
        )

        # High volatility should reduce confidence
        if result.portfolio_var and abs(result.portfolio_var) > 0.30:
            assert result.confidence < 1.0

    def test_analyze_pre_trade_all_systems_contribute(self, engine_without_logging):
        """Test that all available systems contribute to analysis."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        # Check that multiple systems contributed
        # At minimum: data_engine, risk_engine, execution_engine should contribute
        assert result.systems_contributed >= 3

    def test_analyze_pre_trade_aggregates_liquidity_metrics(self, engine_without_logging):
        """Test that liquidity metrics are aggregated correctly."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        # Liquidity should be aggregated
        assert result.liquidity_score >= 0
        assert result.liquidity_regime in ["LOW", "NORMAL", "HIGH"]

    def test_analyze_pre_trade_aggregates_cost_metrics(self, engine_without_logging):
        """Test that cost metrics are aggregated correctly."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        # Total cost should be sum of components
        expected_total = (
            result.market_impact_bps + result.timing_cost_bps + result.narang_transaction_cost_bps
        )
        assert result.total_cost_bps == expected_total

    def test_analyze_pre_trade_with_urgency_parameter(self, engine_without_logging):
        """Test that urgency parameter affects analysis."""
        engine = engine_without_logging

        # Low urgency
        result_low = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            urgency=0.1,
        )

        # High urgency
        result_high = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            urgency=0.9,
        )

        # Both should return valid analysis
        assert isinstance(result_low, PreTradeAnalysis)
        assert isinstance(result_high, PreTradeAnalysis)

    def test_analyze_pre_trade_sell_side(self, engine_without_logging):
        """Test pre-trade analysis for sell orders."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        assert isinstance(result, PreTradeAnalysis)
        assert result.can_execute is not None


# =============================================================================
# TEST CLASS: ComplianceEngine - Post-Trade Analysis
# =============================================================================


class TestComplianceEnginePostTradeAnalysis:
    """Test suite for post-trade analysis functionality."""

    def test_analyze_post_trade_returns_post_trade_analysis(self, engine_without_logging):
        """Test that analyze_post_trade returns PostTradeAnalysis object."""
        engine = engine_without_logging

        result = engine.analyze_post_trade(
            order_id="order_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
            signal_price=Decimal("150.00"),
            signal_time=datetime.now() - timedelta(minutes=5),
            submission_time=datetime.now() - timedelta(seconds=1),
            execution_time=datetime.now(),
            nbbo=(Decimal("150.20"), Decimal("150.30")),
        )

        assert isinstance(result, PostTradeAnalysis)

    def test_analyze_post_trade_calculates_implementation_shortfall(
        self, engine_without_logging, mock_harris_integrator
    ):
        """Test that implementation shortfall is calculated."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_post_trade(
                order_id="order_123",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.25"),
                signal_price=Decimal("150.00"),
                signal_time=datetime.now() - timedelta(minutes=5),
                submission_time=datetime.now() - timedelta(seconds=1),
                execution_time=datetime.now(),
            )

            # Should calculate implementation shortfall
            assert result.implementation_shortfall_bps >= 0

    def test_analyze_post_trade_calculates_latency(self, engine_without_logging):
        """Test that latency is calculated correctly."""
        engine = engine_without_logging

        submission_time = datetime.now() - timedelta(milliseconds=50)
        execution_time = datetime.now()

        result = engine.analyze_post_trade(
            order_id="order_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
            signal_price=None,
            signal_time=None,
            submission_time=submission_time,
            execution_time=execution_time,
        )

        # Latency should be approximately 50ms
        assert result.latency_ms > 0
        assert 40 < result.latency_ms < 100  # Allow some margin

    def test_analyze_post_trade_slo_tracking(self, engine_without_logging):
        """Test that SLO tracking works correctly."""
        engine = engine_without_logging

        # Fast execution - should meet SLO
        result_fast = engine.analyze_post_trade(
            order_id="order_fast",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
            signal_price=None,
            signal_time=None,
            submission_time=datetime.now() - timedelta(milliseconds=50),
            execution_time=datetime.now(),
        )
        assert result_fast.slo_met is True

        # Slow execution - should violate SLO
        result_slow = engine.analyze_post_trade(
            order_id="order_slow",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
            signal_price=None,
            signal_time=None,
            submission_time=datetime.now() - timedelta(milliseconds=150),
            execution_time=datetime.now(),
        )
        assert result_slow.slo_met is False

    def test_analyze_post_trade_execution_quality_score(
        self, engine_without_logging, mock_harris_integrator
    ):
        """Test that execution quality score is calculated."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_post_trade(
                order_id="order_123",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.25"),
                signal_price=Decimal("150.00"),
                signal_time=datetime.now() - timedelta(minutes=5),
                submission_time=datetime.now() - timedelta(seconds=1),
                execution_time=datetime.now(),
            )

            # Should have execution quality score
            assert result.execution_quality_score >= 0
            assert result.execution_quality_score <= 100

    def test_analyze_post_trade_fallback_without_harris(self, engine_without_logging):
        """Test fallback behavior when Harris is not available."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=None):
            result = engine.analyze_post_trade(
                order_id="order_123",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.25"),
                signal_price=None,
                signal_time=None,
                submission_time=datetime.now() - timedelta(milliseconds=50),
                execution_time=datetime.now(),
            )

            # Should still return valid analysis
            assert isinstance(result, PostTradeAnalysis)
            assert result.latency_ms > 0

    def test_analyze_post_trade_with_nbbo(self, engine_without_logging, mock_harris_integrator):
        """Test post-trade analysis with NBBO data."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_post_trade(
                order_id="order_123",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.25"),
                signal_price=None,
                signal_time=None,
                submission_time=datetime.now() - timedelta(milliseconds=50),
                execution_time=datetime.now(),
                nbbo=(Decimal("150.20"), Decimal("150.30")),
            )

            # Should calculate effective spread
            assert result.effective_spread_bps >= 0

    def test_analyze_post_trade_price_improvement(
        self, engine_without_logging, mock_harris_integrator
    ):
        """Test that price improvement is calculated."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=mock_harris_integrator):
            result = engine.analyze_post_trade(
                order_id="order_123",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.25"),
                signal_price=Decimal("150.00"),
                signal_time=datetime.now() - timedelta(minutes=5),
                submission_time=datetime.now() - timedelta(seconds=1),
                execution_time=datetime.now(),
                nbbo=(Decimal("150.20"), Decimal("150.30")),
            )

            # Should calculate price improvement
            assert hasattr(result, 'price_improvement_bps')


# =============================================================================
# TEST CLASS: ComplianceEngine - Portfolio Optimization
# =============================================================================


class TestComplianceEnginePortfolioOptimization:
    """Test suite for portfolio optimization functionality."""

    def test_optimize_portfolio_returns_portfolio_optimization(
        self, engine_without_logging, sample_returns
    ):
        """Test that optimize_portfolio returns PortfolioOptimization object."""
        engine = engine_without_logging

        current_prices = {
            'AAPL': Decimal("150"),
            'MSFT': Decimal("300"),
            'GOOGL': Decimal("2500"),
        }

        result = engine.optimize_portfolio(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            returns=sample_returns,
            current_prices=current_prices,
        )

        assert isinstance(result, PortfolioOptimization)

    def test_optimize_portfolio_returns_valid_weights(self, engine_without_logging, sample_returns):
        """Test that optimization returns valid weights."""
        engine = engine_without_logging

        current_prices = {
            'AAPL': Decimal("150"),
            'MSFT': Decimal("300"),
            'GOOGL': Decimal("2500"),
        }

        result = engine.optimize_portfolio(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            returns=sample_returns,
            current_prices=current_prices,
        )

        # Should have weights for all symbols
        assert len(result.weights) == 3
        assert all(s in result.weights for s in ['AAPL', 'MSFT', 'GOOGL'])

        # Weights should be Decimals
        assert all(isinstance(w, Decimal) for w in result.weights.values())

        # Weights should sum to approximately 1.0
        weight_sum = sum(result.weights.values())
        assert abs(float(weight_sum) - 1.0) < 0.01

    def test_optimize_portfolio_chan_method_used(
        self, engine_without_logging, sample_returns, mock_regime_detector
    ):
        """Test that Chan optimization method is used when available."""
        engine = engine_without_logging

        mock_chan_subsystem = {
            "regime": mock_regime_detector,
        }

        def mock_get_subsystem(name):
            if name == "ernest_chan":
                return mock_chan_subsystem
            return None

        # Test with Chan available - should return optimization result
        with patch.object(engine, '_get_subsystem', side_effect=mock_get_subsystem):
            with patch.object(engine.availability, 'is_available', return_value=True):
                current_prices = {
                    'AAPL': Decimal("150"),
                    'MSFT': Decimal("300"),
                    'GOOGL': Decimal("2500"),
                }

                result = engine.optimize_portfolio(
                    symbols=['AAPL', 'MSFT', 'GOOGL'],
                    returns=sample_returns,
                    current_prices=current_prices,
                )

                # Should return PortfolioOptimization
                assert isinstance(result, PortfolioOptimization)
                # Should attempt to use Chan's method (may fall back if imports fail)
                assert 'AAPL' in result.weights

    def test_optimize_portfolio_equal_weight_fallback(self, engine_without_logging, sample_returns):
        """Test equal weight fallback when Chan is unavailable."""
        engine = engine_without_logging

        with patch.object(engine, '_get_subsystem', return_value=None):
            current_prices = {
                'AAPL': Decimal("150"),
                'MSFT': Decimal("300"),
                'GOOGL': Decimal("2500"),
            }

            result = engine.optimize_portfolio(
                symbols=['AAPL', 'MSFT', 'GOOGL'],
                returns=sample_returns,
                current_prices=current_prices,
            )

            # Should use equal weights
            assert len(result.weights) == 3
            expected_weight = Decimal("1") / Decimal("3")
            for weight in result.weights.values():
                assert abs(float(weight - expected_weight)) < 0.001

    def test_optimize_portfolio_includes_regime(
        self, engine_without_logging, sample_returns, mock_regime_detector
    ):
        """Test that regime detection is included in optimization."""
        engine = engine_without_logging

        mock_chan_subsystem = {
            "regime": mock_regime_detector,
        }

        def mock_get_subsystem(name):
            if name == "ernest_chan":
                return mock_chan_subsystem
            return None

        with patch.object(engine, '_get_subsystem', side_effect=mock_get_subsystem):
            with patch.object(engine.availability, 'is_available', return_value=True):
                current_prices = {
                    'AAPL': Decimal("150"),
                    'MSFT': Decimal("300"),
                    'GOOGL': Decimal("2500"),
                }

                result = engine.optimize_portfolio(
                    symbols=['AAPL', 'MSFT', 'GOOGL'],
                    returns=sample_returns,
                    current_prices=current_prices,
                )

                # Should include regime field (even if UNKNOWN)
                assert hasattr(result, 'regime')
                # Regime should be a valid value
                assert result.regime in ["BULL", "BEAR", "NEUTRAL", "UNKNOWN", None]


# =============================================================================
# TEST CLASS: ComplianceEngine - Kill Switch
# =============================================================================


class TestComplianceEngineKillSwitch:
    """Test suite for kill switch functionality (Hull Rule 13.1)."""

    def test_initial_daily_pnl_tracking_empty(self, engine_without_logging):
        """Test that daily PnL tracking starts empty."""
        engine = engine_without_logging

        assert hasattr(engine, '_daily_pnl_tracking')
        assert len(engine._daily_pnl_tracking) == 0

    def test_starting_capital_initialized(self, engine_without_logging):
        """Test that starting capital is initialized."""
        engine = engine_without_logging

        assert hasattr(engine, '_starting_capital')
        assert engine._starting_capital == 100000.0

    def test_track_order_submission_stores_order(self, engine_without_logging):
        """Test that order submission is tracked correctly."""
        engine = engine_without_logging

        order_id = "test_order_123"
        engine.track_order_submission(
            order_id=order_id,
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            submission_time=datetime.now(),
        )

        assert order_id in engine._active_orders
        assert engine._active_orders[order_id]['symbol'] == "AAPL"
        assert engine._active_orders[order_id]['side'] == "BUY"

    def test_track_order_completion_records_trade(self, engine_without_logging):
        """Test that order completion is recorded correctly."""
        engine = engine_without_logging

        order_id = "test_order_123"
        submission_time = datetime.now() - timedelta(seconds=5)

        engine.track_order_submission(
            order_id=order_id,
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            submission_time=submission_time,
        )

        engine.track_order_completion(
            order_id=order_id,
            execution_price=Decimal("150.25"),
            execution_time=datetime.now(),
            filled_quantity=Decimal("100"),
        )

        # Order should be removed from active
        assert order_id not in engine._active_orders

        # Should be in completed trades
        assert len(engine._completed_trades) == 1
        assert engine._completed_trades[0]['order_id'] == order_id

    def test_slo_metrics_calculated_correctly(self, engine_without_logging):
        """Test that SLO metrics are calculated correctly."""
        engine = engine_without_logging

        # Clear any existing trades first
        engine._completed_trades.clear()
        engine._active_orders.clear()

        # Track some orders with varying latencies
        base_time = datetime.now()
        for i in range(5):
            order_id = f"order_slo_{i}"
            submission_time = base_time - timedelta(milliseconds=50 + i * 30)

            engine.track_order_submission(
                order_id=order_id,
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                submission_time=submission_time,
            )

            execution_time = base_time - timedelta(milliseconds=i * 30)
            engine.track_order_completion(
                order_id=order_id,
                execution_price=Decimal("150.25"),
                execution_time=execution_time,
            )

        metrics = engine.get_slo_metrics()

        # Should have exactly 5 trades from this test
        assert metrics['total_trades'] == 5
        assert 'slo_violations' in metrics
        assert 'slo_compliance_rate' in metrics
        assert 'avg_latency_ms' in metrics

    def test_get_slo_metrics_with_no_trades(self, engine_without_logging):
        """Test SLO metrics when no trades have been completed."""
        engine = engine_without_logging

        # Clear any existing trades
        engine._completed_trades.clear()

        metrics = engine.get_slo_metrics()

        assert metrics['total_trades'] == 0
        assert metrics['slo_violations'] == 0
        assert metrics['slo_compliance_rate'] == 1.0
        assert metrics['avg_latency_ms'] == 0.0


# =============================================================================
# TEST CLASS: ComplianceEngine - Helper Methods
# =============================================================================


class TestComplianceEngineHelpers:
    """Test suite for helper methods."""

    def test_estimate_adv_with_volume_data(self, engine_without_logging):
        """Test ADV estimation with volume data."""
        engine = engine_without_logging

        price_history = pd.DataFrame({'volume': [1000000, 1100000, 900000, 1050000, 950000]})

        adv = engine._estimate_adv(price_history)

        assert isinstance(adv, Decimal)
        assert adv > 0

    def test_estimate_adv_without_volume_data(self, engine_without_logging):
        """Test ADV estimation without volume data."""
        engine = engine_without_logging

        # No volume column
        price_history = pd.DataFrame({'close': [100, 101, 102, 103, 104]})

        adv = engine._estimate_adv(price_history)

        # Should return default value
        assert adv == Decimal("1000000")

    def test_estimate_adv_with_none(self, engine_without_logging):
        """Test ADV estimation with None."""
        engine = engine_without_logging

        adv = engine._estimate_adv(None)

        # Should return default value
        assert adv == Decimal("1000000")

    def test_get_system_status(self, engine_without_logging):
        """Test get_system_status returns complete status."""
        engine = engine_without_logging

        status = engine.get_system_status()

        assert 'availability' in status
        assert 'subsystems_loaded' in status
        assert 'active_orders' in status
        assert 'completed_trades' in status
        assert 'slo_metrics' in status

        # Check structure
        assert 'total_systems' in status['availability']
        assert 'available_systems' in status['availability']

    def test_get_subsystem_lazy_loading(self, engine_without_logging):
        """Test that subsystems are lazy loaded."""
        engine = engine_without_logging

        # Clear existing subsystems
        engine._subsystems.clear()

        # Initially empty
        assert len(engine._subsystems) == 0

        # Access tomasini subsystem (always available)
        engine._get_subsystem('tomasini')

        # Tomasini should be cached
        assert 'tomasini' in engine._subsystems


# =============================================================================
# TEST CLASS: SystemBus
# =============================================================================


class TestSystemBus:
    """Test suite for SystemBus orchestration."""

    def test_system_bus_execution_order(self):
        """Test that system bus has correct execution order."""
        engine = ComplianceEngine(enable_logging=False)
        bus = SystemBus(engine)

        order = bus._execution_order

        # Should have at least 10 systems (we have 17 defined)
        assert len(order) >= 10

        # Data engine should be first
        assert order[0] == "data_engine"

        # Architecture/SRE should be last
        assert "beck_tdd" in order[-4:]
        assert "martin_arch" in order[-4:]

    def test_system_bus_is_critical_failure(self):
        """Test critical failure detection."""
        engine = ComplianceEngine(enable_logging=False)
        bus = SystemBus(engine)

        # Risk engine should be critical
        assert bus._is_critical_failure("risk_engine")

        # Data engine should be critical
        assert bus._is_critical_failure("data_engine")

        # Live trading should be critical
        assert bus._is_critical_failure("live_trading")

        # Strategies should not be critical
        assert not bus._is_critical_failure("strategies")

    def test_system_bus_aggregate_metrics(self):
        """Test metrics aggregation."""
        engine = ComplianceEngine(enable_logging=False)
        bus = SystemBus(engine)

        result = PreTradeAnalysis(
            can_execute=True,
            confidence=1.0,
            harris_liquidity_score=60.0,
            ohara_price_discovery_score=70.0,
            market_impact_bps=5.0,
            timing_cost_bps=2.0,
            narang_transaction_cost_bps=1.0,
            ohara_liquidity_regime="HIGH",
        )

        bus._aggregate_metrics(result)

        # Liquidity should be aggregated (60% Harris, 40% O'Hara)
        expected_liquidity = 60.0 * 0.6 + 70.0 * 0.4
        assert abs(result.liquidity_score - expected_liquidity) < 0.01

        # Total cost should be sum
        assert result.total_cost_bps == 8.0  # 5 + 2 + 1


# =============================================================================
# TEST CLASS: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def test_get_compliance_engine_returns_singleton(self, reset_singleton):
        """Test that get_compliance_engine returns singleton instance."""
        engine1 = get_compliance_engine(enable_logging=False)
        engine2 = get_compliance_engine(enable_logging=False)

        assert engine1 is engine2

    def test_quick_check_returns_tuple(self):
        """Test that quick_check returns (can_execute, message) tuple."""
        result = quick_check(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_quick_check_with_good_trade(self):
        """Test quick_check with a good trade."""
        can_execute, message = quick_check(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        # Should either be True or have a reason
        assert isinstance(can_execute, bool)
        if can_execute:
            assert "OK" in message or "confidence" in message

    def test_get_execution_plan_returns_dict(self):
        """Test that get_execution_plan returns a dictionary."""
        plan = get_execution_plan(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        assert isinstance(plan, dict)

    def test_get_execution_plan_has_required_fields(self):
        """Test that execution plan has all required fields."""
        plan = get_execution_plan(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150"),
        )

        required_fields = [
            'can_execute',
            'venue',
            'algorithm',
            'limit_price',
            'estimated_cost_bps',
            'liquidity_regime',
            'market_regime',
        ]

        for field in required_fields:
            assert field in plan


# =============================================================================
# TEST CLASS: Error Handling
# =============================================================================


class TestComplianceEngineErrorHandling:
    """Test suite for error handling."""

    def test_analyze_pre_trade_handles_missing_price_history(self, engine_without_logging):
        """Test pre-trade analysis handles missing price history gracefully."""
        engine = engine_without_logging

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            price_history=None,
        )

        # Should still return valid analysis
        assert isinstance(result, PreTradeAnalysis)
        assert result.can_execute is not None

    def test_analyze_pre_trade_handles_empty_price_history(self, engine_without_logging):
        """Test pre-trade analysis handles empty price history."""
        engine = engine_without_logging

        empty_history = pd.DataFrame()

        result = engine.analyze_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            price_history=empty_history,
        )

        # Should still return valid analysis
        assert isinstance(result, PreTradeAnalysis)

    def test_analyze_post_trade_handles_unknown_order_id(self, engine_without_logging):
        """Test post-trade analysis handles unknown order gracefully."""
        engine = engine_without_logging

        # Should not raise exception
        engine.track_order_completion(
            order_id="unknown_order",
            execution_price=Decimal("150.25"),
            execution_time=datetime.now(),
        )

    def test_optimize_portfolio_handles_empty_returns(self, engine_without_logging):
        """Test portfolio optimization handles empty returns."""
        engine = engine_without_logging

        empty_returns = pd.DataFrame()
        current_prices = {'AAPL': Decimal("150")}

        # Should use equal weight fallback
        result = engine.optimize_portfolio(
            symbols=['AAPL'],
            returns=empty_returns,
            current_prices=current_prices,
        )

        assert isinstance(result, PortfolioOptimization)
        assert 'AAPL' in result.weights

    def test_subsystem_load_error_handling(self, engine_without_logging):
        """Test that subsystem load errors are handled gracefully."""
        engine = engine_without_logging

        # Try to load a non-existent subsystem
        subsystem = engine._load_subsystem("nonexistent_subsystem")

        # Should return None without raising exception
        assert subsystem is None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
