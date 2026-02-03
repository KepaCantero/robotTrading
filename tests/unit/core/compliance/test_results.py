"""
Unit tests for results.py
=========================

Tests for compliance check result data classes.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.core.compliance.results import (
    CheckResult,
    PreTradeCheckResult,
    PostTradeCheckResult,
    OptimizeResult,
    ComprehensivePreTradeAnalysis,
    ComprehensivePostTradeAnalysis,
    PortfolioOptimizationResult,
)


class TestCheckResult:
    """Tests for CheckResult base class."""

    def test_create_check_result_default(self):
        """Test creating CheckResult with default values."""
        result = CheckResult(passed=True, confidence=1.0)
        assert result.passed is True
        assert result.confidence == 1.0
        assert result.reasons == []
        assert result.risk_factors == {}

    def test_create_check_result_with_values(self):
        """Test creating CheckResult with custom values."""
        result = CheckResult(
            passed=True,
            confidence=0.85,
            reasons=["Reason 1", "Reason 2"],
            risk_factors={"factor1": 0.5},
        )
        assert result.passed is True
        assert result.confidence == 0.85
        assert len(result.reasons) == 2
        assert result.risk_factors["factor1"] == 0.5

    def test_check_result_to_dict(self):
        """Test CheckResult serialization to dict."""
        result = CheckResult(
            passed=True,
            confidence=0.9,
            reasons=["Test reason"],
            risk_factors={"risk": 0.1},
        )
        data = result.to_dict()
        assert data["passed"] is True
        assert data["confidence"] == 0.9
        assert data["reasons"] == ["Test reason"]
        assert data["risk_factors"] == {"risk": 0.1}

    def test_check_result_immutability(self):
        """Test that CheckResult is immutable (frozen=True)."""
        result = CheckResult(passed=True, confidence=1.0)
        with pytest.raises(Exception):  # FrozenInstanceError
            result.passed = False


class TestPreTradeCheckResult:
    """Tests for PreTradeCheckResult class."""

    def test_create_pre_trade_result_default(self):
        """Test creating PreTradeCheckResult with defaults."""
        result = PreTradeCheckResult(
            passed=True,
            confidence=1.0,
            can_execute=True,
        )
        assert result.can_execute is True
        assert result.market_regime is None
        assert result.alpha_signal is None

    def test_create_pre_trade_result_full(self):
        """Test creating PreTradeCheckResult with all fields."""
        result = PreTradeCheckResult(
            passed=True,
            confidence=0.9,
            can_execute=True,
            market_regime="BULL",
            regime_confidence=0.8,
            alpha_signal=0.75,
            alpha_decay_rate=0.01,
            recommended_holding_period=5,
            order_book_depth_ok=True,
            liquidity_score=80.0,
            liquidity_regime="HIGH",
            flow_toxicity=0.2,
            vpin=0.15,
            pin=0.1,
            estimated_market_impact_bps=5.0,
            estimated_timing_cost_bps=2.0,
            estimated_total_cost_bps=7.0,
            recommended_venue="lit_exchange",
            recommended_algorithm="LIMIT",
            recommended_limit_price=Decimal("100.50"),
            var_1d_95=0.03,
            beta=1.2,
        )
        assert result.market_regime == "BULL"
        assert result.alpha_signal == 0.75
        assert result.liquidity_score == 80.0
        assert result.recommended_limit_price == Decimal("100.50")

    def test_pre_trade_result_to_dict(self):
        """Test PreTradeCheckResult serialization."""
        result = PreTradeCheckResult(
            passed=True,
            confidence=1.0,
            can_execute=True,
            market_regime="BULL",
            recommended_limit_price=Decimal("100.50"),
        )
        data = result.to_dict()
        assert data["can_execute"] is True
        assert data["market_regime"] == "BULL"
        assert data["recommended_limit_price"] == "100.50"


class TestPostTradeCheckResult:
    """Tests for PostTradeCheckResult class."""

    def test_create_post_trade_result_default(self):
        """Test creating PostTradeCheckResult with defaults."""
        result = PostTradeCheckResult(
            passed=True,
            confidence=1.0,
            order_id="test-order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
        )
        assert result.order_id == "test-order"
        assert result.symbol == "AAPL"
        assert result.side == "BUY"
        assert result.quantity == Decimal("100")

    def test_post_trade_result_full(self):
        """Test creating PostTradeCheckResult with all fields."""
        result = PostTradeCheckResult(
            passed=True,
            confidence=1.0,
            order_id="order-1",
            symbol="MSFT",
            side="SELL",
            quantity=Decimal("50"),
            execution_price=Decimal("200.00"),
            implementation_shortfall_bps=10.5,
            market_impact_bps=5.0,
            timing_cost_bps=5.5,
            effective_spread_bps=2.0,
            execution_quality_score=85.0,
            price_improvement_bps=1.5,
            latency_ms=50.0,
            fill_rate=100.0,
        )
        assert result.implementation_shortfall_bps == 10.5
        assert result.execution_quality_score == 85.0
        assert result.latency_ms == 50.0

    def test_post_trade_result_to_dict(self):
        """Test PostTradeCheckResult serialization."""
        result = PostTradeCheckResult(
            passed=True,
            confidence=1.0,
            order_id="order-1",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
        )
        data = result.to_dict()
        assert data["order_id"] == "order-1"
        assert data["quantity"] == "100"
        assert data["execution_price"] == "150.00"


class TestOptimizeResult:
    """Tests for OptimizeResult class."""

    def test_create_optimize_result_default(self):
        """Test creating OptimizeResult with defaults."""
        result = OptimizeResult(passed=True, confidence=1.0)
        assert result.weights == {}
        assert result.expected_return == 0.0
        assert result.expected_risk == 0.0

    def test_create_optimize_result_with_weights(self):
        """Test creating OptimizeResult with weights."""
        result = OptimizeResult(
            passed=True,
            confidence=1.0,
            weights={"AAPL": 0.4, "MSFT": 0.3, "GOOGL": 0.3},
            expected_return=0.12,
            expected_risk=0.15,
            sharpe_ratio=0.8,
            factor_exposures={"momentum": 0.5, "value": 0.3},
            regime="BULL",
            regime_adjusted=True,
        )
        assert len(result.weights) == 3
        assert result.expected_return == 0.12
        assert result.regime == "BULL"
        assert result.regime_adjusted is True

    def test_optimize_result_to_dict(self):
        """Test OptimizeResult serialization."""
        result = OptimizeResult(
            passed=True,
            confidence=1.0,
            weights={"AAPL": 0.6, "MSFT": 0.4},
            expected_return=0.10,
            expected_risk=0.12,
            sharpe_ratio=0.83,
        )
        data = result.to_dict()
        assert data["weights"]["AAPL"] == 0.6
        assert data["expected_return"] == 0.10


class TestLegacyCompatibility:
    """Tests for legacy compatibility wrappers."""

    def test_comprehensive_pre_trade_analysis(self):
        """Test ComprehensivePreTradeAnalysis compatibility."""
        result = ComprehensivePreTradeAnalysis(
            passed=True,
            confidence=1.0,
            can_execute=True,
        )
        assert isinstance(result, PreTradeCheckResult)

    def test_comprehensive_post_trade_analysis(self):
        """Test ComprehensivePostTradeAnalysis compatibility."""
        result = ComprehensivePostTradeAnalysis(
            passed=True,
            confidence=1.0,
            order_id="order-1",
        )
        assert isinstance(result, PostTradeCheckResult)

    def test_portfolio_optimization_result_with_decimal_weights(self):
        """Test PortfolioOptimizationResult with Decimal weights."""
        result = PortfolioOptimizationResult(
            passed=True,
            confidence=1.0,
            weights={"AAPL": Decimal("0.6"), "MSFT": Decimal("0.4")},
        )
        data = result.to_dict()
        assert data["weights"]["AAPL"] == "0.6"
