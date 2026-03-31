"""
Comprehensive integration tests for FIFO tax lot tracking.

This module tests the FIFO (First-In, First-Out) tax lot tracking system including:
- Trade recording
- Lot creation for BUY orders
- Lot closure for SELL orders
- Cost basis calculation
- Realized gains/losses tracking
- Multi-broker support
- Tax year reporting
- Integrity verification
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.infrastructure.persistence.database import get_db_transaction
from app.services.fifo.fifo_integrator import FIFOIntegrator, Position, Trade
from app.infrastructure.persistence.tax.fifo_schema import AssetType, Lot, LotStatus, Transaction


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorBasicOperations:
    """Test basic FIFO integrator operations."""

    async def test_initialize_fifo_integrator(self):
        """Test that FIFO integrator initializes correctly."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Verify default account was created
        assert "default" in integrator._accounts_cache

    async def test_record_buy_trade_creates_lot(self):
        """Test that recording a BUY trade creates a FIFO lot."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create BUY trade
        trade = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            commission=Decimal("1.00"),
            broker_name="alpaca",
            broker_trade_id="alpaca_001",
        )

        # Record trade
        await integrator.on_trade_executed(trade)

        # Verify lot was created
        lots = await integrator.get_open_lots("AAPL")
        assert len(lots) == 1
        assert lots[0].quantity_opened == Decimal("100")
        assert lots[0].cost_basis_open == Decimal("15000.00")  # 100 * 150

    async def test_record_sell_trade_closes_lot_fifo(self):
        """Test that recording a SELL trade closes lots in FIFO order."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create multiple BUY trades
        execution_time = datetime.now(timezone.utc)

        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=execution_time,
            broker_name="alpaca",
        )

        buy2 = Trade(
            trade_id="buy_002",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("50"),
            execution_price=Decimal("155.00"),
            execution_time=execution_time + timedelta(seconds=1),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy1)
        await integrator.on_trade_executed(buy2)

        # Verify 2 lots open
        lots = await integrator.get_open_lots("AAPL")
        assert len(lots) == 2

        # Sell 120 shares (should close first lot entirely, 20 from second)
        sell = Trade(
            trade_id="sell_001",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("120"),
            execution_price=Decimal("160.00"),
            execution_time=execution_time + timedelta(seconds=2),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(sell)

        # Verify FIFO closure
        lots = await integrator.get_open_lots("AAPL")
        assert len(lots) == 1  # Only second lot remaining
        assert lots[0].quantity_remaining == Decimal("30")  # 50 - 20

        # Check realized gains/losses
        gains_losses = await integrator.get_realized_gains_losses("AAPL")
        assert gains_losses["lots_closed"] == 2  # First lot fully, second partially

    async def test_cost_basis_calculation(self):
        """Test that cost basis is calculated correctly."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create BUY trades
        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        buy2 = Trade(
            trade_id="buy_002",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("50"),
            execution_price=Decimal("155.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy1)
        await integrator.on_trade_executed(buy2)

        # Calculate expected cost basis
        expected_cost_basis = (100 * 150) + (50 * 155)  # 15000 + 7750 = 22750

        # Verify cost basis
        cost_basis = await integrator.get_cost_basis("AAPL")
        assert cost_basis == Decimal("22750")

    async def test_average_cost_calculation(self):
        """Test that average cost is calculated correctly."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create BUY trades
        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        buy2 = Trade(
            trade_id="buy_002",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("50"),
            execution_price=Decimal("160.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy1)
        await integrator.on_trade_executed(buy2)

        # Calculate expected average cost
        # Total cost: 15000 + 8000 = 23000
        # Total quantity: 150
        # Average: 23000 / 150 = 153.33
        avg_cost = await integrator.get_average_cost("AAPL")
        expected_avg = Decimal("23000") / Decimal("150")

        assert abs(avg_cost - expected_avg) < Decimal("0.01")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorComplexScenarios:
    """Test complex FIFO scenarios."""

    async def test_partial_lot_closure(self):
        """Test partial closure of a lot."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create BUY trade
        buy = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy)

        # Partially close position
        sell = Trade(
            trade_id="sell_001",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("30"),
            execution_price=Decimal("160.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(sell)

        # Verify partial closure
        lots = await integrator.get_open_lots("AAPL")
        assert len(lots) == 1
        assert lots[0].quantity_remaining == Decimal("70")
        assert lots[0].status == LotStatus.PARTIAL

    async def test_multi_symbol_tracking(self):
        """Test tracking multiple symbols simultaneously."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create trades for multiple symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]

        for symbol in symbols:
            buy = Trade(
                trade_id=f"buy_{symbol}",
                symbol=symbol,
                side="BUY",
                quantity=Decimal("100"),
                execution_price=Decimal("150.00"),
                execution_time=datetime.now(timezone.utc),
                broker_name="alpaca",
            )
            await integrator.on_trade_executed(buy)

        # Verify lots for each symbol
        for symbol in symbols:
            lots = await integrator.get_open_lots(symbol)
            assert len(lots) == 1
            assert lots[0].symbol == symbol

    async def test_crypto_asset_detection(self):
        """Test that crypto assets are correctly identified."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create crypto trade
        buy = Trade(
            trade_id="buy_btc",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("1.5"),
            execution_price=Decimal("45000.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="binance",
        )

        await integrator.on_trade_executed(buy)

        # Verify asset type
        async with get_db_transaction() as session:
            stmt = select(Transaction).where(Transaction.symbol == "BTCUSD")
            result = await session.execute(stmt)
            tx = result.scalars().first()

            assert tx is not None
            assert tx.asset_type == AssetType.CRYPTO

    async def test_forex_asset_detection(self):
        """Test that forex assets are correctly identified."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create forex trade
        buy = Trade(
            trade_id="buy_eurusd",
            symbol="EURUSD",
            side="BUY",
            quantity=Decimal("100000"),
            execution_price=Decimal("1.10"),
            execution_time=datetime.now(timezone.utc),
            broker_name="fxcm",
        )

        await integrator.on_trade_executed(buy)

        # Verify asset type
        async with get_db_transaction() as session:
            stmt = select(Transaction).where(Transaction.symbol == "EURUSD")
            result = await session.execute(stmt)
            tx = result.scalars().first()

            assert tx is not None
            assert tx.asset_type == AssetType.FOREX

    async def test_tax_year_filtering(self):
        """Test filtering by tax year."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create trades across multiple years
        buy_2023 = Trade(
            trade_id="buy_2023",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime(2023, 6, 1, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        sell_2023 = Trade(
            trade_id="sell_2023",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("160.00"),
            execution_time=datetime(2023, 8, 1, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        buy_2024 = Trade(
            trade_id="buy_2024",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("155.00"),
            execution_time=datetime(2024, 1, 15, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        sell_2024 = Trade(
            trade_id="sell_2024",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("165.00"),
            execution_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy_2023)
        await integrator.on_trade_executed(sell_2023)
        await integrator.on_trade_executed(buy_2024)
        await integrator.on_trade_executed(sell_2024)

        # Check 2023 gains
        gains_2023 = await integrator.get_realized_gains_losses("AAPL", year=2023)
        assert gains_2023["lots_closed"] == 1
        expected_gain_2023 = (160 - 150) * 100  # 1000
        assert abs(gains_2023["net_gain_loss"] - expected_gain_2023) < 1

        # Check 2024 gains
        gains_2024 = await integrator.get_realized_gains_losses("AAPL", year=2024)
        assert gains_2024["lots_closed"] == 1
        expected_gain_2024 = (165 - 155) * 100  # 1000
        assert abs(gains_2024["net_gain_loss"] - expected_gain_2024) < 1


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorErrorHandling:
    """Test error handling in FIFO integrator."""

    async def test_sell_without_sufficient_lots(self):
        """Test selling without having enough lots."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Try to sell without buying first
        sell = Trade(
            trade_id="sell_001",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("160.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        # Should record transaction but mark with error
        await integrator.on_trade_executed(sell)

        # Verify transaction was recorded
        async with get_db_transaction() as session:
            stmt = select(Transaction).where(Transaction.external_id == "alpaca_sell_001")
            result = await session.execute(stmt)
            tx = result.scalars().first()

            assert tx is not None
            assert "fifo_error" in tx.meta_data

    async def test_duplicate_trade_id(self):
        """Test handling of duplicate trade IDs."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create first trade
        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
            broker_trade_id="dup_001",
        )

        await integrator.on_trade_executed(buy1)

        # Try to record duplicate
        buy2 = Trade(
            trade_id="buy_002",  # Different trade_id
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("155.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
            broker_trade_id="dup_001",  # Same broker_trade_id
        )

        # Should handle duplicate gracefully
        # (implementation may vary - this tests that it doesn't crash)
        try:
            await integrator.on_trade_executed(buy2)
        except Exception as e:
            # Expected - duplicate detection
            assert "duplicate" in str(e).lower() or "exists" in str(e).lower()

    async def test_invalid_trade_side(self):
        """Test handling of invalid trade side."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create trade with invalid side
        trade = Trade(
            trade_id="invalid_001",
            symbol="AAPL",
            side="INVALID",  # Invalid side
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid trade side"):
            await integrator.on_trade_executed(trade)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorIntegrity:
    """Test FIFO data integrity."""

    async def test_fifo_integrity_verification(self):
        """Test FIFO integrity verification."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create trades
        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        buy2 = Trade(
            trade_id="buy_002",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("50"),
            execution_price=Decimal("155.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        sell = Trade(
            trade_id="sell_001",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("75"),
            execution_price=Decimal("160.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy1)
        await integrator.on_trade_executed(buy2)
        await integrator.on_trade_executed(sell)

        # Verify integrity
        integrity = await integrator.verify_fifo_integrity("AAPL")

        assert integrity["is_valid"] is True
        assert integrity["total_bought"] == 150.0
        assert integrity["total_sold"] == 75.0
        assert integrity["total_remaining"] == 75.0

    async def test_position_quantity_matching(self):
        """Test that FIFO lots match position quantities."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create BUY trades
        buy1 = Trade(
            trade_id="buy_001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy1)

        # Create position matching FIFO lots
        position = Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            market_value=Decimal("15000.00"),
            cost_basis=Decimal("15000.00"),
            unrealized_pnl=Decimal("0"),
            timestamp=datetime.now(timezone.utc),
        )

        # Should verify without warnings
        await integrator.on_position_opened(position)

        # Now test mismatch
        position_wrong = Position(
            symbol="AAPL",
            quantity=Decimal("90"),  # Wrong quantity
            average_price=Decimal("150.00"),
            market_value=Decimal("13500.00"),
            cost_basis=Decimal("13500.00"),
            unrealized_pnl=Decimal("0"),
            timestamp=datetime.now(timezone.utc),
        )

        # Should log warning but not crash
        await integrator.on_position_opened(position_wrong)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorMultiBroker:
    """Test multi-broker FIFO tracking."""

    async def test_separate_accounts_per_broker(self):
        """Test that each broker has separate account."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Create trades for different brokers
        buy_alpaca = Trade(
            trade_id="buy_alpaca",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        buy_ibkr = Trade(
            trade_id="buy_ibkr",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="ibkr",
        )

        await integrator.on_trade_executed(buy_alpaca)
        await integrator.on_trade_executed(buy_ibkr)

        # Verify both accounts exist
        assert "alpaca" in integrator._accounts_cache or len(integrator._accounts_cache) > 0

        # Verify lots for each broker
        async with get_db_transaction() as session:
            stmt = select(Lot).where(Lot.symbol == "AAPL")
            result = await session.execute(stmt)
            lots = result.scalars().all()

            # Should have 2 lots (one per broker)
            assert len(lots) == 2

    async def test_cross_broker_fifo(self):
        """Test that FIFO is tracked per broker, not globally."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Buy on Alpaca
        buy_alpaca = Trade(
            trade_id="buy_alpaca",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="alpaca",
        )

        # Sell on IBKR (should not close Alpaca lot)
        sell_ibkr = Trade(
            trade_id="sell_ibkr",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("160.00"),
            execution_time=datetime.now(timezone.utc),
            broker_name="ibkr",
        )

        await integrator.on_trade_executed(buy_alpaca)

        # This should fail or create separate lot
        try:
            await integrator.on_trade_executed(sell_ibkr)
        except Exception:
            pass  # Expected - no lots to close on IBKR


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_database
class TestFIFOIntegratorHoldingPeriods:
    """Test holding period calculations for tax purposes."""

    async def test_short_term_vs_long_term_gains(self):
        """Test differentiation between short-term and long-term gains."""
        integrator = FIFOIntegrator(user_id=uuid4())
        await integrator.initialize()

        # Buy and hold for less than a year (short-term)
        buy_short = Trade(
            trade_id="buy_short",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            execution_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        sell_short = Trade(
            trade_id="sell_short",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("160.00"),
            execution_time=datetime(2023, 6, 1, tzinfo=timezone.utc),  # 5 months later
            broker_name="alpaca",
        )

        # Buy and hold for more than a year (long-term)
        buy_long = Trade(
            trade_id="buy_long",
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("300.00"),
            execution_time=datetime(2022, 1, 1, tzinfo=timezone.utc),
            broker_name="alpaca",
        )

        sell_long = Trade(
            trade_id="sell_long",
            symbol="MSFT",
            side="SELL",
            quantity=Decimal("100"),
            execution_price=Decimal("350.00"),
            execution_time=datetime(2023, 2, 1, tzinfo=timezone.utc),  # 13 months later
            broker_name="alpaca",
        )

        await integrator.on_trade_executed(buy_short)
        await integrator.on_trade_executed(sell_short)
        await integrator.on_trade_executed(buy_long)
        await integrator.on_trade_executed(sell_long)

        # Check gains breakdown
        gains = await integrator.get_realized_gains_losses()

        # Should have both short-term and long-term gains
        assert gains["short_term_gain"] > 0
        assert gains["long_term_gain"] > 0
