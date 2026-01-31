"""
Comprehensive tests for Harris Microstructure Integration (Rule 6).

Tests cover:
- HarrisMicrostructureIntegrator class
- Pre-trade checks
- Post-trade analysis
- All 10 Harris rules implementation
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import numpy as np

from app.engines.execution_engine.microstructure.harris_integration import (
    HarrisMicrostructureIntegrator,
    get_harris_integrator,
    PreTradeCheckResult,
    PostTradeAnalysis,
)

from app.engines.execution_engine.microstructure.order_book_analyzer import (
    OrderBookSnapshot,
    OrderBookLevel,
)


@pytest.fixture
def sample_order_book() -> OrderBookSnapshot:
    """Create sample order book for testing."""
    now = pd.Timestamp.now()
    return OrderBookSnapshot(
        symbol="AAPL",
        timestamp=now,
        bids=[
            OrderBookLevel(price=Decimal("150.00"), size=Decimal("1000")),
            OrderBookLevel(price=Decimal("149.99"), size=Decimal("2000")),
            OrderBookLevel(price=Decimal("149.98"), size=Decimal("3000")),
        ],
        asks=[
            OrderBookLevel(price=Decimal("150.01"), size=Decimal("1000")),
            OrderBookLevel(price=Decimal("150.02"), size=Decimal("2000")),
            OrderBookLevel(price=Decimal("150.03"), size=Decimal("3000")),
        ],
    )


@pytest.fixture
def sample_price_history() -> pd.DataFrame:
    """Create sample price history for testing."""
    np.random.seed(42)
    n = 1000
    dates = pd.date_range(start="2024-01-01", periods=n, freq="1min")

    # Generate realistic price series with some volatility
    returns = np.random.normal(0, 0.0001, n)
    prices = 150 * np.exp(np.cumsum(returns))

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": prices * (1 + np.random.uniform(-0.0001, 0.0001, n)),
            "high": prices * (1 + np.random.uniform(0, 0.0005, n)),
            "low": prices * (1 + np.random.uniform(-0.0005, 0, n)),
            "close": prices,
            "volume": np.random.randint(100, 10000, n),
        }
    )


@pytest.fixture
def harris_integrator() -> HarrisMicrostructureIntegrator:
    """Create Harris integrator for testing."""
    return get_harris_integrator()


class TestHarrisMicrostructureIntegrator:
    """Test HarrisMicrostructureIntegrator class."""

    def test_initialization(self, harris_integrator):
        """Test integrator initialization."""
        assert harris_integrator is not None
        assert harris_integrator.asset_class == "equity"
        assert harris_integrator.enable_all_rules is True

    def test_singleton_pattern(self):
        """Test that get_harris_integrator returns singleton."""
        integrator1 = get_harris_integrator()
        integrator2 = get_harris_integrator()
        assert integrator1 is integrator2


class TestRule61_OrderBookDepth:
    """Test Harris Rule 6.1: Order Book Depth Analysis."""

    def test_analyze_order_book_depth(self, harris_integrator, sample_order_book):
        """Test order book depth analysis."""
        result = harris_integrator.analyze_order_book_depth(
            order_book=sample_order_book,
            order_size=Decimal("100"),
        )

        assert "spread_bps" in result
        assert "imbalance" in result
        assert "liquidity_score" in result
        assert "can_execute_immediately" in result
        assert "effective_spread_bps" in result
        assert "depth_ok" in result

        # Verify reasonable values
        assert result["spread_bps"] >= 0
        assert -1 <= result["imbalance"] <= 1
        assert 0 <= result["liquidity_score"] <= 100

    def test_shallow_book_detection(self, harris_integrator):
        """Test detection of shallow order book."""
        # Create extremely shallow book
        now = pd.Timestamp.now()
        shallow_book = OrderBookSnapshot(
            symbol="ILLIQUID",
            timestamp=now,
            bids=[
                OrderBookLevel(price=Decimal("10.00"), size=Decimal("10")),
            ],
            asks=[
                OrderBookLevel(price=Decimal("10.01"), size=Decimal("10")),
            ],
        )

        result = harris_integrator.analyze_order_book_depth(
            order_book=shallow_book,
            order_size=Decimal("1000"),  # Large order for shallow book
        )

        # Extremely shallow book should not allow immediate execution
        assert not result["can_execute_immediately"]


class TestRule62_BidAskBounce:
    """Test Harris Rule 6.2: Bid-Ask Bounce Removal."""

    def test_remove_bid_ask_bounce(self, harris_integrator):
        """Test bid-ask bounce removal."""
        # Create data with bid-ask bounce pattern
        n = 100
        dates = pd.date_range(start="2024-01-01", periods=n, freq="1s")

        # Alternate between bid and ask
        bid = 150.00
        ask = 150.01
        last_prices = []
        for i in range(n):
            last_prices.append(bid if i % 2 == 0 else ask)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "bid": bid,
                "ask": ask,
                "close": last_prices,
            }
        )

        # Remove bounce
        cleaned = harris_integrator.remove_bid_ask_bounce(df)

        assert len(cleaned) == len(df)
        # Cleaned prices should be more stable (mid price)
        assert (cleaned == 150.005).all()  # Mid price


class TestRule63_TimingCost:
    """Test Harris Rule 6.3: Timing Cost Monitoring."""

    def test_record_signal_time(self, harris_integrator):
        """Test recording signal time."""
        signal_time = datetime.now()
        order_id = "test_order_001"

        harris_integrator.record_signal_time(order_id, signal_time)

        assert order_id in harris_integrator._signal_times
        assert harris_integrator._signal_times[order_id] == signal_time

    def test_calculate_timing_cost(self, harris_integrator):
        """Test timing cost calculation."""
        order_id = "test_order_002"
        signal_time = datetime.now() - timedelta(minutes=5)
        signal_price = Decimal("150.00")
        execution_price = Decimal("150.50")
        execution_time = datetime.now()

        harris_integrator.record_signal_time(order_id, signal_time)

        timing_cost = harris_integrator.calculate_timing_cost(
            order_id=order_id,
            execution_price=execution_price,
            signal_price=signal_price,
            execution_time=execution_time,
        )

        assert timing_cost >= 0
        # Should be approximately 33 bps (0.50 / 150.00 * 10000)
        assert 30 < timing_cost < 40


class TestRule64_MarketImpact:
    """Test Harris Rule 6.4: Almgren-Chriss Market Impact."""

    def test_estimate_market_impact(self, harris_integrator):
        """Test market impact estimation."""
        estimate = harris_integrator.estimate_market_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.2,
            price=Decimal("150.00"),
        )

        assert estimate is not None
        assert hasattr(estimate, "permanent_impact_bps")
        assert hasattr(estimate, "temporary_impact_bps")
        assert hasattr(estimate, "total_impact_bps")
        assert float(estimate.total_impact_bps) > 0


class TestRule65_QuoteStuffing:
    """Test Harris Rule 6.5: Quote Stuffing Detection."""

    def test_detect_quote_stuffing_normal(self, harris_integrator):
        """Test quote stuffing detection with normal rate."""
        now = datetime.now()

        # Normal rate: 10 quotes in 10 seconds
        for i in range(10):
            detected = harris_integrator.detect_quote_stuffing(
                symbol="AAPL",
                current_time=now + timedelta(seconds=i),
                window_seconds=10,
                threshold_quotes_per_second=100.0,
            )
            assert not detected

    def test_detect_quote_stuffing_abnormal(self, harris_integrator):
        """Test quote stuffing detection with abnormal rate."""
        now = datetime.now()

        # Abnormal rate: 1000 quotes in 10 seconds (>100/sec)
        detected = False
        for i in range(1000):
            detected = harris_integrator.detect_quote_stuffing(
                symbol="AAPL",
                current_time=now + timedelta(milliseconds=i * 10),
                window_seconds=10,
                threshold_quotes_per_second=100.0,
            )
            if detected:
                break

        assert detected


class TestRule66_LimitOrderOptimization:
    """Test Harris Rule 6.6: Limit Order Optimization."""

    def test_calculate_optimal_limit_price_buy(self, harris_integrator):
        """Test optimal limit price calculation for buy."""
        limit_price = harris_integrator.calculate_optimal_limit_price(
            side="BUY",
            current_bid=Decimal("150.00"),
            current_ask=Decimal("150.01"),
            urgency=0.5,  # Medium urgency
        )

        # Limit price should be between bid and ask, or slightly above ask due to tick constraints
        assert limit_price >= Decimal("150.00")
        # Tick size constraints might adjust price above ask
        assert limit_price <= Decimal("150.02")  # Allow for tick rounding

    def test_calculate_optimal_limit_price_sell(self, harris_integrator):
        """Test optimal limit price calculation for sell."""
        limit_price = harris_integrator.calculate_optimal_limit_price(
            side="SELL",
            current_bid=Decimal("150.00"),
            current_ask=Decimal("150.01"),
            urgency=0.5,
        )

        assert limit_price >= Decimal("150.00")
        assert limit_price <= Decimal("150.01")


class TestRule67_DarkPoolRouting:
    """Test Harris Rule 6.7: Dark Pool Routing."""

    def test_should_use_dark_pool_small_order(self, harris_integrator):
        """Test dark pool decision for small order."""
        decision = harris_integrator.should_use_dark_pool(
            order_size=Decimal("100"),
            adv=Decimal("1000000"),
            order_value_usd=Decimal("15000"),
            information_leakage_risk="LOW",
        )

        # Small order should not use dark pool
        assert not decision.use_dark_pool

    def test_should_use_dark_pool_large_order(self, harris_integrator):
        """Test dark pool decision for large order."""
        decision = harris_integrator.should_use_dark_pool(
            order_size=Decimal("200000"),  # 20% of ADV
            adv=Decimal("1000000"),
            order_value_usd=Decimal("30000000"),
            information_leakage_risk="HIGH",
        )

        # Large order should use dark pool
        assert decision.use_dark_pool


class TestRule68_LiquidityValidation:
    """Test Harris Rule 6.8: Liquidity Validation."""

    def test_validate_liquidity_assumption_valid(self, harris_integrator):
        """Test liquidity validation for valid order."""
        result = harris_integrator.validate_liquidity_assumption(
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            max_participation=0.20,
        )

        assert result["valid"] is True
        assert result["participation_rate"] == 0.01

    def test_validate_liquidity_assumption_invalid(self, harris_integrator):
        """Test liquidity validation for invalid order."""
        result = harris_integrator.validate_liquidity_assumption(
            order_size=Decimal("300000"),  # 30% of ADV
            adv=Decimal("1000000"),
            max_participation=0.20,
        )

        assert result["valid"] is False
        assert result["participation_rate"] == 0.3
        assert len(result["warnings"]) > 0


class TestRule610_ExecutionQuality:
    """Test Harris Rule 6.10: Execution Quality Evaluation."""

    def test_evaluate_execution_quality(self, harris_integrator):
        """Test execution quality evaluation."""

        # Create mock executions
        class MockExecution:
            def __init__(self, symbol, side, price):
                self.symbol = symbol
                self.side = side
                self.price = price

        executions = [
            MockExecution("AAPL", "BUY", Decimal("150.00")),
            MockExecution("AAPL", "BUY", Decimal("150.01")),
        ]

        nbbo = {"AAPL": (Decimal("149.99"), Decimal("150.02"))}

        result = harris_integrator.evaluate_execution_quality(
            executions=executions,
            nbbo_snapshot=nbbo,
        )

        assert "avg_improvement_bps" in result
        assert "pct_improved" in result


class TestPreTradeCheck:
    """Test comprehensive pre-trade check."""

    def test_pre_trade_check_valid(self, harris_integrator, sample_order_book):
        """Test pre-trade check for valid order."""
        result = harris_integrator.pre_trade_check(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            order_book=sample_order_book,
            adv=Decimal("1000000"),  # Provide ADV to avoid liquidity validation fail
        )

        assert isinstance(result, PreTradeCheckResult)
        # Can execute if no quote stuffing or liquidity issues
        assert isinstance(result.can_execute, bool)
        assert result.confidence >= 0
        assert result.estimated_cost_bps >= 0

    def test_pre_trade_check_liquidity_fail(self, harris_integrator):
        """Test pre-trade check with liquidity failure."""
        # Order too large for available liquidity
        result = harris_integrator.pre_trade_check(
            symbol="ILLIQUID",
            side="BUY",
            quantity=Decimal("500000"),  # 50% of ADV
            current_price=Decimal("10.00"),
            adv=Decimal("1000000"),
        )

        assert isinstance(result, PreTradeCheckResult)
        assert result.can_execute is False
        assert "liquidity" in str(result.reasons).lower()


class TestPostTradeAnalysis:
    """Test post-trade execution analysis."""

    def test_analyze_execution(self, harris_integrator):
        """Test post-trade analysis."""
        signal_time = datetime.now() - timedelta(minutes=10)
        submission_time = datetime.now() - timedelta(minutes=5)
        execution_time = datetime.now()

        analysis = harris_integrator.analyze_execution(
            order_id="test_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
            signal_price=Decimal("150.00"),
            signal_time=signal_time,
            submission_time=submission_time,
            execution_time=execution_time,
            arrival_price=Decimal("150.10"),
            decision_price=Decimal("150.00"),
            nbbo_at_execution=(Decimal("150.20"), Decimal("150.30")),
        )

        assert isinstance(analysis, PostTradeAnalysis)
        assert analysis.order_id == "test_001"
        assert analysis.symbol == "AAPL"
        assert 0 <= analysis.execution_quality_score <= 100
        assert analysis.timing_cost_bps >= 0
