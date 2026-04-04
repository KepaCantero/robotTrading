"""Pytest configuration for migration tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add parent directory to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "app"))

import app.infrastructure.persistence as _persistence_mod

# Make Base available from app.infrastructure.persistence so that
# env.py's "from app.infrastructure.persistence import Base" succeeds.
import app.infrastructure.persistence.database as _db_mod

if not hasattr(_persistence_mod, "Base"):
    _persistence_mod.Base = _db_mod.Base

# Mock alembic.context BEFORE any imports
mock_context = MagicMock()
mock_context.config = MagicMock()
mock_context.config.get_main_option = Mock(return_value="sqlite:///test.db")
mock_context.config.get_section = Mock(return_value={"sqlalchemy.url": "sqlite:///test.db"})
mock_context.config.config_ini_section = "alembic"
mock_context.config.config_file_name = "alembic.ini"
mock_context.config.set_main_option = Mock()
mock_context.is_offline_mode = Mock(return_value=True)  # Return True to prevent actual migration
mock_context.configure = MagicMock()
mock_context.begin_transaction = MagicMock()
mock_context.run_migrations = MagicMock()

# Create the alembic module mock
mock_alembic = MagicMock()
mock_alembic.context = mock_context

# Patch sys.modules BEFORE any imports
sys.modules["alembic"] = mock_alembic
sys.modules["alembic.context"] = mock_context


@pytest.fixture(scope="session", autouse=True)
def setup_mocks():
    """Ensure mocks are in place for all tests."""
    # The mocks are already in place at module level
    # This fixture just ensures they remain throughout the session
    yield
