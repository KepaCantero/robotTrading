"""
Tests for parameter optimization service.

This module contains comprehensive tests for walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

from app.models.optimization import (
    OptimizationMethod, ParameterConstraint, OptimizationParameter,
    WalkForwardConfig, PurgedKFoldConfig, OptimizationConfig,
    OptimizationResult, OutOfSampleTest, OutOfSampleResult,
    ParameterOptimizationRequest, OutOfSampleTestRequest,
    OptimizationArtifact, OptimizationMetrics, OptimizationSummary,
    ParameterType
)
from app.services.parameter_optimization_service import ParameterOptimizationService
from app.services.cost_analysis_service import CostAnalysisService


class TestParameterOptimizationService:
    """Test cases for ParameterOptimizationService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        cost_service = Mock(spec=CostAnalysisService)
        return ParameterOptimizationService(cost_service)
    
    @pytest.fixture
    def sample_parameters(self):
        """Create sample parameters for testing."""
        return [
            OptimizationParameter(
                name="min_strength",
                current_value=60.0,
                constraints=ParameterConstraint(
                    min_value=50.0,
                    max_value=80.0,
                    step_size=5.0,
                    parameter_type=ParameterType.THRESHOLD
                ),
                description="Minimum signal strength"
            ),
            OptimizationParameter(
                name="rsi_period",
                current_value=14,
                constraints=ParameterConstraint(
                    min_value=5,
                    max_value=30,
                    step_size=1,
                    parameter_type=ParameterType.PERIOD
                ),
                description="RSI calculation period"
            )
        ]
    
    @pytest.fixture
    def walk_forward_config(self):
        """Create walk-forward configuration for testing."""
        return WalkForwardConfig(
            initial_train_period=90,
            retrain_frequency=30,
            test_period=30,
            min_train_period=60,
            purged_period=5
        )
    
    @pytest.fixture
    def purged_k_fold_config(self):
        """Create purged K-fold configuration for testing."""
        return PurgedKFoldConfig(
            n_splits=5,
            purged_period=2,
            embargo_period=1,
            shuffle=False
        )
    
    @pytest.fixture
    def optimization_request(self, sample_parameters, walk_forward_config):
        """Create optimization request for testing."""
        return ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.WALK_FORWARD,
                walk_forward_config=walk_forward_config,
                max_iterations=50,
                convergence_threshold=0.001,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31),
            cost_analysis_enabled=True
        )
    
    @pytest.fixture
    def out_of_sample_test_request(self):
        """Create out-of-sample test request for testing."""
        return OutOfSampleTestRequest(
            test_config=OutOfSampleTest(
                test_start_date=date(2023, 1, 1),
                test_end_date=date(2023, 12, 31),
                train_start_date=date(2020, 1, 1),
                train_end_date=date(2022, 12, 31),
                parameters={"min_strength": 65.0, "rsi_period": 14},
                strategy_name="momentum_strategy"
            ),
            cost_analysis_enabled=True
        )


class TestOptimizationModels(TestParameterOptimizationService):
    """Test cases for optimization models."""
    
    def test_parameter_constraint_validation(self):
        """Test parameter constraint validation."""
        # Valid constraint
        constraint = ParameterConstraint(
            min_value=0.0,
            max_value=1.0,
            step_size=0.1,
            parameter_type=ParameterType.THRESHOLD
        )
        assert constraint.min_value == 0.0
        assert constraint.max_value == 1.0
        
        # Invalid constraint (min >= max)
        with pytest.raises(ValueError, match="min_value must be less than max_value"):
            ParameterConstraint(
                min_value=1.0,
                max_value=0.5,
                parameter_type=ParameterType.THRESHOLD
            )
    
    def test_optimization_parameter_validation(self):
        """Test optimization parameter validation."""
        constraint = ParameterConstraint(
            min_value=50.0,
            max_value=80.0,
            parameter_type=ParameterType.THRESHOLD
        )
        
        # Valid parameter
        param = OptimizationParameter(
            name="test_param",
            current_value=65.0,
            constraints=constraint
        )
        assert param.current_value == 65.0
        
        # Invalid parameter (outside constraints)
        with pytest.raises(ValueError, match="current_value .* must be within constraints"):
            OptimizationParameter(
                name="test_param",
                current_value=90.0,
                constraints=constraint
            )
    
    def test_walk_forward_config_validation(self):
        """Test walk-forward configuration validation."""
        # Valid config
        config = WalkForwardConfig(
            initial_train_period=90,
            retrain_frequency=30,
            test_period=30,
            min_train_period=60
        )
        assert config.initial_train_period == 90
        
        # Invalid config (test_period >= initial_train_period)
        with pytest.raises(ValueError, match="test_period must be less than initial_train_period"):
            WalkForwardConfig(
                initial_train_period=30,
                retrain_frequency=10,
                test_period=30,
                min_train_period=20
            )
    
    def test_optimization_config_validation(self):
        """Test optimization configuration validation."""
        walk_forward_config = WalkForwardConfig(
            initial_train_period=90,
            retrain_frequency=30,
            test_period=30,
            min_train_period=60
        )
        
        # Valid config
        config = OptimizationConfig(
            method=OptimizationMethod.WALK_FORWARD,
            walk_forward_config=walk_forward_config
        )
        assert config.method == OptimizationMethod.WALK_FORWARD
        
        # Invalid config (missing walk_forward_config)
        with pytest.raises(ValueError, match="walk_forward_config is required"):
            OptimizationConfig(
                method=OptimizationMethod.WALK_FORWARD,
                walk_forward_config=None
            )
    
    def test_out_of_sample_test_validation(self):
        """Test out-of-sample test validation."""
        # Valid test
        test = OutOfSampleTest(
            test_start_date=date(2023, 1, 1),
            test_end_date=date(2023, 12, 31),
            train_start_date=date(2020, 1, 1),
            train_end_date=date(2022, 12, 31),
            parameters={"param1": 0.5},
            strategy_name="test_strategy"
        )
        assert test.test_start_date == date(2023, 1, 1)
        
        # Invalid test (test_end_date <= test_start_date)
        with pytest.raises(ValueError, match="test_end_date must be after test_start_date"):
            OutOfSampleTest(
                test_start_date=date(2023, 12, 31),
                test_end_date=date(2023, 1, 1),
                train_start_date=date(2020, 1, 1),
                train_end_date=date(2022, 12, 31),
                parameters={"param1": 0.5},
                strategy_name="test_strategy"
            )


class TestParameterOptimizationServiceMethods(TestParameterOptimizationService):
    """Test cases for ParameterOptimizationService methods."""
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_walk_forward(self, service, optimization_request):
        """Test walk-forward parameter optimization."""
        result = await service.optimize_parameters(optimization_request)
        
        assert isinstance(result, OptimizationResult)
        assert result.method_used == OptimizationMethod.WALK_FORWARD
        assert result.optimization_time > 0
        assert len(result.optimized_parameters) == 2
        assert "min_strength" in result.optimized_parameters
        assert "rsi_period" in result.optimized_parameters
        assert len(result.optimization_history) > 0
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_purged_k_fold(self, service, sample_parameters, purged_k_fold_config):
        """Test purged K-fold parameter optimization."""
        request = ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.PURGED_K_FOLD,
                purged_k_fold_config=purged_k_fold_config,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        result = await service.optimize_parameters(request)
        
        assert isinstance(result, OptimizationResult)
        assert result.method_used == OptimizationMethod.PURGED_K_FOLD
        assert result.convergence_achieved is True
        assert len(result.optimization_history) == purged_k_fold_config.n_splits
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_out_of_sample(self, service, sample_parameters):
        """Test out-of-sample parameter optimization."""
        request = ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.OUT_OF_SAMPLE,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        result = await service.optimize_parameters(request)
        
        assert isinstance(result, OptimizationResult)
        assert result.method_used == OptimizationMethod.OUT_OF_SAMPLE
        assert result.convergence_achieved is True
        assert result.iterations_completed == 2
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_monte_carlo(self, service, sample_parameters):
        """Test Monte Carlo parameter optimization."""
        request = ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.MONTE_CARLO,
                max_iterations=20,
                convergence_threshold=0.01,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        result = await service.optimize_parameters(request)
        
        assert isinstance(result, OptimizationResult)
        assert result.method_used == OptimizationMethod.MONTE_CARLO
        assert result.iterations_completed <= 20
    
    @pytest.mark.asyncio
    async def test_optimize_parameters_invalid_request(self, service):
        """Test optimization with invalid request."""
        # Empty parameters
        request = ParameterOptimizationRequest(
            strategy_name="test_strategy",
            parameters=[],
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.WALK_FORWARD,
                walk_forward_config=WalkForwardConfig(
                    initial_train_period=90,
                    retrain_frequency=30,
                    test_period=30,
                    min_train_period=60
                )
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        with pytest.raises(RuntimeError, match="Parameter optimization failed"):
            await service.optimize_parameters(request)
    
    @pytest.mark.asyncio
    async def test_perform_out_of_sample_test(self, service, out_of_sample_test_request):
        """Test out-of-sample testing."""
        result = await service.perform_out_of_sample_test(out_of_sample_test_request)
        
        assert isinstance(result, OutOfSampleResult)
        assert result.test_config.strategy_name == "momentum_strategy"
        assert result.total_return is not None
        assert result.sharpe_ratio is not None
        assert result.max_drawdown is not None
        assert result.win_rate is not None
        assert result.profit_factor is not None
        assert result.total_trades is not None
        assert result.avg_trade_duration is not None
        assert result.volatility is not None
        assert result.calmar_ratio is not None
        assert result.sortino_ratio is not None
    
    @pytest.mark.asyncio
    async def test_perform_out_of_sample_test_invalid_config(self, service):
        """Test out-of-sample testing with invalid configuration."""
        request = OutOfSampleTestRequest(
            test_config=OutOfSampleTest(
                test_start_date=date(2023, 12, 31),
                test_end_date=date(2023, 1, 1),  # Invalid: end before start
                train_start_date=date(2020, 1, 1),
                train_end_date=date(2022, 12, 31),
                parameters={"param1": 0.5},
                strategy_name="test_strategy"
            )
        )
        
        with pytest.raises(RuntimeError, match="Out-of-sample test failed"):
            await service.perform_out_of_sample_test(request)
    
    @pytest.mark.asyncio
    async def test_get_optimization_artifacts(self, service, optimization_request):
        """Test getting optimization artifacts."""
        # Initially no artifacts
        artifacts = await service.get_optimization_artifacts()
        assert len(artifacts) == 0
        
        # Perform optimization to create artifact
        await service.optimize_parameters(optimization_request)
        
        # Check artifacts
        artifacts = await service.get_optimization_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].strategy_name == "momentum_strategy"
        
        # Filter by strategy name
        artifacts = await service.get_optimization_artifacts("momentum_strategy")
        assert len(artifacts) == 1
        
        artifacts = await service.get_optimization_artifacts("nonexistent_strategy")
        assert len(artifacts) == 0
    
    @pytest.mark.asyncio
    async def test_get_optimization_summary(self, service, optimization_request):
        """Test getting optimization summary."""
        summary = await service.get_optimization_summary()
        
        assert isinstance(summary, OptimizationSummary)
        assert summary.total_optimizations == 0
        assert summary.successful_optimizations == 0
        assert summary.failed_optimizations == 0
        
        # Perform optimization
        await service.optimize_parameters(optimization_request)
        
        summary = await service.get_optimization_summary()
        assert summary.total_optimizations == 1
        assert summary.successful_optimizations == 1
        assert summary.best_strategy == "momentum_strategy"
        assert summary.artifacts_count == 1
    
    @pytest.mark.asyncio
    async def test_calculate_optimization_metrics(self, service, optimization_request):
        """Test calculating optimization metrics."""
        # Perform optimization to create artifact
        await service.optimize_parameters(optimization_request)
        
        artifacts = await service.get_optimization_artifacts()
        artifact = artifacts[0]
        
        metrics = await service.calculate_optimization_metrics(artifact)
        
        assert isinstance(metrics, OptimizationMetrics)
        assert metrics.optimization_score is not None
        assert 0 <= metrics.stability_score <= 1
        assert 0 <= metrics.robustness_score <= 1
        assert 0 <= metrics.overfitting_risk <= 1
        assert 0 <= metrics.cost_efficiency <= 1
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown is not None
        assert 0 <= metrics.win_rate <= 1
        assert metrics.profit_factor is not None


class TestOptimizationServiceIntegration(TestParameterOptimizationService):
    """Integration tests for optimization service."""
    
    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self, service, sample_parameters, walk_forward_config):
        """Test complete optimization workflow."""
        # Step 1: Optimize parameters
        request = ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.WALK_FORWARD,
                walk_forward_config=walk_forward_config,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        optimization_result = await service.optimize_parameters(request)
        
        # Step 2: Perform out-of-sample test
        test_request = OutOfSampleTestRequest(
            test_config=OutOfSampleTest(
                test_start_date=date(2023, 1, 1),
                test_end_date=date(2023, 12, 31),
                train_start_date=date(2020, 1, 1),
                train_end_date=date(2022, 12, 31),
                parameters=optimization_result.optimized_parameters,
                strategy_name="momentum_strategy"
            )
        )
        
        test_result = await service.perform_out_of_sample_test(test_request)
        
        # Step 3: Get artifacts and metrics
        artifacts = await service.get_optimization_artifacts()
        assert len(artifacts) == 1
        
        metrics = await service.calculate_optimization_metrics(artifacts[0])
        
        # Step 4: Verify results
        assert optimization_result.best_score is not None
        assert test_result.total_return is not None
        assert metrics.optimization_score is not None
        
        # Step 5: Get summary
        summary = await service.get_optimization_summary()
        assert summary.total_optimizations == 1
        assert summary.successful_optimizations == 1
    
    @pytest.mark.asyncio
    async def test_multiple_strategy_optimization(self, service, sample_parameters):
        """Test optimization for multiple strategies."""
        strategies = ["momentum_strategy", "mean_reversion_strategy", "liquidity_strategy"]
        
        for strategy in strategies:
            request = ParameterOptimizationRequest(
                strategy_name=strategy,
                parameters=sample_parameters,
                optimization_config=OptimizationConfig(
                    method=OptimizationMethod.OUT_OF_SAMPLE,
                    random_seed=42
                ),
                data_start_date=date(2020, 1, 1),
                data_end_date=date(2023, 12, 31)
            )
            
            await service.optimize_parameters(request)
        
        # Check all artifacts
        artifacts = await service.get_optimization_artifacts()
        assert len(artifacts) == 3
        
        # Check summary
        summary = await service.get_optimization_summary()
        assert summary.total_optimizations == 3
        assert summary.successful_optimizations == 3
        assert summary.artifacts_count == 3
    
    @pytest.mark.asyncio
    async def test_optimization_with_cost_analysis(self, service, sample_parameters):
        """Test optimization with cost analysis enabled."""
        request = ParameterOptimizationRequest(
            strategy_name="momentum_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.OUT_OF_SAMPLE,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31),
            cost_analysis_enabled=True
        )
        
        result = await service.optimize_parameters(request)
        
        assert result.best_score is not None
        assert result.optimization_time > 0
        
        # Verify cost analysis service was used
        assert service.cost_analysis_service is not None


class TestOptimizationServiceEdgeCases(TestParameterOptimizationService):
    """Test edge cases for optimization service."""
    
    @pytest.mark.asyncio
    async def test_optimization_with_single_parameter(self, service):
        """Test optimization with single parameter."""
        single_param = [
            OptimizationParameter(
                name="single_param",
                current_value=0.5,
                constraints=ParameterConstraint(
                    min_value=0.0,
                    max_value=1.0,
                    parameter_type=ParameterType.THRESHOLD
                )
            )
        ]
        
        request = ParameterOptimizationRequest(
            strategy_name="single_param_strategy",
            parameters=single_param,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.OUT_OF_SAMPLE,
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        result = await service.optimize_parameters(request)
        
        assert len(result.optimized_parameters) == 1
        assert "single_param" in result.optimized_parameters
    
    @pytest.mark.asyncio
    async def test_optimization_with_convergence_failure(self, service, sample_parameters):
        """Test optimization with convergence failure."""
        request = ParameterOptimizationRequest(
            strategy_name="convergence_test",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.MONTE_CARLO,
                max_iterations=5,  # Very low to force convergence failure
                convergence_threshold=0.0001,  # Very strict
                random_seed=42
            ),
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31)
        )
        
        result = await service.optimize_parameters(request)
        
        assert result.iterations_completed == 5
        assert result.convergence_achieved is False
    
    @pytest.mark.asyncio
    async def test_optimization_with_minimal_data_period(self, service, sample_parameters):
        """Test optimization with minimal data period."""
        request = ParameterOptimizationRequest(
            strategy_name="minimal_data_strategy",
            parameters=sample_parameters,
            optimization_config=OptimizationConfig(
                method=OptimizationMethod.OUT_OF_SAMPLE,
                random_seed=42
            ),
            data_start_date=date(2023, 1, 1),
            data_end_date=date(2023, 1, 31)  # Only 30 days
        )
        
        result = await service.optimize_parameters(request)
        
        assert result.best_score is not None
        assert result.optimization_time > 0
