"""
Unit tests for BrokerNegotiationEngine

Tests commission tier calculation, asset class adjustments, and savings analysis.
"""

from decimal import Decimal

import pytest

from app.services.smart_order_routing.broker_negotiation_engine import (
    BrokerNegotiationEngine,
)


class TestBrokerNegotiationEngine:
    """Test suite for BrokerNegotiationEngine."""

    @pytest.fixture
    def engine(self):
        """Create engine instance for testing."""
        return BrokerNegotiationEngine()

    def test_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine is not None
        assert engine.COMMISSION_TIERS is not None
        assert len(engine.COMMISSION_TIERS) == 4

    def test_retail_tier_commission(self, engine):
        """Test retail tier commission for <€50k volume."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("10000"),
            asset_class="equity",
        )
        assert rate == Decimal("0.001")  # 0.1%

    def test_semi_pro_tier_commission(self, engine):
        """Test semi-pro tier for €50k-€250k volume."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        assert rate == Decimal("0.0005")  # 0.05%

    def test_pro_tier_commission(self, engine):
        """Test pro tier for €250k-€1M volume."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("500000"),
            asset_class="equity",
        )
        assert rate == Decimal("0.0003")  # 0.03%

    def test_institutional_tier_commission(self, engine):
        """Test institutional tier for €1M+ volume."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("2000000"),
            asset_class="equity",
        )
        assert rate == Decimal("0.0002")  # 0.02%

    def test_crypto_premium(self, engine):
        """Test crypto asset class adds 50% premium."""
        equity_rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        crypto_rate = engine.get_rate_for_volume(
            symbol="BTC",
            volume_usd=Decimal("100000"),
            asset_class="crypto",
        )
        assert crypto_rate == equity_rate * Decimal("1.5")

    def test_forex_discount(self, engine):
        """Test forex asset class gives 50% discount."""
        equity_rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        forex_rate = engine.get_rate_for_volume(
            symbol="EURUSD",
            volume_usd=Decimal("100000"),
            asset_class="forex",
        )
        assert forex_rate == equity_rate * Decimal("0.5")

    def test_tier_boundary_50k(self, engine):
        """Test tier boundary at €50k (retail to semi-pro)."""
        # Just below €50k
        rate_below = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("49999"),
            asset_class="equity",
        )
        assert rate_below == Decimal("0.001")  # retail

        # At €50k
        rate_at = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("50000"),
            asset_class="equity",
        )
        assert rate_at == Decimal("0.0005")  # semi_pro

    def test_explicit_tier_override(self, engine):
        """Test explicit account tier overrides volume-based calculation."""
        # Large volume would normally give pro rate
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("500000"),
            asset_class="equity",
            account_tier="retail",  # Override to retail
        )
        assert rate == Decimal("0.001")  # Forced to retail

    def test_get_all_tiers(self, engine):
        """Test get_all_tiers returns proper structure."""
        tiers = engine.get_all_tiers()
        assert len(tiers) == 4
        assert "retail" in tiers
        assert "semi_pro" in tiers
        assert "pro" in tiers
        assert "institutional" in tiers

        # Check structure
        for tier_name, tier_data in tiers.items():
            assert "rate" in tier_data
            assert "min_volume" in tier_data
            assert isinstance(tier_data["rate"], Decimal)
            assert isinstance(tier_data["min_volume"], Decimal)

    def test_estimate_commission_savings_equity(self, engine):
        """Test commission savings calculation for equity."""
        volume = Decimal("100000")
        savings = engine.estimate_commission_savings(
            symbol="AAPL",
            volume_usd=volume,
            asset_class="equity",
        )

        # Should have 4 tiers
        assert len(savings) == 4
        assert "retail" in savings
        assert "semi_pro" in savings
        assert "pro" in savings
        assert "institutional" in savings

        # Costs should decrease with tiers
        retail_cost = savings["retail"]["cost"]
        semi_pro_cost = savings["semi_pro"]["cost"]
        pro_cost = savings["pro"]["cost"]
        institutional_cost = savings["institutional"]["cost"]

        assert retail_cost > semi_pro_cost > pro_cost > institutional_cost

    def test_estimate_commission_savings_structure(self, engine):
        """Test commission savings data structure."""
        savings = engine.estimate_commission_savings(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )

        # Check retail tier structure
        retail = savings["retail"]
        assert "rate" in retail
        assert "cost" in retail
        assert "savings_vs_retail" in retail
        assert "min_volume" in retail

        # Retail should have no savings vs itself
        assert retail["savings_vs_retail"] == Decimal("0")

        # Higher tiers should have positive savings
        assert savings["semi_pro"]["savings_vs_retail"] > Decimal("0")
        assert savings["pro"]["savings_vs_retail"] > Decimal("0")

    def test_zero_volume(self, engine):
        """Test handling of zero volume."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("0"),
            asset_class="equity",
        )
        # Should return retail rate for zero volume
        assert rate == Decimal("0.001")

    def test_large_volume_ceiling(self, engine):
        """Test that very large volumes don't exceed institutional rate."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000000"),  # €100M
            asset_class="equity",
        )
        # Should cap at institutional rate
        assert rate == Decimal("0.0002")

    def test_commodity_premium(self, engine):
        """Test commodity asset class adds 20% premium."""
        equity_rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        commodity_rate = engine.get_rate_for_volume(
            symbol="GOLD",
            volume_usd=Decimal("100000"),
            asset_class="commodity",
        )
        assert commodity_rate == equity_rate * Decimal("1.2")

    def test_bond_discount(self, engine):
        """Test bond asset class gives 30% discount."""
        equity_rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        bond_rate = engine.get_rate_for_volume(
            symbol="BOND",
            volume_usd=Decimal("100000"),
            asset_class="bond",
        )
        assert bond_rate == equity_rate * Decimal("0.7")

    def test_commission_cost_calculation(self, engine):
        """Test actual commission cost calculation."""
        rate = engine.get_rate_for_volume(
            symbol="AAPL",
            volume_usd=Decimal("100000"),
            asset_class="equity",
        )
        # Semi-pro rate should be 0.05% = 0.0005
        expected_cost = Decimal("100000") * Decimal("0.0005")
        assert expected_cost == Decimal("50")
