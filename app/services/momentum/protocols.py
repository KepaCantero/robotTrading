"""
Protocol interfaces for momentum analysis services.

Following SOLID principles:
- Interface Segregation: Small, focused protocols
- Dependency Inversion: Depend on abstractions
- Open/Closed: Extensible through protocol implementations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

logger = logging.getLogger(__name__)

from app.domain.models.momentum import (
    MomentumAnalysis,
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    TechnicalIndicators,
    Timeframe,
)

if TYPE_CHECKING:
    from decimal import Decimal


class IndicatorCalculator(Protocol):
    """
    Protocol for technical indicator calculations.

    Single Responsibility: Calculate technical indicators
    Interface Segregation: Focused on indicator calculations only
    """

    def calculate_rsi(self, prices: list[float], period: int = 14) -> float | None:
        """Calculate Relative Strength Index."""
        ...

    def calculate_ema(self, prices: list[float], period: int = 9) -> float | None:
        """Calculate Exponential Moving Average."""
        ...

    def calculate_macd(
        self,
        prices: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> tuple[float | None, float | None, float | None]:
        """Calculate MACD indicator."""
        ...

    def calculate_roc(self, prices: list[float], period: int = 12) -> float | None:
        """Calculate Rate of Change."""
        ...

    def calculate_stochastic_rsi(
        self, rsi_values: list[float], period: int = 14, smooth_k: int = 3
    ) -> tuple[float | None, float | None]:
        """Calculate Stochastic RSI."""
        ...

    def calculate_atr(
        self, highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> float | None:
        """Calculate Average True Range."""
        ...

    def calculate_adx(
        self, highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> float | None:
        """Calculate Average Directional Index."""
        ...

    def calculate_volume_sma(self, volumes: list[Decimal], period: int = 20) -> Decimal | None:
        """Calculate Volume Simple Moving Average."""
        ...

    def calculate_vwap(
        self, prices: list[float], volumes: list[float], period: int | None = None
    ) -> float | None:
        """Calculate Volume-Weighted Average Price."""
        ...

    def calculate_zscore(
        self, prices: list[float], period: int = 30, std: float = 1.0
    ) -> float | None:
        """Calculate Z-score."""
        ...

    def calculate_volatility(
        self, prices: list[float], tf: str = "days", returns: bool = False, log: bool = False
    ) -> float | None:
        """Calculate volatility."""
        ...

    def calculate_expectancy(
        self,
        winning_trades: int,
        losing_trades: int,
        avg_win_amount: float,
        avg_loss_amount: float,
    ) -> float | None:
        """Calculate expectancy metric."""
        ...

    def detect_macd_divergence(
        self, prices: list[float], macd_histograms: list[float], lookback: int = 5
    ) -> str | None:
        """Detect MACD divergence patterns."""
        ...

    def calculate_all_indicators(
        self, prices: list[float], highs: list[float], lows: list[float], volumes: list[Decimal]
    ) -> TechnicalIndicators:
        """Calculate all technical indicators at once."""
        ...


class MomentumAnalyzer(Protocol):
    """
    Protocol for momentum analysis.

    Single Responsibility: Analyze momentum data
    Interface Segregation: Focused on analysis operations
    """

    async def analyze_asset_momentum(
        self, symbol: str, timeframe: Timeframe = Timeframe.DAILY
    ) -> MomentumAnalysis:
        """Analyze momentum for a specific asset."""
        ...

    def calculate_overall_momentum(self, signals: list[MomentumSignal]) -> float:
        """Calculate overall momentum score from signals."""
        ...

    def determine_trend_direction(self, indicators: TechnicalIndicators) -> str:
        """Determine trend direction from indicators."""
        ...

    def assess_risk_level(
        self, indicators: TechnicalIndicators, signals: list[MomentumSignal]
    ) -> str:
        """Assess risk level."""
        ...

    def assess_volatility_level(self, indicators: TechnicalIndicators) -> str:
        """Assess volatility level."""
        ...


class SignalGenerator(Protocol):
    """
    Protocol for signal generation.

    Single Responsibility: Generate trading signals
    Interface Segregation: Focused on signal generation
    """

    async def generate_signals(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> list[MomentumSignal]:
        """Generate momentum signals from indicators."""
        ...

    async def create_price_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> MomentumSignal | None:
        """Create price momentum signal."""
        ...

    async def create_volume_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> MomentumSignal | None:
        """Create volume momentum signal."""
        ...

    async def create_combined_momentum_signal(
        self,
        symbol: str,
        indicators: TechnicalIndicators,
        timeframe: Timeframe,
        existing_signals: list[MomentumSignal],
    ) -> MomentumSignal | None:
        """Create combined momentum signal."""
        ...

    def filter_signals(
        self, signals: list[MomentumSignal], filter_criteria: MomentumFilter | None
    ) -> list[MomentumSignal]:
        """Filter signals based on criteria."""
        ...


class StrategyManager(Protocol):
    """
    Protocol for strategy management.

    Single Responsibility: Manage momentum strategies
    Interface Segregation: Focused on strategy CRUD operations
    """

    def initialize_default_strategies(self) -> None:
        """Initialize default momentum strategies."""
        ...

    async def create_strategy(self, strategy: MomentumStrategy) -> MomentumStrategy:
        """Create a new momentum strategy."""
        ...

    async def get_strategy(self, strategy_name: str) -> MomentumStrategy | None:
        """Get a momentum strategy by name."""
        ...

    async def update_strategy(
        self, strategy_name: str, updated_fields: dict[str, Any]
    ) -> MomentumStrategy | None:
        """Update a momentum strategy."""
        ...

    async def delete_strategy(self, strategy_name: str) -> bool:
        """Delete a momentum strategy."""
        ...

    async def get_strategy_signals(
        self, strategy_name: str, all_signals: list[MomentumSignal]
    ) -> list[MomentumSignal]:
        """Get signals for a specific strategy."""
        ...

    async def get_top_momentum_assets(
        self, all_signals: list[MomentumSignal], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get top momentum assets."""
        ...


class StorageBackend(Protocol):
    """
    Protocol for storage operations.

    Single Responsibility: Persist and retrieve data
    Interface Segregation: Focused on storage operations
    Dependency Inversion: High-level modules depend on this abstraction
    """

    async def save_analysis(self, analysis_id: str, analysis: MomentumAnalysis) -> None:
        """Save momentum analysis."""
        ...

    async def get_analysis(self, analysis_id: str) -> MomentumAnalysis | None:
        """Get momentum analysis by ID."""
        ...

    async def get_all_analyses(self) -> list[MomentumAnalysis]:
        """Get all momentum analyses."""
        ...

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Delete momentum analysis."""
        ...

    async def save_strategy(self, strategy: MomentumStrategy) -> None:
        """Save momentum strategy."""
        ...

    async def load_strategies(self) -> dict[str, MomentumStrategy]:
        """Load all momentum strategies."""
        ...


class PriceDataProvider(Protocol):
    """
    Protocol for price data provision.

    Single Responsibility: Provide market data
    Interface Segregation: Focused on data retrieval
    """

    async def get_price_data(self, symbol: str, timeframe: Timeframe) -> dict[str, list[float]]:
        """Get price data for a symbol."""
        ...

    async def generate_mock_data(self, symbol: str, timeframe: Timeframe) -> dict[str, list[float]]:
        """Generate mock price data for testing."""
        ...
