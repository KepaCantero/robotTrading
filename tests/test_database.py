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


class TestDatabaseSession:
    """Test database session management."""
    
    def setup_method(self):
        """Reset global variables before each test."""
        import app.core.database
        app.core.database._engine = None
        app.core.database._session_factory = None
    
    @pytest.mark.asyncio
    async def test_get_db_session_basic(self):
        """Test basic get_db_session functionality."""
        # This test verifies the function exists and can be imported
        assert callable(get_db_session)
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_basic(self):
        """Test basic get_db_transaction functionality."""
        # This test verifies the function exists and can be imported
        assert callable(get_db_transaction)
    
    @pytest.mark.asyncio
    async def test_get_db_session_generator(self):
        """Test that get_db_session returns an async generator."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Mock session factory to avoid actual database calls
            mock_factory = MagicMock()
            mock_get_factory.return_value = mock_factory
            
            # Test that the function returns an async generator
            gen = get_db_session()
            assert hasattr(gen, '__aiter__')
            assert hasattr(gen, '__anext__')
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_context_manager(self):
        """Test that get_db_transaction returns an async context manager."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Mock session factory to avoid actual database calls
            mock_factory = MagicMock()
            mock_get_factory.return_value = mock_factory
            
            # Test that the function returns an async context manager
            cm = get_db_transaction()
            assert hasattr(cm, '__aenter__')
            assert hasattr(cm, '__aexit__')
    
    @pytest.mark.asyncio
    async def test_get_db_session_execution(self):
        """Test get_db_session execution with proper mocking."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.close = AsyncMock()
            
            # Create a mock context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            
            # Mock the session factory
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            # Test the async generator
            gen = get_db_session()
            session = await gen.__anext__()
            assert session == mock_session
            
            # Test cleanup
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass  # Expected when generator is exhausted
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_execution(self):
        """Test get_db_transaction execution with proper mocking."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Create a mock context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            
            # Mock the session factory
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            # Test the async context manager
            async with get_db_transaction() as session:
                assert session == mock_session
            
            # Verify commit was called
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_session_error_handling(self):
        """Test get_db_session error handling."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session that raises an error
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.rollback = AsyncMock()
            
            # Create a mock context manager that raises an error during execution
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(side_effect=Exception("Session error"))
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            
            # Mock the session factory
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            # Test error handling
            gen = get_db_session()
            with pytest.raises(Exception, match="Session error"):
                await gen.__anext__()
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_error_handling(self):
        """Test get_db_transaction error handling."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session that raises an error
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.rollback = AsyncMock()
            
            # Create a mock context manager that raises an error
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(side_effect=Exception("Transaction error"))
            
            # Mock the session factory
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            # Test error handling
            with pytest.raises(Exception, match="Transaction error"):
                async with get_db_transaction() as session:
                    pass


class TestDatabaseOperations:
    """Test database operation convenience functions."""
    
    def setup_method(self):
        """Reset global variables before each test."""
        import app.core.database
        app.core.database._engine = None
        app.core.database._session_factory = None
    
    def test_execute_query_function_exists(self):
        """Test that execute_query function exists."""
        assert callable(execute_query)
    
    def test_execute_scalar_function_exists(self):
        """Test that execute_scalar function exists."""
        assert callable(execute_scalar)
    
    @pytest.mark.asyncio
    async def test_execute_query_with_mock_session(self):
        """Test execute_query with mocked session factory."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session factory that returns a mock session
            mock_session = AsyncMock(spec=AsyncSession)
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("test",)]
            mock_session.execute.return_value = mock_result
            
            # Mock the session factory to return a context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            result = await execute_query("SELECT 1")
            assert result == [("test",)]
    
    @pytest.mark.asyncio
    async def test_execute_scalar_with_mock_session(self):
        """Test execute_scalar with mocked session factory."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session factory that returns a mock session
            mock_session = AsyncMock(spec=AsyncSession)
            mock_result = MagicMock()
            mock_result.scalar.return_value = 42
            mock_session.execute.return_value = mock_result
            
            # Mock the session factory to return a context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_factory = MagicMock(return_value=mock_context_manager)
            mock_get_factory.return_value = mock_factory
            
            result = await execute_scalar("SELECT COUNT(*) FROM test")
            assert result == 42
    
    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self):
        """Test execute_query error handling."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session factory that raises an error
            mock_factory = MagicMock()
            mock_factory.side_effect = Exception("Session factory error")
            mock_get_factory.return_value = mock_factory
            
            with pytest.raises(Exception, match="Session factory error"):
                await execute_query("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_execute_scalar_error_handling(self):
        """Test execute_scalar error handling."""
        with patch('app.core.database.get_session_factory') as mock_get_factory:
            # Create a mock session factory that raises an error
            mock_factory = MagicMock()
            mock_factory.side_effect = Exception("Session factory error")
            mock_get_factory.return_value = mock_factory
            
            with pytest.raises(Exception, match="Session factory error"):
                await execute_scalar("SELECT COUNT(*) FROM test")


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