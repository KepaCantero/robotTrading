# feature_importance.py

## Purpose
 file for feature importance

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### ImportanceCategory
**Purpose:** Feature importance category levels....
### FeatureImportanceResult
**Purpose:** Result of feature importance analysis for a single feature....
### ComprehensiveImportanceReport
**Purpose:** Comprehensive feature importance report....
### SHAPAnalyzer
**Purpose:** Analizador de importancia de características usando SHAP.

Importaciones opcionales para SHAP:
    i...
### AttentionWeightsAnalyzer
**Purpose:** Analizador de attention weights para modelos Transformer.

Extrae y analiza los pesos de atención pa...
### FeatureSelector
**Purpose:** Sistema de selección automática de features basado en importancia.

Métodos soportados:
- Univariate...
### FeatureImportanceAnalyzer
**Purpose:** Analizador unificado de importancia de features.

Combina SHAP, attention weights y feature selectio...
### PermutationImportanceAnalyzer
**Purpose:** Model-agnostic permutation importance analyzer.

Measures feature importance by shuffling each featu...
### BuiltInImportanceAnalyzer
**Purpose:** Extract built-in feature importance from tree-based models.

Works with models that have feature_imp...
### CorrelationAnalyzer
**Purpose:** Analyze feature correlations for importance insights.

Includes:
- Feature-target correlation
- Feat...
### FeatureStabilityTracker
**Purpose:** Track feature importance stability over time.

Monitors:
- Importance changes between training runs
...
### ComprehensiveFeatureAnalyzer
**Purpose:** Comprehensive feature importance analyzer combining all methods.

Integrates:
- SHAP analysis
- Perm...

---

## Function Signatures (Contracts)

### `FeatureImportanceResult.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveImportanceReport.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `SHAPAnalyzer.explain_model(self, model, X, feature_names, model_type) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `SHAPAnalyzer.explain_prediction(self, model, X, instance_idx, feature_names) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AttentionWeightsAnalyzer.extract_attention_weights(self, model, sequence, layer_idx) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureSelector.select_features(self, X, y, feature_names, model, task_type) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureImportanceAnalyzer.analyze(self, model, X, y, feature_names, model_type, include_shap, include_attention, include_selection) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `PermutationImportanceAnalyzer.calculate_importance(self, model, X, y, feature_names, scoring) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `BuiltInImportanceAnalyzer.calculate_importance(self, model, feature_names) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `BuiltInImportanceAnalyzer.get_importance_type(self, model) -> str`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CorrelationAnalyzer.analyze(self, X, y, feature_names) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureStabilityTracker.record_importance(self, importance_dict, timestamp) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureStabilityTracker.analyze_stability(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureStabilityTracker.get_importance_change(self) -> Dict[str, float]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FeatureStabilityTracker.reset(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveFeatureAnalyzer.analyze(self, model, X, y, feature_names, include_shap, include_permutation, include_builtin, include_correlation, include_selection) -> ComprehensiveImportanceReport`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveFeatureAnalyzer.get_top_features(self, n) -> List[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ComprehensiveFeatureAnalyzer.reset(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `load_feature_importance_config(config_path) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `get_default_feature_importance_config() -> Dict[str, Any]`
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
- **test_feature_importance.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/momentum_modular/learning/feature_importance.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
