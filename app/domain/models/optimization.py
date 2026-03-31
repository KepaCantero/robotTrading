"""
Optimization models for parameter optimization and overfitting prevention.

This module contains Pydantic models for walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


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

    min_value: Union[float, int] = Field(..., description="Minimum value for the parameter")
    max_value: Union[float, int] = Field(..., description="Maximum value for the parameter")
    step_size: Optional[Union[float, int]] = Field(None, description="Step size for optimization")
    parameter_type: ParameterType = Field(..., description="Type of parameter")

    @model_validator(mode="after")
    def validate_values(self):
        if self.min_value >= self.max_value:
            logger.error(
                "Parameter constraint validation failed - min >= max",
                extra={
                    "component": "optimization",
                    "action": "constraint_validation_error",
                    "min_value": self.min_value,
                    "max_value": self.max_value,
                },
            )
            raise ValueError("min_value must be less than max_value")
        logger.debug(
            "ParameterConstraint validated",
            extra={
                "component": "optimization",
                "action": "constraint_validated",
                "min_value": self.min_value,
                "max_value": self.max_value,
                "parameter_type": self.parameter_type.value,
            },
        )
        return self


class OptimizationParameter(BaseModel):
    """Parameter to be optimized."""

    name: str = Field(..., description="Name of the parameter")
    current_value: Union[float, int] = Field(..., description="Current value of the parameter")
    constraints: ParameterConstraint = Field(..., description="Constraints for optimization")
    description: Optional[str] = Field(None, description="Description of the parameter")

    @model_validator(mode="after")
    def validate_current_value(self):
        if not (self.constraints.min_value <= self.current_value <= self.constraints.max_value):
            logger.error(
                "Optimization parameter validation failed - value out of bounds",
                extra={
                    "component": "optimization",
                    "action": "parameter_validation_error",
                    "parameter_name": self.name,
                    "current_value": self.current_value,
                    "min_value": self.constraints.min_value,
                    "max_value": self.constraints.max_value,
                },
            )
            raise ValueError(
                f"current_value {self.current_value} must be within constraints [{self.constraints.min_value}, {self.constraints.max_value}]"
            )
        logger.debug(
            "OptimizationParameter validated",
            extra={
                "component": "optimization",
                "action": "parameter_validated",
                "parameter_name": self.name,
                "current_value": self.current_value,
            },
        )
        return self


class WalkForwardConfig(BaseModel):
    """Configuration for walk-forward analysis."""

    initial_train_period: int = Field(
        ...,
        ge=30,
        description="Initial training period in days",
    )
    retrain_frequency: int = Field(..., ge=1, description="Retraining frequency in days")
    test_period: int = Field(..., ge=7, description="Test period in days")
    min_train_period: int = Field(
        ...,
        ge=30,
        description="Minimum training period in days",
    )
    max_train_period: Optional[int] = Field(None, description="Maximum training period in days")
    purged_period: int = Field(
        0,
        ge=0,
        description="Purged period to avoid look-ahead bias",
    )

    @field_validator("test_period")
    @classmethod
    def validate_test_period(cls, v, info):
        if (
            hasattr(info, "data")
            and "initial_train_period" in info.data
            and v >= info.data["initial_train_period"]
        ):
            logger.error(
                "Walk-forward config validation failed - test_period >= initial_train_period",
                extra={
                    "component": "optimization",
                    "action": "walk_forward_validation_error",
                    "test_period": v,
                    "initial_train_period": info.data.get("initial_train_period"),
                },
            )
            raise ValueError("test_period must be less than initial_train_period")
        logger.debug(
            "WalkForwardConfig test_period validated",
            extra={
                "component": "optimization",
                "action": "walk_forward_validated",
                "test_period": v,
            },
        )
        return v


class PurgedKFoldConfig(BaseModel):
    """Configuration for Purged K-Fold Cross Validation."""

    n_splits: int = Field(5, ge=2, le=10, description="Number of splits for K-Fold")
    purged_period: int = Field(
        1,
        ge=0,
        description="Purged period to avoid look-ahead bias",
    )
    embargo_period: int = Field(
        1,
        ge=0,
        description="Embargo period to avoid look-ahead bias",
    )
    shuffle: bool = Field(False, description="Whether to shuffle the data")


class OptimizationConfig(BaseModel):
    """Configuration for parameter optimization."""

    method: OptimizationMethod = Field(..., description="Optimization method to use")
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
    )
    convergence_threshold: float = Field(
        0.001,
        ge=0.0001,
        le=0.1,
        description="Convergence threshold",
    )
    random_seed: Optional[int] = Field(None, description="Random seed for reproducibility")

    @field_validator("walk_forward_config")
    @classmethod
    def validate_walk_forward_config(cls, v, info):
        if (
            hasattr(info, "data")
            and info.data.get("method") == OptimizationMethod.WALK_FORWARD
            and v is None
        ):
            logger.error(
                "Optimization config validation failed - missing walk_forward_config",
                extra={
                    "component": "optimization",
                    "action": "config_validation_error",
                    "method": OptimizationMethod.WALK_FORWARD.value,
                },
            )
            raise ValueError("walk_forward_config is required when method is walk_forward")
        return v

    @field_validator("purged_k_fold_config")
    @classmethod
    def validate_purged_k_fold_config(cls, v, info):
        if (
            hasattr(info, "data")
            and info.data.get("method") == OptimizationMethod.PURGED_K_FOLD
            and v is None
        ):
            logger.error(
                "Optimization config validation failed - missing purged_k_fold_config",
                extra={
                    "component": "optimization",
                    "action": "config_validation_error",
                    "method": OptimizationMethod.PURGED_K_FOLD.value,
                },
            )
            raise ValueError("purged_k_fold_config is required when method is purged_k_fold")
        return v


class OptimizationResult(BaseModel):
    """Result of parameter optimization."""

    optimized_parameters: dict[str, Union[float, int]] = Field(
        ..., description="Optimized parameter values"
    )
    best_score: float = Field(..., description="Best optimization score")
    optimization_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Optimization history"
    )
    convergence_achieved: bool = Field(..., description="Whether convergence was achieved")
    iterations_completed: int = Field(..., description="Number of iterations completed")
    optimization_time: float = Field(..., description="Optimization time in seconds")
    method_used: OptimizationMethod = Field(..., description="Optimization method used")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class OutOfSampleTest(BaseModel):
    """Out-of-sample test configuration and results."""

    test_start_date: date = Field(..., description="Start date for out-of-sample testing")
    test_end_date: date = Field(..., description="End date for out-of-sample testing")
    train_start_date: date = Field(..., description="Start date for training data")
    train_end_date: date = Field(..., description="End date for training data")
    parameters: dict[str, Union[float, int]] = Field(..., description="Parameters to test")
    strategy_name: str = Field(..., description="Name of the strategy to test")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.test_end_date <= self.test_start_date:
            logger.error(
                "OutOfSampleTest validation failed - test_end_date <= test_start_date",
                extra={
                    "component": "optimization",
                    "action": "oos_test_validation_error",
                    "test_start_date": str(self.test_start_date),
                    "test_end_date": str(self.test_end_date),
                },
            )
            raise ValueError("test_end_date must be after test_start_date")
        if self.train_end_date <= self.train_start_date:
            logger.error(
                "OutOfSampleTest validation failed - train_end_date <= train_start_date",
                extra={
                    "component": "optimization",
                    "action": "oos_test_validation_error",
                    "train_start_date": str(self.train_start_date),
                    "train_end_date": str(self.train_end_date),
                },
            )
            raise ValueError("train_end_date must be after train_start_date")
        logger.debug(
            "OutOfSampleTest dates validated",
            extra={
                "component": "optimization",
                "action": "oos_test_validated",
                "strategy_name": self.strategy_name,
                "test_period_days": (self.test_end_date - self.test_start_date).days,
            },
        )
        return self


class OutOfSampleResult(BaseModel):
    """Results of out-of-sample testing."""

    test_config: OutOfSampleTest = Field(..., description="Test configuration")
    total_return: float = Field(..., description="Total return during test period")
    sharpe_ratio: float = Field(..., description="Sharpe ratio during test period")
    max_drawdown: float = Field(..., description="Maximum drawdown during test period")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate during test period")
    profit_factor: float = Field(..., description="Profit factor during test period")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    avg_trade_duration: float = Field(
        ...,
        ge=0,
        description="Average trade duration in days",
    )
    volatility: float = Field(..., ge=0, description="Volatility during test period")
    calmar_ratio: float = Field(..., description="Calmar ratio during test period")
    sortino_ratio: float = Field(..., description="Sortino ratio during test period")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class ParameterOptimizationRequest(BaseModel):
    """Request model for parameter optimization."""

    strategy_name: str = Field(..., description="Name of the strategy to optimize")
    parameters: list[OptimizationParameter] = Field(
        ..., min_length=1, description="Parameters to optimize"
    )
    optimization_config: OptimizationConfig = Field(..., description="Optimization configuration")
    data_start_date: date = Field(..., description="Start date for optimization data")
    data_end_date: date = Field(..., description="End date for optimization data")
    cost_analysis_enabled: bool = Field(
        True,
        description="Whether to include cost analysis",
    )

    @model_validator(mode="after")
    def validate_data_end_date(self):
        if self.data_end_date <= self.data_start_date:
            logger.error(
                "ParameterOptimizationRequest validation failed - data_end_date <= data_start_date",
                extra={
                    "component": "optimization",
                    "action": "optimization_request_validation_error",
                    "strategy_name": self.strategy_name,
                    "data_start_date": str(self.data_start_date),
                    "data_end_date": str(self.data_end_date),
                },
            )
            raise ValueError("data_end_date must be after data_start_date")
        logger.info(
            "ParameterOptimizationRequest validated",
            extra={
                "component": "optimization",
                "action": "optimization_request_validated",
                "strategy_name": self.strategy_name,
                "parameters_count": len(self.parameters),
                "optimization_method": self.optimization_config.method.value,
            },
        )
        return self


class OutOfSampleTestRequest(BaseModel):
    """Request model for out-of-sample testing."""

    test_config: OutOfSampleTest = Field(..., description="Out-of-sample test configuration")
    cost_analysis_enabled: bool = Field(
        True,
        description="Whether to include cost analysis",
    )


class OptimizationArtifact(BaseModel):
    """Artifact for storing optimization results."""

    artifact_id: str = Field(..., description="Unique artifact identifier")
    optimization_result: OptimizationResult = Field(..., description="Optimization result")
    out_of_sample_results: list[OutOfSampleResult] = Field(
        default_factory=list, description="Out-of-sample test results"
    )
    strategy_name: str = Field(..., description="Name of the optimized strategy")
    optimization_date: datetime = Field(
        default_factory=datetime.now,
        description="Optimization date",
    )
    version: str = Field("1.0", description="Artifact version")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    }


class OptimizationMetrics(BaseModel):
    """Metrics for optimization performance."""

    optimization_score: float = Field(..., description="Overall optimization score")
    stability_score: float = Field(..., ge=0, le=1, description="Parameter stability score")
    robustness_score: float = Field(..., ge=0, le=1, description="Robustness score")
    overfitting_risk: float = Field(..., ge=0, le=1, description="Overfitting risk score")
    cost_efficiency: float = Field(..., ge=0, le=1, description="Cost efficiency score")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate")
    profit_factor: float = Field(..., description="Profit factor")

    @field_validator("overfitting_risk")
    @classmethod
    def validate_overfitting_risk(cls, v):
        if v > 0.7:
            logger.error(
                "OptimizationMetrics validation failed - high overfitting risk",
                extra={
                    "component": "optimization",
                    "action": "metrics_validation_error",
                    "overfitting_risk": v,
                    "threshold": 0.7,
                },
            )
            raise ValueError("High overfitting risk detected")
        if v > 0.5:
            logger.warning(
                "OptimizationMetrics warning - elevated overfitting risk",
                extra={
                    "component": "optimization",
                    "action": "metrics_validation_warning",
                    "overfitting_risk": v,
                },
            )
        return v


class OptimizationSummary(BaseModel):
    """Summary of optimization process."""

    total_optimizations: int = Field(
        ...,
        ge=0,
        description="Total number of optimizations performed",
    )
    successful_optimizations: int = Field(
        ...,
        ge=0,
        description="Number of successful optimizations",
    )
    failed_optimizations: int = Field(
        ...,
        ge=0,
        description="Number of failed optimizations",
    )
    avg_optimization_time: float = Field(
        ...,
        ge=0,
        description="Average optimization time in seconds",
    )
    best_strategy: str = Field(..., description="Name of the best performing strategy")
    best_score: float = Field(..., description="Best optimization score achieved")
    last_optimization_date: datetime = Field(..., description="Date of last optimization")
    artifacts_count: int = Field(
        ...,
        ge=0,
        description="Number of optimization artifacts stored",
    )

    @model_validator(mode="after")
    def validate_numeric_values(self):
        """Ensure all numeric values are JSON-serializable."""
        import math

        # Replace NaN and infinity with None or default values
        if math.isnan(self.avg_optimization_time) or math.isinf(self.avg_optimization_time):
            logger.warning(
                "OptimizationSummary contains invalid avg_optimization_time, resetting to 0",
                extra={
                    "component": "optimization",
                    "action": "summary_validation_warning",
                    "original_value": str(self.avg_optimization_time),
                },
            )
            self.avg_optimization_time = 0.0

        if math.isnan(self.best_score) or math.isinf(self.best_score):
            logger.warning(
                "OptimizationSummary contains invalid best_score, resetting to 0",
                extra={
                    "component": "optimization",
                    "action": "summary_validation_warning",
                    "original_value": str(self.best_score),
                },
            )
            self.best_score = 0.0

        logger.debug(
            "OptimizationSummary validated",
            extra={
                "component": "optimization",
                "action": "summary_validated",
                "total_optimizations": self.total_optimizations,
                "best_strategy": self.best_strategy,
            },
        )

        return self
