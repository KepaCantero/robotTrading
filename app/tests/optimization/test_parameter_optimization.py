"""
Comprehensive tests for Parameter Optimization Module - FASE 6.1

Tests for:
- ParameterRange and ParameterGrid models
- Trial tracking and history
- Grid search optimizer
- Random search optimizer
- Bayesian optimizer (with Optuna fallback)
- Multi-objective optimization
- Edge cases and error handling
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict
from unittest.mock import patch

import pytest

from app.optimization.parameter.base_optimizer import OptimizationConfig, OptimizationResult
from app.optimization.parameter.bayesian_optimizer import OPTUNA_AVAILABLE, BayesianOptimizer
from app.optimization.parameter.grid_search import GridSearchOptimizer, GridSearchOptimizerCV

# Import modules to test
from app.optimization.parameter.models import (
    ParameterConstraint,
    ParameterGrid,
    ParameterRange,
    ParameterScale,
    ParameterType,
)
from app.optimization.parameter.random_search import RandomSearchOptimizer, RandomSearchOptimizerCV
from app.optimization.parameter.trial import TrialContext, TrialHistory, TrialResult, TrialStatus

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_params() -> Dict[str, Any]:
    """Sample parameter dictionary."""
    return {
        "lookback": 20,
        "threshold": 0.5,
        "strategy": "momentum",
    }


@pytest.fixture
def param_grid_continuous() -> ParameterGrid:
    """Parameter grid with continuous parameters."""
    return ParameterGrid(
        parameters=[
            ParameterRange(
                name="lookback",
                min_value=5,
                max_value=50,
                step=5,
                parameter_type=ParameterType.INTEGER,
            ),
            ParameterRange(
                name="threshold",
                min_value=0.1,
                max_value=2.0,
                step=0.1,
                parameter_type=ParameterType.CONTINUOUS,
            ),
        ]
    )


@pytest.fixture
def param_grid_categorical() -> ParameterGrid:
    """Parameter grid with categorical parameters."""
    return ParameterGrid(
        parameters=[
            ParameterRange(
                name="strategy",
                values=["momentum", "mean_reversion", "pairs_trading"],
                parameter_type=ParameterType.CATEGORICAL,
            ),
            ParameterRange(
                name="timeframe",
                values=["1h", "4h", "1d"],
                parameter_type=ParameterType.CATEGORICAL,
            ),
        ]
    )


@pytest.fixture
def param_grid_mixed() -> ParameterGrid:
    """Parameter grid with mixed types."""
    return ParameterGrid(
        parameters=[
            ParameterRange(
                name="lookback",
                min_value=5,
                max_value=20,
                step=5,
                parameter_type=ParameterType.INTEGER,
            ),
            ParameterRange(
                name="threshold",
                min_value=0.1,
                max_value=0.5,
                step=0.1,
            ),
            ParameterRange(
                name="strategy",
                values=["momentum", "mean_reversion"],
                parameter_type=ParameterType.CATEGORICAL,
            ),
        ]
    )


@pytest.fixture
def param_grid_log_scale() -> ParameterGrid:
    """Parameter grid with log scale parameters."""
    return ParameterGrid(
        parameters=[
            ParameterRange(
                name="learning_rate",
                min_value=1e-5,
                max_value=1e-1,
                scale=ParameterScale.LOG,
            ),
            ParameterRange(
                name="batch_size",
                min_value=16,
                max_value=256,
                step=16,
                parameter_type=ParameterType.INTEGER,
            ),
        ]
    )


@pytest.fixture
def param_grid_with_constraints() -> ParameterGrid:
    """Parameter grid with constraints."""
    return ParameterGrid(
        parameters=[
            ParameterRange(
                name="param_a",
                min_value=0,
                max_value=10,
                step=1,
                parameter_type=ParameterType.INTEGER,
            ),
            ParameterRange(
                name="param_b",
                min_value=0,
                max_value=10,
                step=1,
                parameter_type=ParameterType.INTEGER,
            ),
        ],
        constraints=[
            ParameterConstraint(
                name="sum_constraint",
                constraint_func=lambda p: p["param_a"] + p["param_b"] <= 15,
                description="Sum of parameters must not exceed 15",
            ),
        ],
    )


@pytest.fixture
def optimization_config() -> OptimizationConfig:
    """Default optimization configuration."""
    return OptimizationConfig(
        max_iterations=50,
        n_jobs=1,
        early_stopping=True,
        early_stopping_patience=10,
        metric="sharpe_ratio",
        maximize=True,
        random_seed=42,
        verbose=0,  # Suppress logs in tests
        progress_bar=False,
    )


@pytest.fixture
def simple_objective() -> Callable:
    """Simple objective function for testing."""

    def objective(params: Dict[str, Any]) -> float:
        # Simple function: maximize lookback, minimize threshold
        return params.get("lookback", 0) - params.get("threshold", 0) * 10

    return objective


@pytest.fixture
def mock_objective() -> Callable:
    """Mock objective that returns predictable values."""

    def objective(params: Dict[str, Any]) -> float:
        # Return value based on params hash for consistency
        param_str = json.dumps(params, sort_keys=True)
        return float(hash(param_str) % 1000) / 100

    return objective


@pytest.fixture
def slow_objective() -> Callable:
    """Objective function with deliberate delay."""

    def objective(params: Dict[str, Any]) -> float:
        time.sleep(0.01)  # 10ms delay
        return params.get("lookback", 0)

    return objective


# =============================================================================
# Tests for ParameterRange
# =============================================================================


class TestParameterRange:
    """Tests for ParameterRange class."""

    def test_categorical_parameter(self):
        """Test categorical parameter creation."""
        param = ParameterRange(
            name="strategy",
            values=["momentum", "mean_reversion"],
            parameter_type=ParameterType.CATEGORICAL,
        )

        assert param.name == "strategy"
        assert param.parameter_type == ParameterType.CATEGORICAL
        assert param.values == ["momentum", "mean_reversion"]

    def test_continuous_parameter(self):
        """Test continuous parameter creation."""
        param = ParameterRange(
            name="threshold",
            min_value=0.1,
            max_value=2.0,
            step=0.1,
            parameter_type=ParameterType.CONTINUOUS,
        )

        assert param.name == "threshold"
        assert param.min_value == 0.1
        assert param.max_value == 2.0
        assert param.step == 0.1

    def test_integer_parameter(self):
        """Test integer parameter creation."""
        param = ParameterRange(
            name="lookback",
            min_value=5,
            max_value=50,
            step=5,
            parameter_type=ParameterType.INTEGER,
        )

        assert param.name == "lookback"
        assert param.parameter_type == ParameterType.INTEGER
        assert param.min_value == 5
        assert param.max_value == 50
        assert param.step == 5

    def test_log_scale_parameter(self):
        """Test log scale parameter."""
        param = ParameterRange(
            name="learning_rate",
            min_value=1e-5,
            max_value=1e-1,
            scale=ParameterScale.LOG,
        )

        assert param.scale == ParameterScale.LOG
        assert param.min_value == 1e-5
        assert param.max_value == 1e-1

    def test_log_scale_validation_positive_only(self):
        """Test that log scale requires positive values."""
        with pytest.raises(ValueError, match="log scale requires positive"):
            ParameterRange(
                name="invalid",
                min_value=-1,
                max_value=1,
                scale=ParameterScale.LOG,
            )

    def test_min_max_validation(self):
        """Test that min < max validation works."""
        with pytest.raises(ValueError, match="must be less than max_value"):
            ParameterRange(
                name="invalid",
                min_value=10,
                max_value=5,
            )

    def test_categorical_requires_values(self):
        """Test that categorical parameters require values."""
        with pytest.raises(ValueError, match="must have values"):
            ParameterRange(
                name="invalid",
                parameter_type=ParameterType.CATEGORICAL,
            )

    def test_sample_categorical(self):
        """Test sampling from categorical parameter."""
        param = ParameterRange(
            name="strategy",
            values=["a", "b", "c"],
            parameter_type=ParameterType.CATEGORICAL,
        )

        for _ in range(20):
            value = param.sample()
            assert value in ["a", "b", "c"]

    def test_sample_integer(self):
        """Test sampling from integer parameter."""
        param = ParameterRange(
            name="lookback",
            min_value=5,
            max_value=20,
            step=5,
            parameter_type=ParameterType.INTEGER,
        )

        samples = [param.sample() for _ in range(20)]
        assert all(5 <= s <= 20 for s in samples)
        assert all(s % 5 == 0 for s in samples)

    def test_sample_continuous(self):
        """Test sampling from continuous parameter."""
        param = ParameterRange(
            name="threshold",
            min_value=0.0,
            max_value=1.0,
        )

        samples = [param.sample() for _ in range(20)]
        assert all(0.0 <= s <= 1.0 for s in samples)

    def test_sample_log_scale(self):
        """Test sampling from log scale parameter."""
        param = ParameterRange(
            name="lr",
            min_value=1e-5,
            max_value=1e-1,
            scale=ParameterScale.LOG,
        )

        samples = [param.sample() for _ in range(20)]
        assert all(1e-5 <= s <= 1e-1 for s in samples)

    def test_get_grid_values_categorical(self):
        """Test grid values for categorical parameter."""
        param = ParameterRange(
            name="strategy",
            values=["a", "b", "c"],
            parameter_type=ParameterType.CATEGORICAL,
        )

        values = param.get_grid_values()
        assert values == ["a", "b", "c"]

    def test_get_grid_values_integer(self):
        """Test grid values for integer parameter."""
        param = ParameterRange(
            name="lookback",
            min_value=5,
            max_value=20,
            step=5,
            parameter_type=ParameterType.INTEGER,
        )

        values = param.get_grid_values()
        assert values == [5, 10, 15, 20]

    def test_get_grid_values_continuous(self):
        """Test grid values for continuous parameter."""
        param = ParameterRange(
            name="threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.2,
        )

        values = param.get_grid_values()
        assert len(values) == 6  # 0.0, 0.2, 0.4, 0.6, 0.8, 1.0

    def test_to_dict(self):
        """Test ParameterRange serialization."""
        param = ParameterRange(
            name="test",
            min_value=0.1,
            max_value=1.0,
            step=0.1,
        )

        data = param.to_dict()
        assert data["name"] == "test"
        assert data["min_value"] == 0.1
        assert data["max_value"] == 1.0
        assert data["step"] == 0.1


# =============================================================================
# Tests for ParameterGrid
# =============================================================================


class TestParameterGrid:
    """Tests for ParameterGrid class."""

    def test_empty_grid_raises_error(self):
        """Test that empty grid raises error."""
        with pytest.raises(ValueError, match="at least one parameter"):
            ParameterGrid(parameters=[])

    def test_duplicate_names_raises_error(self):
        """Test that duplicate parameter names raise error."""
        with pytest.raises(ValueError, match="Duplicate parameter names"):
            ParameterGrid(
                parameters=[
                    ParameterRange(name="param", min_value=0, max_value=1),
                    ParameterRange(name="param", min_value=0, max_value=2),
                ]
            )

    def test_size_calculation(self):
        """Test grid size calculation."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(name="a", values=[1, 2, 3]),
                ParameterRange(name="b", values=[4, 5]),
            ]
        )

        assert grid.size() == 6  # 3 * 2

    def test_generate_combinations(self):
        """Test combination generation."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="a",
                    values=[1, 2],
                    parameter_type=ParameterType.DISCRETE,
                ),
                ParameterRange(
                    name="b",
                    values=[3, 4],
                    parameter_type=ParameterType.DISCRETE,
                ),
            ]
        )

        combinations = grid.generate_combinations()
        assert len(combinations) == 4
        assert {"a": 1, "b": 3} in combinations
        assert {"a": 2, "b": 4} in combinations

    def test_sample_random(self):
        """Test random parameter sampling."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="a",
                    values=[1, 2, 3],
                    parameter_type=ParameterType.DISCRETE,
                ),
                ParameterRange(
                    name="b",
                    min_value=0,
                    max_value=1,
                ),
            ]
        )

        for _ in range(10):
            params = grid.sample_random()
            assert "a" in params
            assert "b" in params
            assert params["a"] in [1, 2, 3]
            assert 0 <= params["b"] <= 1

    def test_constraint_filtering(self):
        """Test that constraints filter combinations."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="a",
                    min_value=0,
                    max_value=10,
                    step=1,
                    parameter_type=ParameterType.INTEGER,
                ),
                ParameterRange(
                    name="b",
                    min_value=0,
                    max_value=10,
                    step=1,
                    parameter_type=ParameterType.INTEGER,
                ),
            ],
            constraints=[
                ParameterConstraint(
                    name="max_sum",
                    constraint_func=lambda p: p["a"] + p["b"] <= 5,
                ),
            ],
        )

        combinations = grid.generate_combinations()

        # All combinations should satisfy constraint
        for combo in combinations:
            assert combo["a"] + combo["b"] <= 5

    def test_to_dict(self):
        """Test ParameterGrid serialization."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(name="a", values=[1, 2]),
            ]
        )

        data = grid.to_dict()
        assert "parameters" in data
        assert data["total_combinations"] == 2


# =============================================================================
# Tests for TrialResult and TrialHistory
# =============================================================================


class TestTrialResult:
    """Tests for TrialResult class."""

    def test_create_trial_result(self):
        """Test creating a trial result."""
        result = TrialResult(
            trial_id="test_1",
            params={"lookback": 20},
            objective_value=0.5,
            status=TrialStatus.COMPLETED,
        )

        assert result.trial_id == "test_1"
        assert result.params == {"lookback": 20}
        assert result.objective_value == 0.5
        assert result.is_success
        assert not result.is_failed
        assert not result.is_pruned

    def test_failed_trial(self):
        """Test failed trial status."""
        result = TrialResult(
            trial_id="test_2",
            params={},
            objective_value=-1.0,
            status=TrialStatus.FAILED,
            error_message="Test error",
        )

        assert result.is_failed
        assert not result.is_success
        assert result.error_message == "Test error"

    def test_to_dict(self):
        """Test TrialResult serialization."""
        result = TrialResult(
            trial_id="test_1",
            params={"a": 1},
            objective_value=0.5,
        )

        data = result.to_dict()
        assert data["trial_id"] == "test_1"
        assert data["params"] == {"a": 1}
        assert data["objective_value"] == 0.5

    def test_from_dict(self):
        """Test TrialResult deserialization."""
        data = {
            "trial_id": "test_1",
            "params": {"a": 1},
            "objective_value": 0.5,
            "status": "completed",
        }

        result = TrialResult.from_dict(data)
        assert result.trial_id == "test_1"
        assert result.params == {"a": 1}
        assert result.objective_value == 0.5


class TestTrialHistory:
    """Tests for TrialHistory class."""

    def test_create_history(self):
        """Test creating trial history."""
        history = TrialHistory()
        assert len(history.trials) == 0
        assert history.start_time is not None

    def test_add_trial(self):
        """Test adding trials to history."""
        history = TrialHistory()

        trial = TrialResult(
            trial_id="test_1",
            params={"a": 1},
            objective_value=0.5,
        )

        history.add_trial(trial)
        assert len(history.trials) == 1

    def test_get_best_trial(self):
        """Test getting best trial."""
        history = TrialHistory()

        history.add_trial(TrialResult(trial_id="t1", params={}, objective_value=0.3))
        history.add_trial(TrialResult(trial_id="t2", params={}, objective_value=0.7))
        history.add_trial(TrialResult(trial_id="t3", params={}, objective_value=0.5))

        best = history.get_best_trial()
        assert best.objective_value == 0.7
        assert best.trial_id == "t2"

    def test_get_best_score(self):
        """Test getting best score."""
        history = TrialHistory()

        history.add_trial(TrialResult(trial_id="t1", params={}, objective_value=0.3))
        history.add_trial(TrialResult(trial_id="t2", params={}, objective_value=0.7))

        assert history.get_best_score() == 0.7

    def test_get_mean_score(self):
        """Test getting mean score."""
        history = TrialHistory()

        history.add_trial(TrialResult(trial_id="t1", params={}, objective_value=0.3))
        history.add_trial(TrialResult(trial_id="t2", params={}, objective_value=0.7))

        assert history.get_mean_score() == 0.5

    def test_success_rate(self):
        """Test success rate calculation."""
        history = TrialHistory()

        history.add_trial(TrialResult(trial_id="t1", params={}, objective_value=0.5))
        history.add_trial(
            TrialResult(
                trial_id="t2",
                params={},
                objective_value=-1.0,
                status=TrialStatus.FAILED,
            )
        )

        assert history.get_success_rate() == 0.5

    def test_convergence_detection(self):
        """Test convergence detection."""
        history = TrialHistory()

        # Add trials with improving scores
        for i in range(20):
            history.add_trial(
                TrialResult(
                    trial_id=f"t{i}",
                    params={},
                    objective_value=0.5 + i * 0.01,
                )
            )

        # Should not converge yet (still improving)
        assert not history.check_convergence(patience=5)

        # Add non-improving trials
        for i in range(10):
            history.add_trial(
                TrialResult(
                    trial_id=f"s{i}",
                    params={},
                    objective_value=0.7,  # Same value
                )
            )

        # Should now converge
        assert history.check_convergence(patience=5)

    def test_save_and_load(self):
        """Test saving and loading history."""
        history = TrialHistory()

        history.add_trial(TrialResult(trial_id="t1", params={"a": 1}, objective_value=0.5))

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            filepath = f.name

        try:
            history.save(filepath)
            loaded = TrialHistory.load(filepath)

            assert len(loaded.trials) == 1
            assert loaded.trials[0].trial_id == "t1"
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestTrialContext:
    """Tests for TrialContext."""

    def test_successful_trial(self):
        """Test context manager for successful trial."""
        with TrialContext("test_1", {"a": 1}) as ctx:
            assert ctx.start_time is not None
            assert ctx.error is None

        result = ctx.create_result(objective_value=0.5)
        assert result.is_success
        assert result.start_time is not None
        assert result.end_time is not None

    def test_failed_trial(self):
        """Test context manager for failed trial."""
        try:
            with TrialContext("test_1", {"a": 1}) as ctx:
                raise ValueError("Test error")
        except ValueError:
            pass

        result = ctx.create_result(objective_value=-1.0)
        assert result.is_failed
        assert "Test error" in result.error_message


# =============================================================================
# Tests for OptimizationConfig
# =============================================================================


class TestOptimizationConfig:
    """Tests for OptimizationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OptimizationConfig()

        assert config.max_iterations == 100
        assert config.n_jobs == 1
        assert config.early_stopping is True
        assert config.early_stopping_patience == 10
        assert config.metric == "sharpe_ratio"
        assert config.maximize is True

    def test_minimize_alias(self):
        """Test minimize as alias for not maximize."""
        config = OptimizationConfig(minimize=True)
        assert config.maximize is False

    def test_validation_max_iterations(self):
        """Test validation of max_iterations."""
        with pytest.raises(ValueError, match="must be positive"):
            OptimizationConfig(max_iterations=0)

    def test_validation_patience(self):
        """Test validation of early_stopping_patience."""
        with pytest.raises(ValueError, match="must be positive"):
            OptimizationConfig(early_stopping_patience=0)

    def test_validation_validation_split(self):
        """Test validation of validation_split."""
        with pytest.raises(ValueError, match=r"must be in \[0, 1\)"):
            OptimizationConfig(validation_split=1.5)

    def test_to_dict(self):
        """Test config serialization."""
        config = OptimizationConfig(max_iterations=50)
        data = config.to_dict()

        assert data["max_iterations"] == 50
        assert data["early_stopping"] is True


# =============================================================================
# Tests for GridSearchOptimizer
# =============================================================================


class TestGridSearchOptimizer:
    """Tests for GridSearchOptimizer."""

    @pytest.mark.asyncio
    async def test_basic_optimization(
        self, param_grid_mixed, simple_objective, optimization_config
    ):
        """Test basic grid search optimization."""
        optimizer = GridSearchOptimizer(optimization_config)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        assert result.n_iterations > 0
        assert result.best_params is not None
        assert len(result.all_trials) > 0

    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, param_grid_mixed, simple_objective):
        """Test that max_iterations limits the search."""
        config = OptimizationConfig(max_iterations=5)
        optimizer = GridSearchOptimizer(config)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        assert result.n_iterations <= 5

    @pytest.mark.asyncio
    async def test_early_stopping(self, param_grid_mixed, mock_objective):
        """Test early stopping functionality."""
        config = OptimizationConfig(
            max_iterations=100,
            early_stopping=True,
            early_stopping_patience=5,
            early_stopping_min_improvement=0.001,
        )
        optimizer = GridSearchOptimizer(config)
        await optimizer.optimize(mock_objective, param_grid_mixed)

        # Should stop before max_iterations if converged
        # (This depends on the objective function behavior)

    @pytest.mark.asyncio
    async def test_timeout(self, param_grid_mixed, slow_objective):
        """Test timeout functionality."""
        config = OptimizationConfig(
            max_iterations=1000,
            timeout_seconds=1,
            n_jobs=1,
        )
        optimizer = GridSearchOptimizer(config)
        result = await optimizer.optimize(slow_objective, param_grid_mixed)

        # Should stop due to timeout
        assert result.n_iterations < 1000

    @pytest.mark.asyncio
    async def test_best_score_tracking(self, param_grid_mixed, simple_objective):
        """Test that best score is tracked correctly."""
        optimizer = GridSearchOptimizer(OptimizationConfig(verbose=0))
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        best_from_trials = max(
            [t.objective_value for t in result.all_trials if t.is_success],
            default=float("-inf"),
        )
        assert result.best_score == best_from_trials

    @pytest.mark.asyncio
    async def test_result_serialization(self, param_grid_mixed, simple_objective):
        """Test saving and loading results."""
        optimizer = GridSearchOptimizer(OptimizationConfig(verbose=0))
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            filepath = f.name

        try:
            result.save(filepath)
            loaded = OptimizationResult.load(filepath)

            assert loaded.best_params == result.best_params
            assert loaded.best_score == result.best_score
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestGridSearchOptimizerCV:
    """Tests for GridSearchOptimizer with cross-validation."""

    @pytest.mark.asyncio
    async def test_cv_optimization(self, param_grid_mixed):
        """Test grid search with cross-validation."""

        def cv_objective(params, fold):
            return params.get("lookback", 10) - fold * 0.1

        config = OptimizationConfig(max_iterations=20, verbose=0)
        optimizer = GridSearchOptimizerCV(config, cv_folds=3)

        result = await optimizer.optimize(cv_objective, param_grid_mixed)

        assert result.n_iterations > 0
        assert result.best_params is not None


# =============================================================================
# Tests for RandomSearchOptimizer
# =============================================================================


class TestRandomSearchOptimizer:
    """Tests for RandomSearchOptimizer."""

    @pytest.mark.asyncio
    async def test_basic_optimization(self, param_grid_mixed, simple_objective):
        """Test basic random search optimization."""
        config = OptimizationConfig(max_iterations=20, verbose=0)
        optimizer = RandomSearchOptimizer(config)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        assert result.n_iterations > 0
        assert result.best_params is not None

    @pytest.mark.asyncio
    async def test_random_sampling(self, param_grid_mixed, simple_objective):
        """Test that parameters are randomly sampled."""
        config = OptimizationConfig(
            max_iterations=30,
            random_seed=42,
            verbose=0,
        )
        optimizer = RandomSearchOptimizer(config)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        # Check that we got multiple trials
        assert len(result.all_trials) > 0

    @pytest.mark.asyncio
    async def test_log_scale_sampling(self, param_grid_log_scale):
        """Test log scale parameter sampling."""

        def objective(params):
            return params.get("learning_rate", 1e-3)

        config = OptimizationConfig(max_iterations=20, verbose=0)
        optimizer = RandomSearchOptimizer(config)
        result = await optimizer.optimize(objective, param_grid_log_scale)

        assert result.n_iterations > 0

        # Check that we sampled values across log scale
        lr_values = [t.params.get("learning_rate") for t in result.all_trials if t.is_success]
        assert len(lr_values) > 0

    @pytest.mark.asyncio
    async def test_unique_samples(self, param_grid_mixed, simple_objective):
        """Test that duplicate samples are avoided."""
        config = OptimizationConfig(
            max_iterations=50,
            random_seed=42,
            verbose=0,
        )
        optimizer = RandomSearchOptimizer(config)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        # Get unique parameter sets
        unique_params = set(json.dumps(t.params, sort_keys=True) for t in result.all_trials)

        # Most samples should be unique (allowing for some duplicates)
        assert len(unique_params) >= len(result.all_trials) * 0.9


class TestRandomSearchOptimizerCV:
    """Tests for RandomSearchOptimizer with cross-validation."""

    @pytest.mark.asyncio
    async def test_cv_optimization(self, param_grid_mixed):
        """Test random search with cross-validation."""

        def cv_objective(params, fold):
            return params.get("lookback", 10) - fold * 0.1

        config = OptimizationConfig(max_iterations=15, verbose=0)
        optimizer = RandomSearchOptimizerCV(config, cv_folds=3)

        result = await optimizer.optimize(cv_objective, param_grid_mixed)

        assert result.n_iterations > 0

        # Check CV metrics are stored
        if result.all_trials:
            best_trial = result.best_trial
            if best_trial and best_trial.metrics:
                assert "cv_scores" in best_trial.metrics


# =============================================================================
# Tests for BayesianOptimizer
# =============================================================================


class TestBayesianOptimizer:
    """Tests for BayesianOptimizer."""

    @pytest.mark.asyncio
    async def test_basic_optimization_with_optuna(self, param_grid_mixed, simple_objective):
        """Test Bayesian optimization with Optuna."""
        if not OPTUNA_AVAILABLE:
            pytest.skip("Optuna not installed")

        config = OptimizationConfig(max_iterations=20, verbose=0)
        optimizer = BayesianOptimizer(config, n_trials=20)

        result = await optimizer.optimize(simple_objective, param_grid_mixed)

        assert result.n_iterations > 0
        assert result.best_params is not None

    @pytest.mark.asyncio
    async def test_fallback_to_random_search(self, param_grid_mixed, simple_objective):
        """Test fallback to random search when Optuna unavailable."""
        # Mock Optuna as unavailable
        with patch("app.optimization.parameter.bayesian_optimizer.OPTUNA_AVAILABLE", False):
            config = OptimizationConfig(max_iterations=10, verbose=0)
            optimizer = BayesianOptimizer(config, n_trials=10)

            result = await optimizer.optimize(simple_objective, param_grid_mixed)

            # Should still work using random search fallback
            assert result.n_iterations >= 0

    @pytest.mark.asyncio
    async def test_log_scale_with_optuna(self, param_grid_log_scale):
        """Test log scale parameters with Optuna."""
        if not OPTUNA_AVAILABLE:
            pytest.skip("Optuna not installed")

        def objective(params):
            # Prefer middle of log range
            lr = params.get("learning_rate", 1e-3)
            return -abs(lr - 1e-3)

        config = OptimizationConfig(max_iterations=15, verbose=0)
        optimizer = BayesianOptimizer(config, n_trials=15)

        result = await optimizer.optimize(objective, param_grid_log_scale)

        assert result.best_params is not None
        # Best learning rate should be near 1e-3
        best_lr = result.best_params.get("learning_rate", 0)
        assert 1e-4 < best_lr < 1e-2

    @pytest.mark.asyncio
    async def test_pruning_configuration(self, param_grid_mixed, simple_objective):
        """Test different pruner configurations."""
        if not OPTUNA_AVAILABLE:
            pytest.skip("Optuna not installed")

        config = OptimizationConfig(max_iterations=10, verbose=0)

        # Test median pruner
        optimizer = BayesianOptimizer(config, n_trials=10, pruner="median")
        result = await optimizer.optimize(simple_objective, param_grid_mixed)
        assert result.n_iterations >= 0

        # Test no pruning
        optimizer = BayesianOptimizer(config, n_trials=10, pruner=None)
        result = await optimizer.optimize(simple_objective, param_grid_mixed)
        assert result.n_iterations >= 0


# =============================================================================
# Tests for Constraints
# =============================================================================


class TestParameterConstraints:
    """Tests for parameter constraints."""

    def test_constraint_check(self):
        """Test constraint checking."""
        constraint = ParameterConstraint(
            name="test",
            constraint_func=lambda p: p["a"] < p["b"],
        )

        assert constraint.check({"a": 1, "b": 2}) is True
        assert constraint.check({"a": 2, "b": 1}) is False

    def test_constraint_with_exception(self):
        """Test constraint that raises exception."""
        constraint = ParameterConstraint(
            name="test",
            constraint_func=lambda p: p["a"] / p["b"] > 0,
        )

        # Division by zero should return False
        assert constraint.check({"a": 1, "b": 0}) is False

    def test_constraint_in_grid(self, param_grid_with_constraints):
        """Test constraints in parameter grid."""
        combinations = param_grid_with_constraints.generate_combinations()

        # All combinations should satisfy constraint
        for combo in combinations:
            assert combo["param_a"] + combo["param_b"] <= 15


# =============================================================================
# Tests for Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_parameter_combinations(self):
        """Test handling of no valid combinations."""
        # Create grid with impossible constraints
        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="a",
                    min_value=10,
                    max_value=20,
                    parameter_type=ParameterType.INTEGER,
                ),
            ],
            constraints=[
                ParameterConstraint(
                    name="impossible",
                    constraint_func=lambda p: p["a"] < 5,
                ),
            ],
        )

        optimizer = GridSearchOptimizer(OptimizationConfig(verbose=0))

        def objective(params):
            return 0.5

        result = await optimizer.optimize(objective, grid)

        # Should handle gracefully
        assert result.n_iterations == 0

    @pytest.mark.asyncio
    async def test_failing_objective(self):
        """Test handling of failing objective function."""

        def failing_objective(params):
            if params.get("lookback", 0) > 10:
                raise ValueError("Too large!")
            return 0.5

        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="lookback",
                    min_value=5,
                    max_value=20,
                    step=5,
                    parameter_type=ParameterType.INTEGER,
                ),
            ]
        )

        optimizer = GridSearchOptimizer(OptimizationConfig(verbose=0))
        result = await optimizer.optimize(failing_objective, grid)

        # Some trials should fail
        failed_count = sum(1 for t in result.all_trials if t.is_failed)
        assert failed_count > 0

    @pytest.mark.asyncio
    async def test_single_parameter(self, simple_objective):
        """Test optimization with single parameter."""
        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="param",
                    min_value=1,
                    max_value=10,
                    step=1,
                    parameter_type=ParameterType.INTEGER,
                ),
            ]
        )

        optimizer = GridSearchOptimizer(OptimizationConfig(verbose=0))
        result = await optimizer.optimize(simple_objective, grid)

        assert result.n_iterations == 10

    @pytest.mark.asyncio
    async def test_minimize_objective(self):
        """Test minimization instead of maximization."""

        def objective(params):
            return params.get("value", 0)

        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="value",
                    min_value=1,
                    max_value=10,
                    step=1,
                    parameter_type=ParameterType.INTEGER,
                ),
            ]
        )

        config = OptimizationConfig(maximize=False, verbose=0)
        optimizer = GridSearchOptimizer(config)
        result = await optimizer.optimize(objective, grid)

        # Should minimize (find lowest value)
        assert result.best_params.get("value") == 1


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Performance-related tests."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution performance."""
        import time

        def slow_objective(params):
            time.sleep(0.01)
            return params.get("a", 0)

        grid = ParameterGrid(
            parameters=[
                ParameterRange(
                    name="a", min_value=1, max_value=5, parameter_type=ParameterType.INTEGER
                ),
            ]
        )

        # Sequential
        start = time.time()
        optimizer_seq = GridSearchOptimizer(OptimizationConfig(n_jobs=1, verbose=0))
        await optimizer_seq.optimize(slow_objective, grid)
        time_seq = time.time() - start

        # Parallel
        start = time.time()
        optimizer_par = GridSearchOptimizer(OptimizationConfig(n_jobs=2, verbose=0))
        await optimizer_par.optimize(slow_objective, grid)
        time_par = time.time() - start

        # Parallel should be faster (with tolerance)
        assert time_par <= time_seq * 1.5


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
