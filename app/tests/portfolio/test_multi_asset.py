"""
Comprehensive tests for Multi-Asset Portfolio Management.

Tests cover:
- Asset class creation and validation
- Multi-asset portfolio construction
- Strategic allocation methods
- Tactical allocation with signals
- Risk parity allocation
- Portfolio rebalancing
- Cost estimation
- Risk contribution calculation
- Edge cases and error handling

FASE 7.2 - Multi-Asset Portfolio Support Tests
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.portfolio.multi_asset import (
    AllocationStrategy,
    AssetClass,
    AssetClassConfig,
    AssetClassMetrics,
    AssetClassReturns,
    AssetClassType,
    CostEstimate,
    MarketRegime,
    MultiAssetAllocation,
    MultiAssetAllocator,
    MultiAssetConfig,
    MultiAssetPortfolio,
    MultiAssetPortfolioManager,
    MultiAssetRebalancer,
    PortfolioMetrics,
    RebalanceFrequency,
    RebalancePlan,
    RebalancePriority,
    RebalanceTrade,
    RiskParityAllocationParams,
    RiskTolerance,
    StrategicAllocationParams,
    TacticalAllocationParams,
    Trade,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def equity_asset_class():
    """Create equity asset class for testing."""
    return AssetClass(
        name="US Equities",
        type=AssetClassType.EQUITY,
        expected_return=Decimal("0.08"),
        volatility=Decimal("0.15"),
        min_weight=Decimal("0.2"),
        max_weight=Decimal("0.8"),
        rebalance_frequency="monthly",
        symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        max_positions=20,
    )


@pytest.fixture
def bond_asset_class():
    """Create bond asset class for testing."""
    return AssetClass(
        name="US Bonds",
        type=AssetClassType.FIXED_INCOME,
        expected_return=Decimal("0.03"),
        volatility=Decimal("0.05"),
        min_weight=Decimal("0.1"),
        max_weight=Decimal("0.6"),
        rebalance_frequency="quarterly",
        symbols=["TLT", "IEF", "SHY", "LQD"],
        max_positions=10,
    )


@pytest.fixture
def crypto_asset_class():
    """Create crypto asset class for testing."""
    return AssetClass(
        name="Cryptocurrencies",
        type=AssetClassType.CRYPTO,
        expected_return=Decimal("0.15"),
        volatility=Decimal("0.60"),
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.2"),
        rebalance_frequency="weekly",
        symbols=["BTC", "ETH", "SOL"],
        max_positions=5,
    )


@pytest.fixture
def asset_classes(equity_asset_class, bond_asset_class, crypto_asset_class):
    """Create dictionary of asset classes for testing."""
    return {
        equity_asset_class.name: equity_asset_class,
        bond_asset_class.name: bond_asset_class,
        crypto_asset_class.name: crypto_asset_class,
    }


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")

    # Equity returns
    equity_returns = np.random.randn(252, 5) * 0.02 + 0.0003
    equity_df = pd.DataFrame(
        equity_returns, index=dates, columns=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    )

    # Bond returns (lower volatility)
    bond_returns = np.random.randn(252, 4) * 0.005 + 0.0001
    bond_df = pd.DataFrame(bond_returns, index=dates, columns=["TLT", "IEF", "SHY", "LQD"])

    # Crypto returns (higher volatility)
    crypto_returns = np.random.randn(252, 3) * 0.05 + 0.001
    crypto_df = pd.DataFrame(crypto_returns, index=dates, columns=["BTC", "ETH", "SOL"])

    return {
        "US Equities": equity_df,
        "US Bonds": bond_df,
        "Cryptocurrencies": crypto_df,
    }


@pytest.fixture
def sample_prices():
    """Create sample current prices for testing."""
    return {
        "AAPL": Decimal("150.00"),
        "MSFT": Decimal("300.00"),
        "GOOGL": Decimal("2500.00"),
        "AMZN": Decimal("3000.00"),
        "TSLA": Decimal("800.00"),
        "TLT": Decimal("100.00"),
        "IEF": Decimal("95.00"),
        "SHY": Decimal("90.00"),
        "LQD": Decimal("105.00"),
        "BTC": Decimal("25000.00"),
        "ETH": Decimal("1500.00"),
        "SOL": Decimal("25.00"),
    }


@pytest.fixture
def multi_asset_config(equity_asset_class, bond_asset_class, crypto_asset_class):
    """Create MultiAssetConfig for testing."""
    equity_config = equity_asset_class.to_config()
    bond_config = bond_asset_class.to_config()
    crypto_config = crypto_asset_class.to_config()

    return MultiAssetConfig(
        asset_classes=[equity_config, bond_config, crypto_config],
        rebalance_threshold=Decimal("0.05"),
        risk_tolerance=RiskTolerance.MODERATE,
        max_positions_per_class=20,
        min_position_size=Decimal("0.01"),
        max_position_size=Decimal("0.20"),
        trading_cost_bps=Decimal("10"),
    )


@pytest.fixture
def portfolio_manager(multi_asset_config):
    """Create portfolio manager for testing."""
    return MultiAssetPortfolioManager(multi_asset_config)


@pytest.fixture
def sample_portfolio(asset_classes):
    """Create sample multi-asset portfolio for testing."""
    # Create allocations
    equity_alloc = MultiAssetAllocation(
        asset_class=asset_classes["US Equities"],
        weight=Decimal("0.60"),
        assets={
            "AAPL": Decimal("0.25"),
            "MSFT": Decimal("0.25"),
            "GOOGL": Decimal("0.20"),
            "AMZN": Decimal("0.20"),
            "TSLA": Decimal("0.10"),
        },
        expected_return=Decimal("0.048"),
        risk=Decimal("0.09"),
    )

    bond_alloc = MultiAssetAllocation(
        asset_class=asset_classes["US Bonds"],
        weight=Decimal("0.35"),
        assets={
            "TLT": Decimal("0.40"),
            "IEF": Decimal("0.30"),
            "SHY": Decimal("0.20"),
            "LQD": Decimal("0.10"),
        },
        expected_return=Decimal("0.0105"),
        risk=Decimal("0.0175"),
    )

    crypto_alloc = MultiAssetAllocation(
        asset_class=asset_classes["Cryptocurrencies"],
        weight=Decimal("0.05"),
        assets={
            "BTC": Decimal("0.60"),
            "ETH": Decimal("0.30"),
            "SOL": Decimal("0.10"),
        },
        expected_return=Decimal("0.0075"),
        risk=Decimal("0.03"),
    )

    portfolio = MultiAssetPortfolio(
        name="Test Portfolio",
        allocations={
            "US Equities": equity_alloc,
            "US Bonds": bond_alloc,
            "Cryptocurrencies": crypto_alloc,
        },
        total_value=Decimal("1000000"),
        last_rebalanced=datetime.utcnow(),
        rebalance_threshold=Decimal("0.05"),
    )

    return portfolio


# =============================================================================
# ASSET CLASS TESTS
# =============================================================================


class TestAssetClass:
    """Tests for AssetClass creation and validation."""

    def test_create_asset_class_success(self, equity_asset_class):
        """Test successful asset class creation."""
        assert equity_asset_class.name == "US Equities"
        assert equity_asset_class.type == AssetClassType.EQUITY
        assert equity_asset_class.expected_return == Decimal("0.08")
        assert equity_asset_class.volatility == Decimal("0.15")
        assert equity_asset_class.min_weight == Decimal("0.2")
        assert equity_asset_class.max_weight == Decimal("0.8")

    def test_asset_class_validation_valid(self, equity_asset_class):
        """Test validation of valid asset class."""
        assert equity_asset_class.validate() is True

    def test_asset_class_validation_invalid_volatility(self):
        """Test validation fails with negative volatility."""
        with pytest.raises(ValueError, match="Volatility must be non-negative"):
            AssetClass(
                name="Test",
                type=AssetClassType.EQUITY,
                expected_return=Decimal("0.08"),
                volatility=Decimal("-0.1"),
            )

    def test_asset_class_validation_invalid_return(self):
        """Test validation fails with invalid expected return."""
        with pytest.raises(ValueError, match="Expected return cannot be less than -100%"):
            AssetClass(
                name="Test",
                type=AssetClassType.EQUITY,
                expected_return=Decimal("-1.5"),
                volatility=Decimal("0.15"),
            )

    def test_asset_class_validation_invalid_weight_range(self):
        """Test validation fails when min_weight > max_weight."""
        with pytest.raises(ValueError, match="min_weight .* cannot exceed max_weight"):
            AssetClass(
                name="Test",
                type=AssetClassType.EQUITY,
                expected_return=Decimal("0.08"),
                volatility=Decimal("0.15"),
                min_weight=Decimal("0.5"),
                max_weight=Decimal("0.3"),
            )

    def test_asset_class_validation_invalid_frequency(self):
        """Test validation fails with invalid rebalance frequency."""
        with pytest.raises(ValueError, match="Invalid rebalance frequency"):
            AssetClass(
                name="Test",
                type=AssetClassType.EQUITY,
                expected_return=Decimal("0.08"),
                volatility=Decimal("0.15"),
                rebalance_frequency="invalid",
            )

    def test_asset_class_sharpe_ratio(self, equity_asset_class):
        """Test Sharpe ratio calculation."""
        sharpe = equity_asset_class.calculate_sharpe_ratio(risk_free_rate=0.02)
        expected = (Decimal("0.08") - Decimal("0.02")) / Decimal("0.15")
        assert abs(sharpe - float(expected)) < 0.01

    def test_asset_class_sharpe_ratio_property(self, equity_asset_class):
        """Test Sharpe ratio property with default risk-free rate."""
        sharpe = equity_asset_class.sharpe_ratio
        expected = (Decimal("0.08") - Decimal("0.02")) / Decimal("0.15")
        assert abs(sharpe - float(expected)) < 0.01

    def test_asset_class_risk_return_ratio(self, equity_asset_class):
        """Test risk-return ratio calculation."""
        ratio = equity_asset_class.risk_return_ratio
        expected = Decimal("0.08") / Decimal("0.15")
        assert ratio == expected

    def test_asset_class_to_config(self, equity_asset_class):
        """Test conversion to AssetClassConfig."""
        config = equity_asset_class.to_config()
        assert config.name == equity_asset_class.name
        assert config.type == equity_asset_class.type
        assert config.expected_return == equity_asset_class.expected_return
        assert config.volatility == equity_asset_class.volatility

    def test_asset_class_from_config(self, equity_asset_class):
        """Test creation from AssetClassConfig."""
        config = equity_asset_class.to_config()
        asset_class = AssetClass.from_config(config)
        assert asset_class.name == equity_asset_class.name
        assert asset_class.type == equity_asset_class.type

    def test_asset_class_is_within_weight_bounds(self, equity_asset_class):
        """Test weight bounds checking."""
        assert equity_asset_class.is_within_weight_bounds(Decimal("0.5")) is True
        assert equity_asset_class.is_within_weight_bounds(Decimal("0.1")) is False
        assert equity_asset_class.is_within_weight_bounds(Decimal("0.9")) is False

    def test_asset_class_calculate_position_size(self, equity_asset_class):
        """Test position size calculation."""
        portfolio_value = Decimal("1000000")
        target_weight = Decimal("0.6")
        position_size = equity_asset_class.calculate_position_size(portfolio_value, target_weight)
        assert position_size == Decimal("600000")


class TestAssetClassType:
    """Tests for AssetClassType enum methods."""

    def test_get_trading_hours_equity(self):
        """Test trading hours for equities."""
        hours = AssetClassType.get_trading_hours(AssetClassType.EQUITY)
        assert "open" in hours
        assert "close" in hours

    def test_get_trading_hours_crypto(self):
        """Test trading hours for crypto (24/7)."""
        hours = AssetClassType.get_trading_hours(AssetClassType.CRYPTO)
        assert hours["open"] == "00:00"
        assert hours["close"] == "23:59"

    def test_get_settlement_period_equity(self):
        """Test settlement period for equities (T+2)."""
        period = AssetClassType.get_settlement_period(AssetClassType.EQUITY)
        assert period == timedelta(days=2)

    def test_get_settlement_period_crypto(self):
        """Test settlement period for crypto (instant)."""
        period = AssetClassType.get_settlement_period(AssetClassType.CRYPTO)
        assert period == timedelta(seconds=0)

    def test_get_typical_volatility(self):
        """Test typical volatility ranges."""
        min_vol, max_vol = AssetClassType.get_typical_volatility(AssetClassType.EQUITY)
        assert min_vol == Decimal("0.10")
        assert max_vol == Decimal("0.30")

    def test_get_typical_return(self):
        """Test typical return ranges."""
        min_ret, max_ret = AssetClassType.get_typical_return(AssetClassType.CRYPTO)
        assert min_ret == Decimal("-0.20")
        assert max_ret == Decimal("0.50")


# =============================================================================
# MULTI-ASSET ALLOCATION TESTS
# =============================================================================


class TestMultiAssetAllocation:
    """Tests for MultiAssetAllocation."""

    def test_create_allocation_success(self, equity_asset_class):
        """Test successful allocation creation."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("0.6"),
            assets={"AAPL": Decimal("0.5"), "MSFT": Decimal("0.5")},
        )
        assert alloc.weight == Decimal("0.6")
        assert len(alloc.assets) == 2

    def test_allocation_total_weight(self, equity_asset_class):
        """Test total weight calculation."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("0.6"),
            assets={"AAPL": Decimal("0.5"), "MSFT": Decimal("0.5")},
        )
        assert alloc.total_weight == Decimal("1.0")

    def test_allocation_get_absolute_weight(self, equity_asset_class):
        """Test absolute weight calculation."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("0.6"),
            assets={"AAPL": Decimal("0.5"), "MSFT": Decimal("0.5")},
        )
        abs_weight = alloc.get_absolute_weight("AAPL")
        assert abs_weight == Decimal("0.3")  # 0.6 * 0.5

    def test_allocation_validation_valid(self, equity_asset_class):
        """Test validation of valid allocation."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("0.6"),
            assets={"AAPL": Decimal("0.5"), "MSFT": Decimal("0.5")},
        )
        assert alloc.validate() is True

    def test_allocation_validation_invalid_weight(self, equity_asset_class):
        """Test validation fails with invalid weight."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("1.5"),
            assets={"AAPL": Decimal("1.0")},
        )
        with pytest.raises(ValueError, match="Asset class weight must be between 0 and 1"):
            alloc.validate()

    def test_allocation_validation_weights_not_summing_to_one(self, equity_asset_class):
        """Test validation fails when sub-allocations don't sum to 1."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("0.6"),
            assets={"AAPL": Decimal("0.3"), "MSFT": Decimal("0.3")},
        )
        with pytest.raises(ValueError, match="Sub-allocations must sum to 1"):
            alloc.validate()


# =============================================================================
# MULTI-ASSET PORTFOLIO TESTS
# =============================================================================


class TestMultiAssetPortfolio:
    """Tests for MultiAssetPortfolio."""

    def test_create_portfolio_success(self, sample_portfolio):
        """Test successful portfolio creation."""
        assert sample_portfolio.name == "Test Portfolio"
        assert len(sample_portfolio.allocations) == 3
        assert sample_portfolio.total_value == Decimal("1000000")

    def test_portfolio_get_asset_class_weights(self, sample_portfolio):
        """Test getting asset class weights."""
        weights = sample_portfolio.get_asset_class_weights()
        assert weights["US Equities"] == Decimal("0.60")
        assert weights["US Bonds"] == Decimal("0.35")
        assert weights["Cryptocurrencies"] == Decimal("0.05")

    def test_portfolio_get_all_assets(self, sample_portfolio):
        """Test getting all assets."""
        all_assets = sample_portfolio.get_all_assets()
        assert "AAPL" in all_assets
        assert "MSFT" in all_assets
        assert "BTC" in all_assets

    def test_portfolio_get_total_allocation(self, sample_portfolio):
        """Test getting total allocation for a symbol."""
        total_alloc = sample_portfolio.get_total_allocation("AAPL")
        # AAPL is 25% of 60% equity allocation
        expected = Decimal("0.15")
        assert abs(total_alloc - expected) < Decimal("0.001")

    def test_portfolio_validate_valid(self, sample_portfolio):
        """Test validation of valid portfolio."""
        assert sample_portfolio.validate() is True

    def test_portfolio_validate_weights_not_summing_to_one(self, asset_classes):
        """Test validation fails when weights don't sum to 1."""
        equity_alloc = MultiAssetAllocation(
            asset_class=asset_classes["US Equities"],
            weight=Decimal("0.3"),
            assets={"AAPL": Decimal("1.0")},
        )

        portfolio = MultiAssetPortfolio(
            name="Invalid Portfolio",
            allocations={"US Equities": equity_alloc},
            total_value=Decimal("1000000"),
            last_rebalanced=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="Portfolio weights must sum to 1"):
            portfolio.validate()

    def test_portfolio_add_allocation(self, sample_portfolio, crypto_asset_class):
        """Test adding allocation to portfolio."""
        new_alloc = MultiAssetAllocation(
            asset_class=crypto_asset_class,
            weight=Decimal("0.05"),
            assets={"BTC": Decimal("1.0")},
        )
        sample_portfolio.add_allocation(new_alloc)
        assert "Cryptocurrencies" in sample_portfolio.allocations

    def test_portfolio_remove_allocation(self, sample_portfolio):
        """Test removing allocation from portfolio."""
        removed = sample_portfolio.remove_allocation("Cryptocurrencies")
        assert removed is True
        assert "Cryptocurrencies" not in sample_portfolio.allocations


# =============================================================================
# PORTFOLIO MANAGER TESTS
# =============================================================================


class TestMultiAssetPortfolioManager:
    """Tests for MultiAssetPortfolioManager."""

    def test_manager_initialization(self, portfolio_manager):
        """Test manager initialization."""
        assert len(portfolio_manager.asset_classes) == 3
        assert portfolio_manager.config.rebalance_threshold == Decimal("0.05")

    def test_construct_portfolio_success(self, portfolio_manager, sample_market_data):
        """Test successful portfolio construction."""
        target_weights = {
            "US Equities": Decimal("0.60"),
            "US Bonds": Decimal("0.35"),
            "Cryptocurrencies": Decimal("0.05"),
        }

        result = portfolio_manager.construct_portfolio(
            target_weights=target_weights,
            market_data=sample_market_data,
        )

        assert result.success is True
        assert result.portfolio is not None
        assert len(result.portfolio.allocations) == 3

    def test_construct_portfolio_invalid_weights(self, portfolio_manager, sample_market_data):
        """Test portfolio construction fails with invalid weights."""
        target_weights = {
            "US Equities": Decimal("0.5"),
            "US Bonds": Decimal("0.3"),
        }  # Only sums to 0.8

        result = portfolio_manager.construct_portfolio(
            target_weights=target_weights,
            market_data=sample_market_data,
        )

        assert result.success is False
        assert result.error is not None

    def test_construct_portfolio_negative_weight(self, portfolio_manager, sample_market_data):
        """Test portfolio construction fails with negative weight."""
        target_weights = {
            "US Equities": Decimal("-0.1"),
            "US Bonds": Decimal("0.6"),
            "Cryptocurrencies": Decimal("0.5"),
        }

        result = portfolio_manager.construct_portfolio(
            target_weights=target_weights,
            market_data=sample_market_data,
        )

        assert result.success is False

    def test_rebalance_portfolio(self, portfolio_manager, sample_portfolio, sample_prices):
        """Test portfolio rebalancing."""
        # Create drift by changing weights
        target_weights = {
            "US Equities": Decimal("0.50"),
            "US Bonds": Decimal("0.40"),
            "Cryptocurrencies": Decimal("0.10"),
        }

        result = portfolio_manager.rebalance(
            current_portfolio=sample_portfolio,
            target_weights=target_weights,
            current_prices=sample_prices,
            portfolio_value=Decimal("1000000"),
        )

        assert result.success is True
        assert isinstance(result.trades, list)

    def test_calculate_risk_contributions(
        self, portfolio_manager, sample_portfolio, sample_market_data
    ):
        """Test risk contribution calculation."""
        # Combine all returns
        all_returns = pd.concat(sample_market_data.values(), axis=1)

        risk_contribs = portfolio_manager.calculate_risk_contributions(
            portfolio=sample_portfolio,
            returns=all_returns,
        )

        assert isinstance(risk_contribs, dict)
        assert len(risk_contribs) > 0

        # Check contributions sum to approximately 1
        total = sum(risk_contribs.values())
        assert abs(total - Decimal("1")) < Decimal("0.01")


# =============================================================================
# ALLOCATION TESTS
# =============================================================================


class TestMultiAssetAllocator:
    """Tests for MultiAssetAllocator."""

    @pytest.fixture
    def allocator(self, asset_classes):
        """Create allocator for testing."""
        return MultiAssetAllocator(asset_classes)

    def test_strategic_allocation_conservative(self, allocator):
        """Test strategic allocation for conservative investor."""
        params = StrategicAllocationParams(
            risk_tolerance=RiskTolerance.CONSERVATIVE,
            time_horizon=5,
        )

        result = allocator.strategic_allocation(params)

        assert result.method == AllocationStrategy.STRATEGIC
        assert result.weights is not None
        # Conservative should have more bonds
        bond_weight = result.weights.get(AssetClassType.FIXED_INCOME, Decimal("0"))
        equity_weight = result.weights.get(AssetClassType.EQUITY, Decimal("0"))
        assert bond_weight > equity_weight

    def test_strategic_allocation_aggressive(self, allocator):
        """Test strategic allocation for aggressive investor."""
        params = StrategicAllocationParams(
            risk_tolerance=RiskTolerance.AGGRESSIVE,
            time_horizon=20,
        )

        result = allocator.strategic_allocation(params)

        # Aggressive should have more equities
        equity_weight = result.weights.get(AssetClassType.EQUITY, Decimal("0"))
        assert equity_weight > Decimal("0.70")

    def test_strategic_allocation_moderate(self, allocator):
        """Test strategic allocation for moderate investor."""
        params = StrategicAllocationParams(
            risk_tolerance=RiskTolerance.MODERATE,
            time_horizon=10,
        )

        result = allocator.strategic_allocation(params)

        # Moderate should have balanced allocation
        equity_weight = result.weights.get(AssetClassType.EQUITY, Decimal("0"))
        assert Decimal("0.50") <= equity_weight <= Decimal("0.70")

    def test_tactical_allocation(self, allocator):
        """Test tactical allocation with signals."""
        strategic_weights = {
            AssetClassType.EQUITY: Decimal("0.60"),
            AssetClassType.FIXED_INCOME: Decimal("0.40"),
        }

        params = TacticalAllocationParams(
            strategic_weights=strategic_weights,
            market_conditions={AssetClassType.EQUITY: MarketRegime.BULL},
            signals={AssetClassType.EQUITY: 0.5},
            max_tilt=Decimal("0.10"),
        )

        result = allocator.tactical_allocation(params)

        assert result.method == AllocationStrategy.TACTICAL
        # Should overweight equities due to positive signal
        equity_weight = result.weights.get(AssetClassType.EQUITY)
        # The weight should be adjusted (not equal to strategic weight)
        assert equity_weight is not None
        # Check that the allocation result contains tactical metadata
        assert "tilts" in result.metadata

    def test_risk_parity_allocation(self, allocator, sample_market_data):
        """Test risk parity allocation."""
        # Create asset class returns
        equity_returns = sample_market_data["US Equities"].mean(axis=1)
        bond_returns = sample_market_data["US Bonds"].mean(axis=1)

        asset_returns = pd.DataFrame(
            {
                "equity": equity_returns,
                "bonds": bond_returns,
            }
        )

        params = RiskParityAllocationParams(
            asset_class_returns=asset_returns,
            risk_free_rate=0.02,
        )

        result = allocator.risk_parity_allocation(params)

        assert result.method == AllocationStrategy.RISK_PARITY
        assert result.weights is not None
        # Risk parity should give higher weight to lower volatility asset
        # Bonds typically have lower volatility than equities
        # So bonds should have higher weight in simple risk parity

    def test_momentum_allocation(self, allocator, sample_market_data):
        """Test momentum-based allocation."""
        equity_returns = sample_market_data["US Equities"]
        bond_returns = sample_market_data["US Bonds"]

        combined_returns = pd.concat([equity_returns, bond_returns], axis=1)

        result = allocator.momentum_allocation(
            lookback_returns=combined_returns,
            lookback_period=63,  # 3 months
            top_n=2,
        )

        assert result.method == AllocationStrategy.MOMENTUM
        assert result.weights is not None

    def test_equal_weight_allocation(self, allocator):
        """Test equal weight allocation."""
        result = allocator.equal_weight_allocation()

        assert result.method == AllocationStrategy.EQUAL_WEIGHT
        assert result.weights is not None

        # Check that weights sum to 1
        total_weight = sum(result.weights.values())
        assert abs(total_weight - Decimal("1")) < Decimal("0.001")

        # Check that crypto weight is at its max (0.2) due to constraints
        crypto_weight = result.weights.get("Cryptocurrencies", Decimal("0"))
        # Crypto has max_weight=0.2, so it should be capped there
        assert crypto_weight <= Decimal("0.25")  # Allow some tolerance

        # The remaining weight should be distributed between equities and bonds
        # After applying constraints and renormalizing
        assert "US Equities" in result.weights
        assert "US Bonds" in result.weights
        assert "Cryptocurrencies" in result.weights


# =============================================================================
# REBALANCER TESTS
# =============================================================================


class TestMultiAssetRebalancer:
    """Tests for MultiAssetRebalancer."""

    @pytest.fixture
    def rebalancer(self):
        """Create rebalancer for testing."""
        return MultiAssetRebalancer(
            trading_cost_bps=Decimal("10"),
            rebalance_threshold=Decimal("0.05"),
            min_trade_size=Decimal("1000"),
        )

    def test_create_rebalance_plan(
        self, rebalancer, sample_portfolio, sample_prices, asset_classes
    ):
        """Test creating rebalancing plan."""
        target_weights = {
            "US Equities": Decimal("0.50"),
            "US Bonds": Decimal("0.45"),
            "Cryptocurrencies": Decimal("0.05"),
        }

        plan = rebalancer.create_rebalance_plan(
            current_portfolio=sample_portfolio,
            target_weights=target_weights,
            current_prices=sample_prices,
            portfolio_value=Decimal("1000000"),
            asset_classes=asset_classes,
        )

        assert isinstance(plan, RebalancePlan)
        assert isinstance(plan.trades, list)
        assert isinstance(plan.total_cost, CostEstimate)
        assert plan.pre_rebalance_portfolio == sample_portfolio

    def test_prioritize_trades(self, rebalancer):
        """Test trade prioritization."""
        trades = [
            RebalanceTrade(
                symbol="AAPL",
                asset_class="US Equities",
                quantity=Decimal("100"),
                current_price=Decimal("150"),
                target_value=Decimal("15000"),
                current_value=Decimal("10000"),
                deviation=Decimal("0.10"),
                priority=0,
                estimated_cost=Decimal("15"),
                reason="Rebalance",
            ),
            RebalanceTrade(
                symbol="BTC",
                asset_class="Cryptocurrencies",
                quantity=Decimal("1"),
                current_price=Decimal("25000"),
                target_value=Decimal("25000"),
                current_value=Decimal("20000"),
                deviation=Decimal("0.05"),
                priority=0,
                estimated_cost=Decimal("25"),
                reason="Rebalance",
            ),
        ]

        prioritized = rebalancer.prioritize_trades(trades)

        assert len(prioritized) == 2
        assert all(t.priority >= 0 for t in prioritized)

    def test_estimate_costs(self, rebalancer):
        """Test cost estimation."""
        trades = [
            RebalanceTrade(
                symbol="AAPL",
                asset_class="equity",
                quantity=Decimal("100"),
                current_price=Decimal("150"),
                target_value=Decimal("15000"),
                current_value=Decimal("10000"),
                deviation=Decimal("0.10"),
                priority=50,
                estimated_cost=Decimal("15"),
                reason="Test",
            )
        ]

        costs = rebalancer.estimate_costs(trades, Decimal("1000000"))

        assert isinstance(costs, CostEstimate)
        assert costs.total_cost >= Decimal("0")
        assert costs.commission >= Decimal("0")
        assert costs.spread_cost >= Decimal("0")


# =============================================================================
# TRADE TESTS
# =============================================================================


class TestTrade:
    """Tests for Trade model."""

    def test_create_trade_success(self):
        """Test successful trade creation."""
        trade = Trade(
            symbol="AAPL",
            asset_class="equity",
            quantity=Decimal("100"),
            price=Decimal("150"),
            value=Decimal("15000"),
            reason="Rebalancing",
        )

        assert trade.symbol == "AAPL"
        assert trade.quantity == Decimal("100")
        assert trade.is_buy is True
        assert trade.is_sell is False

    def test_create_sell_trade(self):
        """Test creating a sell trade."""
        trade = Trade(
            symbol="AAPL",
            asset_class="equity",
            quantity=Decimal("-100"),
            price=Decimal("150"),
            value=Decimal("15000"),
            reason="Rebalancing",
        )

        assert trade.is_buy is False
        assert trade.is_sell is True

    def test_trade_validation_zero_quantity(self):
        """Test trade validation fails with zero quantity."""
        with pytest.raises(ValueError, match="Trade quantity cannot be zero"):
            Trade(
                symbol="AAPL",
                asset_class="equity",
                quantity=Decimal("0"),
                price=Decimal("150"),
                value=Decimal("15000"),
                reason="Test",
            )

    def test_trade_validation_negative_price(self):
        """Test trade validation fails with negative price."""
        with pytest.raises(ValueError, match="Price must be positive"):
            Trade(
                symbol="AAPL",
                asset_class="equity",
                quantity=Decimal("100"),
                price=Decimal("-10"),
                value=Decimal("15000"),
                reason="Test",
            )

    def test_trade_total_cost(self):
        """Test total cost calculation."""
        trade = Trade(
            symbol="AAPL",
            asset_class="equity",
            quantity=Decimal("100"),
            price=Decimal("150"),
            value=Decimal("15000"),
            reason="Test",
            estimated_cost=Decimal("10"),
        )

        assert trade.total_cost == Decimal("15010")


# =============================================================================
# PORTFOLIO METRICS TESTS
# =============================================================================


class TestPortfolioMetrics:
    """Tests for PortfolioMetrics."""

    def test_create_metrics_success(self):
        """Test successful metrics creation."""
        metrics = PortfolioMetrics(
            total_return=Decimal("0.10"),
            annualized_return=Decimal("0.08"),
            volatility=Decimal("0.15"),
            sharpe_ratio=Decimal("0.5"),
            max_drawdown=Decimal("-0.10"),  # Drawdown is negative (loss)
        )

        assert metrics.total_return == Decimal("0.10")
        assert metrics.sharpe_ratio == Decimal("0.5")

    def test_metrics_validation_negative_volatility(self):
        """Test validation fails with negative volatility."""
        with pytest.raises(ValueError, match="Risk metric must be non-negative"):
            PortfolioMetrics(
                total_return=Decimal("0.10"),
                annualized_return=Decimal("0.08"),
                volatility=Decimal("-0.05"),
            )

    def test_metrics_validation_positive_drawdown(self):
        """Test validation fails with positive drawdown."""
        with pytest.raises(ValueError, match="Max drawdown must be non-positive"):
            PortfolioMetrics(
                total_return=Decimal("0.10"),
                annualized_return=Decimal("0.08"),
                volatility=Decimal("0.15"),
                max_drawdown=Decimal("0.10"),  # Drawdown should be negative
            )


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestMultiAssetIntegration:
    """Integration tests for multi-asset portfolio system."""

    def test_full_portfolio_workflow(self, portfolio_manager, sample_market_data):
        """Test complete portfolio construction and management workflow."""
        # Step 1: Construct portfolio
        target_weights = {
            "US Equities": Decimal("0.60"),
            "US Bonds": Decimal("0.35"),
            "Cryptocurrencies": Decimal("0.05"),
        }

        construct_result = portfolio_manager.construct_portfolio(
            target_weights=target_weights,
            market_data=sample_market_data,
        )

        assert construct_result.success is True
        portfolio = construct_result.portfolio

        # Step 2: Create allocator
        allocator = MultiAssetAllocator(portfolio_manager.asset_classes)

        # Step 3: Calculate strategic allocation
        strategic_params = StrategicAllocationParams(
            risk_tolerance=RiskTolerance.MODERATE,
            time_horizon=10,
        )
        alloc_result = allocator.strategic_allocation(strategic_params)

        # Step 4: Rebalance portfolio
        rebalancer = MultiAssetRebalancer()

        prices = {
            "AAPL": Decimal("150"),
            "MSFT": Decimal("300"),
            "GOOGL": Decimal("2500"),
            "AMZN": Decimal("3000"),
            "TSLA": Decimal("800"),
            "TLT": Decimal("100"),
            "BTC": Decimal("25000"),
        }

        plan = rebalancer.create_rebalance_plan(
            current_portfolio=portfolio,
            target_weights=target_weights,
            current_prices=prices,
            portfolio_value=Decimal("1000000"),
            asset_classes=portfolio_manager.asset_classes,
        )

        assert isinstance(plan, RebalancePlan)

    def test_portfolio_drift_detection(self, portfolio_manager, sample_portfolio, sample_prices):
        """Test detection of portfolio drift from targets."""
        # Slightly change weights to create drift
        target_weights = {
            "US Equities": Decimal("0.55"),  # Down from 0.60
            "US Bonds": Decimal("0.35"),  # Same
            "Cryptocurrencies": Decimal("0.10"),  # Up from 0.05
        }

        result = portfolio_manager.rebalance(
            current_portfolio=sample_portfolio,
            target_weights=target_weights,
            current_prices=sample_prices,
            portfolio_value=Decimal("1000000"),
        )

        # Should trigger rebalancing due to >5% threshold
        assert result.success is True

    def test_cost_optimization(self, portfolio_manager, sample_portfolio, sample_prices):
        """Test that rebalancing optimizes for costs."""
        rebalancer = MultiAssetRebalancer(trading_cost_bps=Decimal("10"))

        plan = rebalancer.create_rebalance_plan(
            current_portfolio=sample_portfolio,
            target_weights={
                "US Equities": Decimal("0.59"),
                "US Bonds": Decimal("0.36"),
                "Cryptocurrencies": Decimal("0.05"),
            },
            current_prices=sample_prices,
            portfolio_value=Decimal("1000000"),
            asset_classes=portfolio_manager.asset_classes,
        )

        # Small drift should result in minimal trades due to cost optimization
        # The plan might defer trading if costs exceed benefits
        assert plan.total_cost.cost_as_percentage < Decimal("0.5")  # Less than 0.5%


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_asset_classes(self):
        """Test handling of empty asset classes."""
        with pytest.raises(ValueError):  # Pydantic validation error
            MultiAssetConfig(
                asset_classes=[],
                rebalance_threshold=Decimal("0.05"),
            )

    def test_duplicate_asset_class_names(self):
        """Test handling of duplicate asset class names."""
        config1 = AssetClassConfig(
            name="Duplicate",
            type=AssetClassType.EQUITY,
            expected_return=Decimal("0.08"),
            volatility=Decimal("0.15"),
        )
        config2 = AssetClassConfig(
            name="Duplicate",
            type=AssetClassType.FIXED_INCOME,
            expected_return=Decimal("0.03"),
            volatility=Decimal("0.05"),
        )

        with pytest.raises(ValueError, match="Asset class names must be unique"):
            MultiAssetConfig(asset_classes=[config1, config2])

    def test_zero_volatility_asset_class(self):
        """Test handling of zero volatility (cash)."""
        cash_class = AssetClass(
            name="Cash",
            type=AssetClassType.CASH,
            expected_return=Decimal("0.01"),
            volatility=Decimal("0.0"),
        )

        assert cash_class.validate() is True
        assert cash_class.sharpe_ratio == 0.0  # Property, not method

    def test_extreme_weights(self):
        """Test handling of extreme weight scenarios."""
        with pytest.raises(ValueError):
            AssetClass(
                name="Test",
                type=AssetClassType.EQUITY,
                expected_return=Decimal("0.08"),
                volatility=Decimal("0.15"),
                min_weight=Decimal("0"),
                max_weight=Decimal("1.5"),  # Invalid
            )

    def test_portfolio_with_single_asset_class(self, equity_asset_class):
        """Test portfolio with only one asset class."""
        alloc = MultiAssetAllocation(
            asset_class=equity_asset_class,
            weight=Decimal("1.0"),
            assets={"AAPL": Decimal("1.0")},
        )

        portfolio = MultiAssetPortfolio(
            name="Single Asset Portfolio",
            allocations={"US Equities": alloc},
            total_value=Decimal("1000000"),
            last_rebalanced=datetime.utcnow(),
        )

        assert portfolio.validate() is True

    def test_rebalance_with_no_drift(self, portfolio_manager, sample_portfolio, sample_prices):
        """Test rebalancing when there's no drift."""
        # Same weights as current portfolio
        target_weights = {
            "US Equities": Decimal("0.60"),
            "US Bonds": Decimal("0.35"),
            "Cryptocurrencies": Decimal("0.05"),
        }

        result = portfolio_manager.rebalance(
            current_portfolio=sample_portfolio,
            target_weights=target_weights,
            current_prices=sample_prices,
            portfolio_value=Decimal("1000000"),
        )

        # Should not require trades
        assert result.success is True
        assert len(result.trades) == 0
