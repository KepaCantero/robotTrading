"""
Optimization models for parameter optimization and overfitting prevention.

This module contains Pydantic models for walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, model_validator


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
    
    @model_validator(mode='after')
    def validate_values(self):
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be less than max_value")
        return self


class OptimizationParameter(BaseModel):
    """Parameter to be optimized."""
    name: str = Field(..., description="Name of the parameter")
    current_value: Union[float, int] = Field(..., description="Current value of the parameter")
    constraints: ParameterConstraint = Field(..., description="Constraints for optimization")
    description: Optional[str] = Field(None, description="Description of the parameter")
    
    @validator('current_value')
    def validate_current_value(cls, v, values):
        if 'constraints' in values:
            constraints = values['constraints']
            if not (constraints.min_value <= v <= constraints.max_value):
                raise ValueError(f"current_value {v} must be within constraints [{constraints.min_value}, {constraints.max_value}]")
        return v


class WalkForwardConfig(BaseModel):
    """Configuration for walk-forward analysis."""
    initial_train_period: int = Field(..., ge=30, description="Initial training period in days")
    retrain_frequency: int = Field(..., ge=1, description="Retraining frequency in days")
    test_period: int = Field(..., ge=7, description="Test period in days")
    min_train_period: int = Field(..., ge=30, description="Minimum training period in days")
    max_train_period: Optional[int] = Field(None, description="Maximum training period in days")
    purged_period: int = Field(0, ge=0, description="Purged period to avoid look-ahead bias")
    
    @validator('test_period')
    def validate_test_period(cls, v, values):
        if 'initial_train_period' in values and v >= values['initial_train_period']:
            raise ValueError("test_period must be less than initial_train_period")
        return v


class PurgedKFoldConfig(BaseModel):
    """Configuration for Purged K-Fold Cross Validation."""
    n_splits: int = Field(5, ge=2, le=10, description="Number of splits for K-Fold")
    purged_period: int = Field(1, ge=0, description="Purged period to avoid look-ahead bias")
    embargo_period: int = Field(1, ge=0, description="Embargo period to avoid look-ahead bias")
    shuffle: bool = Field(False, description="Whether to shuffle the data")


class OptimizationConfig(BaseModel):
    """Configuration for parameter optimization."""
    method: OptimizationMethod = Field(..., description="Optimization method to use")
    walk_forward_config: Optional[WalkForwardConfig] = Field(None, description="Walk-forward configuration")
    purged_k_fold_config: Optional[PurgedKFoldConfig] = Field(None, description="Purged K-Fold configuration")
    max_iterations: int = Field(100, ge=1, le=1000, description="Maximum optimization iterations")
    convergence_threshold: float = Field(0.001, ge=0.0001, le=0.1, description="Convergence threshold")
    random_seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    
    @validator('walk_forward_config')
    def validate_walk_forward_config(cls, v, values):
        if values.get('method') == OptimizationMethod.WALK_FORWARD and v is None:
            raise ValueError("walk_forward_config is required when method is walk_forward")
        return v
    
    @validator('purged_k_fold_config')
    def validate_purged_k_fold_config(cls, v, values):
        if values.get('method') == OptimizationMethod.PURGED_K_FOLD and v is None:
            raise ValueError("purged_k_fold_config is required when method is purged_k_fold")
        return v


class OptimizationResult(BaseModel):
    """Result of parameter optimization."""
    optimized_parameters: Dict[str, Union[float, int]] = Field(..., description="Optimized parameter values")
    best_score: float = Field(..., description="Best optimization score")
    optimization_history: List[Dict[str, Any]] = Field(default_factory=list, description="Optimization history")
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
    parameters: Dict[str, Union[float, int]] = Field(..., description="Parameters to test")
    strategy_name: str = Field(..., description="Name of the strategy to test")
    
    @validator('test_end_date')
    def validate_test_end_date(cls, v, values):
        if 'test_start_date' in values and v <= values['test_start_date']:
            raise ValueError("test_end_date must be after test_start_date")
        return v
    
    @validator('train_end_date')
    def validate_train_end_date(cls, v, values):
        if 'train_start_date' in values and v <= values['train_start_date']:
            raise ValueError("train_end_date must be after train_start_date")
        return v


class OutOfSampleResult(BaseModel):
    """Results of out-of-sample testing."""
    test_config: OutOfSampleTest = Field(..., description="Test configuration")
    total_return: float = Field(..., description="Total return during test period")
    sharpe_ratio: float = Field(..., description="Sharpe ratio during test period")
    max_drawdown: float = Field(..., description="Maximum drawdown during test period")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate during test period")
    profit_factor: float = Field(..., description="Profit factor during test period")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    avg_trade_duration: float = Field(..., ge=0, description="Average trade duration in days")
    volatility: float = Field(..., ge=0, description="Volatility during test period")
    calmar_ratio: float = Field(..., description="Calmar ratio during test period")
    sortino_ratio: float = Field(..., description="Sortino ratio during test period")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class ParameterOptimizationRequest(BaseModel):
    """Request model for parameter optimization."""
    strategy_name: str = Field(..., description="Name of the strategy to optimize")
    parameters: List[OptimizationParameter] = Field(..., min_items=1, description="Parameters to optimize")
    optimization_config: OptimizationConfig = Field(..., description="Optimization configuration")
    data_start_date: date = Field(..., description="Start date for optimization data")
    data_end_date: date = Field(..., description="End date for optimization data")
    cost_analysis_enabled: bool = Field(True, description="Whether to include cost analysis")
    
    @validator('data_end_date')
    def validate_data_end_date(cls, v, values):
        if 'data_start_date' in values and v <= values['data_start_date']:
            raise ValueError("data_end_date must be after data_start_date")
        return v


class OutOfSampleTestRequest(BaseModel):
    """Request model for out-of-sample testing."""
    test_config: OutOfSampleTest = Field(..., description="Out-of-sample test configuration")
    cost_analysis_enabled: bool = Field(True, description="Whether to include cost analysis")


class OptimizationArtifact(BaseModel):
    """Artifact for storing optimization results."""
    artifact_id: str = Field(..., description="Unique artifact identifier")
    optimization_result: OptimizationResult = Field(..., description="Optimization result")
    out_of_sample_results: List[OutOfSampleResult] = Field(default_factory=list, description="Out-of-sample test results")
    strategy_name: str = Field(..., description="Name of the optimized strategy")
    optimization_date: datetime = Field(default_factory=datetime.now, description="Optimization date")
    version: str = Field("1.0", description="Artifact version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
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
    
    @validator('overfitting_risk')
    def validate_overfitting_risk(cls, v):
        if v > 0.7:
            raise ValueError("High overfitting risk detected")
        return v


class OptimizationSummary(BaseModel):
    """Summary of optimization process."""
    total_optimizations: int = Field(..., ge=0, description="Total number of optimizations performed")
    successful_optimizations: int = Field(..., ge=0, description="Number of successful optimizations")
    failed_optimizations: int = Field(..., ge=0, description="Number of failed optimizations")
    avg_optimization_time: float = Field(..., ge=0, description="Average optimization time in seconds")
    best_strategy: str = Field(..., description="Name of the best performing strategy")
    best_score: float = Field(..., description="Best optimization score achieved")
    last_optimization_date: datetime = Field(..., description="Date of last optimization")
    artifacts_count: int = Field(..., ge=0, description="Number of optimization artifacts stored")
