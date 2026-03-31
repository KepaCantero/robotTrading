"""
Test suite for T006: Top 20 Liquid Assets Identification.

This module contains comprehensive tests for asset models, services, and API endpoints.
"""

from decimal import Decimal

import pytest

from app.domain.models.assets import (
    Asset,
    AssetClass,
    AssetFilter,
    AssetRanking,
    AssetUniverse,
    Exchange,
    LiquidityMetrics,
)
from app.services.asset_identification import AssetIdentificationService


class TestAssetModels:
    """Test asset model functionality."""

    def test_asset_creation(self):
        """Test basic asset creation."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
            market_cap=Decimal("3000000000000"),
        )
        assert asset.symbol == "AAPL"
        assert asset.name == "Apple Inc."
        assert asset.asset_class == AssetClass.EQUITY
        assert asset.exchange == Exchange.NASDAQ
        assert asset.avg_volume == Decimal("50000000")
        assert asset.avg_spread == Decimal("0.01")
        assert asset.market_cap == Decimal("3000000000000")
        assert asset.is_active is True
        assert asset.liquidity_score == 85.0

    def test_asset_symbol_validation(self):
        """Test asset symbol validation."""
        # Valid symbol
        asset = Asset(
            symbol="  AAPL  ",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        )
        assert asset.symbol == "AAPL"

        # Invalid symbol
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            Asset(
                symbol="",
                name="Apple Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.01"),
            )

    def test_asset_name_validation(self):
        """Test asset name validation."""
        # Valid name
        asset = Asset(
            symbol="AAPL",
            name="  Apple Inc.  ",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        )
        assert asset.name == "Apple Inc."

        # Invalid name
        with pytest.raises(ValueError, match="Name cannot be empty"):
            Asset(
                symbol="AAPL",
                name="",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.01"),
            )

    def test_asset_liquidity_score_calculation(self):
        """Test liquidity score calculation."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        )
        # Test volume score calculation
        volume_score = asset.volume_score
        assert 0 <= volume_score <= 100

        # Test spread score calculation
        spread_score = asset.spread_score
        assert 0 <= spread_score <= 100

        # Test combined score
        combined_score = asset.combined_liquidity_score
        assert 0 <= combined_score <= 100

    def test_asset_universe_creation(self):
        """Test asset universe creation."""
        universe = AssetUniverse(asset_class=AssetClass.EQUITY, top_n=20)
        assert universe.asset_class == AssetClass.EQUITY
        assert universe.top_n == 20
        assert universe.total_assets == 0
        assert universe.avg_liquidity_score == 0.0
        assert universe.total_market_cap is None

    def test_asset_universe_add_asset(self):
        """Test adding assets to universe."""
        universe = AssetUniverse(asset_class=AssetClass.EQUITY, top_n=20)
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        )
        # Add asset
        success = universe.add_asset(asset)
        assert success is True
        assert universe.total_assets == 1
        assert universe.get_asset_by_symbol("AAPL") == asset

        # Try to add same asset again
        success = universe.add_asset(asset)
        assert success is False
        assert universe.total_assets == 1

    def test_asset_universe_remove_asset(self):
        """Test removing assets from universe."""
        universe = AssetUniverse(asset_class=AssetClass.EQUITY, top_n=20)
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        )
        universe.add_asset(asset)
        assert universe.total_assets == 1

        # Remove asset
        success = universe.remove_asset("AAPL")
        assert success is True
        assert universe.total_assets == 0

        # Try to remove non-existent asset
        success = universe.remove_asset("MSFT")
        assert success is False

    def test_asset_universe_top_liquid_assets(self):
        """Test getting top liquid assets."""
        universe = AssetUniverse(asset_class=AssetClass.EQUITY, top_n=20)
        # Add multiple assets with different liquidity scores
        assets = [
            Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=90.0,
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft Corporation",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("30000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=85.0,
            ),
            Asset(
                symbol="GOOGL",
                name="Alphabet Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("25000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=80.0,
            ),
        ]

        for asset in assets:
            universe.add_asset(asset)

        # Get top liquid assets
        top_assets = universe.get_top_liquid_assets(2)
        assert len(top_assets) == 2
        assert top_assets[0].symbol == "AAPL"  # Highest liquidity
        assert top_assets[1].symbol == "MSFT"  # Second highest

    def test_liquidity_metrics_creation(self):
        """Test liquidity metrics creation."""
        metrics = LiquidityMetrics(
            symbol="AAPL",
            daily_volume=Decimal("50000000"),
            avg_volume_30d=Decimal("45000000"),
            current_spread=Decimal("0.01"),
            avg_spread_30d=Decimal("0.012"),
            current_price=Decimal("150.0"),
            volume_score=85.0,
            spread_score=90.0,
            overall_liquidity_score=87.5,
        )
        assert metrics.symbol == "AAPL"
        assert metrics.daily_volume == Decimal("50000000")
        assert metrics.volume_score == 85.0
        assert metrics.spread_score == 90.0
        assert metrics.overall_liquidity_score == 87.5

    def test_asset_ranking_creation(self):
        """Test asset ranking creation."""
        ranking = AssetRanking(asset_class=AssetClass.EQUITY)
        assert ranking.asset_class == AssetClass.EQUITY
        assert len(ranking.rankings) == 0

        # Add ranking
        ranking.add_ranking("AAPL", 90.0, 1, 85.0, 95.0)
        assert len(ranking.rankings) == 1
        assert ranking.rankings[0]["symbol"] == "AAPL"
        assert ranking.rankings[0]["rank"] == 1

    def test_asset_filter_matching(self):
        """Test asset filter matching."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=90.0,
        )
        # Test matching filter
        filter_criteria = AssetFilter(
            asset_class=AssetClass.EQUITY,
            min_liquidity_score=80.0,
            min_volume=Decimal("10000000"),
            max_spread=Decimal("0.02"),
            active_only=True,
        )
        assert filter_criteria.matches(asset) is True

        # Test non-matching filter
        filter_criteria.min_liquidity_score = 95.0
        assert filter_criteria.matches(asset) is False


class TestAssetIdentificationService:
    """Test asset identification service functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return AssetIdentificationService()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert len(service.asset_universes) == len(AssetClass)
        assert len(service.rankings) == len(AssetClass)

        # Check that all asset classes have universes
        for asset_class in AssetClass:
            assert asset_class in service.asset_universes
            assert asset_class in service.rankings

    @pytest.mark.asyncio
    async def test_identify_liquid_equities(self, service):
        """Test identifying liquid equity assets."""
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 5)

        assert len(assets) == 5
        assert all(asset.asset_class == AssetClass.EQUITY for asset in assets)
        assert all(asset.liquidity_score > 0 for asset in assets)

        # Check that assets are sorted by liquidity score
        for i in range(len(assets) - 1):
            assert assets[i].liquidity_score >= assets[i + 1].liquidity_score

    @pytest.mark.asyncio
    async def test_identify_liquid_cryptos(self, service):
        """Test identifying liquid crypto assets."""
        assets = await service.identify_liquid_assets(AssetClass.CRYPTO, 3)

        assert len(assets) == 3
        assert all(asset.asset_class == AssetClass.CRYPTO for asset in assets)
        assert all(asset.liquidity_score > 0 for asset in assets)

    @pytest.mark.asyncio
    async def test_identify_liquid_forex(self, service):
        """Test identifying liquid forex assets."""
        assets = await service.identify_liquid_assets(AssetClass.FOREX, 3)

        assert len(assets) == 3
        assert all(asset.asset_class == AssetClass.FOREX for asset in assets)
        assert all(asset.liquidity_score > 0 for asset in assets)

    @pytest.mark.asyncio
    async def test_update_asset_universe(self, service):
        """Test updating asset universe."""
        # Create test assets
        assets = [
            Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=90.0,
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft Corporation",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("30000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=85.0,
            ),
        ]

        # Update universe
        success = await service.update_asset_universe(AssetClass.EQUITY, assets)
        assert success is True

        # Check universe was updated
        universe = service.asset_universes[AssetClass.EQUITY]
        assert universe.total_assets == 2
        assert universe.get_asset_by_symbol("AAPL") is not None
        assert universe.get_asset_by_symbol("MSFT") is not None

    @pytest.mark.asyncio
    async def test_get_top_liquid_assets(self, service):
        """Test getting top liquid assets."""
        # First identify and update universe
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 10)
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Get top liquid assets
        top_assets = await service.get_top_liquid_assets(AssetClass.EQUITY, 5)

        assert len(top_assets) == 5
        assert all(asset.asset_class == AssetClass.EQUITY for asset in top_assets)

        # Check sorting
        for i in range(len(top_assets) - 1):
            assert top_assets[i].liquidity_score >= top_assets[i + 1].liquidity_score

    @pytest.mark.asyncio
    async def test_get_asset_rankings(self, service):
        """Test getting asset rankings."""
        # First identify and update universe
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 5)
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Get rankings
        ranking = await service.get_asset_rankings(AssetClass.EQUITY)

        assert ranking.asset_class == AssetClass.EQUITY
        assert len(ranking.rankings) == 5

        # Check ranking order
        for i in range(len(ranking.rankings) - 1):
            assert ranking.rankings[i]["rank"] < ranking.rankings[i + 1]["rank"]

    @pytest.mark.asyncio
    async def test_filter_assets(self, service):
        """Test filtering assets."""
        # First identify and update universe
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 10)
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Create filter
        filter_criteria = AssetFilter(
            asset_class=AssetClass.EQUITY,
            min_liquidity_score=80.0,
            min_volume=Decimal("20000000"),
            active_only=True,
        )
        # Filter assets
        filtered_assets = await service.filter_assets(AssetClass.EQUITY, filter_criteria)

        assert len(filtered_assets) <= 10
        assert all(asset.liquidity_score >= 80.0 for asset in filtered_assets)
        assert all(asset.avg_volume >= Decimal("20000000") for asset in filtered_assets)
        assert all(asset.is_active for asset in filtered_assets)

    @pytest.mark.asyncio
    async def test_get_asset_by_symbol(self, service):
        """Test getting asset by symbol."""
        # First identify and update universe
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 5)
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Get asset by symbol
        asset = await service.get_asset_by_symbol("AAPL", AssetClass.EQUITY)
        assert asset is not None
        assert asset.symbol == "AAPL"

        # Get non-existent asset
        asset = await service.get_asset_by_symbol("NONEXISTENT", AssetClass.EQUITY)
        assert asset is None

    @pytest.mark.asyncio
    async def test_get_universe_summary(self, service):
        """Test getting universe summary."""
        # First identify and update universe
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 5)
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Get summary
        summary = await service.get_universe_summary(AssetClass.EQUITY)

        assert summary["asset_class"] == AssetClass.EQUITY.value
        assert summary["total_assets"] == 5
        assert summary["top_n"] == 20
        assert summary["avg_liquidity_score"] > 0
        assert len(summary["top_assets"]) == 5
        assert summary["ranking_count"] == 5


class TestAssetServiceIntegration:
    """Test asset service integration scenarios."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return AssetIdentificationService()

    @pytest.mark.asyncio
    async def test_complete_asset_identification_workflow(self, service):
        """Test complete asset identification workflow."""
        # Step 1: Identify liquid assets
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 10)
        assert len(assets) == 10

        # Step 2: Update universe
        success = await service.update_asset_universe(AssetClass.EQUITY, assets)
        assert success is True

        # Step 3: Get top assets
        top_assets = await service.get_top_liquid_assets(AssetClass.EQUITY, 5)
        assert len(top_assets) == 5

        # Step 4: Get rankings
        ranking = await service.get_asset_rankings(AssetClass.EQUITY)
        assert len(ranking.rankings) == 10

        # Step 5: Get summary
        summary = await service.get_universe_summary(AssetClass.EQUITY)
        assert summary["total_assets"] == 10

        # Step 6: Filter assets
        filter_criteria = AssetFilter(asset_class=AssetClass.EQUITY, min_liquidity_score=70.0)
        filtered_assets = await service.filter_assets(AssetClass.EQUITY, filter_criteria)
        assert len(filtered_assets) > 0

    @pytest.mark.asyncio
    async def test_multiple_asset_classes_workflow(self, service):
        """Test workflow with multiple asset classes."""
        asset_classes = [AssetClass.EQUITY, AssetClass.CRYPTO, AssetClass.FOREX]

        for asset_class in asset_classes:
            # Identify assets
            assets = await service.identify_liquid_assets(asset_class, 5)
            assert len(assets) == 5

            # Update universe
            success = await service.update_asset_universe(asset_class, assets)
            assert success is True

            # Get summary
            summary = await service.get_universe_summary(asset_class)
            assert summary["total_assets"] == 5

    @pytest.mark.asyncio
    async def test_asset_liquidity_score_consistency(self, service):
        """Test that liquidity scores are consistent across operations."""
        # Identify assets
        assets = await service.identify_liquid_assets(AssetClass.EQUITY, 5)

        # Store original scores
        original_scores = {asset.symbol: asset.liquidity_score for asset in assets}

        # Update universe
        await service.update_asset_universe(AssetClass.EQUITY, assets)

        # Get assets back and check scores
        retrieved_assets = await service.get_top_liquid_assets(AssetClass.EQUITY, 5)

        for asset in retrieved_assets:
            assert asset.liquidity_score == original_scores[asset.symbol]

    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling in service methods."""
        # Test with invalid asset class (if any)
        # This should not raise an exception but return empty list
        assets = await service.identify_liquid_assets(AssetClass.BOND, 5)
        assert isinstance(assets, list)

        # Test getting rankings for empty universe
        ranking = await service.get_asset_rankings(AssetClass.BOND)
        assert ranking.asset_class == AssetClass.BOND
        assert len(ranking.rankings) == 0

        # Test getting summary for empty universe
        summary = await service.get_universe_summary(AssetClass.BOND)
        assert summary["total_assets"] == 0
        assert summary["avg_liquidity_score"] == 0.0
