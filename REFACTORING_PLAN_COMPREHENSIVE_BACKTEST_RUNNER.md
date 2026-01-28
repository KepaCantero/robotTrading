# Clean Architecture Refactoring Plan: Comprehensive Backtest Runner

**Project:** AlgoTrading System
**File:** `/app/backtesting/comprehensive_backtest_runner.py`
**Current Size:** 3,968 lines
**Target Size:** Split into 5 modules (~200-800 lines each)
**Date:** 2026-01-28
**Goal:** 80% -> 95% Clean Architecture compliance

---

## Executive Summary

The `comprehensive_backtest_runner.py` file has grown to 3,968 lines, violating Single Responsibility Principle and making maintenance difficult. This refactoring plan splits the monolithic class into focused modules following Clean Architecture principles.

### Current Problems
1. **God Class:** Single class handles 10+ different backtest types
2. **Mixed Concerns:** Execution, validation, aggregation, and configuration in one file
3. **High Cyclomatic Complexity:** Multiple nested conditionals
4. **Poor Testability:** Difficult to unit test individual components
5. **Code Duplication:** Similar patterns repeated across backtest methods

### Refactoring Goals
1. **Separation of Concerns:** Each module has a single, well-defined responsibility
2. **Improved Testability:** Components can be tested in isolation
3. **Better Maintainability:** Changes are localized to specific modules
4. **Backward Compatibility:** Existing API remains functional
5. **Clean Architecture:** Clear layer boundaries and dependency flow

---

## Current File Structure Analysis

### Class: `ComprehensiveBacktestRunner`
**Total Lines:** 3,968
**Total Methods:** 47

### Method Categories

#### 1. Core Orchestration (5 methods, ~200 lines)
- `__init__` - Initialization
- `_integrate_meta_analyzer` - Meta analyzer integration
- `_load_market_data` - Data loading
- `run_all_backtests` - Main orchestrator
- `run_specific_backtests` - Specific test execution

#### 2. Backtest Execution Logic (10 methods, ~1,800 lines)
- `run_baseline_backtest` - Baseline execution
- `run_learning_engines_backtest` - Learning engines testing
- `_test_learning_engine` - Single engine test
- `run_monte_carlo_backtest` - Monte Carlo simulation
- `run_walk_forward_backtest` - Walk-forward validation
- `run_transformer_optimization_backtest` - Transformer optimization
- `run_ablation_backtest` - Ablation testing
- `run_grid_search_backtest` - Grid search optimization
- `run_out_of_sample_backtest` - Out-of-sample validation
- `run_multi_strategy_backtest` - Multi-strategy testing
- `run_regime_test_backtest` - Regime-based testing

#### 3. Configuration & Strategy (5 methods, ~300 lines)
- `_create_strategy_config` - Strategy configuration creation
- `_create_strategy_config_for_type` - Type-specific config
- `_get_filter_config` - Filter configuration
- `_extract_thresholds` - Threshold extraction
- `_get_strategy_name` - Strategy naming

#### 4. Metrics & Aggregation (4 methods, ~200 lines)
- `_calculate_consistent_metrics` - Metrics calculation
- `_format_multi_strategy_results` - Multi-strategy formatting
- `_save_results` - Results persistence
- `get_results` - Results retrieval
- `get_memory_stats` - Memory statistics

#### 5. Validation & Analysis (8 methods, ~600 lines)
- `_evaluate_param_set_static` - Parameter evaluation
- `optimize_with_validation` - Optimization with validation
- `_backtest_with_quotes` - Quote-based backtesting
- `_extract_transformer_predictions` - Transformer prediction extraction
- `_extract_transformer_feature_importance` - Feature importance
- `_apply_meta_labeling` - Meta-labeling application
- `_detect_simple_regimes` - Regime detection
- `_get_regime_name_mapping` - Regime naming
- `_analyze_regime_transitions` - Transition analysis

#### 6. Data Generation & Helpers (3 methods, ~200 lines)
- `_create_monte_carlo_quotes` - Monte Carlo quote generation
- `_create_ablation_config` - Ablation configuration
- `_create_input_profile_from_config` - Profile creation

#### 7. Audit & Persistence (3 methods, ~150 lines)
- `_save_test_audit_and_weights` - Audit trail saving
- `_optimize_transformer_parameters` - Transformer optimization
- `_run_backtest_with_quotes` - Quote-based execution

---

## Proposed New Structure

### Module 1: `comprehensive_backtest_runner.py` (Main Orchestrator)
**Target Size:** ~200 lines
**Responsibility:** High-level orchestration and coordination

```python
"""
Comprehensive Backtest Runner - Main Orchestrator
Simplified orchestrator that delegates to specialized modules.
"""

class ComprehensiveBacktestRunner:
    """
    Main orchestrator for comprehensive backtesting suite.

    Delegates specific backtest types to specialized executors.
    Maintains backward compatibility with existing API.
    """

    def __init__(self, config_path: str):
        """Initialize runner with configuration."""

    def run_all_backtests(self) -> List[Dict[str, Any]]:
        """Execute all configured backtests."""

    def run_specific_backtests(self, backtest_names: List[str]) -> List[Dict[str, Any]]:
        """Execute specific backtests by name."""

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all backtest results."""

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
```

**Dependencies:**
- `BacktestConfigLoader` (from core)
- `BacktestExecutorFactory` (from execution module)
- `BacktestResultAggregator` (from aggregation module)
- `BacktestValidator` (from validation module)

---

### Module 2: `backtest_execution.py` (Execution Logic)
**Target Size:** ~1,200 lines
**Responsibility:** Execute different types of backtests

```python
"""
Backtest Execution Module
Contains specialized executors for each backtest type.
"""

class BacktestExecutionEngine:
    """
    Executes various types of backtests.

    Each backtest type has its own specialized execution method
    that follows consistent patterns but handles type-specific logic.
    """

    def __init__(self, config: BacktestConfig, data_loader: DataLoader):
        """Initialize execution engine."""

    def execute_baseline(self, quotes: List, strategy) -> Dict[str, Any]:
        """Execute baseline backtest."""

    def execute_learning_engines(self, quotes: List) -> List[Dict[str, Any]]:
        """Execute learning engines backtests."""

    def execute_monte_carlo(self, quotes: List, num_simulations: int) -> List[Dict[str, Any]]:
        """Execute Monte Carlo simulations."""

    def execute_walk_forward(
        self,
        quotes: List,
        train_pct: float,
        test_pct: float
    ) -> Dict[str, Any]:
        """Execute walk-forward validation."""

    def execute_transformer_optimization(
        self,
        quotes: List
    ) -> Dict[str, Any]:
        """Execute Transformer optimization."""

    def execute_ablation(self, quotes: List, filters: List[str]) -> List[Dict[str, Any]]:
        """Execute ablation testing."""

    def execute_grid_search(
        self,
        quotes: List,
        param_grid: Dict[str, List]
    ) -> Dict[str, Any]:
        """Execute grid search optimization."""

    def execute_out_of_sample(
        self,
        quotes: List,
        train_ratio: float
    ) -> Dict[str, Any]:
        """Execute out-of-sample validation."""

    def execute_multi_strategy(
        self,
        quotes: List,
        strategies: List[str]
    ) -> Dict[str, Any]:
        """Execute multi-strategy backtest."""

    def execute_regime_test(
        self,
        quotes: List,
        detection_method: str
    ) -> Dict[str, Any]:
        """Execute regime-based backtest."""


class LearningEngineTester:
    """Handles learning engine specific testing logic."""

    def test_engine(self, engine_type: str, quotes: List) -> Optional[Dict[str, Any]]:
        """Test a single learning engine."""


class RegimeAnalyzer:
    """Handles regime detection and analysis."""

    def detect_regimes(
        self,
        prices: np.ndarray,
        method: str,
        n_regimes: int
    ) -> np.ndarray:
        """Detect market regimes."""

    def analyze_transitions(
        self,
        regime_labels: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze regime transitions."""
```

**Dependencies:**
- `SimpleBacktestExecutor` (from core)
- `ProcessPoolBacktestExecutor` (from core)
- `ModularMomentumStrategy` (from strategies)
- `train_with_retry` (from error_handling)

---

### Module 3: `backtest_aggregation.py` (Result Aggregation)
**Target Size:** ~400 lines
**Responsibility:** Aggregate and format backtest results

```python
"""
Backtest Result Aggregation Module
Handles result aggregation, formatting, and persistence.
"""

class BacktestResultAggregator:
    """
    Aggregates and formats backtest results.

    Provides consistent result formatting across all backtest types
    and handles persistence to various formats.
    """

    def __init__(self, output_dir: Path):
        """Initialize aggregator."""

    def aggregate_baseline_result(
        self,
        result: BacktestResult,
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """Aggregate baseline backtest result."""

    def aggregate_learning_engine_result(
        self,
        result: BacktestResult,
        engine_type: str,
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """Aggregate learning engine result."""

    def aggregate_monte_carlo_results(
        self,
        results: List[BacktestResult]
    ) -> List[Dict[str, Any]]:
        """Aggregate Monte Carlo simulation results."""

    def aggregate_walk_forward_results(
        self,
        window_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate walk-forward window results."""

    def aggregate_ablation_results(
        self,
        baseline: Dict[str, Any],
        ablation_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Aggregate ablation test results."""

    def aggregate_grid_search_results(
        self,
        param_results: List[Dict[str, Any]],
        best_params: Dict[str, Any],
        test_result: BacktestResult
    ) -> Dict[str, Any]:
        """Aggregate grid search results."""

    def aggregate_regime_results(
        self,
        regime_results: List[Dict[str, Any]],
        transition_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate regime test results."""

    def calculate_consistent_metrics(
        self,
        result: BacktestResult,
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """Calculate consistently formatted metrics."""

    def format_multi_strategy_results(
        self,
        consolidated_results: Dict,
        strategy_mapping,
        profile
    ) -> List[Dict[str, Any]]:
        """Format multi-strategy backtest results."""

    def save_results(
        self,
        results: List[Dict[str, Any]],
        formats: List[str]
    ) -> None:
        """Save results to specified formats."""

    def save_audit_and_weights(
        self,
        result: Dict[str, Any],
        test_type: str,
        strategy
    ) -> None:
        """Save audit trail and model weights."""
```

**Dependencies:**
- `pandas` (for CSV export)
- `json` (for JSON export)
- `Path` (for file paths)

---

### Module 4: `backtest_validation.py` (Validation Logic)
**Target Size:** ~500 lines
**Responsibility:** Validate backtest configurations and results

```python
"""
Backtest Validation Module
Handles validation of configurations, parameters, and results.
"""

class BacktestValidator:
    """
    Validates backtest configurations and results.

    Ensures data integrity, statistical validity, and
    prevents common backtesting pitfalls.
    """

    def validate_configuration(
        self,
        config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate backtest configuration."""

    def validate_data_sufficiency(
        self,
        quotes: List,
        test_type: str
    ) -> Tuple[bool, str]:
        """Validate sufficient data for test type."""

    def validate_stationarity(
        self,
        returns: pd.Series
    ) -> Dict[str, Any]:
        """Validate time-series stationarity (ADF test)."""

    def validate_out_of_sample_performance(
        self,
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
        confidence: float = 0.95
    ) -> bool:
        """Validate out-of-sample performance is acceptable."""

    def evaluate_parameter_set(
        self,
        params: Dict[str, Any],
        train_quotes: List,
        val_quotes: List,
        config_path: str
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single parameter set (for grid search)."""

    def optimize_with_validation(
        self,
        strategy,
        quotes: List,
        param_bounds: Dict[str, Tuple[float, float]],
        n_iterations: int
    ) -> Dict[str, float]:
        """Optimize parameters with validation guardrails."""


class TransformerFeatureAnalyzer:
    """Analyzes Transformer model features and predictions."""

    def extract_predictions(
        self,
        strategy,
        quotes: List
    ) -> np.ndarray:
        """Extract Transformer predictions."""

    def extract_feature_importance(
        self,
        strategy
    ) -> Dict[str, float]:
        """Extract feature importance from Transformer."""

    def apply_meta_labeling(
        self,
        baseline_predictions: np.ndarray,
        optimized_predictions: np.ndarray,
        quotes: List
    ) -> Dict[str, float]:
        """Apply meta-labeling (Lopez de Prado)."""


class RegimeDetector:
    """Detects and analyzes market regimes."""

    def detect_simple_regimes(
        self,
        returns: np.ndarray
    ) -> np.ndarray:
        """Simple regime detection based on returns/volatility."""

    def get_regime_name_mapping(
        self,
        regime_labels: np.ndarray,
        returns: pd.Series
    ) -> Dict[int, str]:
        """Map regime indices to descriptive names."""

    def analyze_regime_transitions(
        self,
        regime_labels: np.ndarray,
        regime_names: Dict[int, str]
    ) -> Dict[str, Any]:
        """Analyze regime transition matrix and durations."""
```

**Dependencies:**
- `statsmodels.tsa.stattools.adfuller` (for ADF test)
- `numpy` (for numerical operations)
- `pandas` (for time series)

---

### Module 5: `backtest_config.py` (Configuration Classes)
**Target Size:** ~300 lines
**Responsibility:** Configuration creation and management

```python
"""
Backtest Configuration Module
Handles configuration creation for different backtest types.
"""

class BacktestConfigFactory:
    """
    Factory for creating backtest configurations.

    Centralizes configuration logic and ensures consistency
    across different backtest types.
    """

    def __init__(self, raw_config: Dict[str, Any]):
        """Initialize factory with raw YAML config."""

    def create_strategy_config(self) -> Dict[str, Any]:
        """Create base strategy configuration."""

    def create_strategy_config_for_type(
        self,
        strategy_name: str,
        strategy_mapping
    ) -> Dict[str, Any]:
        """Create strategy config for specific strategy type."""

    def create_ablation_config(
        self,
        disabled_filter: str
    ) -> Dict[str, Any]:
        """Create config with specific filter disabled."""

    def create_input_profile_from_config(self):
        """Create input profile from configuration."""

    def get_filter_config(self) -> Dict[str, Any]:
        """Get filter configuration."""

    def extract_thresholds(
        self,
        strategy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract thresholds from strategy config."""

    def get_strategy_name(self, strategy) -> str:
        """Get strategy name for logging/reporting."""

    def create_backtest_config(self) -> BacktestConfig:
        """Create BacktestConfig object from YAML config."""

    def get_monte_carlo_config(self) -> Dict[str, Any]:
        """Get Monte Carlo specific configuration."""

    def get_walk_forward_config(self) -> Dict[str, Any]:
        """Get walk-forward specific configuration."""

    def get_grid_search_config(self) -> Dict[str, Any]:
        """Get grid search specific configuration."""

    def get_regime_test_config(self) -> Dict[str, Any]:
        """Get regime test specific configuration."""


class MonteCarloDataGenerator:
    """Generates realistic Monte Carlo simulation data."""

    def create_monte_carlo_quotes(
        self,
        base_quotes: List,
        volatility_multiplier: float
    ) -> List:
        """Create Monte Carlo quotes with realistic volatility."""


class ParameterGridGenerator:
    """Generates parameter grids for optimization."""

    def generate_parameter_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all parameter combinations."""

    def create_default_param_grid(self) -> Dict[str, List[Any]]:
        """Create default parameter grid."""
```

**Dependencies:**
- `BacktestConfig` (from models)
- `ModularMomentumStrategy` (from strategies)
- `RealisticDataGenerator` (from backtesting)

---

## Interface Definitions

### Interface: IBacktestExecutor
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IBacktestExecutor(ABC):
    """Interface for backtest executors."""

    @abstractmethod
    def execute(
        self,
        quotes: List,
        strategy,
        strategy_name: str
    ) -> BacktestResult:
        """Execute backtest and return result."""
```

### Interface: IResultAggregator
```python
class IResultAggregator(ABC):
    """Interface for result aggregators."""

    @abstractmethod
    def aggregate(
        self,
        result: BacktestResult,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate backtest result into standardized format."""
```

### Interface: IBacktestValidator
```python
class IBacktestValidator(ABC):
    """Interface for backtest validators."""

    @abstractmethod
    def validate(
        self,
        data: Any,
        config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate data/configuration. Returns (is_valid, errors)."""
```

---

## Code Migration Plan

### Phase 1: Create New Module Structure (No Changes to Original)
1. Create `backtest_execution.py` with class stubs
2. Create `backtest_aggregation.py` with class stubs
3. Create `backtest_validation.py` with class stubs
4. Create `backtest_config.py` with class stubs
5. Create `comprehensive_backtest_runner_v2.py` with new orchestrator

### Phase 2: Extract Configuration Logic
1. Move configuration methods to `backtest_config.py`
2. Update imports in original file
3. Test configuration creation
4. Commit: "Extract configuration logic"

### Phase 3: Extract Validation Logic
1. Move validation methods to `backtest_validation.py`
2. Update imports in original file
3. Run existing tests
4. Commit: "Extract validation logic"

### Phase 4: Extract Aggregation Logic
1. Move aggregation methods to `backtest_aggregation.py`
2. Update imports in original file
3. Run existing tests
4. Commit: "Extract aggregation logic"

### Phase 5: Extract Execution Logic
1. Move execution methods to `backtest_execution.py`
2. Update imports in original file
3. Run existing tests
4. Commit: "Extract execution logic"

### Phase 6: Create New Orchestrator
1. Implement `comprehensive_backtest_runner_v2.py`
2. Add backward compatibility wrapper
3. Run all tests
4. Commit: "Create new orchestrator"

### Phase 7: Update Imports & Deprecate Old File
1. Update all imports across codebase
2. Add deprecation warnings to old file
3. Run comprehensive test suite
4. Commit: "Update imports and deprecate old file"

### Phase 8: Remove Old File
1. Verify all tests pass
2. Remove old `comprehensive_backtest_runner.py`
3. Rename `v2` to original name
4. Final commit: "Complete refactoring"

---

## Dependency Graph

```
comprehensive_backtest_runner.py (Orchestrator)
    |
    +-- backtest_execution.py (Execution)
    |       |
    |       +-- backtest_config.py (Configuration)
    |       +-- core.executor (Executor Factory)
    |       +-- core.error_handling (Error Handling)
    |
    +-- backtest_aggregation.py (Aggregation)
    |       |
    |       +-- backtest_config.py (Configuration)
    |
    +-- backtest_validation.py (Validation)
    |       |
    |       +-- backtest_config.py (Configuration)
    |
    +-- backtest_config.py (Configuration)
            |
            +-- models (BacktestConfig)
            +-- strategies (Strategy Factory)
```

---

## Backward Compatibility Strategy

### Option 1: Wrapper Class (Recommended)
```python
# comprehensive_backtest_runner.py (deprecated wrapper)

class ComprehensiveBacktestRunner:
    """
    Deprecated: Use BacktestOrchestrator instead.

    This class maintains backward compatibility but delegates
    to the new modular implementation.
    """

    def __init__(self, config_path: str):
        import warnings
        warnings.warn(
            "ComprehensiveBacktestRunner is deprecated. "
            "Use BacktestOrchestrator from execution module instead.",
            DeprecationWarning,
            stacklevel=2
        )
        from app.backtesting.execution import BacktestOrchestrator
        self._orchestrator = BacktestOrchestrator(config_path)

    def run_all_backtests(self) -> List[Dict[str, Any]]:
        return self._orchestrator.run_all_backtests()

    # ... all other methods delegate to orchestrator
```

### Option 2: Facade Pattern
```python
# backtest_facade.py (new facade)

class BacktestFacade:
    """
    Facade providing simple interface to backtesting modules.

    Maintains the old API while using new modular implementation.
    """

    def __init__(self, config_path: str):
        self.config_factory = BacktestConfigFactory(...)
        self.execution_engine = BacktestExecutionEngine(...)
        self.result_aggregator = BacktestResultAggregator(...)
        self.validator = BacktestValidator(...)

    # Implement all public methods from old class
```

---

## Testing Strategy

### Unit Tests for Each Module
```python
# tests/unit/backtesting/test_backtest_execution.py

class TestBacktestExecutionEngine:
    """Test suite for BacktestExecutionEngine."""

    def test_execute_baseline(self):
        """Test baseline execution."""

    def test_execute_monte_carlo(self):
        """Test Monte Carlo execution."""

    # ... tests for each method

# tests/unit/backtesting/test_backtest_aggregation.py

class TestBacktestResultAggregator:
    """Test suite for BacktestResultAggregator."""

    def test_aggregate_baseline_result(self):
        """Test baseline result aggregation."""

    def test_calculate_consistent_metrics(self):
        """Test metrics calculation."""

    # ... more tests

# tests/unit/backtesting/test_backtest_validation.py

class TestBacktestValidator:
    """Test suite for BacktestValidator."""

    def test_validate_configuration(self):
        """Test configuration validation."""

    def test_validate_stationarity(self):
        """Test stationarity validation."""

    # ... more tests

# tests/unit/backtesting/test_backtest_config.py

class TestBacktestConfigFactory:
    """Test suite for BacktestConfigFactory."""

    def test_create_strategy_config(self):
        """Test strategy config creation."""

    def test_extract_thresholds(self):
        """Test threshold extraction."""

    # ... more tests
```

### Integration Tests
```python
# tests/integration/backtesting/test_backtest_orchestrator.py

class TestBacktestOrchestrator:
    """Integration tests for the orchestrator."""

    def test_run_all_backtests(self):
        """Test running complete backtest suite."""

    def test_backward_compatibility(self):
        """Test that old API still works."""

    # ... more integration tests
```

---

## Example: Split File Structure

### Before: Single File (3,968 lines)
```
app/backtesting/
└── comprehensive_backtest_runner.py (3,968 lines)
    └── class ComprehensiveBacktestRunner
        ├── __init__ (50 lines)
        ├── run_all_backtests (100 lines)
        ├── run_baseline_backtest (70 lines)
        ├── run_learning_engines_backtest (30 lines)
        ├── run_monte_carlo_backtest (90 lines)
        ├── run_walk_forward_backtest (250 lines)
        ├── run_transformer_optimization_backtest (200 lines)
        ├── run_ablation_backtest (280 lines)
        ├── run_grid_search_backtest (350 lines)
        ├── run_out_of_sample_backtest (450 lines)
        ├── run_multi_strategy_backtest (200 lines)
        ├── run_regime_test_backtest (450 lines)
        └── ... 30+ helper methods
```

### After: Modular Structure (5 files, ~2,600 total lines)
```
app/backtesting/
├── comprehensive_backtest_runner.py (200 lines)
│   └── class BacktestOrchestrator
│       ├── __init__
│       ├── run_all_backtests
│       ├── run_specific_backtests
│       └── get_results
│
├── backtest_execution.py (1,200 lines)
│   ├── class BacktestExecutionEngine
│   │   ├── execute_baseline
│   │   ├── execute_learning_engines
│   │   ├── execute_monte_carlo
│   │   ├── execute_walk_forward
│   │   ├── execute_transformer_optimization
│   │   ├── execute_ablation
│   │   ├── execute_grid_search
│   │   ├── execute_out_of_sample
│   │   ├── execute_multi_strategy
│   │   └── execute_regime_test
│   ├── class LearningEngineTester
│   ├── class RegimeAnalyzer
│   └── class MonteCarloDataGenerator
│
├── backtest_aggregation.py (400 lines)
│   └── class BacktestResultAggregator
│       ├── aggregate_baseline_result
│       ├── aggregate_learning_engine_result
│       ├── aggregate_monte_carlo_results
│       ├── aggregate_walk_forward_results
│       ├── aggregate_ablation_results
│       ├── aggregate_grid_search_results
│       ├── aggregate_regime_results
│       ├── calculate_consistent_metrics
│       ├── format_multi_strategy_results
│       ├── save_results
│       └── save_audit_and_weights
│
├── backtest_validation.py (500 lines)
│   ├── class BacktestValidator
│   │   ├── validate_configuration
│   │   ├── validate_data_sufficiency
│   │   ├── validate_stationarity
│   │   ├── validate_out_of_sample_performance
│   │   ├── evaluate_parameter_set
│   │   └── optimize_with_validation
│   ├── class TransformerFeatureAnalyzer
│   │   ├── extract_predictions
│   │   ├── extract_feature_importance
│   │   └── apply_meta_labeling
│   └── class RegimeDetector
│       ├── detect_simple_regimes
│       ├── get_regime_name_mapping
│       └── analyze_regime_transitions
│
└── backtest_config.py (300 lines)
    ├── class BacktestConfigFactory
    │   ├── create_strategy_config
    │   ├── create_strategy_config_for_type
    │   ├── create_ablation_config
    │   ├── create_input_profile_from_config
    │   ├── get_filter_config
    │   ├── extract_thresholds
    │   ├── get_strategy_name
    │   ├── create_backtest_config
    │   ├── get_monte_carlo_config
    │   ├── get_walk_forward_config
    │   ├── get_grid_search_config
    │   └── get_regime_test_config
    └── class ParameterGridGenerator
        ├── generate_parameter_combinations
        └── create_default_param_grid
```

---

## Benefits of Refactoring

### Code Quality Improvements
1. **Single Responsibility:** Each class has one clear purpose
2. **Open/Closed Principle:** Easy to add new backtest types without modifying existing code
3. **Dependency Inversion:** High-level modules don't depend on low-level details
4. **Interface Segregation:** Small, focused interfaces

### Maintainability Improvements
1. **Easier Navigation:** Clear file structure makes finding code easier
2. **Localized Changes:** Changes to one backtest type don't affect others
3. **Better Testing:** Each module can be tested independently
4. **Clear Dependencies:** Explicit dependency graph

### Performance Improvements
1. **Lazy Loading:** Load only what's needed
2. **Parallel Execution:** Easier to parallelize independent modules
3. **Memory Management:** Better control over memory usage per module

### Team Collaboration
1. **Reduced Conflicts:** Multiple developers can work on different modules
2. **Clear Ownership:** Each module has clear ownership boundaries
3. **Easier Onboarding:** New developers can understand one module at a time

---

## Metrics & Success Criteria

### Code Metrics (Before -> After)
- **File Size:** 3,968 lines -> 200 lines (main), 300-1,200 lines (modules)
- **Class Size:** 1 class (3,968 lines) -> 5 classes (200-1,200 lines each)
- **Method Count:** 47 methods in 1 class -> ~10 methods per class
- **Cyclomatic Complexity:** High -> Low per class
- **Test Coverage:** ~40% -> Target 80%+

### Success Criteria
1. All existing tests pass without modification
2. New unit tests for each module achieve 80%+ coverage
3. Integration tests verify end-to-end functionality
4. No performance regression
5. Backward compatibility maintained
6. Documentation updated for all modules
7. Code review approved by team

---

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Maintain backward compatibility wrapper
- Comprehensive integration testing
- Incremental migration with rollback plan

### Risk 2: Performance Regression
**Mitigation:**
- Benchmark before/after performance
- Profile critical paths
- Optimize hot paths after refactoring

### Risk 3: Increased Complexity
**Mitigation:**
- Clear dependency graph
- Well-documented interfaces
- Examples and usage guides

### Risk 4: Team Adoption
**Mitigation:**
- Training sessions on new structure
- Pair programming during transition
- Clear documentation and examples

---

## Timeline

### Week 1: Preparation & Planning
- Day 1-2: Finalize refactoring plan
- Day 3-4: Create test coverage for existing code
- Day 5: Review and approve plan with team

### Week 2: Implementation (Phase 1-3)
- Day 1-2: Create new module structure
- Day 3-4: Extract configuration logic
- Day 5: Extract validation logic

### Week 3: Implementation (Phase 4-6)
- Day 1-2: Extract aggregation logic
- Day 3-4: Extract execution logic
- Day 5: Create new orchestrator

### Week 4: Finalization (Phase 7-8)
- Day 1-2: Update imports and add deprecation warnings
- Day 3-4: Comprehensive testing and bug fixes
- Day 5: Remove old file and final cleanup

---

## Next Steps

1. **Review this plan** with the development team
2. **Get approval** for the refactoring approach
3. **Set up feature branch** for refactoring work
4. **Create comprehensive tests** for existing functionality
5. **Begin Phase 1** of the migration plan

---

## Appendix: Code Examples

### Example 1: Extracted Configuration Factory
```python
# backtest_config.py

class BacktestConfigFactory:
    """Factory for creating backtest configurations."""

    def __init__(self, raw_config: Dict[str, Any]):
        self.raw_config = raw_config
        self.config_loader = BacktestConfigLoader.from_dict(raw_config)

    def create_strategy_config(self) -> Dict[str, Any]:
        """Create base strategy configuration."""
        return {
            'type': 'modular_momentum',
            'preset': 'custom',
            'modules': self.get_filter_config(),
            'presets': {
                'custom': {
                    'combination_mode': 'MAJORITY',
                    'min_confidence': 0.7,
                }
            }
        }

    def get_filter_config(self) -> Dict[str, Any]:
        """Get filter configuration from YAML."""
        filters_config = {}

        if "modules" in self.raw_config and "filters" in self.raw_config["modules"]:
            filters = self.raw_config["modules"]["filters"]

            for filter_name, filter_config in filters.items():
                if filter_config.get("enabled", False):
                    filter_params = {
                        param_name: param_config["default"]
                        for param_name, param_config in filter_config.get("parameters", {}).items()
                        if "default" in param_config
                    }

                    filters_config[filter_name] = {
                        "enabled": True,
                        **filter_params
                    }

        return filters_config
```

### Example 2: Extracted Execution Engine
```python
# backtest_execution.py

class BacktestExecutionEngine:
    """Executes various types of backtests."""

    def __init__(self, config: BacktestConfig, data_loader: DataLoader):
        self.config = config
        self.data_loader = data_loader
        self.executor = SimpleBacktestExecutor(config)

    def execute_baseline(
        self,
        quotes: List,
        strategy
    ) -> Dict[str, Any]:
        """Execute baseline backtest."""
        result = self.executor.execute(
            quotes,
            strategy,
            strategy_name="baseline"
        )

        # Delegation to aggregator for result formatting
        from app.backtesting.aggregation import BacktestResultAggregator
        aggregator = BacktestResultAggregator(self.config.output_dir)

        return aggregator.aggregate_baseline_result(
            result,
            self.config.initial_capital
        )

    def execute_monte_carlo(
        self,
        quotes: List,
        num_simulations: int
    ) -> List[Dict[str, Any]]:
        """Execute Monte Carlo simulations."""
        from app.backtesting.config import MonteCarloDataGenerator

        generator = MonteCarloDataGenerator()
        results = []

        for i in range(num_simulations):
            modified_quotes = generator.create_monte_carlo_quotes(
                quotes,
                volatility_multiplier=1.0
            )

            result = self.executor.execute(
                modified_quotes,
                strategy=self._create_strategy(),
                strategy_name=f"monte_carlo_{i}"
            )

            results.append(result)

        return results
```

### Example 3: New Orchestrator
```python
# comprehensive_backtest_runner.py (new version)

class BacktestOrchestrator:
    """
    Main orchestrator for comprehensive backtesting suite.

    Replaces the monolithic ComprehensiveBacktestRunner with
    a clean, modular implementation.
    """

    def __init__(self, config_path: str):
        # Load configuration
        self.raw_config = self._load_config(config_path)

        # Initialize modules
        from app.backtesting.config import BacktestConfigFactory
        from app.backtesting.execution import BacktestExecutionEngine
        from app.backtesting.aggregation import BacktestResultAggregator
        from app.backtesting.validation import BacktestValidator

        self.config_factory = BacktestConfigFactory(self.raw_config)
        self.execution_engine = BacktestExecutionEngine(
            self.config_factory.create_backtest_config(),
            DataLoader()
        )
        self.result_aggregator = BacktestResultAggregator(
            Path(self.raw_config['reporting']['output_directory'])
        )
        self.validator = BacktestValidator()

    def run_all_backtests(self) -> List[Dict[str, Any]]:
        """Execute all configured backtests."""
        results = []

        # Load market data
        quotes = self._load_market_data()

        # Execute enabled backtests
        if self.raw_config.get('backtests', {}).get('baseline', {}).get('enabled', True):
            results.extend(self._run_baseline(quotes))

        if self.raw_config.get('backtests', {}).get('monte_carlo', {}).get('enabled', False):
            results.extend(self._run_monte_carlo(quotes))

        # ... other backtest types

        # Save results
        self.result_aggregator.save_results(
            results,
            self.raw_config.get('reporting', {}).get('output_format', ['csv', 'json'])
        )

        return results

    def _run_baseline(self, quotes: List) -> List[Dict[str, Any]]:
        """Run baseline backtest."""
        strategy_config = self.config_factory.create_strategy_config()
        strategy = ModularMomentumStrategy(strategy_config)

        return [self.execution_engine.execute_baseline(quotes, strategy)]
```

---

## Conclusion

This refactoring plan transforms a 3,968-line monolithic class into a clean, modular architecture following Clean Architecture principles. The split into five focused modules improves maintainability, testability, and team collaboration while maintaining backward compatibility.

The modular structure enables:
- Easier testing of individual components
- Better code organization and navigation
- Reduced merge conflicts in team development
- Clearer separation of concerns
- Future extensibility for new backtest types

By following this plan incrementally with comprehensive testing at each phase, we can achieve a 95% Clean Architecture compliance score while maintaining system stability.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-28
**Author:** Refactoring Specialist
**Status:** Ready for Review
