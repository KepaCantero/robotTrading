"""Shared fixtures for portfolio optimization tests."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from app.domain.portfolio_optimization.black_litterman_optimizer import (
    BlackLittermanConfig,
    BlackLittermanOptimizer,
    InvestorView,
    ViewType,
)


@pytest.fixture
def bl_optimizer() -> BlackLittermanOptimizer:
    """Create default Black-Litterman optimizer."""
    return BlackLittermanOptimizer()


@pytest.fixture
def bl_config() -> BlackLittermanConfig:
    """Create default Black-Litterman configuration."""
    return BlackLittermanConfig()


@pytest.fixture
def sample_5_asset_returns() -> NDArray[np.float64]:
    """Sample returns for 5 assets over 252 days."""
    np.random.seed(42)
    # Simulate correlated daily returns
    mean_returns = np.array([0.0005, 0.0003, 0.0007, 0.0004, 0.0006])
    cov_matrix = np.array(
        [
            [0.0004, 0.0002, 0.0001, 0.00015, 0.0001],
            [0.0002, 0.0003, 0.00015, 0.0001, 0.00005],
            [0.0001, 0.00015, 0.0005, 0.0002, 0.00015],
            [0.00015, 0.0001, 0.0002, 0.00035, 0.0001],
            [0.0001, 0.00005, 0.00015, 0.0001, 0.00025],
        ]
    )

    returns = np.random.multivariate_normal(mean_returns, cov_matrix, 252)
    return returns.astype(np.float64)


@pytest.fixture
def sample_5_asset_caps() -> NDArray[np.float64]:
    """Sample market capitalizations for 5 assets."""
    return np.array([1000.0, 800.0, 600.0, 400.0, 200.0], dtype=np.float64)


@pytest.fixture
def sample_5_asset_weights() -> NDArray[np.float64]:
    """Sample market weights for 5 assets (sums to 1)."""
    caps = np.array([1000.0, 800.0, 600.0, 400.0, 200.0])
    return (caps / caps.sum()).astype(np.float64)


@pytest.fixture
def sample_5_asset_covariance() -> NDArray[np.float64]:
    """Sample covariance matrix for 5 assets (annualized)."""
    cov = np.array(
        [
            [0.04, 0.02, 0.01, 0.015, 0.01],
            [0.02, 0.03, 0.015, 0.01, 0.005],
            [0.01, 0.015, 0.05, 0.02, 0.015],
            [0.015, 0.01, 0.02, 0.035, 0.01],
            [0.01, 0.005, 0.015, 0.01, 0.025],
        ],
        dtype=np.float64,
    )
    return cov


@pytest.fixture
def absolute_view_0() -> InvestorView:
    """Absolute view: Asset 0 will return 8%."""
    return InvestorView(
        view_type=ViewType.ABSOLUTE,
        assets=[0],
        pick_vector=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
        expected_return=0.08,
        confidence=0.70,
        id="absolute_view_0",
    )


@pytest.fixture
def relative_view_0_1() -> InvestorView:
    """Relative view: Asset 0 will outperform Asset 1 by 3%."""
    return InvestorView(
        view_type=ViewType.RELATIVE,
        assets=[0, 1],
        pick_vector=np.array([1.0, -1.0, 0.0, 0.0, 0.0]),
        expected_return=0.03,
        confidence=0.60,
        id="relative_view_0_1",
    )


@pytest.fixture
def sample_views() -> list[InvestorView]:
    """Multiple sample views for testing."""
    return [
        InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
            expected_return=0.08,
            confidence=0.70,
        ),
        InvestorView(
            view_type=ViewType.RELATIVE,
            assets=[0, 1],
            pick_vector=np.array([1.0, -1.0, 0.0, 0.0, 0.0]),
            expected_return=0.03,
            confidence=0.60,
        ),
        InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[2],
            pick_vector=np.array([0.0, 0.0, 1.0, 0.0, 0.0]),
            expected_return=0.10,
            confidence=0.50,
        ),
    ]


@pytest.fixture
def empty_views() -> list[InvestorView]:
    """Empty list of views (no investor views)."""
    return []
