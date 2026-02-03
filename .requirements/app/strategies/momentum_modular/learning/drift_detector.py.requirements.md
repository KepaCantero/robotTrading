# drift_detector.py

## Purpose
 file for drift detector

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### DriftSeverity
**Purpose:** Severity levels for drift detection....
### DriftResult
**Purpose:** Result from a drift detection check....
### FeatureDriftReport
**Purpose:** Report for feature-level drift analysis....
### ComprehensiveDriftReport
**Purpose:** Comprehensive drift report combining all detectors....
### PSIDetector
**Purpose:** Population Stability Index (PSI) detector.

PSI es estándar en la industria financiera para detectar...
### ADWINDetector
**Purpose:** ADWIN (Adaptive Windowing) detector for streaming data.

ADWIN mantiene una ventana de tamaño variab...
### ConceptDriftDetector
**Purpose:** Detecta concept drift usando tests estadísticos.

Tests soportados:
- Kolmogorov-Smirnov (KS) test: ...
### FeatureDriftMonitor
**Purpose:** Monitors drift for individual features.

Tracks each feature independently to identify which feature...
### OverfittingSeverity
**Purpose:** Severity levels for overfitting detection....
### OverfittingMetrics
**Purpose:** Metrics for a single training epoch....
### OverfittingResult
**Purpose:** Result from overfitting detection....
### OverfittingReport
**Purpose:** Comprehensive overfitting analysis report....
### OverfittingDetector
**Purpose:** Detects overfitting using train/val gap and learning curves....
### AdvancedOverfittingDetector
**Purpose:** Advanced overfitting detection system with comprehensive analysis.

Detects:
1. Train/val gap diverg...
### ComprehensiveDriftDetector
**Purpose:** Comprehensive drift detection system combining all detectors.

Provides a unified interface for:
- M...
### AutoRetrainingTrigger
**Purpose:** Sistema de triggers automáticos para reentrenamiento.

Combina detección de drift y overfitting para...

---

## Function Signatures (Contracts)

### `DriftResult.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `PSIDetector.calculate_psi(self, expected, actual, buckets) -> Tuple[float, Dict[str, Any]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `PSIDetector.detect(self, expected, actual, timestamp) -> DriftResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ADWINDetector.add_element(self, value) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ADWINDetector.detect(self, data, timestamp) -> DriftResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ADWINDetector.reset(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.update_reference(self, data, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.detect_drift_ks(self, current_data, timestamp) -> DriftResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.detect_drift_mmd(self, current_data, timestamp) -> DriftResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.detect(self, current_data, timestamp) -> Dict[str, DriftResult]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.detect_drift(self, current_data, timestamp) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ConceptDriftDetector.get_drift_history(self, limit) -> List[Dict[str, Any]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureDriftMonitor.initialize_features(self, feature_names) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureDriftMonitor.set_reference(self, data, feature_names) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureDriftMonitor.detect_feature_drift(self, current_data, timestamp) -> List[FeatureDriftReport]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingMetrics.generalization_gap(self) -> Optional[float]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingMetrics.gap_ratio(self) -> Optional[float]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingResult.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingReport.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingDetector.update_metrics(self, epoch, train_metric, val_metric) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingDetector.detect_overfitting(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OverfittingDetector.get_learning_curves(self) -> Dict[str, List]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.update_metrics(self, epoch, train_loss, val_loss, train_metric, val_metric, test_loss, test_metric, l1_regularization, l2_regularization, model_params_count) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.add_cv_scores(self, cv_scores) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.detect_overfitting(self) -> OverfittingResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.get_learning_curves(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.generate_report(self, model_name) -> OverfittingReport`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdvancedOverfittingDetector.reset(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveDriftDetector.set_reference(self, data, predictions, feature_names) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveDriftDetector.update_reference(self, data, predictions, feature_names) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveDriftDetector.detect(self, current_data, current_predictions, timestamp) -> ComprehensiveDriftReport`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveDriftDetector.record_retrain(self, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveDriftDetector.reset(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.should_retrain(self, current_data, current_predictions, current_performance, timestamp) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.record_retrain(self, timestamp, metadata) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.record_performance(self, performance, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.record_drift(self, drift_detected, severity, detectors_triggered, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.record_overfitting(self, overfitting_detected, train_val_gap, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AutoRetrainingTrigger.get_retrain_history(self) -> List[Dict[str, Any]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `load_drift_config(config_path) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `get_default_drift_config() -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `load_overfitting_config(config_path) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `get_default_overfitting_config() -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD


---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_drift_detector.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/momentum_modular/learning/drift_detector.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
