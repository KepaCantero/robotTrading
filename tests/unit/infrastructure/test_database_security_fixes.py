"""
Test database security fixes.

Tests for:
1. Connection string sanitization
2. Position state persistence
3. Position recovery after restart
"""

import json
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.core.database import get_database_engine
from app.database import get_sync_db
from app.database.models import PositionState
from app.services.position_monitor.position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
)


class TestConnectionStringSanitization:
    """Test that database connection strings are sanitized in logs."""

    @patch('app.core.database.logger')
    def test_postgresql_connection_sanitized(self, mock_logger):
        """Test PostgreSQL connection string is sanitized."""
        from app.core.config import get_settings

        settings = get_settings()

        # Mock settings to return connection string with credentials
        with patch.object(
            settings, 'database_url', 'postgresql://user:password@localhost:5432/trading'
        ):
            with patch.object(
                settings, 'get_database_url_async', return_value=settings.database_url
            ):
                # Trigger database engine creation
                try:
                    get_database_engine()
                except Exception:
                    # Engine creation might fail due to invalid connection
                    pass

                # Check that logger.info was called
                info_calls = [call for call in mock_logger.info.call_args_list]

                # Verify no call contains the full connection string
                for call in info_calls:
                    call_str = str(call)
                    assert 'user:password' not in call_str, "Credentials exposed in log!"
                    assert 'postgresql://user' not in call_str, "Full connection string logged!"

                # Verify at least one call contains host info
                host_logged = any(
                    'localhost:5432' in str(call) or 'host=' in str(call) for call in info_calls
                )
                assert host_logged, "Host information not logged"

    @patch('app.core.database.logger')
    def test_sqlite_connection_logged(self, mock_logger):
        """Test SQLite connection doesn't expose sensitive info."""
        from app.core.config import get_settings

        settings = get_settings()

        # Mock settings for SQLite
        with patch.object(settings, 'database_url', 'sqlite:///./trading.db'):
            with patch.object(
                settings, 'get_database_url_async', return_value=settings.database_url
            ):
                try:
                    get_database_engine()
                except Exception:
                    pass

                # Check logger was called with SQLite message
                info_calls = [str(call) for call in mock_logger.info.call_args_list]
                sqlite_logged = any('SQLite' in call for call in info_calls)
                assert sqlite_logged, "SQLite database type not logged"


class TestPositionStatePersistence:
    """Test position state persistence to database."""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker."""
        broker = Mock()
        broker.get_positions = Mock(return_value=[])
        broker.get_quote = Mock()
        return broker

    @pytest.fixture
    def sample_position(self):
        """Create a sample monitored position."""
        return MonitoredPosition(
            position_id="test_pos_1",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150.00"),
            quantity=Decimal("100"),
            current_price=Decimal("152.00"),
            stop_loss_pct=Decimal("0.05"),
            take_profit_pct=Decimal("0.10"),
        )

    @pytest.mark.asyncio
    async def test_monitor_id_generated(self, mock_broker):
        """Test that monitor_id is generated on initialization."""
        config = PositionMonitorConfig(persist_state=False)
        monitor = PositionMonitor(mock_broker, config)

        assert monitor.monitor_id is not None
        assert isinstance(monitor.monitor_id, str)
        assert 'monitor_' in monitor.monitor_id

    @pytest.mark.asyncio
    async def test_sync_state_to_database(self, mock_broker, sample_position):
        """Test syncing state to database."""
        config = PositionMonitorConfig(persist_state=True, state_sync_interval_seconds=1.0)
        monitor = PositionMonitor(mock_broker, config)

        # Add a position
        await monitor.add_position(sample_position)

        # Sync to database
        await monitor._sync_state()

        # Verify database entry
        with get_sync_db() as session:
            state_record = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == monitor.monitor_id)
                .first()
            )

            assert state_record is not None
            assert state_record.monitor_id == monitor.monitor_id
            assert state_record.is_active is True
            assert state_record.version == 1

            # Verify JSON serialization
            state_data = json.loads(state_record.positions_json)
            assert 'positions' in state_data
            assert len(state_data['positions']) == 1
            assert state_data['positions'][0]['symbol'] == 'AAPL'

    @pytest.mark.asyncio
    async def test_load_state_from_database(self, mock_broker, sample_position):
        """Test loading state from database."""
        config = PositionMonitorConfig(persist_state=True)

        # Create first monitor and save state
        monitor1 = PositionMonitor(mock_broker, config)
        await monitor1.add_position(sample_position)
        await monitor1._sync_state()

        # Create second monitor (simulating restart)
        monitor2 = PositionMonitor(mock_broker, config)
        monitor2.monitor_id = monitor1.monitor_id  # Simulate same monitor

        # Load state from database
        await monitor2._load_state_from_db()

        # Verify position was loaded
        assert len(monitor2._positions) == 1
        loaded_position = monitor2._positions[sample_position.position_id]
        assert loaded_position.symbol == sample_position.symbol
        assert loaded_position.side == sample_position.side
        assert loaded_position.quantity == sample_position.quantity

    @pytest.mark.asyncio
    async def test_state_version_increment(self, mock_broker, sample_position):
        """Test that state version increments on each sync."""
        config = PositionMonitorConfig(persist_state=True)
        monitor = PositionMonitor(mock_broker, config)

        await monitor.add_position(sample_position)

        # First sync
        await monitor._sync_state()

        with get_sync_db() as session:
            state = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == monitor.monitor_id)
                .first()
            )
            initial_version = state.version

        # Second sync
        await monitor._sync_state()

        with get_sync_db() as session:
            state = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == monitor.monitor_id)
                .first()
            )
            assert state.version == initial_version + 1

    @pytest.mark.asyncio
    async def test_persistence_disabled(self, mock_broker, sample_position):
        """Test that persistence can be disabled."""
        config = PositionMonitorConfig(persist_state=False)
        monitor = PositionMonitor(mock_broker, config)

        await monitor.add_position(sample_position)
        await monitor._sync_state()

        # Verify no database entry was created
        with get_sync_db() as session:
            state = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == monitor.monitor_id)
                .first()
            )
            assert state is None


class TestPositionStateModel:
    """Test PositionState database model."""

    def test_position_state_creation(self):
        """Test creating a PositionState record."""
        with get_sync_db() as session:
            state = PositionState(
                monitor_id="test_monitor_1",
                positions_json='{"positions": []}',
                is_active=True,
                version=1,
            )
            session.add(state)
            session.commit()

            # Retrieve and verify
            retrieved = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == "test_monitor_1")
                .first()
            )

            assert retrieved is not None
            assert retrieved.monitor_id == "test_monitor_1"
            assert retrieved.is_active is True
            assert retrieved.version == 1

    def test_position_state_update(self):
        """Test updating a PositionState record."""
        with get_sync_db() as session:
            # Create
            state = PositionState(
                monitor_id="test_monitor_2", positions_json='{"positions": []}', version=1
            )
            session.add(state)
            session.commit()

            # Update
            state.positions_json = '{"positions": [{"symbol": "AAPL"}]}'
            state.version = 2
            session.commit()

            # Verify
            retrieved = (
                session.query(PositionState)
                .filter(PositionState.monitor_id == "test_monitor_2")
                .first()
            )

            assert retrieved.version == 2
            data = json.loads(retrieved.positions_json)
            assert len(data['positions']) == 1
            assert data['positions'][0]['symbol'] == 'AAPL'

    def test_position_state_repr(self):
        """Test PositionState string representation."""
        state = PositionState(monitor_id="test_monitor", positions_json='{}')
        repr_str = repr(state)
        assert 'test_monitor' in repr_str
        assert 'version=' in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
