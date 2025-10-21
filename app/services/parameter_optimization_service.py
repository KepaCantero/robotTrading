"""
Parameter optimization service for trading strategies.

This service implements walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

import asyncio
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass

from app.models.optimization import (
    OptimizationMethod, ParameterConstraint, OptimizationParameter,
    WalkForwardConfig, PurgedKFoldConfig, OptimizationConfig,
    OptimizationResult, OutOfSampleTest, OutOfSampleResult,
    ParameterOptimizationRequest, OutOfSampleTestRequest,
    OptimizationArtifact, OptimizationMetrics, OptimizationSummary
)
from app.models.cost_analysis import CostBreakdownModel, CostAnalysisResultModel
from app.services.cost_analysis_service import CostAnalysisService


@dataclass
class OptimizationState:
    """State tracking for optimization process."""
    current_iteration: int = 0
    best_score: float = float('-inf')
    best_parameters: Dict[str, Union[float, int]] = None
    optimization_history: List[Dict[str, Any]] = None
    convergence_count: int = 0
    
    def __post_init__(self):
        if self.optimization_history is None:
            self.optimization_history = []


class ParameterOptimizationService:
    """Service for parameter optimization and overfitting prevention."""
    
    def __init__(self, cost_analysis_service: Optional[CostAnalysisService] = None):
        """Initialize the parameter optimization service."""
        self.cost_analysis_service = cost_analysis_service or CostAnalysisService()
        self.optimization_artifacts: Dict[str, OptimizationArtifact] = {}
        self.optimization_summary = OptimizationSummary(
            total_optimizations=0,
            successful_optimizations=0,
            failed_optimizations=0,
            avg_optimization_time=0.0,
            best_strategy="",
            best_score=float('-inf'),
            last_optimization_date=datetime.now(),
            artifacts_count=0
        )
    
    async def optimize_parameters(
        self, 
        request: ParameterOptimizationRequest
    ) -> OptimizationResult:
        """
        Optimize parameters for a trading strategy using the specified method.
        
        Args:
            request: Parameter optimization request
            
        Returns:
            Optimization result with optimized parameters
            
        Raises:
            ValueError: If optimization configuration is invalid
            RuntimeError: If optimization fails
        """
        start_time = datetime.now()
        
        try:
            # Validate request
            await self._validate_optimization_request(request)
            
            # Initialize optimization state
            state = OptimizationState()
            
            # Set random seed for reproducibility
            if request.optimization_config.random_seed:
                random.seed(request.optimization_config.random_seed)
            
            # Perform optimization based on method
            if request.optimization_config.method == OptimizationMethod.WALK_FORWARD:
                result = await self._walk_forward_optimization(request, state)
            elif request.optimization_config.method == OptimizationMethod.PURGED_K_FOLD:
                result = await self._purged_k_fold_optimization(request, state)
            elif request.optimization_config.method == OptimizationMethod.OUT_OF_SAMPLE:
                result = await self._out_of_sample_optimization(request, state)
            elif request.optimization_config.method == OptimizationMethod.MONTE_CARLO:
                result = await self._monte_carlo_optimization(request, state)
            else:
                raise ValueError(f"Unsupported optimization method: {request.optimization_config.method}")
            
            # Calculate optimization time
            optimization_time = (datetime.now() - start_time).total_seconds()
            result.optimization_time = optimization_time
            
            # Update summary
            await self._update_optimization_summary(request.strategy_name, result)
            
            # Store artifact
            await self._store_optimization_artifact(request, result)
            
            return result
            
        except Exception as e:
            self.optimization_summary.failed_optimizations += 1
            raise RuntimeError(f"Parameter optimization failed: {str(e)}")
    
    async def _validate_optimization_request(self, request: ParameterOptimizationRequest) -> None:
        """Validate the optimization request."""
        if not request.parameters:
            raise ValueError("At least one parameter must be specified for optimization")
        
        if request.data_end_date <= request.data_start_date:
            raise ValueError("data_end_date must be after data_start_date")
        
        # Validate optimization config based on method
        if request.optimization_config.method == OptimizationMethod.WALK_FORWARD:
            if not request.optimization_config.walk_forward_config:
                raise ValueError("walk_forward_config is required for walk-forward optimization")
        
        elif request.optimization_config.method == OptimizationMethod.PURGED_K_FOLD:
            if not request.optimization_config.purged_k_fold_config:
                raise ValueError("purged_k_fold_config is required for purged K-fold optimization")
    
    async def _walk_forward_optimization(
        self, 
        request: ParameterOptimizationRequest, 
        state: OptimizationState
    ) -> OptimizationResult:
        """Perform walk-forward optimization."""
        config = request.optimization_config.walk_forward_config
        current_date = request.data_start_date + timedelta(days=config.initial_train_period)
        
        while current_date + timedelta(days=config.test_period) <= request.data_end_date:
            # Define training and test periods
            train_start = current_date - timedelta(days=config.initial_train_period)
            train_end = current_date - timedelta(days=config.purged_period)
            test_start = current_date
            test_end = current_date + timedelta(days=config.test_period)
            
            # Optimize parameters for this period
            period_result = await self._optimize_period(
                request, train_start, train_end, test_start, test_end
            )
            
            # Update state
            state.optimization_history.append({
                'period': f"{train_start} to {test_end}",
                'train_period': f"{train_start} to {train_end}",
                'test_period': f"{test_start} to {test_end}",
                'score': period_result['score'],
                'parameters': period_result['parameters']
            })
            
            if period_result['score'] > state.best_score:
                state.best_score = period_result['score']
                state.best_parameters = period_result['parameters']
                state.convergence_count = 0
            else:
                state.convergence_count += 1
            
            # Move to next period
            current_date += timedelta(days=config.retrain_frequency)
            state.current_iteration += 1
            
            # Check convergence
            if state.convergence_count >= 3:
                break
        
        return OptimizationResult(
            optimized_parameters=state.best_parameters or {},
            best_score=state.best_score,
            optimization_history=state.optimization_history,
            convergence_achieved=state.convergence_count >= 3,
            iterations_completed=state.current_iteration,
            optimization_time=0.0,  # Will be set by caller
            method_used=OptimizationMethod.WALK_FORWARD
        )
    
    async def _purged_k_fold_optimization(
        self, 
        request: ParameterOptimizationRequest, 
        state: OptimizationState
    ) -> OptimizationResult:
        """Perform purged K-fold cross validation optimization."""
        config = request.optimization_config.purged_k_fold_config
        
        # Generate K-fold splits with purging
        splits = await self._generate_purged_splits(
            request.data_start_date, 
            request.data_end_date, 
            config.n_splits,
            config.purged_period,
            config.embargo_period
        )
        
        for fold_idx, (train_start, train_end, test_start, test_end) in enumerate(splits):
            # Optimize parameters for this fold
            fold_result = await self._optimize_period(
                request, train_start, train_end, test_start, test_end
            )
            
            # Update state
            state.optimization_history.append({
                'fold': fold_idx + 1,
                'train_period': f"{train_start} to {train_end}",
                'test_period': f"{test_start} to {test_end}",
                'score': fold_result['score'],
                'parameters': fold_result['parameters']
            })
            
            if fold_result['score'] > state.best_score:
                state.best_score = fold_result['score']
                state.best_parameters = fold_result['parameters']
                state.convergence_count = 0
            else:
                state.convergence_count += 1
            
            state.current_iteration += 1
        
        return OptimizationResult(
            optimized_parameters=state.best_parameters or {},
            best_score=state.best_score,
            optimization_history=state.optimization_history,
            convergence_achieved=True,  # K-fold always completes
            iterations_completed=state.current_iteration,
            optimization_time=0.0,  # Will be set by caller
            method_used=OptimizationMethod.PURGED_K_FOLD
        )
    
    async def _out_of_sample_optimization(
        self, 
        request: ParameterOptimizationRequest, 
        state: OptimizationState
    ) -> OptimizationResult:
        """Perform out-of-sample optimization."""
        # Split data into training and testing periods
        total_days = (request.data_end_date - request.data_start_date).days
        train_days = int(total_days * 0.7)  # 70% for training
        test_days = total_days - train_days
        
        train_start = request.data_start_date
        train_end = train_start + timedelta(days=train_days)
        test_start = train_end + timedelta(days=1)
        test_end = request.data_end_date
        
        # Optimize parameters on training data
        train_result = await self._optimize_period(
            request, train_start, train_end, train_start, train_end
        )
        
        # Test on out-of-sample data
        test_result = await self._optimize_period(
            request, train_start, train_end, test_start, test_end
        )
        
        state.optimization_history = [
            {
                'phase': 'training',
                'period': f"{train_start} to {train_end}",
                'score': train_result['score'],
                'parameters': train_result['parameters']
            },
            {
                'phase': 'testing',
                'period': f"{test_start} to {test_end}",
                'score': test_result['score'],
                'parameters': test_result['parameters']
            }
        ]
        
        # Use test score as final score
        state.best_score = test_result['score']
        state.best_parameters = test_result['parameters']
        
        return OptimizationResult(
            optimized_parameters=state.best_parameters or {},
            best_score=state.best_score,
            optimization_history=state.optimization_history,
            convergence_achieved=True,
            iterations_completed=2,
            optimization_time=0.0,  # Will be set by caller
            method_used=OptimizationMethod.OUT_OF_SAMPLE
        )
    
    async def _monte_carlo_optimization(
        self, 
        request: ParameterOptimizationRequest, 
        state: OptimizationState
    ) -> OptimizationResult:
        """Perform Monte Carlo optimization."""
        max_iterations = request.optimization_config.max_iterations
        convergence_threshold = request.optimization_config.convergence_threshold
        
        for iteration in range(max_iterations):
            # Generate random parameters
            random_params = await self._generate_random_parameters(request.parameters)
            
            # Evaluate parameters
            score = await self._evaluate_parameters(request, random_params)
            
            # Update state
            state.optimization_history.append({
                'iteration': iteration + 1,
                'score': score,
                'parameters': random_params
            })
            
            if score > state.best_score:
                improvement = score - state.best_score
                state.best_score = score
                state.best_parameters = random_params
                
                # Check convergence
                if improvement < convergence_threshold:
                    state.convergence_count += 1
                    if state.convergence_count >= 5:
                        break
                else:
                    state.convergence_count = 0
            
            state.current_iteration += 1
        
        return OptimizationResult(
            optimized_parameters=state.best_parameters or {},
            best_score=state.best_score,
            optimization_history=state.optimization_history,
            convergence_achieved=state.convergence_count >= 5,
            iterations_completed=state.current_iteration,
            optimization_time=0.0,  # Will be set by caller
            method_used=OptimizationMethod.MONTE_CARLO
        )
    
    async def _optimize_period(
        self,
        request: ParameterOptimizationRequest,
        train_start: date,
        train_end: date,
        test_start: date,
        test_end: date
    ) -> Dict[str, Any]:
        """Optimize parameters for a specific period."""
        # This is a simplified implementation
        # In a real implementation, you would:
        # 1. Load historical data for the period
        # 2. Run the strategy with different parameter combinations
        # 3. Calculate performance metrics
        # 4. Return the best parameters and score
        
        # For now, return mock data
        best_params = {}
        for param in request.parameters:
            # Generate a random value within constraints
            min_val = param.constraints.min_value
            max_val = param.constraints.max_value
            if param.constraints.step_size:
                steps = int((max_val - min_val) / param.constraints.step_size)
                value = min_val + random.randint(0, steps) * param.constraints.step_size
            else:
                value = random.uniform(min_val, max_val)
            
            best_params[param.name] = value
        
        # Calculate score (mock implementation)
        score = random.uniform(0.5, 2.0)
        
        return {
            'parameters': best_params,
            'score': score
        }
    
    async def _generate_purged_splits(
        self,
        start_date: date,
        end_date: date,
        n_splits: int,
        purged_period: int,
        embargo_period: int
    ) -> List[Tuple[date, date, date, date]]:
        """Generate purged K-fold splits."""
        total_days = (end_date - start_date).days
        split_size = total_days // n_splits
        
        splits = []
        for i in range(n_splits):
            # Calculate split boundaries
            split_start = start_date + timedelta(days=i * split_size)
            # For the last split, extend to the end date
            if i == n_splits - 1:
                split_end = end_date
            else:
                split_end = start_date + timedelta(days=(i + 1) * split_size)
            
            # Calculate training period (all data except this split)
            train_start = start_date
            train_end = split_start - timedelta(days=purged_period)
            
            # Calculate test period
            test_start = split_start
            test_end = split_end - timedelta(days=embargo_period)
            
            # Ensure we have valid periods and don't exceed the end date
            if (train_end > train_start and test_end > test_start and 
                test_end <= end_date and train_end <= end_date):
                splits.append((train_start, train_end, test_start, test_end))
        
        return splits
    
    async def _generate_random_parameters(
        self, 
        parameters: List[OptimizationParameter]
    ) -> Dict[str, Union[float, int]]:
        """Generate random parameters within constraints."""
        random_params = {}
        
        for param in parameters:
            min_val = param.constraints.min_value
            max_val = param.constraints.max_value
            
            if param.constraints.step_size:
                steps = int((max_val - min_val) / param.constraints.step_size)
                value = min_val + random.randint(0, steps) * param.constraints.step_size
            else:
                value = random.uniform(min_val, max_val)
            
            random_params[param.name] = value
        
        return random_params
    
    async def _evaluate_parameters(
        self,
        request: ParameterOptimizationRequest,
        parameters: Dict[str, Union[float, int]]
    ) -> float:
        """Evaluate parameters and return a score."""
        # This is a simplified implementation
        # In a real implementation, you would:
        # 1. Run the strategy with the given parameters
        # 2. Calculate performance metrics
        # 3. Include cost analysis if enabled
        # 4. Return a composite score
        
        # Mock score calculation
        base_score = random.uniform(0.5, 2.0)
        
        # Include cost analysis if enabled
        if request.cost_analysis_enabled:
            # Mock cost analysis impact
            cost_impact = random.uniform(0.8, 1.2)
            base_score *= cost_impact
        
        return base_score
    
    async def _update_optimization_summary(
        self, 
        strategy_name: str, 
        result: OptimizationResult
    ) -> None:
        """Update optimization summary."""
        self.optimization_summary.total_optimizations += 1
        self.optimization_summary.successful_optimizations += 1
        self.optimization_summary.last_optimization_date = datetime.now()
        
        if result.best_score > self.optimization_summary.best_score:
            self.optimization_summary.best_score = result.best_score
            self.optimization_summary.best_strategy = strategy_name
        
        # Update average optimization time
        total_time = (self.optimization_summary.avg_optimization_time * 
                     (self.optimization_summary.successful_optimizations - 1) + 
                     result.optimization_time)
        self.optimization_summary.avg_optimization_time = (
            total_time / self.optimization_summary.successful_optimizations
        )
    
    async def _store_optimization_artifact(
        self, 
        request: ParameterOptimizationRequest, 
        result: OptimizationResult
    ) -> None:
        """Store optimization artifact."""
        artifact_id = f"{request.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        artifact = OptimizationArtifact(
            artifact_id=artifact_id,
            optimization_result=result,
            strategy_name=request.strategy_name,
            metadata={
                'optimization_config': request.optimization_config.model_dump(),
                'parameters_count': len(request.parameters),
                'data_period': f"{request.data_start_date} to {request.data_end_date}"
            }
        )
        
        self.optimization_artifacts[artifact_id] = artifact
        self.optimization_summary.artifacts_count = len(self.optimization_artifacts)
    
    async def perform_out_of_sample_test(
        self, 
        request: OutOfSampleTestRequest
    ) -> OutOfSampleResult:
        """
        Perform out-of-sample testing for a strategy.
        
        Args:
            request: Out-of-sample test request
            
        Returns:
            Out-of-sample test results
            
        Raises:
            ValueError: If test configuration is invalid
            RuntimeError: If test fails
        """
        try:
            # Validate test configuration
            await self._validate_out_of_sample_test(request.test_config)
            
            # Run strategy with given parameters
            test_results = await self._run_strategy_test(
                request.test_config, 
                request.cost_analysis_enabled
            )
            
            return OutOfSampleResult(
                test_config=request.test_config,
                total_return=test_results['total_return'],
                sharpe_ratio=test_results['sharpe_ratio'],
                max_drawdown=test_results['max_drawdown'],
                win_rate=test_results['win_rate'],
                profit_factor=test_results['profit_factor'],
                total_trades=test_results['total_trades'],
                avg_trade_duration=test_results['avg_trade_duration'],
                volatility=test_results['volatility'],
                calmar_ratio=test_results['calmar_ratio'],
                sortino_ratio=test_results['sortino_ratio']
            )
            
        except Exception as e:
            raise RuntimeError(f"Out-of-sample test failed: {str(e)}")
    
    async def _validate_out_of_sample_test(self, test_config: OutOfSampleTest) -> None:
        """Validate out-of-sample test configuration."""
        if test_config.test_end_date <= test_config.test_start_date:
            raise ValueError("test_end_date must be after test_start_date")
        
        if test_config.train_end_date <= test_config.train_start_date:
            raise ValueError("train_end_date must be after train_start_date")
        
        if not test_config.parameters:
            raise ValueError("Parameters must be specified for testing")
    
    async def _run_strategy_test(
        self, 
        test_config: OutOfSampleTest, 
        cost_analysis_enabled: bool
    ) -> Dict[str, float]:
        """Run strategy test and return performance metrics."""
        # This is a simplified implementation
        # In a real implementation, you would:
        # 1. Load historical data for the test period
        # 2. Run the strategy with the given parameters
        # 3. Calculate all performance metrics
        # 4. Include cost analysis if enabled
        
        # Mock test results
        test_results = {
            'total_return': random.uniform(-0.2, 0.5),
            'sharpe_ratio': random.uniform(0.5, 2.5),
            'max_drawdown': random.uniform(0.05, 0.3),
            'win_rate': random.uniform(0.4, 0.7),
            'profit_factor': random.uniform(0.8, 2.0),
            'total_trades': random.randint(10, 100),
            'avg_trade_duration': random.uniform(1, 10),
            'volatility': random.uniform(0.1, 0.4),
            'calmar_ratio': random.uniform(0.5, 3.0),
            'sortino_ratio': random.uniform(0.5, 2.5)
        }
        
        # Include cost analysis if enabled
        if cost_analysis_enabled:
            # Mock cost analysis impact
            cost_impact = random.uniform(0.9, 1.1)
            test_results['total_return'] *= cost_impact
            test_results['sharpe_ratio'] *= cost_impact
        
        return test_results
    
    async def get_optimization_artifacts(
        self, 
        strategy_name: Optional[str] = None
    ) -> List[OptimizationArtifact]:
        """Get optimization artifacts, optionally filtered by strategy."""
        artifacts = list(self.optimization_artifacts.values())
        
        if strategy_name:
            artifacts = [a for a in artifacts if a.strategy_name == strategy_name]
        
        return sorted(artifacts, key=lambda x: x.optimization_date, reverse=True)
    
    async def get_optimization_summary(self) -> OptimizationSummary:
        """Get optimization summary."""
        return self.optimization_summary
    
    async def calculate_optimization_metrics(
        self, 
        artifact: OptimizationArtifact
    ) -> OptimizationMetrics:
        """Calculate optimization metrics for an artifact."""
        # This is a simplified implementation
        # In a real implementation, you would calculate:
        # - Stability score based on parameter variance across folds
        # - Robustness score based on performance consistency
        # - Overfitting risk based on train/test performance difference
        
        # Mock metrics calculation
        metrics = OptimizationMetrics(
            optimization_score=artifact.optimization_result.best_score,
            stability_score=random.uniform(0.6, 0.9),
            robustness_score=random.uniform(0.5, 0.8),
            overfitting_risk=random.uniform(0.1, 0.6),
            cost_efficiency=random.uniform(0.7, 0.95),
            sharpe_ratio=random.uniform(0.5, 2.5),
            max_drawdown=random.uniform(0.05, 0.3),
            win_rate=random.uniform(0.4, 0.7),
            profit_factor=random.uniform(0.8, 2.0)
        )
        
        return metrics
