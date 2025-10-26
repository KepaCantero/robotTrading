"""
Optimization models for parameter optimization and overfitting prevention.

This module contains Pydantic models for walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class OptimizationMethod(str, Enum):
    """Optimization methods for parameter tuning."""

    WALK_FORWARD = "walk_forward"
    PURGED_K_FOLD = "purged_k_fold"
    OUT_OF_SAMPLE = "out_of_sample"
    MONTE_CARLO = "monte_carlo"


class ParameterType(str, Enum):
    """Types of parameters that can be optimized."""

    THRESHOLD = "threshold"
    PERIOD = "period"
    WEIGHT = "weight"
    MULTIPLIER = "multiplier"
    PERCENTAGE = "percentage"


class ParameterConstraint(BaseModel):
    """Constraints for parameter optimization."""

    min_value: Union[float, int] = Field(
        ..., description="Minimum value for the parameter"
    )
    max_value: Union[float, int] = Field(
        ..., description="Maximum value for the parameter"
    )
    step_size: Optional[Union[float, int]] = Field(
        None, description="Step size for optimization"
    )
    parameter_type: ParameterType = Field(
        ..., description="Type of parameter", env="PARAMETER_TYPE"
    )

    @model_validator(mode="after")
    def validate_values(self):
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be less than max_value")
        return self


class OptimizationParameter(BaseModel):
    """Parameter to be optimized."""

    name: str = Field(..., description="Name of the parameter", env="NAME")
    current_value: Union[float, int] = Field(
        ..., description="Current value of the parameter"
    )
    constraints: ParameterConstraint = Field(
        ..., description="Constraints for optimization", env="CONSTRAINTS"
    )
    description: Optional[str] = Field(None, description="Description of the parameter")

    @model_validator(mode="after")
    def validate_current_value(self):
        if not (
            self.constraints.min_value
            <= self.current_value
            <= self.constraints.max_value
        ):
            raise ValueError(
                f"current_value {self.current_value} must be within constraints [{self.constraints.min_value}, {self.constraints.max_value}]"
            )
        return self


class WalkForwardConfig(BaseModel):
    """Configuration for walk-forward analysis."""

    initial_train_period: int = Field(
        ...,
        ge=30,
        description="Initial training period in days",
        env="INITIAL_TRAIN_PERIOD",
    )
    retrain_frequency: int = Field(
        ..., ge=1, description="Retraining frequency in days", env="RETRAIN_FREQUENCY"
    )
    test_period: int = Field(
        ..., ge=7, description="Test period in days", env="TEST_PERIOD"
    )
    min_train_period: int = Field(
        ...,
        ge=30,
        description="Minimum training period in days",
        env="MIN_TRAIN_PERIOD",
    )
    max_train_period: Optional[int] = Field(
        None, description="Maximum training period in days"
    )
    purged_period: int = Field(
        0,
        ge=0,
        description="Purged period to avoid look-ahead bias",
        env="PURGED_PERIOD",
    )

    @field_validator("test_period")
    @classmethod
    def validate_test_period(cls, v, info):
        if (
            hasattr(info, "data")
            and "initial_train_period" in info.data
            and v >= info.data["initial_train_period"]
        ):
            raise ValueError("test_period must be less than initial_train_period")
        return v


class PurgedKFoldConfig(BaseModel):
    """Configuration for Purged K-Fold Cross Validation."""

    n_splits: int = Field(
        5, ge=2, le=10, description="Number of splits for K-Fold", env="N_SPLITS"
    )
    purged_period: int = Field(
        1,
        ge=0,
        description="Purged period to avoid look-ahead bias",
        env="PURGED_PERIOD",
    )
    embargo_period: int = Field(
        1,
        ge=0,
        description="Embargo period to avoid look-ahead bias",
        env="EMBARGO_PERIOD",
    )
    shuffle: bool = Field(
        False, description="Whether to shuffle the data", env="SHUFFLE"
    )


class OptimizationConfig(BaseModel):
    """Configuration for parameter optimization."""

    method: OptimizationMethod = Field(
        ..., description="Optimization method to use", env="METHOD"
    )
    walk_forward_config: Optional[WalkForwardConfig] = Field(
        None, description="Walk-forward configuration"
    )
    purged_k_fold_config: Optional[PurgedKFoldConfig] = Field(
        None, description="Purged K-Fold configuration"
    )
    max_iterations: int = Field(
        100,
        ge=1,
        le=1000,
        description="Maximum optimization iterations",
        env="MAX_ITERATIONS",
    )
    convergence_threshold: float = Field(
        0.001,
        ge=0.0001,
        le=0.1,
        description="Convergence threshold",
        env="CONVERGENCE_THRESHOLD",
    )
    random_seed: Optional[int] = Field(
        None, description="Random seed for reproducibility"
    )

    @field_validator("walk_forward_config")
    @classmethod
    def validate_walk_forward_config(cls, v, info):
        if (
            hasattr(info, "data")
            and info.data.get("method") == OptimizationMethod.WALK_FORWARD
            and v is None
        ):
            raise ValueError(
                "walk_forward_config is required when method is walk_forward"
            )
        return v

    @field_validator("purged_k_fold_config")
    @classmethod
    def validate_purged_k_fold_config(cls, v, info):
        if (
            hasattr(info, "data")
            and info.data.get("method") == OptimizationMethod.PURGED_K_FOLD
            and v is None
        ):
            raise ValueError(
                "purged_k_fold_config is required when method is purged_k_fold"
            )
        return v


class OptimizationResult(BaseModel):
    """Result of parameter optimization."""

    optimized_parameters: Dict[str, Union[float, int]] = Field(
        ..., description="Optimized parameter values"
    )
    best_score: float = Field(
        ..., description="Best optimization score", env="BEST_SCORE"
    )
    optimization_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Optimization history"
    )
    convergence_achieved: bool = Field(
        ..., description="Whether convergence was achieved", env="CONVERGENCE_ACHIEVED"
    )
    iterations_completed: int = Field(
        ..., description="Number of iterations completed", env="ITERATIONS_COMPLETED"
    )
    optimization_time: float = Field(
        ..., description="Optimization time in seconds", env="OPTIMIZATION_TIME"
    )
    method_used: OptimizationMethod = Field(
        ..., description="Optimization method used", env="METHOD_USED"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp", env="CREATED_AT"
    )


class OutOfSampleTest(BaseModel):
    """Out-of-sample test configuration and results."""

    test_start_date: date = Field(
        ..., description="Start date for out-of-sample testing", env="TEST_START_DATE"
    )
    test_end_date: date = Field(
        ..., description="End date for out-of-sample testing", env="TEST_END_DATE"
    )
    train_start_date: date = Field(
        ..., description="Start date for training data", env="TRAIN_START_DATE"
    )
    train_end_date: date = Field(
        ..., description="End date for training data", env="TRAIN_END_DATE"
    )
    parameters: Dict[str, Union[float, int]] = Field(
        ..., description="Parameters to test"
    )
    strategy_name: str = Field(
        ..., description="Name of the strategy to test", env="STRATEGY_NAME"
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if self.test_end_date <= self.test_start_date:
            raise ValueError("test_end_date must be after test_start_date")
        if self.train_end_date <= self.train_start_date:
            raise ValueError("train_end_date must be after train_start_date")
        return self


class OutOfSampleResult(BaseModel):
    """Results of out-of-sample testing."""

    test_config: OutOfSampleTest = Field(
        ..., description="Test configuration", env="TEST_CONFIG"
    )
    total_return: float = Field(
        ..., description="Total return during test period", env="TOTAL_RETURN"
    )
    sharpe_ratio: float = Field(
        ..., description="Sharpe ratio during test period", env="SHARPE_RATIO"
    )
    max_drawdown: float = Field(
        ..., description="Maximum drawdown during test period", env="MAX_DRAWDOWN"
    )
    win_rate: float = Field(
        ..., ge=0, le=1, description="Win rate during test period", env="WIN_RATE"
    )
    profit_factor: float = Field(
        ..., description="Profit factor during test period", env="PROFIT_FACTOR"
    )
    total_trades: int = Field(
        ..., ge=0, description="Total number of trades", env="TOTAL_TRADES"
    )
    avg_trade_duration: float = Field(
        ...,
        ge=0,
        description="Average trade duration in days",
        env="AVG_TRADE_DURATION",
    )
    volatility: float = Field(
        ..., ge=0, description="Volatility during test period", env="VOLATILITY"
    )
    calmar_ratio: float = Field(
        ..., description="Calmar ratio during test period", env="CALMAR_RATIO"
    )
    sortino_ratio: float = Field(
        ..., description="Sortino ratio during test period", env="SORTINO_RATIO"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp", env="CREATED_AT"
    )


class ParameterOptimizationRequest(BaseModel):
    """Request model for parameter optimization."""

    strategy_name: str = Field(
        ..., description="Name of the strategy to optimize", env="STRATEGY_NAME"
    )
    parameters: List[OptimizationParameter] = Field(
        ..., min_length=1, description="Parameters to optimize"
    )
    optimization_config: OptimizationConfig = Field(
        ..., description="Optimization configuration", env="OPTIMIZATION_CONFIG"
    )
    data_start_date: date = Field(
        ..., description="Start date for optimization data", env="DATA_START_DATE"
    )
    data_end_date: date = Field(
        ..., description="End date for optimization data", env="DATA_END_DATE"
    )
    cost_analysis_enabled: bool = Field(
        True,
        description="Whether to include cost analysis",
        env="COST_ANALYSIS_ENABLED",
    )

    @model_validator(mode="after")
    def validate_data_end_date(self):
        if self.data_end_date <= self.data_start_date:
            raise ValueError("data_end_date must be after data_start_date")
        return self


class OutOfSampleTestRequest(BaseModel):
    """Request model for out-of-sample testing."""

    test_config: OutOfSampleTest = Field(
        ..., description="Out-of-sample test configuration", env="TEST_CONFIG"
    )
    cost_analysis_enabled: bool = Field(
        True,
        description="Whether to include cost analysis",
        env="COST_ANALYSIS_ENABLED",
    )


class OptimizationArtifact(BaseModel):
    """Artifact for storing optimization results."""

    artifact_id: str = Field(
        ..., description="Unique artifact identifier", env="ARTIFACT_ID"
    )
    optimization_result: OptimizationResult = Field(
        ..., description="Optimization result", env="OPTIMIZATION_RESULT"
    )
    out_of_sample_results: List[OutOfSampleResult] = Field(
        default_factory=list, description="Out-of-sample test results"
    )
    strategy_name: str = Field(
        ..., description="Name of the optimized strategy", env="STRATEGY_NAME"
    )
    optimization_date: datetime = Field(
        default_factory=datetime.now,
        description="Optimization date",
        env="OPTIMIZATION_DATE",
    )
    version: str = Field("1.0", description="Artifact version", env="VERSION")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }


class OptimizationMetrics(BaseModel):
    """Metrics for optimization performance."""

    optimization_score: float = Field(
        ..., description="Overall optimization score", env="OPTIMIZATION_SCORE"
    )
    stability_score: float = Field(
        ..., ge=0, le=1, description="Parameter stability score", env="STABILITY_SCORE"
    )
    robustness_score: float = Field(
        ..., ge=0, le=1, description="Robustness score", env="ROBUSTNESS_SCORE"
    )
    overfitting_risk: float = Field(
        ..., ge=0, le=1, description="Overfitting risk score", env="OVERFITTING_RISK"
    )
    cost_efficiency: float = Field(
        ..., ge=0, le=1, description="Cost efficiency score", env="COST_EFFICIENCY"
    )
    sharpe_ratio: float = Field(..., description="Sharpe ratio", env="SHARPE_RATIO")
    max_drawdown: float = Field(..., description="Maximum drawdown", env="MAX_DRAWDOWN")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate", env="WIN_RATE")
    profit_factor: float = Field(..., description="Profit factor", env="PROFIT_FACTOR")

    @field_validator("overfitting_risk")
    @classmethod
    def validate_overfitting_risk(cls, v):
        if v > 0.7:
            raise ValueError("High overfitting risk detected")
        return v


class OptimizationSummary(BaseModel):
    """Summary of optimization process."""

    total_optimizations: int = Field(
        ...,
        ge=0,
        description="Total number of optimizations performed",
        env="TOTAL_OPTIMIZATIONS",
    )
    successful_optimizations: int = Field(
        ...,
        ge=0,
        description="Number of successful optimizations",
        env="SUCCESSFUL_OPTIMIZATIONS",
    )
    failed_optimizations: int = Field(
        ...,
        ge=0,
        description="Number of failed optimizations",
        env="FAILED_OPTIMIZATIONS",
    )
    avg_optimization_time: float = Field(
        ...,
        ge=0,
        description="Average optimization time in seconds",
        env="AVG_OPTIMIZATION_TIME",
    )
    best_strategy: str = Field(
        ..., description="Name of the best performing strategy", env="BEST_STRATEGY"
    )
    best_score: float = Field(
        ..., description="Best optimization score achieved", env="BEST_SCORE"
    )
    last_optimization_date: datetime = Field(
        ..., description="Date of last optimization", env="LAST_OPTIMIZATION_DATE"
    )
    artifacts_count: int = Field(
        ...,
        ge=0,
        description="Number of optimization artifacts stored",
        env="ARTIFACTS_COUNT",
    )

    @model_validator(mode="after")
    def validate_numeric_values(self):
        """Ensure all numeric values are JSON-serializable."""
        import math

        # Replace NaN and infinity with None or default values
        if math.isnan(self.avg_optimization_time) or math.isinf(
            self.avg_optimization_time
        ):
            self.avg_optimization_time = 0.0

        if math.isnan(self.best_score) or math.isinf(self.best_score):
            self.best_score = 0.0

        return self
