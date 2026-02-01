# concurrent_training.py

## Purpose
Implements concurrent and sequential model training for financial ML with proper handling of sample uniqueness, ensemble methods (simple, weighted, stacking, voting), and purged cross-validation to prevent data leakage.

---

## Type Definitions / Data Classes

### ConcurrentTrainingConfig Class/DataClass
```python
@dataclass
class ConcurrentTrainingConfig:
    n_jobs: int = -1                          # REQUIRED - Parallel jobs (-1 = all cores)
    verbose: int = 1                          # REQUIRED - Verbosity level
    ensemble_method: str = "weighted"         # REQUIRED - Method: 'simple', 'weighted', 'stacking', 'voting'
    weight_by: str = "accuracy"               # REQUIRED - Weight metric: 'accuracy', 'f1', 'roc_auc', 'uniqueness'
    use_uniqueness_weights: bool = True       # OPTIONAL - Apply uniqueness weighting
    uniqueness_method: str = "average"        # OPTIONAL - Uniqueness calculation method
    cv_folds: int = 5                         # OPTIONAL - CV folds > 0
    purge_pct: float = 0.05                   # OPTIONAL - Purge percentage [0,1)
    embargo_pct: float = 0.01                 # OPTIONAL - Embargo percentage [0,1)
    stacking_meta_model: str = "logistic"     # OPTIONAL - Stacking meta-model type
    select_best_models: bool = True           # OPTIONAL - Select top N models
    top_n_models: int = 3                     # OPTIONAL - Number of top models > 0
```

**Validation Rules:**
- ensemble_method must be in ['simple', 'weighted', 'stacking', 'voting']
- weight_by must be in ['accuracy', 'f1', 'roc_auc', 'uniqueness']
- cv_folds must be > 1
- purge_pct must be in [0, 1)
- embargo_pct must be in [0, 1)
- top_n_models must be > 0

### ModelResult Class/DataClass
```python
@dataclass
class ModelResult:
    model_name: str                           # REQUIRED - Model identifier
    model: Any                                # REQUIRED - Trained model instance
    predictions: np.ndarray                   # REQUIRED - Model predictions
    probabilities: Optional[np.ndarray]       # OPTIONAL - Prediction probabilities
    score: float                              # REQUIRED - Performance score
    training_time: float                      # REQUIRED - Training time in seconds
    uniqueness_weights: Optional[np.ndarray]  # OPTIONAL - Sample uniqueness weights
    avg_uniqueness: float = 0.0               # OPTIONAL - Average uniqueness score
    feature_importance: Dict[str, float]      # OPTIONAL - Feature importance dict
    metadata: Dict[str, Any]                  # OPTIONAL - Additional metadata
    timestamp: datetime = field(default_factory=datetime.now)
```

**Validation Rules:**
- predictions must be 1D array
- probabilities (if provided) must match predictions length
- score must be in [0, 1] for accuracy-type metrics
- training_time must be non-negative

### EnsembleResult Class/DataClass
```python
@dataclass
class EnsembleResult:
    model_results: List[ModelResult]          # REQUIRED - Results from individual models
    ensemble_predictions: np.ndarray          # REQUIRED - Ensemble predictions
    ensemble_probabilities: Optional[np.ndarray] # OPTIONAL - Ensemble probabilities
    ensemble_score: float                     # REQUIRED - Ensemble performance score
    ensemble_weights: Dict[str, float]        # REQUIRED - Model weights in ensemble
    stacking_model: Optional[Any]             # OPTIONAL - Stacking meta-model
    metadata: Dict[str, Any]                  # OPTIONAL - Additional metadata
    timestamp: datetime = field(default_factory=datetime.now)
```

**Validation Rules:**
- model_results must not be empty
- ensemble_predictions must be 1D array
- ensemble_weights must sum to approximately 1.0
- ensemble_score must be in [0, 1]

---

## Function Signatures (Contracts)

### `ConcurrentModelTrainer.__init__(config: Optional[ConcurrentTrainingConfig] = None) -> None`
**Pre:** config is None or valid ConcurrentTrainingConfig
**Post:** Instance initialized with config
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `ConcurrentModelTrainer.train_models_concurrent(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, sample_weights: Optional[np.ndarray] = None) -> EnsembleResult`
**Pre:** models dict not empty, X and y have same length > 0
**Post:** Returns EnsembleResult with all trained models and ensemble predictions
**Raises:** RuntimeError if all models fail to train
**Retry:** No
**Side Effects:** Trains models in parallel using ProcessPoolExecutor

### `ConcurrentModelTrainer._train_single_model(model_name: str, model: Any, X: np.ndarray, y: np.ndarray, sample_weights: Optional[np.ndarray], uniqueness_weights: Optional[np.ndarray]) -> ModelResult`
**Pre:** Model implements fit() and predict(), X and y have same length
**Post:** Returns ModelResult with trained model and metrics
**Raises:** None (exceptions caught by caller)
**Retry:** No
**Side Effects:** Fits model, makes predictions

### `ConcurrentModelTrainer._create_ensemble(model_results: List[ModelResult], X: np.ndarray, y: np.ndarray, events: Optional[pd.Series], labels: Optional[pd.DataFrame]) -> EnsembleResult`
**Pre:** model_results not empty, X and y have compatible lengths
**Post:** Returns EnsembleResult with ensemble predictions and weights
**Raises:** None
**Retry:** No
**Side Effects:** May create stacking meta-model

### `ConcurrentModelTrainer._calculate_ensemble_weights(model_results: List[ModelResult], X: np.ndarray, y: np.ndarray) -> Dict[str, float]`
**Pre:** model_results not empty
**Post:** Returns weights dict that sum to 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConcurrentModelTrainer._ensemble_predict(model_results: List[ModelResult], X: np.ndarray, weights: Dict[str, float]) -> Tuple[np.ndarray, Optional[np.ndarray]]`
**Pre:** model_results not empty, X has valid shape
**Post:** Returns (predictions, probabilities) tuple
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SequentialModelTrainer.train_models_sequential(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None) -> EnsembleResult`
**Pre:** models dict not empty, X and y have same length > 0
**Post:** Returns EnsembleResult with sequentially trained models
**Raises:** RuntimeError if all models fail
**Retry:** No
**Side Effects:** Trains models sequentially, marking used samples

### `train_models_concurrent(models: Dict[str, Any], X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, ensemble_method: str = "weighted", n_jobs: int = -1) -> EnsembleResult`
**Pre:** models not empty, X and y have same length
**Post:** Returns EnsembleResult
**Raises:** ValueError on invalid inputs
**Retry:** No
**Side Effects:** Creates ConcurrentModelTrainer and trains

---

## Acceptance Criteria
- [ ] All public functions have complete type hints (TYP-001)
- [ ] ConcurrentTrainingConfig validates ensemble_method and weight_by
- [ ] ProcessPoolExecutor used for true parallelism (not threading)
- [ ] All models trained must implement fit() and predict()
- [ ] Ensemble weights sum to approximately 1.0
- [ ] select_best_models correctly selects top N by score
- [ ] Stacking meta-model trained on base model predictions
- [ ] Voting ensemble uses majority voting
- [ ] Weighted ensemble uses softmax weighting
- [ ] Sequential training marks samples as used to prevent overlap
- [ ] Uniqueness weights calculated when events and labels provided
- [ ] Error handling for failed model training (log and continue)
- [ ] Feature importance extracted when available

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ⚠️ NOT APPLIED - Some private methods lack hints |
| ASYNC-001 | BASE_RULES.md | Use async for concurrent operations | ❌ GAP - Uses ProcessPoolExecutor instead of async/await |
| ASYNC-007 | BASE_RULES.md | Run blocking in executor | ✅ OK - Uses ProcessPoolExecutor correctly |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ❌ GAP - Exception logging missing stack traces in line 268 |
| ARCH-004 | BASE_RULES.md | Small functions | ❌ GAP - _ensemble_predict is 58 lines |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ PARTIAL - Catches exceptions but doesn't specify types |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Separate classes for concurrent/sequential |
| PERF-001 | BASE_RULES.md | List comprehensions | ⚠️ PARTIAL - Some loops could be comprehensions |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, sklearn, logging, dataclasses, concurrent.futures
- **Internal:** .triple_barrier (for calculate_sample_weights_uniqueness), .meta_labeling_cv (for PurgedKFold)

---

## Required Tests
- **tests/unit/backtesting/labeling/test_concurrent_training.py:**
  - Test ConcurrentTrainingConfig validation
  - Test train_models_concurrent with multiple models
  - Test model failure handling (one model fails, others succeed)
  - Test ensemble methods (simple, weighted, voting, stacking)
  - Test ensemble weight calculation (softmax, equal)
  - Test select_best_models filters correctly
  - Test uniqueness weights application
  - Test voting ensemble with majority vote
  - Test stacking meta-model creation
  - Test sequential training marks samples as used
  - Test ProcessPoolExecutor parallelism
  - Test feature importance extraction
  - Test edge cases: single model, empty models dict

---

## Notes
Implements López de Prado's concurrent training approach with uniqueness weighting. Critical for robust model development and ensembling. The sequential trainer prevents data leakage by purging used samples.
