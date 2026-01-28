"""Shared fixtures and configuration for pytest tests.

This conftest.py provides common fixtures used across multiple test files.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray


@pytest.fixture(scope="session")
def random_seed() -> int:
    """Fixed random seed for reproducible tests."""
    return 42


@pytest.fixture(scope="function")
def set_random_seed(random_seed: int) -> None:
    """Set random seed before each test."""
    np.random.seed(random_seed)


@pytest.fixture(scope="session")
def n_assets() -> int:
    """Default number of assets for portfolio tests."""
    return 5


@pytest.fixture(scope="session")
def n_periods() -> int:
    """Default number of time periods (1 year of daily data)."""
    return 252


@pytest.fixture(scope="function")
def sample_returns_matrix(
    n_periods: int, n_assets: int, set_random_seed: None
) -> NDArray[np.float64]:
    """Generate sample returns matrix for testing.

    Returns:
        Returns array of shape (n_periods, n_assets).
    """
    mean_returns = np.random.randn(n_assets) * 0.0005
    cov_matrix = np.random.randn(n_assets, n_assets)
    cov_matrix = cov_matrix @ cov_matrix.T  # Make positive semi-definite
    cov_matrix = cov_matrix * 0.0001  # Scale down

    returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_periods)
    return returns.astype(np.float64)


@pytest.fixture(scope="function")
def sample_covariance_matrix(n_assets: int, set_random_seed: None) -> NDArray[np.float64]:
    """Generate sample covariance matrix for testing.

    Returns:
        Covariance matrix of shape (n_assets, n_assets).
    """
    # Generate random positive definite matrix
    A = np.random.randn(n_assets, n_assets)
    cov = A @ A.T
    # Add diagonal dominance for stability
    cov = cov + np.eye(n_assets) * 0.04
    return cov.astype(np.float64)


@pytest.fixture(scope="function")
def sample_correlation_matrix(n_assets: int) -> NDArray[np.float64]:
    """Generate sample correlation matrix for testing.

    Returns:
        Correlation matrix of shape (n_assets, n_assets) with 1s on diagonal.
    """
    # Generate random correlation matrix
    A = np.random.randn(n_assets, n_assets)
    corr = A @ A.T
    # Convert to correlation
    d = np.sqrt(np.diag(corr))
    corr = corr / np.outer(d, d)
    return corr.astype(np.float64)


@pytest.fixture(scope="session")
def risk_free_rate() -> float:
    """Default risk-free rate for Sharpe ratio calculation."""
    return 0.02


@pytest.fixture(scope="session")
def max_position() -> float:
    """Default maximum position size for diversification."""
    return 0.20


@pytest.fixture(scope="session")
def lookback_days() -> int:
    """Default lookback period for covariance calculation (Rule 66)."""
    return 252


@pytest.fixture(scope="session")
def tau() -> float:
    """Default uncertainty parameter for Black-Litterman."""
    return 0.05


@pytest.fixture(scope="session")
def risk_aversion() -> float:
    """Default risk aversion coefficient."""
    return 3.0
