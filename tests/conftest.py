"""
Pytest configuration and shared fixtures for AlgoTrading tests.

This module provides common fixtures and configuration for all tests.
"""

import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# ==============================================================================
# CRITICAL: Configure Numba BEFORE any imports that use it
# ==============================================================================
# This must happen before importing any modules with Numba JIT functions
# to prevent: "RuntimeError: cannot cache function 'func_name': no locator available for file '<string>'"
#
# The error occurs because:
# 1. Numba JIT functions with cache=True try to cache compiled functions
# 2. When imported during tests, Numba can't determine the source file location
# 3. Setting NUMBA_CACHE_DIR to a valid path before imports fixes this

# Set Numba cache directory to a writable location
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache_test"
try:
    os.makedirs("/tmp/numba_cache_test", exist_ok=True)
except (OSError, PermissionError):
    # If we can't create the directory, disable caching entirely
    os.environ["NUMBA_CACHE_DIR"] = ""

# ==============================================================================
# Load test environment variables from .env.test before importing app
# ==============================================================================
test_env_file = Path(__file__).parent.parent / ".env.test"
if test_env_file.exists():
    load_dotenv(test_env_file)
else:
    # Fallback: Set essential test environment variables
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")

# ==============================================================================
# Import app.main conditionally to avoid NumPy compatibility issues
# ==============================================================================
# Matplotlib compiled with NumPy 1.x is incompatible with NumPy 2.x
# This causes ImportError during test collection. We import app.main lazily.
_app = None


def get_app():
    """Lazy load FastAPI app to avoid import errors during collection."""
    global _app
    if _app is None:
        from app.main import app as _app_impl

        _app = _app_impl
    return _app


# Import models that don't depend on matplotlib/numpy 2.x compatibility
from app.domain.models.assets import Asset, AssetClass, AssetRanking, Exchange  # noqa: E402
from app.domain.models.momentum import MomentumStrategy, TechnicalIndicators, Timeframe  # noqa: E402


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(get_app())


@pytest.fixture
def mock_asset_service():
    """Mock asset identification service."""
    service = AsyncMock()

    # Mock get_asset_rankings
    ranking = AssetRanking(asset_class=AssetClass.EQUITY)
    ranking.add_ranking("AAPL", 85.0, 1, 80.0, 90.0)
    ranking.add_ranking("MSFT", 82.0, 2, 78.0, 86.0)
    ranking.add_ranking("GOOGL", 80.0, 3, 75.0, 85.0)
    service.get_asset_rankings.return_value = ranking

    # Mock get_top_liquid_assets
    assets = [
        Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=85.0,
        ),
        Asset(
            symbol="MSFT",
            name="Microsoft Corporation",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("40000000"),
            avg_spread=Decimal("0.01"),
            liquidity_score=82.0,
        ),
    ]
    service.get_top_liquid_assets.return_value = assets

    # Mock get_asset_by_symbol
    service.get_asset_by_symbol.return_value = assets[0]

    # Mock get_universe_summary
    service.get_universe_summary.return_value = {
        "asset_class": "equity",
        "total_assets": 2,
        "avg_liquidity_score": 83.5,
        "last_updated": "2025-10-20T15:20:00",
        "ranking_count": 2,
        "top_assets": [
            {"symbol": "AAPL", "liquidity_score": 85.0},
            {"symbol": "MSFT", "liquidity_score": 82.0},
        ],
    }

    # Mock filter_assets
    service.filter_assets.return_value = assets

    # Mock refresh_liquidity_data
    service.refresh_liquidity_data.return_value = {"refreshed": 2}

    return service


@pytest.fixture
def mock_momentum_service():
    """Mock momentum analysis service."""
    service = AsyncMock()

    # Mock get_technical_indicators
    indicators = TechnicalIndicators(
        symbol="AAPL",
        rsi=70.0,
        ema_9=Decimal("145.0"),
        ema_21=Decimal("144.0"),
        ema_50=Decimal("142.0"),
        ema_200=Decimal("140.0"),
        macd=Decimal("2.5"),
        macd_signal=Decimal("2.0"),
        macd_histogram=Decimal("0.5"),
        atr=Decimal("3.0"),
        volatility=Decimal("0.15"),
        volume_sma_20=Decimal("1200000"),
        volume_ratio=1.2,
        ema_trend="BULLISH",
        rsi_signal="NEUTRAL",
    )
    service.get_technical_indicators.return_value = indicators

    # Mock analyze_asset_momentum
    from app.models.momentum import MomentumAnalysis, MomentumSignal, MomentumType  # noqa: E402

    analysis = MomentumAnalysis(
        symbol="AAPL",
        timeframe=Timeframe.DAILY,
        analysis_date="2025-10-20T15:20:00",
        overall_momentum=75.0,
        trend_direction="BULLISH",
        signal_count=2,
        risk_level="MEDIUM",
        volatility_level="LOW",
        indicators=indicators,
        signals=[
            MomentumSignal(
                symbol="AAPL",
                signal_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                strength=80.0,
                direction="BUY",
                confidence=75.0,
                momentum_score=80.0,
                current_price=Decimal("145.0"),
                price_change_pct=2.5,
                volume_change_pct=15.0,
                rsi=70.0,
                ema_short=Decimal("145.0"),
                ema_long=Decimal("142.0"),
                macd=Decimal("2.5"),
                macd_signal=Decimal("2.0"),
                macd_histogram=Decimal("0.5"),
                timestamp="2025-10-20T15:20:00",
                expires_at="2025-10-21T15:20:00",
                is_expired=False,
            )
        ],
    )
    service.analyze_asset_momentum.return_value = analysis

    # Mock get_top_momentum_assets
    service.get_top_momentum_assets.return_value = [
        {
            "symbol": "AAPL",
            "momentum_score": 80.0,
            "confidence": 75.0,
            "direction": "BUY",
            "signal_type": "price_momentum",
        },
        {
            "symbol": "MSFT",
            "momentum_score": 75.0,
            "confidence": 70.0,
            "direction": "BUY",
            "signal_type": "price_momentum",
        },
    ]

    # Mock get_momentum_signals
    service.get_momentum_signals.return_value = []

    # Mock get_strategies
    strategies = [
        MomentumStrategy(
            name="daily_momentum",
            description="Daily momentum strategy",
            momentum_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            momentum_types=[MomentumType.PRICE_MOMENTUM],
            min_confidence=0.7,
            min_strength=70.0,
            max_positions=10,
            risk_per_trade=0.02,
            is_active=True,
        )
    ]
    service.get_strategies.return_value = strategies
    service.strategies = {"daily_momentum": strategies[0]}

    # Mock get_strategy_signals
    service.get_strategy_signals.return_value = []

    # Mock get_analyses
    service.get_analyses = []

    return service


@pytest.fixture
def asset_service_patch(mock_asset_service):
    """Patch asset service with mock."""
    with patch(
        "app.services.asset_identification.get_asset_identification_service",
        return_value=mock_asset_service,
    ):
        yield mock_asset_service


@pytest.fixture
def momentum_service_patch(mock_momentum_service):
    """Patch momentum service with mock."""
    with patch(
        "app.services.momentum_analysis.get_momentum_analysis_service",
        return_value=mock_momentum_service,
    ):
        yield mock_momentum_service
