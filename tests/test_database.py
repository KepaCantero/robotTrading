"""
Tests for database configuration and session management.

This module tests the async PostgreSQL database connection, session management,
and connection pooling functionality for the AlgoTrading MVP.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text

# Set DEBUG mode for tests to avoid SECRET_KEY validation
os.environ["DEBUG"] = "true"

from app.core.database import (
    Base,
    metadata,
    get_database_engine,
    get_session_factory,
    get_db_session,
    get_db_transaction,
    init_database,
    close_database,
    check_database_connection,
    get_database_info,
    execute_query,
    execute_scalar,
    _engine,
    _session_factory
)


class TestDatabaseEngine:
    """Test database engine creation and configuration."""
    
    def setup_method(self):
        """Reset global variables before each test."""
        import app.core.database
        app.core.database._engine = None
        app.core.database._session_factory = None
    
    def test_get_database_engine_creates_engine(self):
        """Test that get_database_engine creates an engine instance."""
        with patch('app.core.database.create_async_engine') as mock_create_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            engine = get_database_engine()
            
            assert engine == mock_engine
            mock_create_engine.assert_called_once()
    
    def test_get_database_engine_reuses_existing_engine(self):
        """Test that get_database_engine reuses existing engine."""
        with patch('app.core.database.create_async_engine') as mock_create_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # First call
            engine1 = get_database_engine()
            # Second call
            engine2 = get_database_engine()
            
            assert engine1 == engine2
            # Should only create engine once
            mock_create_engine.assert_called_once()
    
    def test_get_database_engine_handles_creation_error(self):
        """Test that get_database_engine handles creation errors."""
        with patch('app.core.database.create_async_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Engine creation failed")
            
            with pytest.raises(RuntimeError, match="Database engine creation failed"):
                get_database_engine()


class TestSessionFactory:
    """Test session factory creation and management."""
    
    def setup_method(self):
        """Reset global variables before each test."""
        import app.core.database
        app.core.database._engine = None
        app.core.database._session_factory = None
    
    def test_get_session_factory_creates_factory(self):
        """Test that get_session_factory creates a session factory."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_get_engine.return_value = mock_engine
            
            with patch('app.core.database.async_sessionmaker') as mock_sessionmaker:
                mock_factory = MagicMock()
                mock_sessionmaker.return_value = mock_factory
                
                factory = get_session_factory()
                
                assert factory == mock_factory
                mock_sessionmaker.assert_called_once()
    
    def test_get_session_factory_reuses_existing_factory(self):
        """Test that get_session_factory reuses existing factory."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_get_engine.return_value = mock_engine
            
            with patch('app.core.database.async_sessionmaker') as mock_sessionmaker:
                mock_factory = MagicMock()
                mock_sessionmaker.return_value = mock_factory
                
                # First call
                factory1 = get_session_factory()
                # Second call
                factory2 = get_session_factory()
                
                assert factory1 == factory2
                # Should only create factory once
                mock_sessionmaker.assert_called_once()
    
    def test_get_session_factory_handles_creation_error(self):
        """Test that get_session_factory handles creation errors."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_get_engine.side_effect = Exception("Engine creation failed")
            
            with pytest.raises(RuntimeError, match="Session factory creation failed"):
                get_session_factory()


class TestDatabaseInitialization:
    """Test database initialization and cleanup."""
    
    @pytest.mark.asyncio
    async def test_init_database_creates_tables(self):
        """Test that init_database creates all tables."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_engine = AsyncMock(spec=AsyncEngine)
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__.return_value = mock_conn
            mock_engine.begin.return_value.__aexit__.return_value = None
            mock_get_engine.return_value = mock_engine
            
            await init_database()
            
            mock_conn.run_sync.assert_called_once_with(Base.metadata.create_all)
    
    @pytest.mark.asyncio
    async def test_init_database_handles_errors(self):
        """Test that init_database handles initialization errors."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_get_engine.side_effect = Exception("Engine creation failed")
            
            with pytest.raises(RuntimeError, match="Database initialization failed"):
                await init_database()
    
    @pytest.mark.asyncio
    async def test_close_database_disposes_engine(self):
        """Test that close_database properly disposes the engine."""
        with patch('app.core.database._engine') as mock_engine:
            mock_engine.dispose = AsyncMock()
            
            await close_database()
            
            mock_engine.dispose.assert_called_once()


class TestDatabaseConnection:
    """Test database connection checking."""
    
    @pytest.mark.asyncio
    async def test_check_database_connection_success(self):
        """Test successful database connection check."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_engine = AsyncMock(spec=AsyncEngine)
            mock_conn = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (1,)
            mock_conn.execute.return_value = mock_result
            mock_engine.begin.return_value.__aenter__.return_value = mock_conn
            mock_engine.begin.return_value.__aexit__.return_value = None
            mock_get_engine.return_value = mock_engine
            
            result = await check_database_connection()
            
            assert result is True
            mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self):
        """Test database connection check failure."""
        with patch('app.core.database.get_database_engine') as mock_get_engine:
            mock_get_engine.side_effect = Exception("Connection failed")
            
            result = await check_database_connection()
            
            assert result is False


class TestDatabaseInfo:
    """Test database information retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_database_info_success(self):
        """Test successful database info retrieval."""
        with patch('app.core.database.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.database_url = "postgresql://user:pass@localhost:5432/db"
            mock_settings.database_echo = False
            mock_settings.database_pool_size = 10
            mock_settings.database_max_overflow = 20
            mock_settings.is_production.return_value = True
            mock_get_settings.return_value = mock_settings
            
            with patch('app.core.database.get_database_engine') as mock_get_engine:
                mock_engine = MagicMock(spec=AsyncEngine)
                mock_pool = MagicMock()
                mock_pool.size.return_value = 10
                mock_pool.checkedin.return_value = 5
                mock_pool.checkedout.return_value = 3
                mock_pool.overflow.return_value = 2
                mock_pool.invalid.return_value = 0
                mock_engine.pool = mock_pool
                mock_get_engine.return_value = mock_engine
                
                info = await get_database_info()
                
                assert info["url"] == "localhost:5432/db"
                assert info["echo"] is False
                assert info["pool_size"] == 10
                assert info["max_overflow"] == 20
                assert info["is_production"] is True
                assert "pool_status" in info
    
    @pytest.mark.asyncio
    async def test_get_database_info_handles_errors(self):
        """Test database info retrieval error handling."""
        with patch('app.core.database.get_settings') as mock_get_settings:
            mock_get_settings.side_effect = Exception("Settings error")
            
            info = await get_database_info()
            
            assert "error" in info
            assert "Settings error" in info["error"]


class TestBaseModel:
    """Test Base model class."""
    
    def test_base_model_has_metadata(self):
        """Test that Base model has proper metadata configuration."""
        assert Base.metadata == metadata
        assert metadata.naming_convention is not None
    
    def test_base_model_metadata_convention(self):
        """Test that Base model metadata has proper naming convention."""
        convention = metadata.naming_convention
        assert "ix" in convention
        assert "uq" in convention
        assert "ck" in convention
        assert "fk" in convention
        assert "pk" in convention


# Integration tests
class TestDatabaseIntegration:
    """Integration tests for database functionality."""
    
    def setup_method(self):
        """Reset global variables before each test."""
        import app.core.database
        app.core.database._engine = None
        app.core.database._session_factory = None
    
    def test_database_engine_and_session_integration(self):
        """Test integration between engine and session factory."""
        with patch('app.core.database.create_async_engine') as mock_create_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            with patch('app.core.database.async_sessionmaker') as mock_sessionmaker:
                mock_factory = MagicMock()
                mock_sessionmaker.return_value = mock_factory
                
                # Get engine and session factory
                engine = get_database_engine()
                factory = get_session_factory()
                
                # Verify they work together
                assert engine == mock_engine
                assert factory == mock_factory
                mock_sessionmaker.assert_called_once_with(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=True,
                    autocommit=False,
                )


if __name__ == "__main__":
    pytest.main([__file__])