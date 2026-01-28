# Phase 2 Changelog: ML/AI Fallbacks Eliminated

**Date:** 2026-01-28
**Files Changed:** 9
**Lines Removed:** ~200 (fallback code)
**Lines Added:** ~50 (required imports)

---

## 1. deep_learning_engine.py

**File:** `app/strategies/momentum_modular/learning/deep_learning_engine.py`

### Lines 38-52: Removed lazy import pattern
```diff
- # NO importar PyTorch aquí - será importado lazy cuando se necesite
- PYTORCH_AVAILABLE = False
- torch = None
- nn = None
- optim = None
- Dataset = None
- DataLoader = None

- def _ensure_pytorch_imported():
-     """Importar PyTorch de forma lazy con configuración de threading."""
-     global torch, nn, optim, Dataset, DataLoader, PYTORCH_AVAILABLE
-     if PYTORCH_AVAILABLE:
-         return True
-     try:
-         os.environ['OMP_NUM_THREADS'] = '1'
-         # ... 30+ lines of threading configuration
-         PYTORCH_AVAILABLE = True
-         return True
-     except ImportError:
-         PYTORCH_AVAILABLE = False
-         return False

+ # REQUIRED: PyTorch must be available - NO FALLBACKS
+ import torch
+ import torch.nn as nn
+ import torch.optim as optim
+ from torch.utils.data import DataLoader, Dataset
+
+ # Configure threading BEFORE any PyTorch operations
+ torch.set_num_threads(1)
+ try:
+     torch.set_num_interop_threads(1)
+ except RuntimeError:
+     pass  # Already configured
+ torch.backends.cudnn.enabled = False
+ torch.backends.cudnn.benchmark = False
```

### Lines 82-105: Removed availability check in __init__
```diff
- if not _ensure_pytorch_imported():
-     if not TENSORFLOW_AVAILABLE:
-         logger.warning("PyTorch o TensorFlow no disponibles...")
-         self.enabled = False
-         return

+ # PyTorch es REQUIRED - ya importado al inicio del módulo
+ # Si defer_pytorch_init=True, solo configurar valores pero no deshabilitar
+ if defer_pytorch_init:
+     self.enabled = True
+     # ... configuration only
+     return
```

### Lines 154-155: Removed availability check in train()
```diff
- # Asegurar que PyTorch está disponible
- if not _ensure_pytorch_imported():
-     if not TENSORFLOW_AVAILABLE:
-         raise ImportError("PyTorch o TensorFlow requeridos")

+ # PyTorch es REQUIRED - ya importado al inicio del módulo
+ # No hay fallbacks
```

---

## 2. supervised_learning_engine.py

**File:** `app/strategies/momentum_modular/learning/supervised_learning_engine.py`

### Lines 15-37: Removed all optional imports
```diff
- # Importaciones opcionales para diferentes algoritmos
- try:
-     from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
-     SKLEARN_AVAILABLE = True
- except ImportError:
-     SKLEARN_AVAILABLE = False
-     logger.warning("scikit-learn no disponible. Funcionalidad limitada.")

- try:
-     import xgboost as xgb
-     XGBOOST_AVAILABLE = True
- except ImportError:
-     XGBOOST_AVAILABLE = False
-     logger.warning("XGBoost no disponible...")

- try:
-     import lightgbm as lgb
-     LIGHTGBM_AVAILABLE = True
- except ImportError:
-     LIGHTGBM_AVAILABLE = False
-     logger.warning("LightGBM no disponible...")

- try:
-     import catboost as cb
-     CATBOOST_AVAILABLE = True
- except ImportError:
-     CATBOOST_AVAILABLE = False
-     logger.warning("CatBoost no disponible...")

- try:
-     import torch
-     import torch.nn as nn
-     PYTORCH_AVAILABLE = True
- except ImportError:
-     PYTORCH_AVAILABLE = False
-     logger.warning("PyTorch no disponible...")

+ # REQUIRED: scikit-learn is REQUIRED - NO FALLBACKS
+ from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
+ from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
+ from sklearn.model_selection import train_test_split
+
+ # REQUIRED: XGBoost is REQUIRED - NO FALLBACKS
+ import xgboost as xgb
+
+ # REQUIRED: LightGBM is REQUIRED - NO FALLBACKS
+ import lightgbm as lgb
+
+ # REQUIRED: CatBoost is REQUIRED - NO FALLBACKS
+ import catboost as cb
+
+ # REQUIRED: PyTorch is REQUIRED for neural networks - NO FALLBACKS
+ import torch
+ import torch.nn as nn
```

### Lines 97-97: Removed availability check in train()
```diff
- # Verificar disponibilidad dinámicamente para asegurar que sklearn está disponible
- try:
-     from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
-     from sklearn.model_selection import train_test_split
- except ImportError as e:
-     raise ImportError("scikit-learn es requerido...")

+ # scikit-learn es REQUIRED - ya importado al inicio del módulo
```

### Lines 145-163: Removed algorithm fallbacks
```diff
- if self.algorithm == "random_forest":
-     self.model = self._train_random_forest(X_train, y_train)
- elif self.algorithm == "xgboost" and XGBOOST_AVAILABLE:
-     self.model = self._train_xgboost(X_train, y_train)
- elif self.algorithm == "lightgbm" and LIGHTGBM_AVAILABLE:
-     self.model = self._train_lightgbm(X_train, y_train, X_val, y_val)
- elif self.algorithm == "catboost" and CATBOOST_AVAILABLE:
-     self.model = self._train_catboost(X_train, y_train, X_val, y_val)
- elif self.algorithm == "gradient_boosting":
-     self.model = self._train_gradient_boosting(X_train, y_train)
- elif self.algorithm == "neural_net" and PYTORCH_AVAILABLE:
-     self.model = self._train_neural_net(X_train, y_train, X_val, y_val)
- else:
-     logger.warning(f"Algoritmo {self.algorithm} no disponible, usando RandomForest")
-     self.model = self._train_random_forest(X_train, y_train)

+ # Todos los algoritmos son REQUIRED - no fallbacks
+ if self.algorithm == "random_forest":
+     self.model = self._train_random_forest(X_train, y_train)
+ elif self.algorithm == "xgboost":
+     self.model = self._train_xgboost(X_train, y_train)
+ elif self.algorithm == "lightgbm":
+     self.model = self._train_lightgbm(X_train, y_train, X_val, y_val)
+ elif self.algorithm == "catboost":
+     self.model = self._train_catboost(X_train, y_train, X_val, y_val)
+ elif self.algorithm == "gradient_boosting":
+     self.model = self._train_gradient_boosting(X_train, y_train)
+ elif self.algorithm == "neural_net":
+     self.model = self._train_neural_net(X_train, y_train, X_val, y_val)
+ else:
+     raise ValueError(f"Algoritmo {self.algorithm} no soportado...")
```

---

## 3. transformer_engine.py

**File:** `app/strategies/momentum_modular/learning/transformer_engine.py`

### Lines 36-50: Removed lazy import pattern
```diff
- # NO importar PyTorch aquí - será importado lazy cuando se necesite
- PYTORCH_AVAILABLE = False
- torch = None
- nn = None
- optim = None
- Dataset = None
- DataLoader = None

- def _ensure_pytorch_imported():
-     """Importar PyTorch de forma lazy con configuración de threading."""
-     global torch, nn, optim, Dataset, DataLoader, PYTORCH_AVAILABLE
-     if PYTORCH_AVAILABLE:
-         return True
-     try:
-         os.environ['OMP_NUM_THREADS'] = '1'
-         # ... 30+ lines of configuration
-         PYTORCH_AVAILABLE = True
-         return True
-     except ImportError:
-         PYTORCH_AVAILABLE = False
-         logger.warning("PyTorch no disponible...")
-         return False

+ # REQUIRED: PyTorch is REQUIRED - NO FALLBACKS
+ import torch
+ import torch.nn as nn
+ import torch.optim as optim
+ from torch.utils.data import DataLoader, Dataset
+
+ # Configure threading BEFORE any PyTorch operations
+ torch.set_num_threads(1)
+ try:
+     torch.set_num_interop_threads(1)
+ except RuntimeError:
+     pass  # Already configured
+ torch.backends.cudnn.enabled = False
+ torch.backends.cudnn.benchmark = False
```

### Lines 96-96: Removed availability check
```diff
- if not _ensure_pytorch_imported():
-     logger.error("TransformerEngine requiere PyTorch. No disponible.")
-     self.enabled = False
-     return

+ # PyTorch es REQUIRED - ya importado al inicio del módulo
```

---

## 4. reinforcement_learning_engine.py

**File:** `app/strategies/momentum_modular/learning/reinforcement_learning_engine.py`

### Lines 14-24: Removed optional imports
```diff
- # Importaciones opcionales para RL
- STABLE_BASELINES3_AVAILABLE = False
- GYM_AVAILABLE = False

- try:
-     os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
-     os.environ.setdefault('OMP_NUM_THREADS', '1')
-     from stable_baselines3 import A2C, DDPG, DQN, PPO, SAC, TD3
-     from stable_baselines3.common.callbacks import BaseCallback
-     STABLE_BASELINES3_AVAILABLE = True
- except (FileNotFoundError, ValueError, KeyError, TypeError):
-     STABLE_BASELINES3_AVAILABLE = False
-     logger.debug("stable-baselines3 no disponible o bloqueado")

- try:
-     import gym
-     import gym.spaces
-     GYM_AVAILABLE = True
- except ImportError:
-     GYM_AVAILABLE = False
-     logger.debug("gym no disponible. Funcionalidad RL limitada.")

+ # REQUIRED: stable-baselines3 is REQUIRED - NO FALLBACKS
+ import os
+ os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
+ os.environ.setdefault('OMP_NUM_THREADS', '1')
+
+ from stable_baselines3 import A2C, DDPG, DQN, PPO, SAC, TD3
+ from stable_baselines3.common.callbacks import BaseCallback
+
+ # REQUIRED: gym is REQUIRED - NO FALLBACKS
+ import gym
+ import gym.spaces
```

### Lines 312-312: Removed availability check
```diff
- if not STABLE_BASELINES3_AVAILABLE:
-     raise ImportError("stable-baselines3 es requerido")

+ # stable-baselines3 y gym son REQUIRED - ya importados al inicio del módulo
```

---

## 5. hmm_regime_detector.py

**File:** `app/engines/context_engine/regime_detectors/hmm_regime_detector.py`

### Lines 14-18: Removed optional imports
```diff
- # Importaciones opcionales
- try:
-     from hmmlearn import hmm
-     HMMLEARN_AVAILABLE = True
- except ImportError:
-     HMMLEARN_AVAILABLE = False
-     logger.warning("hmmlearn no disponible. HMMRegimeDetector limitado.")

- try:
-     from sklearn.preprocessing import StandardScaler
-     SKLEARN_AVAILABLE = True
- except ImportError:
-     SKLEARN_AVAILABLE = False
-     logger.warning("sklearn no disponible. HMMRegimeDetector limitado.")

+ # REQUIRED: hmmlearn is REQUIRED - NO FALLBACKS
+ from hmmlearn import hmm
+
+ # REQUIRED: sklearn is REQUIRED - NO FALLBACKS
+ from sklearn.preprocessing import StandardScaler
```

### Lines 42-42: Updated __init__
```diff
- self.model = None
- self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None

+ self.model = None
+ self.scaler = StandardScaler()
```

### Lines 59-59: Updated fit()
```diff
- if not HMMLEARN_AVAILABLE:
-     logger.warning("hmmlearn no disponible. HMM no puede entrenarse.")
-     return False

+ # hmmlearn es REQUIRED - ya importado al inicio del módulo
```

---

## 6. clustering_regime_detector.py

**File:** `app/engines/context_engine/regime_detectors/clustering_regime_detector.py`

### Lines 14-17: Removed optional imports
```diff
- # Importaciones opcionales
- try:
-     from sklearn.cluster import DBSCAN, KMeans
-     from sklearn.decomposition import PCA
-     from sklearn.preprocessing import StandardScaler
-     SKLEARN_AVAILABLE = True
- except ImportError:
-     SKLEARN_AVAILABLE = False
-     logger.warning("sklearn no disponible. ClusteringRegimeDetector limitado.")

+ # REQUIRED: sklearn is REQUIRED - NO FALLBACKS
+ from sklearn.cluster import DBSCAN, KMeans
+ from sklearn.decomposition import PCA
+ from sklearn.preprocessing import StandardScaler
```

### Lines 43-44: Updated __init__
```diff
- self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
- self.pca = PCA(n_components=self.n_components_pca) if SKLEARN_AVAILABLE and self.use_pca else None

+ self.scaler = StandardScaler()
+ self.pca = PCA(n_components=self.n_components_pca) if self.use_pca else None
```

---

## 7. garch_analyzer.py

**File:** `app/engines/context_engine/volatility_analyzers/garch_analyzer.py`

### Lines 14-15: Removed optional import
```diff
- # Importaciones opcionales
- try:
-     from arch import arch_model
-     ARCH_AVAILABLE = True
- except ImportError:
-     ARCH_AVAILABLE = False
-     logger.warning("arch no disponible. GARCHAnalyzer limitado.")

+ # REQUIRED: arch is REQUIRED - NO FALLBACKS
+ from arch import arch_model
```

### Lines 51-51: Updated fit()
```diff
- if not ARCH_AVAILABLE:
-     logger.warning("arch no disponible. GARCH no puede entrenarse.")
-     return False

+ # arch es REQUIRED - ya importado al inicio del módulo
```

---

## 8. portfolio_engine/optimizers/__init__.py

**File:** `app/engines/portfolio_engine/optimizers/__init__.py`

### Lines 19-26: Removed optional imports
```diff
- # Optional dependencies
- try:
-     import cvxpy as cp
-     CVXPY_AVAILABLE = True
- except ImportError:
-     CVXPY_AVAILABLE = False
-     logger.warning("cvxpy no disponible. Optimización avanzada limitada.")

- try:
-     from pypfopt import EfficientFrontier
-     PYPORTFOLIO_AVAILABLE = True
- except ImportError:
-     PYPORTFOLIO_AVAILABLE = False
-     logger.warning("PyPortfolioOpt no disponible...")

- try:
-     from scipy.optimize import minimize
-     SCIPY_AVAILABLE = True
- except ImportError:
-     SCIPY_AVAILABLE = False
-     logger.warning("scipy no disponible. Risk Parity usará método heurístico.")

+ # REQUIRED: cvxpy is REQUIRED - NO FALLBACKS
+ import cvxpy as cp
+
+ # REQUIRED: PyPortfolioOpt is REQUIRED - NO FALLBACKS
+ from pypfopt import EfficientFrontier
+
+ # REQUIRED: scipy is REQUIRED - NO FALLBACKS
+ from scipy.optimize import minimize
```

### Lines 88-93: Removed optimization fallbacks
```diff
- try:
-     if PYPORTFOLIO_AVAILABLE:
-         return self._optimize_pypfopt(expected_returns, cov_matrix, constraints)
-     elif CVXPY_AVAILABLE:
-         return self._optimize_cvxpy(expected_returns, cov_matrix, constraints)
-     else:
-         return self._optimize_basic(expected_returns, cov_matrix, constraints)

+ try:
+     # All optimization libraries are REQUIRED - no fallbacks
+     return self._optimize_pypfopt(expected_returns, cov_matrix, constraints)
```

### Lines 347-379: Removed scipy fallback
```diff
- if SCIPY_AVAILABLE:
-     # Use scipy.optimize.minimize with SLSQP
-     try:
-         result = minimize(...)
-     except Exception as e:
-         self.logger.warning(f"Scipy optimization failed: {e}, using fallback")
- # Fallback: simple iterative method
- return self._risk_parity_fallback(cov_matrix, x0, target_risk, constraints)

+ # scipy is REQUIRED - already imported at module level
+ try:
+     result = minimize(...)
+ except Exception as e:
+     # scipy is REQUIRED - if optimization fails, raise error instead of fallback
+     raise RuntimeError(f"Risk parity optimization failed. scipy.optimize.minimize is required...")
```

---

## 9. portfolio_engine/meta_learners/meta_learners.py

**File:** `app/engines/portfolio_engine/meta_learners/meta_learners.py`

### Lines 19-21: Removed optional import
```diff
- # Optional dependencies
- try:
-     import torch
-     import torch.nn as nn
-     PYTORCH_AVAILABLE = True
- except ImportError:
-     PYTORCH_AVAILABLE = False
-     logger.warning("PyTorch no disponible. Meta-learning RL limitado.")

+ # REQUIRED: PyTorch is REQUIRED - NO FALLBACKS
+ import torch
+ import torch.nn as nn
```

### Lines 238-239: Removed availability check
```diff
- if not PYTORCH_AVAILABLE:
-     self.logger.warning("PyTorch no disponible. RL learner limitado.")
-     self.model = None
- else:
-     self._initialize_model()

+ # PyTorch es REQUIRED - ya importado al inicio del módulo
+ self._initialize_model()
```

### Lines 248-248: Removed availability check
```diff
- def _initialize_model(self) -> None:
-     """Inicializar modelo de RL."""
-     if not PYTORCH_AVAILABLE:
-         return
-     # Red neuronal simple para Q-learning

+ def _initialize_model(self) -> None:
+     """Inicializar modelo de RL."""
+     # PyTorch es REQUIRED - ya importado al inicio del módulo
+     # Red neuronal simple para Q-learning
```

### Lines 288-292: Removed fallback in learn_weights()
```diff
- if not self.model:
-     # Fallback a historical performance
-     learner = HistoricalPerformanceLearner(self.config)
-     return learner.learn_weights(strategy_performance, market_context)

+ if not self.model:
+     raise RuntimeError("ReinforcementLearningLearner model not initialized...")
```

### Lines 320-321: Removed fallback in exception handler
```diff
- except Exception as e:
-     self.logger.error(f"Error en RL learner: {e}", exc_info=True)
-     # Fallback
-     learner = HistoricalPerformanceLearner(self.config)
-     return learner.learn_weights(strategy_performance, market_context)

+ except Exception as e:
+     self.logger.error(f"Error en RL learner: {e}", exc_info=True)
+     # No fallback - PyTorch is REQUIRED
+     raise RuntimeError(f"RL learner failed: {e}") from e
```

---

## Summary

- **Files Modified:** 9
- **Fallback Patterns Removed:** 15 (try/except ImportError blocks)
- **Availability Flags Removed:** 8 (PYTORCH_AVAILABLE, SKLEARN_AVAILABLE, etc.)
- **Fallback Methods Removed:** 5 (_optimize_basic, _risk_parity_fallback, etc.)
- **Lines of Code Removed:** ~200
- **Lines of Code Added:** ~50
- **Net Code Reduction:** ~150 lines

**Result:** Cleaner, more maintainable code with explicit dependencies and fail-fast behavior.
