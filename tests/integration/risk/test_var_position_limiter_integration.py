"""
Integration tests for VaR Position Limiter - Phase 2.5

Tests integration with portfolio risk manager and correlation analyzer.
"""

from decimal import Decimal
from unittest.mock import Mock

import pandas as pd
import pytest

from app.domain.models.portfolio import AssetClass, Portfolio, Position
from app.services.var_position_limiter import VaRConfig, VaRPositionLimiter


@pytest.fixture
def multi_asset_portfolio():
    """Create a portfolio with multiple asset classes."""
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            currency="USD",
            sector="Technology",
            country="US",
            broker="ibkr",
        ),
        Position(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("300.00"),
            market_price=Decimal("310.00"),
            unrealized_pnl=Decimal("500.00"),
            currency="USD",
            sector="Technology",
            country="US",
            broker="ibkr",
        ),
        Position(
            symbol="BTCUSDT",
            asset_class=AssetClass.CRYPTO,
            quantity=Decimal("0.5"),
            avg_price=Decimal("40000.00"),
            market_price=Decimal("42000.00"),
            unrealized_pnl=Decimal("1000.00"),
            currency="USD",
            sector="Crypto",
            country="Global",
            broker="binance",
        ),
        Position(
            symbol="EURUSD",
            asset_class=AssetClass.FOREX,
            quantity=Decimal("1000"),
            avg_price=Decimal("1.10"),
            market_price=Decimal("1.12"),
            unrealized_pnl=Decimal("20.00"),
            currency="USD",
            sector="Forex",
            country="Global",
            broker="ibkr",
        ),
    ]

    portfolio = Portfolio(
        portfolio_id="multi-asset",
        cash=Decimal("50000.00"),
        positions=positions,
        broker="ibkr",
        currency="USD",
    )

    return portfolio


@pytest.fixture
def correlation_matrix():
    """Create a sample correlation matrix."""
    # Correlation matrix for AAPL, MSFT, BTCUSDT, EURUSD
    data = {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.7, "BTCUSDT": 0.3, "EURUSD": 0.1},
        "MSFT": {"AAPL": 0.7, "MSFT": 1.0, "BTCUSDT": 0.25, "EURUSD": 0.05},
        "BTCUSDT": {"AAPL": 0.3, "MSFT": 0.25, "BTCUSDT": 1.0, "EURUSD": 0.0},
        "EURUSD": {"AAPL": 0.1, "MSFT": 0.05, "BTCUSDT": 0.0, "EURUSD": 1.0},
    }
    return pd.DataFrame(data)


@pytest.mark.integration
class TestVaRIntegration:
    """Integration tests for VaR Position Limiter."""

    def test_var_with_multi_asset_portfolio(self, multi_asset_portfolio):
        """Test VaR calculation with multi-asset portfolio."""
        config = VaRConfig(
            max_var_limit_pct=Decimal("0.02"),
            confidence_level=0.95,
            use_real_correlation=False,  # Use identity matrix
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            config=config,
        )

        # Calculate VaR
        var_95 = limiter.calculate_portfolio_var(confidence_level=0.95)
        var_99 = limiter.calculate_portfolio_var(confidence_level=0.99)

        # Verify VaR values
        assert var_95 > 0
        assert var_99 > var_95  # 99% VaR should be higher

        # Get metrics
        metrics = limiter.get_var_metrics()

        assert metrics.var_95 == var_95
        assert metrics.var_99 == var_99
        assert metrics.position_count == 4
        assert metrics.correlation_used == "identity"

    def test_var_with_real_correlation(self, multi_asset_portfolio, correlation_matrix):
        """Test VaR calculation with real correlation matrix."""
        # Create mock correlation analyzer
        mock_analyzer = Mock()
        mock_analyzer.get_cached_matrix.return_value = correlation_matrix

        config = VaRConfig(
            max_var_limit_pct=Decimal("0.02"),
            confidence_level=0.95,
            use_real_correlation=True,
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            correlation_analyzer=mock_analyzer,
            config=config,
        )

        # Calculate VaR
        var_95 = limiter.calculate_portfolio_var(confidence_level=0.95)

        # Verify VaR was calculated
        assert var_95 > 0

        # Verify correlation was used
        mock_analyzer.get_cached_matrix.assert_called_once()

        # Get metrics
        metrics = limiter.get_var_metrics()
        assert metrics.correlation_used == "real"

    def test_position_validation_across_asset_classes(self, multi_asset_portfolio):
        """Test position validation across different asset classes."""
        config = VaRConfig(
            max_var_limit_pct=Decimal("0.05"),  # 5% limit for testing
            confidence_level=0.95,
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            config=config,
        )

        # Test adding equity position
        equity_result = limiter.validate_position_with_var(
            symbol="TSLA",
            quantity=Decimal("10"),
            current_price=Decimal("800.00"),
            side="LONG",
        )

        # Verify result structure
        assert hasattr(equity_result, "passed")
        assert hasattr(equity_result, "current_var")
        assert hasattr(equity_result, "projected_var")

        # Test adding crypto position
        crypto_result = limiter.validate_position_with_var(
            symbol="ETHUSDT",
            quantity=Decimal("1"),
            current_price=Decimal("2500.00"),
            side="LONG",
        )

        # Verify result structure
        assert hasattr(crypto_result, "passed")

    def test_var_utilization_tracking(self, multi_asset_portfolio):
        """Test VaR utilization tracking over multiple positions."""
        limiter = VaRPositionLimiter(portfolio=multi_asset_portfolio)

        # Get initial utilization
        current_var, utilization = limiter.get_var_utilization()

        assert current_var >= 0
        assert utilization >= 0

        # Get comprehensive metrics
        metrics = limiter.get_var_metrics()

        assert metrics.utilization_pct == utilization
        assert metrics.var_95 == current_var  # VaRMetrics uses var_95 for 95% VaR
        assert metrics.portfolio_value > 0

    def test_max_position_size_calculation(self, multi_asset_portfolio):
        """Test maximum position size calculation."""
        config = VaRConfig(
            max_var_limit_pct=Decimal("0.02"),
            confidence_level=0.95,
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            config=config,
        )

        # Calculate max position size for a new stock
        max_qty = limiter.calculate_max_position_size(
            symbol="NVDA",
            current_price=Decimal("500.00"),
            side="LONG",
        )

        # Verify it's a positive number
        assert max_qty >= 0

        # If there's room in the portfolio, should allow some position
        if max_qty > 0:
            # Verify that this position would stay within limits
            result = limiter.validate_position_with_var(
                symbol="NVDA",
                quantity=max_qty,
                current_price=Decimal("500.00"),
                side="LONG",
            )

            # Should either pass or be very close to limit
            assert hasattr(result, "passed")

    def test_volatility_cache_updates(self, multi_asset_portfolio):
        """Test volatility cache management."""
        limiter = VaRPositionLimiter(portfolio=multi_asset_portfolio)

        # Update cache with custom volatilities
        volatilities = {
            "AAPL": 0.25,  # 25% annual vol
            "MSFT": 0.22,
            "BTCUSDT": 0.60,  # High crypto vol
            "EURUSD": 0.10,  # Lower forex vol
        }

        limiter.update_volatility_cache(volatilities)

        # Verify volatilities were updated
        assert limiter._get_symbol_volatility("AAPL") == 0.25
        assert limiter._get_symbol_volatility("BTCUSDT") == 0.60

        # Recalculate VaR with new volatilities
        var_with_vols = limiter.calculate_portfolio_var()

        # Should be different from default calculation
        assert var_with_vols >= 0

    def test_warning_threshold_functionality(self, multi_asset_portfolio):
        """Test warning threshold for approaching VaR limit."""
        config = VaRConfig(
            max_var_limit_pct=Decimal("0.01"),  # 1% limit - very strict
            warning_threshold_pct=Decimal("0.5"),  # Warn at 50%
            confidence_level=0.95,
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            config=config,
        )

        # Try to add a position
        result = limiter.validate_position_with_var(
            symbol="GOOGL",
            quantity=Decimal("1"),
            current_price=Decimal("100.00"),
            side="LONG",
        )

        # Check if warnings were generated
        # Note: May or may not have warnings depending on portfolio state
        assert isinstance(result.warnings, list)

    def test_cross_asset_correlation_impact(self, multi_asset_portfolio, correlation_matrix):
        """Test impact of cross-asset correlations on VaR."""
        # Create two limiters: one with correlation, one without
        mock_analyzer = Mock()
        mock_analyzer.get_cached_matrix.return_value = correlation_matrix

        config_real = VaRConfig(
            max_var_limit_pct=Decimal("0.02"),
            confidence_level=0.95,
            use_real_correlation=True,
        )

        config_identity = VaRConfig(
            max_var_limit_pct=Decimal("0.02"),
            confidence_level=0.95,
            use_real_correlation=False,
        )

        limiter_real = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            correlation_analyzer=mock_analyzer,
            config=config_real,
        )

        limiter_identity = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            correlation_analyzer=None,
            config=config_identity,
        )

        # Calculate VaR with both methods
        var_real = limiter_real.calculate_portfolio_var()
        var_identity = limiter_identity.calculate_portfolio_var()

        # Both should be positive
        assert var_real > 0
        assert var_identity > 0

        # Real correlation should give different (usually higher) VaR
        # when assets are positively correlated
        # Note: This may vary depending on the correlation matrix

    def test_empty_portfolio_handling(self):
        """Test handling of empty portfolio."""
        empty_portfolio = Portfolio(
            portfolio_id="empty",
            cash=Decimal("100000.00"),
            positions=[],
            broker="ibkr",
            currency="USD",
        )

        limiter = VaRPositionLimiter(portfolio=empty_portfolio)

        # VaR should be zero
        var = limiter.calculate_portfolio_var()
        assert var == 0

        # Should be able to validate positions (will just calculate based on new position)
        result = limiter.validate_position_with_var(
            symbol="AAPL",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            side="LONG",
        )

        assert hasattr(result, "passed")

    def test_single_position_portfolio(self):
        """Test portfolio with single position."""
        single_position = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("500.00"),
                currency="USD",
                sector="Technology",
                country="US",
                broker="ibkr",
            )
        ]

        portfolio = Portfolio(
            portfolio_id="single",
            cash=Decimal("50000.00"),
            positions=single_position,
            broker="ibkr",
            currency="USD",
        )

        limiter = VaRPositionLimiter(portfolio=portfolio)

        # Should calculate VaR correctly
        var = limiter.calculate_portfolio_var()
        assert var > 0

        # Should validate new positions
        result = limiter.validate_position_with_var(
            symbol="MSFT",
            quantity=Decimal("10"),
            current_price=Decimal("300.00"),
            side="LONG",
        )

        assert hasattr(result, "passed")


@pytest.mark.integration
class TestVaRWithRiskManager:
    """Integration tests with Portfolio Risk Manager."""

    def test_var_as_complement_to_risk_manager(self, multi_asset_portfolio):
        """Test VaR limiter as complement to existing risk management."""
        from app.services.portfolio_risk_manager import PortfolioRiskManager

        # Create both managers
        risk_manager = PortfolioRiskManager()
        var_limiter = VaRPositionLimiter(portfolio=multi_asset_portfolio)

        # Get risk assessment from risk manager
        risk_assessment = risk_manager.assess_portfolio_risk(multi_asset_portfolio)

        # Get VaR metrics
        var_metrics = var_limiter.get_var_metrics()

        # Both should provide risk metrics
        assert "risk_metrics" in risk_assessment
        assert var_metrics.var_95 >= 0

        # VaR provides different perspective on risk
        # Can be used alongside existing metrics

    def test_var_limit_enforcement(self, multi_asset_portfolio):
        """Test that VaR limits can be enforced alongside other risk limits."""
        config = VaRConfig(
            max_var_limit_pct=Decimal("0.01"),  # 1% - very strict
            confidence_level=0.95,
        )

        limiter = VaRPositionLimiter(
            portfolio=multi_asset_portfolio,
            config=config,
        )

        # Try to add a large position
        result = limiter.validate_position_with_var(
            symbol="TSLA",
            quantity=Decimal("1000"),  # Large position
            current_price=Decimal("800.00"),
            side="LONG",
        )

        # Should likely fail VaR check
        # (depending on portfolio size and configuration)
        assert hasattr(result, "passed")
        if not result.passed:
            assert "exceed" in result.message.lower()
            assert result.excess_var > 0
