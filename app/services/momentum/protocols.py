"""
Protocol interfaces for momentum analysis services.

Following SOLID principles:
- Interface Segregation: Small, focused protocols
- Dependency Inversion: Depend on abstractions
- Open/Closed: Extensible through protocol implementations
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)

from app.domain.models.momentum import (
    MomentumAnalysis,
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    TechnicalIndicators,
    Timeframe,
)


class IndicatorCalculator(Protocol):
    """
    Protocol for technical indicator calculations.

    Single Responsibility: Calculate technical indicators
    Interface Segregation: Focused on indicator calculations only
    """

    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        ...

    def calculate_ema(self, prices: List[float], period: int = 9) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        ...

    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate MACD indicator."""
        ...

    def calculate_roc(self, prices: List[float], period: int = 12) -> Optional[float]:
        """Calculate Rate of Change."""
        ...

    def calculate_stochastic_rsi(
        self, rsi_values: List[float], period: int = 14, smooth_k: int = 3
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate Stochastic RSI."""
        ...

    def calculate_atr(
        self, highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """Calculate Average True Range."""
        ...

    def calculate_adx(
        self, highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """Calculate Average Directional Index."""
        ...

    def calculate_volume_sma(self, volumes: List[Decimal], period: int = 20) -> Optional[Decimal]:
        """Calculate Volume Simple Moving Average."""
        ...

    def calculate_vwap(
        self, prices: List[float], volumes: List[float], period: Optional[int] = None
    ) -> Optional[float]:
        """Calculate Volume-Weighted Average Price."""
        ...

    def calculate_zscore(
        self, prices: List[float], period: int = 30, std: float = 1.0
    ) -> Optional[float]:
        """Calculate Z-score."""
        ...

    def calculate_volatility(
        self, prices: List[float], tf: str = "days", returns: bool = False, log: bool = False
    ) -> Optional[float]:
        """Calculate volatility."""
        ...

    def calculate_expectancy(
        self,
        winning_trades: int,
        losing_trades: int,
        avg_win_amount: float,
        avg_loss_amount: float,
    ) -> Optional[float]:
        """Calculate expectancy metric."""
        ...

    def detect_macd_divergence(
        self, prices: List[float], macd_histograms: List[float], lookback: int = 5
    ) -> Optional[str]:
        """Detect MACD divergence patterns."""
        ...

    def calculate_all_indicators(
        self, prices: List[float], highs: List[float], lows: List[float], volumes: List[Decimal]
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

    def calculate_overall_momentum(self, signals: List[MomentumSignal]) -> float:
        """Calculate overall momentum score from signals."""
        ...

    def determine_trend_direction(self, indicators: TechnicalIndicators) -> str:
        """Determine trend direction from indicators."""
        ...

    def assess_risk_level(
        self, indicators: TechnicalIndicators, signals: List[MomentumSignal]
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
    ) -> List[MomentumSignal]:
        """Generate momentum signals from indicators."""
        ...

    async def create_price_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> Optional[MomentumSignal]:
        """Create price momentum signal."""
        ...

    async def create_volume_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> Optional[MomentumSignal]:
        """Create volume momentum signal."""
        ...

    async def create_combined_momentum_signal(
        self,
        symbol: str,
        indicators: TechnicalIndicators,
        timeframe: Timeframe,
        existing_signals: List[MomentumSignal],
    ) -> Optional[MomentumSignal]:
        """Create combined momentum signal."""
        ...

    def filter_signals(
        self, signals: List[MomentumSignal], filter_criteria: Optional[MomentumFilter]
    ) -> List[MomentumSignal]:
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

    async def get_strategy(self, strategy_name: str) -> Optional[MomentumStrategy]:
        """Get a momentum strategy by name."""
        ...

    async def update_strategy(
        self, strategy_name: str, updated_fields: Dict[str, Any]
    ) -> Optional[MomentumStrategy]:
        """Update a momentum strategy."""
        ...

    async def delete_strategy(self, strategy_name: str) -> bool:
        """Delete a momentum strategy."""
        ...

    async def get_strategy_signals(self, strategy_name: str) -> List[MomentumSignal]:
        """Get signals for a specific strategy."""
        ...

    async def get_top_momentum_assets(self, limit: int = 10) -> List[Dict[str, Any]]:
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

    async def get_analysis(self, analysis_id: str) -> Optional[MomentumAnalysis]:
        """Get momentum analysis by ID."""
        ...

    async def get_all_analyses(self) -> List[MomentumAnalysis]:
        """Get all momentum analyses."""
        ...

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Delete momentum analysis."""
        ...

    async def save_strategy(self, strategy: MomentumStrategy) -> None:
        """Save momentum strategy."""
        ...

    async def load_strategies(self) -> Dict[str, MomentumStrategy]:
        """Load all momentum strategies."""
        ...


class PriceDataProvider(Protocol):
    """
    Protocol for price data provision.

    Single Responsibility: Provide market data
    Interface Segregation: Focused on data retrieval
    """

    async def get_price_data(self, symbol: str, timeframe: Timeframe) -> Dict[str, List[float]]:
        """Get price data for a symbol."""
        ...

    async def generate_mock_data(self, symbol: str, timeframe: Timeframe) -> Dict[str, List[float]]:
        """Generate mock price data for testing."""
        ...
