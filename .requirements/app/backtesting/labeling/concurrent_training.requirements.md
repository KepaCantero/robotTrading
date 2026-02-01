# concurrent_training.py

## Purpose
Implements concurrent training of multiple models with proper handling of sample uniqueness and ensemble methods for robust financial ML.

---

## Type Definitions / Data Classes

### ConcurrentTrainingConfig
```python
@dataclass
class ConcurrentTrainingConfig:
    n_jobs: int = -1                         # REQUIRED - Range [-1, inf] or -1 for all cores
    verbose: int = 1                         # REQUIRED - Verbosity level [0, 1, 2]
    ensemble_method: str = "weighted"        # REQUIRED - One of: 'simple', 'weighted', 'stacking', 'voting'
    weight_by: str = "accuracy"              # REQUIRED - One of: 'accuracy', 'f1', 'roc_auc', 'uniqueness'
    use_uniqueness_weights: bool = True      # OPTIONAL - Apply sample uniqueness weighting
    uniqueness_method: str = "average"       # REQUIRED - Method for uniqueness calculation
    cv_folds: int = 5                        # REQUIRED - Range [2, inf], CV folds for stacking
    purge_pct: float = 0.05                  # REQUIRED - Range [0, 1), purge percentage
    embargo_pct: float = 0.01                # REQUIRED - Range [0, 1), embargo percentage
    stacking_meta_model: str = "logistic"    # REQUIRED - Meta-model for stacking: 'logistic', 'rf', 'xgb'
    select_best_models: bool = True          # OPTIONAL - Select top N models for ensemble
    top_n_models: int = 3                    # REQUIRED - Range [1, inf], number of top models to select
```

**Validation Rules:**
- ensemble_method must be in ['simple', 'weighted', 'stacking', 'voting']
- weight_by must be in ['accuracy', 'f1', 'roc_auc', 'uniqueness']
- n_jobs must be -1 or positive integer
- cv_folds must be >= 2
- purge_pct and embargo_pct must be in [0, 1)
- top_n_models must be >= 1

### ModelResult
```python
@dataclass
class ModelResult:
    model_name: str                          # REQUIRED - Name/identifier for the model
    model: Any                               # REQUIRED - Trained model instance
    predictions: np.ndarray                  # REQUIRED - Model predictions
    probabilities: Optional[np.ndarray]      # OPTIONAL - Prediction probabilities (if available)
    score: float                             # REQUIRED - Model performance score
    training_time: float                     # REQUIRED - Training time in seconds
    uniqueness_weights: Optional[np.ndarray] # OPTIONAL - Sample uniqueness weights
    avg_uniqueness: float = 0.0              # REQUIRED - Average uniqueness score
    feature_importance: Dict[str, float]     # OPTIONAL - Feature importance dict
    metadata: Dict[str, Any]                 # OPTIONAL - Additional metadata
    timestamp: datetime                      # AUTO - Result timestamp
```

**Validation Rules:**
- model_name must be non-empty string
- score must be in [0, 1] for accuracy-type metrics
- training_time must be >= 0
- All arrays must have compatible lengths

### EnsembleResult
```python
@dataclass
class EnsembleResult:
    model_results: List[ModelResult]         # REQUIRED - Results from individual models
    ensemble_predictions: np.ndarray         # REQUIRED - Ensemble predictions
    ensemble_probabilities: Optional[np.ndarray] # OPTIONAL - Ensemble probabilities
    ensemble_score: float                    # REQUIRED - Ensemble performance score
    ensemble_weights: Dict[str, float]       # REQUIRED - Weight for each model in ensemble
    stacking_model: Optional[Any] = None     # OPTIONAL - Stacking meta-model (if used)
    metadata: Dict[str, Any]                 # OPTIONAL - Additional metadata
    timestamp: datetime                      # AUTO - Result timestamp
```

**Validation Rules:**
- model_results must have at least 1 element
- ensemble_weights must sum to 1.0 (or 0.0 if no weights)
- All arrays must have same length
- ensemble_score must be in [0, 1] for accuracy-type metrics

---

## Function Signatures (Contracts)

### `ConcurrentModelTrainer.__init__(config: Optional[ConcurrentTrainingConfig] = None) -> None`
**Pre:** config is None or valid ConcurrentTrainingConfig
**Post:** Instance initialized with config or defaults
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `ConcurrentModelTrainer.train_models_concurrent(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, sample_weights: Optional[np.ndarray] = None) -> EnsembleResult`
**Pre:** models dict has at least 1 entry, X and y have same length
**Post:** Returns EnsembleResult with all models trained concurrently
**Raises:** ValueError if models empty, RuntimeError if all models fail
**Retry:** No
**Side Effects:** Spawns multiple processes for parallel training

### `ConcurrentModelTrainer._train_single_model(model_name: str, model: Any, X: np.ndarray, y: np.ndarray, sample_weights: Optional[np.ndarray], uniqueness_weights: Optional[np.ndarray]) -> ModelResult`
**Pre:** Model is scikit-learn compatible, arrays have compatible lengths
**Post:** Returns ModelResult with trained model and predictions
**Raises:** Exception on training failure (caught by executor)
**Retry:** No
**Side Effects:** Trains model (must be pickleable for multiprocessing)

### `ConcurrentModelTrainer._create_ensemble(model_results: List[ModelResult], X: np.ndarray, y: np.ndarray, events: Optional[pd.Series], labels: Optional[pd.DataFrame]) -> EnsembleResult`
**Pre:** model_results has at least 1 element
**Post:** Returns EnsembleResult with combined predictions
**Raises:** ValueError if model_results empty
**Retry:** No
**Side Effects:** May create stacking meta-model

### `ConcurrentModelTrainer._calculate_ensemble_weights(model_results: List[ModelResult], X: np.ndarray, y: np.ndarray) -> Dict[str, float]`
**Pre:** model_results non-empty
**Post:** Returns weight dict summing to 1.0 (or equal weights)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConcurrentModelTrainer._ensemble_predict(model_results: List[ModelResult], X: np.ndarray, weights: Dict[str, float]) -> Tuple[np.ndarray, Optional[np.ndarray]]`
**Pre:** model_results non-empty, X has compatible features
**Post:** Returns (predictions, probabilities) from ensemble
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConcurrentModelTrainer._create_stacking_model(model_results: List[ModelResult], X: np.ndarray, y: np.ndarray, events: Optional[pd.Series], labels: Optional[pd.DataFrame]) -> Any`
**Pre:** model_results non-empty, at least one has probabilities
**Post:** Returns trained stacking meta-model
**Raises:** ValueError if no valid meta-features
**Retry:** No
**Side Effects:** Trains meta-model on base model predictions

### `SequentialModelTrainer.__init__(config: Optional[ConcurrentTrainingConfig] = None) -> None`
**Pre:** config is None or valid
**Post:** Instance initialized
**Raises:** ValueError if config invalid
**Retry:** No
**Side Effects:** None

### `SequentialModelTrainer.train_models_sequential(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None) -> EnsembleResult`
**Pre:** models dict non-empty, X and y have same length
**Post:** Returns EnsembleResult with models trained sequentially
**Raises:** RuntimeError if all models fail
**Retry:** No
**Side Effects:** Each model uses purged data from previous models

### `train_models_concurrent(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, ensemble_method: str = "weighted", n_jobs: int = -1) -> EnsembleResult`
**Pre:** models non-empty, X and y compatible
**Post:** Returns EnsembleResult from concurrent training
**Raises:** ValueError on invalid inputs
**Retry:** No
**Side Effects:** None (convenience function)

---

## Acceptance Criteria
- [ ] Concurrent training uses ProcessPoolExecutor for true parallelism
- [ ] All models trained concurrently (not sequentially)
- [ ] Sample uniqueness weights calculated if events and labels provided
- [ ] Sample weights combined with uniqueness weights (element-wise multiply)
- [ ] Ensemble weights sum to 1.0 (or equal distribution)
- [ ] Simple ensemble: equal weights (1/n_models)
- [ ] Weighted ensemble: softmax weighting by performance metric
- [ ] Voting ensemble: majority vote (mode of predictions)
- [ ] Stacking ensemble: meta-model trained on base predictions
- [ ] Top N model selection: sort by score, select top_n_models
- [ ] Sequential training: each model gets purged data (no reuse)
- [ ] Sequential training: marks used samples to prevent reuse
- [ ] Ensemble predictions: weighted average or voting
- [ ] Ensemble probabilities: weighted average of probabilities
- [ ] Stacking meta-model: logistic/RF/XGBoost on base predictions

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| ASYNC-001 | BASE_RULES | Use async def | ⚠️ NOT APPLIED - Uses ProcessPoolExecutor instead |
| PERF-006 | BASE_RULES | Async I/O | ⚠️ NOT APPLIED - Uses multiprocessing for CPU-bound tasks |
| ARCH-004 | BASE_RULES | Small functions | ⚠️ PARTIAL - Some methods > 20 lines (_train_single_model, _create_stacking_model) |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - No test file exists for concurrent_training.py (tests out of scope for this task) |
| QL-007 | BASE_RULES | Max 7 parameters | ✅ OK - All methods within limit |

**Concurrent Training Specific Rules:**
- CONC-001: Models must be pickleable for ProcessPoolExecutor
- CONC-002: Each model training must be independent (no shared state)
- CONC-003: Uniqueness weights must be calculated once and passed to all models
- CONC-004: Ensemble weights must sum to 1.0 (before any zero-weight models)
- CONC-005: Stacking meta-model must use purged CV to prevent overfitting
- CONC-006: Sequential training must prevent sample reuse between models
- CONC-007: Failed model training must not crash entire ensemble (log and continue)

---

## Dependencies
- **External:** numpy, pandas, scikit-learn, xgboost (optional), concurrent.futures
- **Internal:** app/backtesting/labeling/triple_barrier (for calculate_sample_weights_uniqueness), app/backtesting/labeling/meta_labeling_cv (for PurgedKFold)

---

## Required Tests
- **tests/backtesting/labeling/test_concurrent_training.py:**
  - Test ConcurrentTrainingConfig validation (methods, parameters)
  - Test ConcurrentModelTrainer.train_models_concurrent with multiple models
  - Test ProcessPoolExecutor spawns processes correctly
  - Test uniqueness weights calculation and application
  - Test sample weights combined with uniqueness weights
  - Test ensemble weight calculation (simple, weighted, voting)
  - Test ensemble prediction (weighted average, voting)
  - Test stacking model creation and prediction
  - Test top N model selection
  - Test ModelResult dataclass structure
  - Test EnsembleResult dataclass structure
  - Test EnsembleResult.to_dict serialization
  - Test SequentialModelTrainer.train_models_sequential
  - Test sequential training purges used samples
  - Test failed model training doesn't crash ensemble
  - Test train_models_concurrent convenience function
  - Test voting ensemble with majority vote
  - Test stacking ensemble with different meta-models

---

## Notes
Based on Marcos López de Prado "Advances in Financial Machine Learning" Chapters 4 & 7. Concurrent training enables faster model development and robustness through diversity. Uses ProcessPoolExecutor for true parallelism (not threading). Uniqueness weighting from triple_barrier module ensures overlapping samples don't overfit. Ensemble methods: simple (equal), weighted (performance), voting (majority), stacking (meta-model). Sequential training purges data to prevent information leakage between models.
