"""
Momentum Modular Strategy Configuration

This module contains all configuration parameters for the momentum modular strategy.
Centralized from momentum_modular/strategy.py hardcoded values.
"""

from pydantic import BaseModel, Field


class MomentumModularConfig(BaseModel):
    """Configuration parameters for Momentum Modular Strategy."""

    # Market regime thresholds
    bear_market_strength_threshold: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Trend strength threshold for bear market detection (99% - only extreme crashes)",
    )
    volatility_crisis_percentile: float = Field(
        default=75.0,
        ge=50.0,
        le=100.0,
        description="Volatility percentile for crisis detection (75%)",
    )
    normal_volatility_min: float = Field(
        default=40.0,
        ge=20.0,
        le=60.0,
        description="Minimum volatility percentile for normal regime (40%)",
    )
    normal_volatility_max: float = Field(
        default=70.0,
        ge=60.0,
        le=90.0,
        description="Maximum volatility percentile for normal regime (70%)",
    )

    # History and training thresholds
    min_history_length: int = Field(
        default=60, ge=30, le=200, description="Minimum history length for momentum signals"
    )
    auto_train_min_history: int = Field(
        default=100, ge=50, le=500, description="Minimum history for auto-training learning engine"
    )

    # Confidence and signal thresholds
    min_success_probability_default: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Default minimum success probability (60%)"
    )
    min_success_probability_strict: float = Field(
        default=0.7, ge=0.5, le=1.0, description="Strict minimum success probability (70%)"
    )

    # Signal strength thresholds (matching Signal model validation)
    very_strong_confidence: float = Field(
        default=80.0, ge=70.0, le=100.0, description="Confidence threshold for VERY_STRONG (80%)"
    )
    strong_confidence: float = Field(
        default=70.0, ge=60.0, le=80.0, description="Confidence threshold for STRONG (70%)"
    )
    moderate_confidence: float = Field(
        default=50.0, ge=30.0, le=70.0, description="Confidence threshold for MODERATE (50%)"
    )

    # Volume ratio calculations
    volume_ratio_min: float = Field(
        default=0.5, ge=0.1, le=1.0, description="Minimum volume ratio for liquidity score (0.5)"
    )
    volume_ratio_multiplier: float = Field(
        default=50.0,
        ge=10.0,
        le=100.0,
        description="Volume ratio multiplier for liquidity score (50)",
    )

    # Priority score weights
    priority_confidence_weight: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Confidence weight for priority score (70%)"
    )
    priority_liquidity_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Liquidity weight for priority score (30%)"
    )

    # Default values
    default_volume: float = Field(
        default=0.01, ge=0.001, le=1.0, description="Default volume when not available (0.01)"
    )

    # Overbought/oversold thresholds
    rsi_overbought_sell: float = Field(
        default=75.0, ge=70.0, le=90.0, description="RSI threshold for overbought sell signal (75)"
    )
    trend_down_sell_strength: float = Field(
        default=0.7, ge=0.5, le=1.0, description="Trend down strength for sell signal (70%)"
    )
    negative_momentum_threshold: float = Field(
        default=-0.03, ge=-0.10, le=-0.01, description="Negative momentum threshold for sell (-3%)"
    )

    # Learning engine weights
    learning_filter_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Filter weight for learning combination (60%)"
    )
    learning_confidence_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Learning confidence weight for combination (40%)"
    )

    # Sequence lengths for deep learning
    default_sequence_length: int = Field(
        default=60, ge=20, le=200, description="Default sequence length for deep learning (60)"
    )
    transformer_sequence_length: int = Field(
        default=30, ge=10, le=100, description="Sequence length for transformer engine (30)"
    )

    # Max position size
    max_position_size_default: float = Field(
        default=0.1, ge=0.01, le=0.5, description="Default max position size for momentum (10%)"
    )
