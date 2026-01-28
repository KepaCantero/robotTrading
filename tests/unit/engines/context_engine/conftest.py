"""
Pytest configuration for context engine tests.

This conftest is isolated and doesn't import the main app to avoid dependency issues.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, MagicMock
import numpy as np


# Shared mock fixtures for context engine tests
@pytest.fixture
def mock_sklearn():
    """Mock sklearn module."""
    sklearn_mock = MagicMock()
    sys.modules['sklearn'] = sklearn_mock
    sys.modules['sklearn.cluster'] = sklearn_mock.cluster
    sys.modules['sklearn.decomposition'] = sklearn_mock.decomposition
    sys.modules['sklearn.preprocessing'] = sklearn_mock.preprocessing
    return sklearn_mock


@pytest.fixture
def mock_hmmlearn():
    """Mock hmmlearn module."""
    hmmlearn_mock = MagicMock()
    sys.modules['hmmlearn'] = hmmlearn_mock
    sys.modules['hmmlearn.hmm'] = hmmlearn_mock.hmm
    return hmmlearn_mock


@pytest.fixture
def mock_arch():
    """Mock arch module."""
    arch_mock = MagicMock()
    sys.modules['arch'] = arch_mock
    sys.modules['arch.univariate'] = arch_mock.univariate
    return arch_mock


@pytest.fixture
def mock_networkx():
    """Mock networkx module."""
    nx_mock = MagicMock()
    sys.modules['networkx'] = nx_mock
    sys.modules['nx'] = nx_mock
    return nx_mock


@pytest.fixture
def mock_statsmodels():
    """Mock statsmodels module."""
    statsmodels_mock = MagicMock()
    sys.modules['statsmodels'] = statsmodels_mock
    sys.modules['statsmodels.api'] = statsmodels_mock.api
    return statsmodels_mock


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
