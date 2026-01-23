"""
Tests for Knowledge Graph Builder (Neo4j integration)
"""

import pytest

from app.services.knowledge_graph.graph_builder import (
    KnowledgeGraphBuilder,
    get_knowledge_graph_builder,
)


@pytest.fixture
def graph_builder():
    """Create knowledge graph builder instance."""
    return KnowledgeGraphBuilder(
        graph_uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
    )


@pytest.fixture
def sample_assets():
    """Create sample asset data."""
    return [
        {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "type": "stock"},
    ]


@pytest.fixture
def sample_strategies():
    """Create sample strategy data."""
    return [
        {
            "name": "momentum_strategy",
            "type": "momentum",
            "risk_level": 0.5,
        },
        {
            "name": "value_strategy",
            "type": "value",
            "risk_level": 0.3,
        },
    ]


@pytest.fixture
def sample_correlations():
    """Create sample correlation data."""
    return [
        {"symbol1": "AAPL", "symbol2": "MSFT", "strength": 0.85},
        {"symbol1": "GOOGL", "symbol2": "MSFT", "strength": 0.78},
        {"symbol1": "AAPL", "symbol2": "GOOGL", "strength": 0.72},
    ]


class TestKnowledgeGraphBuilderInitialization:
    """Test knowledge graph builder initialization."""

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        builder = KnowledgeGraphBuilder()
        assert builder.graph_uri == "bolt://localhost:7687"
        assert builder.user == "neo4j"
        assert builder.password == "password"
        assert builder.connected is False

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        builder = KnowledgeGraphBuilder(
            graph_uri="bolt://custom:7687",
            user="custom_user",
            password="custom_pass",
        )
        assert builder.graph_uri == "bolt://custom:7687"
        assert builder.user == "custom_user"
        assert builder.password == "custom_pass"


class TestKnowledgeGraphBuilderConnection:
    """Test connection management."""

    @pytest.mark.asyncio
    async def test_connect(self, graph_builder):
        """Test connecting to Neo4j."""
        result = await graph_builder.connect()
        assert result is True
        assert graph_builder.connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self, graph_builder):
        """Test disconnecting from Neo4j."""
        await graph_builder.connect()
        await graph_builder.disconnect()
        assert graph_builder.connected is False

    def test_get_builder_status(self, graph_builder):
        """Test getting builder status."""
        status = graph_builder.get_builder_status()
        assert "connected" in status
        assert "graph_uri" in status
        assert "nodes_created" in status
        assert "relationships_created" in status


class TestAssetNodeCreation:
    """Test asset node creation."""

    @pytest.mark.asyncio
    async def test_create_asset_nodes(self, graph_builder, sample_assets):
        """Test creating asset nodes."""
        await graph_builder.connect()
        count = await graph_builder.create_asset_nodes(sample_assets)

        assert count == len(sample_assets)
        assert graph_builder.nodes_created >= count

    @pytest.mark.asyncio
    async def test_create_asset_nodes_without_connection(self, graph_builder, sample_assets):
        """Test creating nodes without connection."""
        count = await graph_builder.create_asset_nodes(sample_assets)
        assert count == 0

    @pytest.mark.asyncio
    async def test_create_asset_nodes_empty_list(self, graph_builder):
        """Test creating nodes with empty list."""
        await graph_builder.connect()
        count = await graph_builder.create_asset_nodes([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_nodes_counter_increment(self, graph_builder, sample_assets):
        """Test that nodes counter increments."""
        await graph_builder.connect()
        initial_count = graph_builder.nodes_created

        await graph_builder.create_asset_nodes(sample_assets)

        assert graph_builder.nodes_created > initial_count


class TestStrategyNodeCreation:
    """Test strategy node creation."""

    @pytest.mark.asyncio
    async def test_create_strategy_nodes(self, graph_builder, sample_strategies):
        """Test creating strategy nodes."""
        await graph_builder.connect()
        count = await graph_builder.create_strategy_nodes(sample_strategies)

        assert count == len(sample_strategies)

    @pytest.mark.asyncio
    async def test_create_strategy_nodes_without_connection(self, graph_builder, sample_strategies):
        """Test creating strategy nodes without connection."""
        count = await graph_builder.create_strategy_nodes(sample_strategies)
        assert count == 0


class TestRelationshipCreation:
    """Test relationship creation."""

    @pytest.mark.asyncio
    async def test_create_correlation_relationships(self, graph_builder, sample_correlations):
        """Test creating correlation relationships."""
        await graph_builder.connect()
        count = await graph_builder.create_correlation_relationships(sample_correlations)

        assert count == len(sample_correlations)
        assert graph_builder.relationships_created >= count

    @pytest.mark.asyncio
    async def test_create_strategy_asset_relationships(self, graph_builder):
        """Test creating strategy-asset relationships."""
        await graph_builder.connect()
        relationships = [
            {"strategy": "momentum_strategy", "symbol": "AAPL", "weight": 1.0},
            {"strategy": "value_strategy", "symbol": "MSFT", "weight": 0.8},
        ]

        count = await graph_builder.create_strategy_asset_relationships(relationships)

        assert count == len(relationships)

    @pytest.mark.asyncio
    async def test_create_performance_nodes(self, graph_builder):
        """Test creating performance nodes."""
        await graph_builder.connect()
        performances = [
            {
                "strategy": "momentum_strategy",
                "return": 0.15,
                "sharpe": 1.5,
                "date": "2025-01-01",
            },
        ]

        count = await graph_builder.create_performance_nodes(performances)
        assert count == len(performances)


class TestAssetQuery:
    """Test asset query operations."""

    @pytest.mark.asyncio
    async def test_find_similar_assets(self, graph_builder):
        """Test finding similar assets."""
        await graph_builder.connect()

        similar = await graph_builder.find_similar_assets("AAPL", limit=10)

        assert isinstance(similar, list)
        # Simulated results should have at most limit items
        assert len(similar) <= 10

    @pytest.mark.asyncio
    async def test_find_similar_assets_structure(self, graph_builder):
        """Test structure of similar assets results."""
        await graph_builder.connect()

        similar = await graph_builder.find_similar_assets("AAPL", limit=5)

        for asset in similar:
            assert "symbol" in asset
            assert "correlation" in asset

    @pytest.mark.asyncio
    async def test_find_correlated_assets(self, graph_builder):
        """Test finding correlated assets."""
        await graph_builder.connect()

        correlated = await graph_builder.find_correlated_assets(
            "AAPL", min_correlation=0.7, limit=10
        )

        assert isinstance(correlated, list)

    @pytest.mark.asyncio
    async def test_find_correlated_assets_with_threshold(self, graph_builder):
        """Test finding assets with correlation threshold."""
        await graph_builder.connect()

        # High threshold should return fewer results
        high_threshold = await graph_builder.find_correlated_assets(
            "AAPL", min_correlation=0.9, limit=10
        )
        low_threshold = await graph_builder.find_correlated_assets(
            "AAPL", min_correlation=0.5, limit=10
        )

        assert len(high_threshold) <= len(low_threshold)


class TestStrategyQuery:
    """Test strategy query operations."""

    @pytest.mark.asyncio
    async def test_find_best_strategies_for_asset(self, graph_builder):
        """Test finding best strategies for an asset."""
        await graph_builder.connect()

        strategies = await graph_builder.find_best_strategies_for_asset("AAPL", limit=10)

        assert isinstance(strategies, list)
        assert len(strategies) <= 10

    @pytest.mark.asyncio
    async def test_find_best_strategies_structure(self, graph_builder):
        """Test structure of best strategies results."""
        await graph_builder.connect()

        strategies = await graph_builder.find_best_strategies_for_asset("AAPL")

        for strat in strategies:
            assert "strategy" in strat
            assert "return_pct" in strat
            assert "sharpe_ratio" in strat


class TestNetworkAnalysis:
    """Test network analysis operations."""

    @pytest.mark.asyncio
    async def test_get_strategy_network(self, graph_builder):
        """Test getting strategy network statistics."""
        await graph_builder.connect()

        network = await graph_builder.get_strategy_network()

        assert "num_strategies" in network
        assert "num_assets" in network
        assert "num_relationships" in network
        assert "average_degree" in network
        assert "top_strategies" in network

    @pytest.mark.asyncio
    async def test_get_asset_portfolio_recommendations(self, graph_builder):
        """Test getting portfolio recommendations."""
        await graph_builder.connect()

        current_assets = ["AAPL", "GOOGL"]
        recommendations = await graph_builder.get_asset_portfolio_recommendations(
            current_assets, target_diversification=0.5
        )

        assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_portfolio_recommendations_structure(self, graph_builder):
        """Test structure of portfolio recommendations."""
        await graph_builder.connect()

        current_assets = ["AAPL"]
        recommendations = await graph_builder.get_asset_portfolio_recommendations(current_assets)

        for rec in recommendations:
            assert "symbol" in rec
            assert "reason" in rec
            assert "expected_return_pct" in rec


class TestKnowledgeGraphSingleton:
    """Test singleton pattern."""

    @pytest.mark.asyncio
    async def test_singleton_same_instance(self):
        """Test that singleton returns same instance."""
        builder1 = get_knowledge_graph_builder()
        builder2 = get_knowledge_graph_builder()
        assert builder1 is builder2

    @pytest.mark.asyncio
    async def test_singleton_with_params(self):
        """Test singleton with parameters."""
        # Reset singleton to allow fresh initialization for this test
        import app.services.knowledge_graph.graph_builder as gb_module

        gb_module._graph_builder = None

        builder1 = get_knowledge_graph_builder(graph_uri="bolt://custom:7687")
        # Same instance returned, params ignored on second call
        builder2 = get_knowledge_graph_builder(graph_uri="bolt://other:7687")
        assert builder1 is builder2
        # First initialization wins
        assert builder1.graph_uri == "bolt://custom:7687"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_create_nodes_with_invalid_data(self, graph_builder):
        """Test node creation with invalid data."""
        await graph_builder.connect()
        # Test with None
        count = await graph_builder.create_asset_nodes(None)
        # Should handle gracefully (likely returns 0 or raises caught exception)
        assert count == 0

    @pytest.mark.asyncio
    async def test_query_without_connection(self, graph_builder):
        """Test querying without connection."""
        # Don't connect
        similar = await graph_builder.find_similar_assets("AAPL")
        assert similar == []

    @pytest.mark.asyncio
    async def test_multiple_operations(self, graph_builder, sample_assets):
        """Test multiple operations in sequence."""
        await graph_builder.connect()

        # Create assets
        asset_count = await graph_builder.create_asset_nodes(sample_assets)
        assert asset_count > 0

        # Query assets
        similar = await graph_builder.find_similar_assets("AAPL")
        assert isinstance(similar, list)

        # Get network stats
        network = await graph_builder.get_strategy_network()
        assert "num_strategies" in network
