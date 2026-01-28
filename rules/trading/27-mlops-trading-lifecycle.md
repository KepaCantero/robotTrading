# 📘 27. Machine Learning Engineering - MLOps para Trading

**Libro:** Machine Learning Engineering - Andriy Burkov
**Objetivo:** Production ML lifecycle para modelos de trading

## 🎯 Resumen Ejecutivo

Claude Code DEBE implementar MLOps para:
1. **Reproducibilidad** completa de experimentos
2. **Monitoreo** de degradación de modelos
3. **Despliegue seguro** con canaries y rollbacks
4. **Gestión** de features y modelos versionados

---

## 📋 Las 15 Reglas Críticas para Claude Code

### Regla 27.1 — Feature Store Centralizado

```python
class FeatureStore:
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    def get_features(self, symbol: str, features: list[str], start: datetime, end: datetime) -> pd.DataFrame:
        query = f"SELECT {', '.join(features)} FROM features WHERE symbol = ? AND timestamp BETWEEN ? AND ?"
        return self.storage.execute(query, (symbol, start, end))
    
    def save_features(self, df: pd.DataFrame, feature_set_name: str):
        self.storage.write(f"features/{feature_set_name}", df)
    
    def compute_features(self, symbol: str, feature_set_name: str) -> pd.DataFrame:
        if feature_set_name == "momentum":
            return self._compute_momentum_features(symbol)
        elif feature_set_name == "volatility":
            return self._compute_volatility_features(symbol)
```

**Regla:** USAR feature store para evitar recomputación y garantizar consistencia.

---

### Regla 27.2 — Model Versioning

```python
import mlflow

class ModelRegistry:
    def save_model(self, model, model_name: str, version: str, metrics: dict):
        with mlflow.start_run():
            mlflow.log_params(model.get_params())
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(model, "model")
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
            mlflow.register_model(model_uri, f"{model_name}_{version}")
    
    def load_model(self, model_name: str, version: str):
        return mlflow.sklearn.load_model(f"models:/{model_name}_{version}")
```

**Regla:** VERSIONAR todos los modelos con metadata y métricas.

---

### Regla 27.3 — Concept Drift Detection

```python
from scipy import stats

class DriftDetector:
    def detect_drift(self, reference_data: pd.Series, current_data: pd.Series, threshold: float = 0.05) -> bool:
        statistic, p_value = stats.ks_2samp(reference_data, current_data)
        return p_value < threshold
    
    def monitor_predictions(self, model, X: pd.DataFrame, y_true: pd.Series):
        y_pred = model.predict(X)
        accuracy = (y_pred == y_true).mean()
        
        if accuracy < self.baseline_accuracy * 0.9:
            logger.warning(f"Model degradation detected: {accuracy:.2%} vs baseline {self.baseline_accuracy:.2%}")
            return True
        return False
```

**Regla:** MONITOREAR drift de conceptos y accuracy en producción.

---

### Regla 27.4 — Shadow Deployment

```python
class ShadowDeployment:
    def __init__(self, production_model, shadow_model):
        self.production_model = production_model
        self.shadow_model = shadow_model
        self.shadow_metrics = []
    
    def predict(self, X: pd.DataFrame):
        production_pred = self.production_model.predict(X)
        shadow_pred = self.shadow_model.predict(X)
        
        self.shadow_metrics.append({
            'timestamp': datetime.now(),
            'shadow_prediction': shadow_pred,
            'production_prediction': production_pred
        })
        
        return production_pred  # Solo retornar predicción de producción
    
    def compare_performance(self) -> dict:
        if len(self.shadow_metrics) < 100:
            return {'status': 'insufficient_data'}
        # Calcular métricas del shadow model
        pass
```

**Regla:** DESPLEGAR shadow models para validar antes de producción.

---

### Regla 27.5 — A/B Testing de Modelos

```python
class ABTestManager:
    def __init__(self, model_a, model_b, traffic_split: float = 0.5):
        self.model_a = model_a
        self.model_b = model_b
        self.traffic_split = traffic_split
        self.metrics_a = []
        self.metrics_b = []
    
    def predict(self, X: pd.DataFrame) -> tuple:
        if random.random() < self.traffic_split:
            pred = self.model_a.predict(X)
            self.metrics_a.append(pred)
            return pred, 'A'
        else:
            pred = self.model_b.predict(X)
            self.metrics_b.append(pred)
            return pred, 'B'
    
    def analyze_results(self) -> dict:
        from scipy import stats
        t_stat, p_value = stats.ttest_ind(self.metrics_a, self.metrics_b)
        return {'t_statistic': t_stat, 'p_value': p_value}
```

**Regla:** EJECUTAR A/B tests estadísticos antes de migrar modelos.

---

### Regla 27.6 — Canary Deployment

```python
class CanaryDeployment:
    def __init__(self, old_model, new_model, canary_traffic: float = 0.1):
        self.old_model = old_model
        self.new_model = new_model
        self.canary_traffic = canary_traffic
    
    def predict(self, X: pd.DataFrame):
        if random.random() < self.canary_traffic:
            return self.new_model.predict(X)
        return self.old_model.predict(X)
    
    def increase_canary(self, increment: float = 0.1):
        self.canary_traffic = min(1.0, self.canary_traffic + increment)
        logger.info(f"Canary traffic increased to {self.canary_traffic:.1%}")
```

**Regla:** INCREMENTAR tráfico al nuevo modelo gradualmente (10% → 50% → 100%).

---

### Regla 27.7 — Model Monitoring

```python
class ModelMonitor:
    def __init__(self, model, baseline_metrics: dict):
        self.model = model
        self.baseline_metrics = baseline_metrics
        self.alerts = []
    
    def check_performance(self, current_metrics: dict):
        for metric, baseline_value in self.baseline_metrics.items():
            current_value = current_metrics.get(metric)
            if current_value < baseline_value * 0.9:
                alert = {
                    'metric': metric,
                    'baseline': baseline_value,
                    'current': current_value,
                    'degradation': (baseline_value - current_value) / baseline_value
                }
                self.alerts.append(alert)
                logger.error(f"Performance degradation: {alert}")
```

**Regla:** MONITOREAR métricas clave y alertar en degradación > 10%.

---

### Regla 27.8 — Data Drift Detection

```python
class DataDriftDetector:
    def detect_distribution_shift(self, train_data: pd.DataFrame, production_data: pd.DataFrame) -> dict:
        drift_report = {}
        for column in train_data.columns:
            statistic, p_value = stats.ks_2samp(train_data[column], production_data[column])
            drift_report[column] = {
                'statistic': statistic,
                'p_value': p_value,
                'drift_detected': p_value < 0.05
            }
        return drift_report
```

**Regla:** DETECTAR cambios en distribución de features vs training.

---

### Regla 27.9 — Feature Importance Tracking

```python
class FeatureImportanceTracker:
    def track_importance(self, model, feature_names: list[str]) -> dict:
        importances = dict(zip(feature_names, model.feature_importances_))
        sorted_importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
        self.save_to_db(sorted_importances)
        return sorted_importances
    
    def detect_importance_shift(self, old_importance: dict, new_importance: dict, threshold: float = 0.2) -> list:
        shifted_features = []
        for feature in old_importance:
            old_val = old_importance[feature]
            new_val = new_importance.get(feature, 0)
            if abs(old_val - new_val) > threshold:
                shifted_features.append(feature)
        return shifted_features
```

**Regla:** RASTREAR importancia de features y detectar cambios significativos.

---

### Regla 27.10 — Explainability (SHAP/LIME)

```python
import shap

class ModelExplainer:
    def explain_prediction(self, model, sample: pd.DataFrame):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(sample)
        
        explanation = {
            'prediction': model.predict(sample)[0],
            'feature_contributions': dict(zip(sample.columns, shap_values[0])),
            'most_important_features': sorted(zip(sample.columns, abs(shap_values[0]), key=lambda x: x[1], reverse=True)[:5]
        }
        return explanation
```

**Regla:** GENERAR explicaciones para predicciones críticas (SHAP/LIME).

---

### Regla 27.11 — Incremental Learning

```python
from sklearn.linear_model import SGDClassifier

class IncrementalModel:
    def __init__(self):
        self.model = SGDClassifier(warm_start=True)
    
    def partial_fit(self, X_batch: pd.DataFrame, y_batch: pd.Series):
        self.model.partial_fit(X_batch, y_batch, classes=np.unique(y_batch))
    
    def predict(self, X: pd.DataFrame):
        return self.model.predict(X)
```

**Regla:** IMPLEMENTAR incremental learning para adaptación continua.

---

### Regla 27.12 — Hyperparameter Tracking

```python
class HyperparameterTracker:
    def log_experiment(self, params: dict, metrics: dict):
        experiment_id = uuid4()
        self.db.execute(
            "INSERT INTO experiments VALUES (?, ?, ?, ?)",
            (experiment_id, json.dumps(params), json.dumps(metrics), datetime.now())
        )
        return experiment_id
    
    def get_best_params(self, metric: str = 'sharpe_ratio') -> dict:
        result = self.db.execute(f"SELECT params, MAX({metric}) FROM experiments GROUP BY params ORDER BY {metric} DESC LIMIT 1")
        return json.loads(result[0]['params'])
```

**Regla:** RASTREAR todos los hiperparámetros experimentados.

---

### Regla 27.13 — Experiment Tracking

```python
import mlflow

class ExperimentTracker:
    def start_run(self, run_name: str):
        mlflow.start_run(run_name=run_name)
    
    def log_params(self, params: dict):
        mlflow.log_params(params)
    
    def log_metrics(self, metrics: dict, step: int | None = None):
        mlflow.log_metrics(metrics, step=step)
    
    def log_artifact(self, file_path: str):
        mlflow.log_artifact(file_path)
    
    def end_run(self):
        mlflow.end_run()
```

**Regla:** REGISTRAR todos los experimentos con metadata completa.

---

### Regla 27.14 — Model Registry

```python
class ModelRegistry:
    def register_model(self, model: object, model_name: str, version: str, metadata: dict):
        model_info = {
            'name': model_name,
            'version': version,
            'metadata': metadata,
            'timestamp': datetime.now(),
            'model_path': self._save_model(model)
        }
        self.db.insert('model_registry', model_info)
    
    def transition_stage(self, model_name: str, version: str, new_stage: str):
        self.db.execute(
            "UPDATE model_registry SET stage = ? WHERE name = ? AND version = ?",
            (new_stage, model_name, version)
        )
```

**Regla:** MANTENER registry de modelos con stages (dev, staging, prod).

---

### Regla 27.15 — Deployment Rollback

```python
class DeploymentManager:
    def deploy(self, model_name: str, version: str):
        self._save_current_model_as_backup()
        new_model = self.registry.load_model(model_name, version)
        self._validate_model(new_model)
        self._switch_to_new_model(new_model)
    
    def rollback(self):
        logger.warning("Rolling back to previous model")
        backup_model = self._load_backup_model()
        self._switch_to_new_model(backup_model)
```

**Regla:** IMPLEMENTAR rollback automático en fallos de deployment.

---

**Última actualización:** 2026-01-28
**Version:** 1.0
