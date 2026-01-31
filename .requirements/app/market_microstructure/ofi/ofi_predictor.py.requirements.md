# ofi_predictor.py

## Purpose
Predict price movements using Order Flow Imbalance with linear/logistic regression models and ensemble signal combination.

---

## Type Definitions / Data Classes

### OFIPredictor Class
```python
class OFIPredictor:
    config: OFIConfig                        # Configuration parameters
    _linear_model: Optional[LinearRegression] # Trained linear regression model
    _logistic_model: Optional[LogisticRegression] # Trained logistic regression model
    _scaler: Optional[StandardScaler]       # Feature scaler for model input
    _ofi_returns_correlation: float         # Historical OFI-returns correlation
    _is_trained: bool                       # Model training status
    _training_samples: int                  # Number of training samples
    _feature_importance: dict               # Model coefficient metadata
```

---

## Function Signatures (Contracts)

### `__init__(config: Optional[OFIConfig] = None) -> None`
**Pre:** config must be OFIConfig instance or None (uses defaults)
**Post:** Predictor initialized with untrained models
**Raises:** TypeError if config is invalid type
**Retry:** No
**Side Effects:** None

### `predict_direction(ofi, historical_ofi, historical_returns, horizon) -> OFIPrediction`
**Pre:** ofi in [-1, 1], historical_ofi has >= 3 elements
**Post:** Returns OFIPrediction with direction (up/down/neutral) and confidence
**Raises:** ValueError on invalid horizon enum
**Retry:** No
**Side Effects:** None (read-only prediction)

### `train_model(ofi_history: List[float], returns_history: List[float]) -> None`
**Pre:** ofi_history and returns_history same length, length >= 10
**Post:** Sets _is_trained=True, stores model coefficients
**Raises:** ValueError if lengths mismatch
**Retry:** No
**Side Effects:** Fits sklearn models, stores correlation

### `predict_with_model(ofi: float) -> Optional[float]`
**Pre:** Model trained (_is_trained=True), scaler fitted
**Post:** Returns predicted return or None if model not trained
**Raises:** None (returns None on error)
**Retry:** No
**Side Effects:** None

### `predict_direction_with_model(ofi: float) -> Optional[str]`
**Pre:** Model trained, logistic model fitted
**Post:** Returns "up" or "down" or None if not trained
**Raises:** None (returns None on error)
**Retry:** No
**Side Effects:** None

### `detect_regime_change(historical_ofi: List[float], window: int = 20) -> Tuple[bool, str]`
**Pre:** historical_ofi length >= window * 2
**Post:** Returns (has_changed, regime_description)
**Raises:** None (returns (False, "insufficient_data") if too short)
**Retry:** No
**Side Effects:** None

### `calculate_prediction_intervals(ofi: float, confidence_level: float = 0.95) -> Tuple[float, float]`
**Pre:** Model trained, ofi in [-1, 1], confidence_level in (0, 1)
**Post:** Returns (lower_bound, upper_bound) for expected return
**Raises:** None (returns (0.0, 0.0) if model not trained)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Linear regression model trained on OFI → returns mapping
- [ ] Logistic regression model trained for direction prediction
- [ ] Signal ensemble combines threshold + model + momentum signals
- [ ] Threshold signal: OFI > 0.3 → strong buy, < -0.3 → strong sell
- [ ] Momentum signal: recent - previous OFI average comparison
- [ ] Expected move calculated in basis points (bps)
- [ ] Confidence = min(1.0, abs(combined_signal))
- [ ] Regime detection identifies bullish/bearish/neutral/volatile
- [ ] Prediction intervals use scipy.stats.norm for z-scores
- [ ] Feature importance stores coefficients and R²

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix positive semidefinite | ✅ OK - Not applicable |
| ML-001 | sklearn | Validate input arrays before fitting | ✅ OK - Checks in train_model |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ✅ OK - Logs training/prediction failures |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Validates array lengths |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Uses try/except, returns defaults |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |

---

## Dependencies
- **External:** numpy (np), sklearn.linear_model (LinearRegression, LogisticRegression), sklearn.preprocessing (StandardScaler), scipy.stats.norm, typing
- **Internal:** app.market_microstructure.ofi.models (OFIConfig, OFIHorizon, OFIPrediction)

---

## Required Tests
- **tests/market_microstructure/ofi/test_ofi_predictor.py:**
  - Test model training with valid data (success path)
  - Test model training failure on mismatched lengths (error path)
  - Test prediction with untrained model returns fallback
  - Test threshold signal generation (buy/sell/neutral)
  - Test momentum signal calculation
  - Test ensemble signal combination weights
  - Test expected move calculation in bps
  - Test regime change detection (bullish/bearish/neutral)
  - Test prediction intervals with confidence levels
  - Test feature importance extraction after training
  - Test edge cases: insufficient data, zero variance

---

## Notes
Positive OFI predicts price increase (buying pressure), negative OFI predicts decrease (selling pressure). Ensemble weights: threshold 50%, model 30%, momentum 20%. Uses Cont & Kukanov (2017) methodology.
