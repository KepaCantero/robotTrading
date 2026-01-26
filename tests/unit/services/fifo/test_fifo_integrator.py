"""
Unit tests for FIFOIntegrator service.

Tests the integration between live trading and FIFO tax lot tracking.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.services.fifo.fifo_integrator import FIFOIntegrator, LotInfo, Trade


@pytest.fixture
def fifo_integrator():
    """Create FIFO integrator instance."""
    return FIFOIntegrator(user_id=uuid4())


@pytest.fixture
def sample_trade_buy():
    """Create sample BUY trade."""
    return Trade(
        trade_id="trade_001",
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        execution_price=Decimal("150.00"),
        execution_time=datetime.now(timezone.utc),
        commission=Decimal("1.00"),
        broker_name="alpaca",
        broker_trade_id="algo_trade_001",
    )


@pytest.fixture
def sample_trade_sell():
    """Create sample SELL trade."""
    return Trade(
        trade_id="trade_002",
        symbol="AAPL",
        side="SELL",
        quantity=Decimal("50"),
        execution_price=Decimal("160.00"),
        execution_time=datetime.now(timezone.utc),
        commission=Decimal("1.00"),
        broker_name="alpaca",
        broker_trade_id="algo_trade_002",
    )


class TestFIFOIntegrator:
    """Test suite for FIFOIntegrator."""

    def test_initialization(self, fifo_integrator):
        """Test FIFO integrator initialization."""
        assert fifo_integrator is not None
        assert fifo_integrator.user_id is not None
        assert isinstance(fifo_integrator.user_id, UUID)

    @pytest.mark.asyncio
    async def test_determine_asset_type_crypto(self, fifo_integrator):
        """Test asset type detection for crypto."""
        # Bitcoin
        assert (await fifo_integrator._determine_asset_type("BTC")) == "crypto"
        assert (await fifo_integrator._determine_asset_type("BTCUSD")) == "crypto"

        # Ethereum
        assert (await fifo_integrator._determine_asset_type("ETH")) == "crypto"

        # Other crypto
        assert (await fifo_integrator._determine_asset_type("SOL")) == "crypto"

    @pytest.mark.asyncio
    async def test_determine_asset_type_stocks(self, fifo_integrator):
        """Test asset type detection for stocks."""
        assert await fifo_integrator._determine_asset_type("AAPL") == "stock_us"
        assert await fifo_integrator._determine_asset_type("TSLA") == "stock_us"

    @pytest.mark.asyncio
    async def test_determine_asset_type_forex(self, fifo_integrator):
        """Test asset type detection for forex."""
        assert await fifo_integrator._determine_asset_type("EURUSD") == "forex"
        assert await fifo_integrator._determine_asset_type("GBPJPY") == "forex"


class TestTradeData:
    """Test suite for Trade dataclass."""

    def test_trade_creation(self, sample_trade_buy):
        """Test trade object creation."""
        assert sample_trade_buy.symbol == "AAPL"
        assert sample_trade_buy.side == "BUY"
        assert sample_trade_buy.quantity == Decimal("100")
        assert sample_trade_buy.execution_price == Decimal("150.00")

    def test_trade_total_value(self, sample_trade_buy):
        """Test trade total value calculation."""
        expected_value = Decimal("100") * Decimal("150.00")
        actual_value = sample_trade_buy.quantity * sample_trade_buy.execution_price
        assert actual_value == expected_value


class TestLotInfo:
    """Test suite for LotInfo dataclass."""

    @pytest.fixture
    def sample_lot_info(self):
        """Create sample lot info."""
        return LotInfo(
            lot_id=uuid4(),
            symbol="AAPL",
            quantity_opened=Decimal("100"),
            quantity_remaining=Decimal("100"),
            cost_basis_open=Decimal("15000.00"),
            average_cost=Decimal("150.00"),
            opened_at=datetime.now(timezone.utc),
            status="open",
        )

    def test_lot_info_creation(self, sample_lot_info):
        """Test lot info creation."""
        assert sample_lot_info.symbol == "AAPL"
        assert sample_lot_info.quantity_opened == Decimal("100")
        assert sample_lot_info.quantity_remaining == Decimal("100")
        assert sample_lot_info.status == "open"

    def test_lot_cost_calculation(self, sample_lot_info):
        """Test cost calculations for lot."""
        # Cost basis should match
        assert sample_lot_info.cost_basis_open == Decimal("15000.00")

        # Average cost should be cost basis / quantity opened
        expected_avg = Decimal("15000.00") / Decimal("100")
        assert sample_lot_info.average_cost == expected_avg
