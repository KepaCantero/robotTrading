# 📙 15. "The Elements of Statistical Learning" - Hastie et al.

## REGLAS DE MACHINE LEARNING ESTADÍSTICO

**Regla 15.1 — Anti-overfitting**

Claude DEBE:
- regularizar
- limitar hiperparámetros

**Mejora marginal + complejidad → rechazar.**

```python
def validate_model_complexity(
    self,
    train_score: float,
    test_score: float,
    complexity_metric: float,  # e.g., # parameters, tree depth
    max_complexity: int = 100
) -> bool:
    """
    Validar que modelo no esté overfitted.

    Hastie et al: Gap train-test >> overfitting.
    """
    # Generalization gap
    gap = train_score - test_score

    # Gap > 20% = overfitting
    if gap > 0.2:
        logger.error(
            f"❌ Overfitting detected: Train={train_score:.2f}, "
            f"Test={test_score:.2f}, Gap={gap:.2f}"
        )
        return False

    # Validar complejidad
    if complexity_metric > max_complexity:
        logger.warning(
            f"⚠️ Model complexity high: {complexity_metric} "
            f"> {max_complexity}"
        )
        return False

    return True
```

**Regla 15.2 — Regularización obligatoria**

```python
def regularize_model(
    self,
    X: np.array,
    y: np.array,
    regularization: str = "ridge",
    alpha: float = 1.0
) -> object:
    """
    Regularizar SIEMPRE modelos lineales.

    Hastie et al: Ridge/Lasso/ElasticNet reducen overfitting.
    """
    from sklearn.linear_model import Ridge, Lasso, ElasticNet

    if regularization == "ridge":
        # L2 penalty
        model = Ridge(alpha=alpha)

    elif regularization == "lasso":
        # L1 penalty (feature selection)
        model = Lasso(alpha=alpha)

    elif regularization == "elasticnet":
        # L1 + L2 penalty
        model = ElasticNet(alpha=alpha, l1_ratio=0.5)

    model.fit(X, y)

    logger.info(f"Trained {regularization} model (alpha={alpha})")

    return model
```

**Regla 15.3 — Cross-validation correcto**

```python
def time_series_cross_validation(
    self,
    model: object,
    X: np.array,
    y: np.array,
    n_splits: int = 5
) -> dict:
    """
    Time Series Cross-Validation.

    Hastie et al: NO usar KFold aleatorio en series temporales.
    """
    from sklearn.model_selection import TimeSeriesSplit

    tscv = TimeSeriesSplit(n_splits=n_splits)

    scores = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Train
        model_clone = clone(model)
        model_clone.fit(X_train, y_train)

        # Test
        score = model_clone.score(X_test, y_test)
        scores.append(score)

        logger.info(f"Fold {fold + 1}: Score = {score:.3f}")

    mean_score = np.mean(scores)
    std_score = np.std(scores)

    logger.info(
        f"CV Results: Mean = {mean_score:.3f}, Std = {std_score:.3f}"
    )

    return {
        'mean_score': mean_score,
        'std_score': std_score,
        'scores': scores
    }
```

**Regla 15.4 — Feature selection con regularización**

```python
def lasso_feature_selection(
    self,
    X: pd.DataFrame,
    y: pd.Series,
    alpha: float = 0.01
) -> dict:
    """
    Feature selection usando Lasso (L1).

    Hastie et al: Lasso zero-out features irrelevantes.
    """
    from sklearn.linear_model import Lasso

    model = Lasso(alpha=alpha)
    model.fit(X, y)

    # Features con coeficiente != 0
    selected_features = X.columns[model.coef_ != 0].tolist()

    logger.info(
        f"Lasso selected {len(selected_features)}/{len(X.columns)} features"
    )

    return {
        'selected_features': selected_features,
        'coefficients': dict(zip(X.columns, model.coef_)),
        'model': model
    }
```

**Regla 15.5 — Bias-Variance tradeoff**

```python
def analyze_bias_variance(
    self,
    train_errors: List[float],
    test_errors: List[float],
    complexities: List[float]
) -> dict:
    """
    Analizar tradeoff bias-variance.

    Hastie et al: Encontrar punto óptimo de complejidad.
    """
    # Plot tradeoff curve
    # Low complexity → High bias, low variance (underfitting)
    # High complexity → Low bias, high variance (overfitting)

    # Encontrar punto óptimo (minimum test error)
    min_idx = np.argmin(test_errors)
    optimal_complexity = complexities[min_idx]

    logger.info(
        f"Optimal complexity: {optimal_complexity} "
        f"(Test error: {test_errors[min_idx]:.3f})"
    )

    # Check si estamos en zona de overfitting
    # (Test error aumentando con complejidad)
    if min_idx < len(test_errors) - 1:
        recent_trend = np.polyfit(
            range(min_idx, len(test_errors)),
            test_errors[min_idx:],
            1
        )[0]

        if recent_trend > 0:
            logger.warning(
                "⚠️ Model may be overfitting: "
                "Test error increasing with complexity"
            )

    return {
        'optimal_complexity': optimal_complexity,
        'min_test_error': test_errors[min_idx],
        'train_error_at_optimal': train_errors[min_idx]
    }
```

**Regla 15.6 — No implicit conversions**

```python
def enforce_explicit_dtypes(
    self,
    df: pd.DataFrame,
    dtype_spec: dict = None
) -> pd.DataFrame:
    """
    Forzar explicit dtype casting.

    Hastie et al: Object dtype en datos numéricos = problemas.
    """
    # Check si hay object dtype
    object_cols = df.select_dtypes(include=['object']).columns.tolist()

    if object_cols:
        logger.error(f"❌ Object dtype columns found: {object_cols}")

        # Intentar convertir
        for col in object_cols:
            try:
                df[col] = pd.to_numeric(df[col], errors='raise')
                logger.info(f"Converted {col} to numeric")
            except:
                logger.error(f"❌ Cannot convert {col} to numeric")

    # Validar no hay object dtype
    assert not df.select_dtypes(include=['object']).any().any(), \
        "Object dtype still present"

    return df
```

**Regla 15.7 — Stability tests**

```python
def stability_test(
    self,
    model: object,
    X: np.array,
    y: np.array,
    n_bootstrap: int = 100,
    tolerance: float = 0.1
) -> bool:
    """
    Test de estabilidad de coeficientes.

    Hastie et al: Modelos inestables no son confiables.
    """
    if hasattr(model, 'coef_'):
        coef_original = model.coef_.copy()
    else:
        logger.warning("Model has no coefficients to test")
        return True

    coef_variations = []

    for i in range(n_bootstrap):
        # Bootstrap sample
        idx = np.random.choice(len(X), len(X), replace=True)
        X_boot, y_boot = X[idx], y[idx]

        # Train
        model_boot = clone(model)
        model_boot.fit(X_boot, y_boot)

        # Coefficient variation
        if hasattr(model_boot, 'coef_'):
            variation = np.abs(model_boot.coef_ - coef_original).mean()
            coef_variations.append(variation)

    # Check estabilidad
    mean_variation = np.mean(coef_variations)

    if mean_variation > tolerance:
        logger.error(
            f"❌ Model unstable: Coefficient variation = {mean_variation:.3f} "
            f"> {tolerance:.3f}"
        )
        return False

    logger.info(f"✅ Model stable: Variation = {mean_variation:.3f}")

    return True
```

**Regla 15.8 — Hyperparameter tuning con validación**

```python
def tune_hyperparameters(
    self,
    X: np.array,
    y: np.array,
    param_grid: dict,
    cv: int = 5
) -> dict:
    """
    Hyperparameter tuning con cross-validation.

    Hastie et al: NO optimizar en test set.
    """
    from sklearn.model_selection import GridSearchCV
    from sklearn.model_selection import TimeSeriesSplit

    # Time Series CV para datos temporales
    tscv = TimeSeriesSplit(n_splits=cv)

    # Grid search
    grid_search = GridSearchCV(
        estimator=self.model,
        param_grid=param_grid,
        cv=tscv,
        scoring='neg_mean_squared_error',
        n_jobs=-1
    )

    grid_search.fit(X, y)

    logger.info(
        f"Best params: {grid_search.best_params_}, "
        f"Best score: {grid_search.best_score_:.3f}"
    )

    return {
        'best_params': grid_search.best_params_,
        'best_model': grid_search.best_estimator_,
        'cv_results': grid_search.cv_results_
    }
```

**Regla 15.9 — Ensemble methods**

```python
def ensemble_predictions(
    self,
    models: List[object],
    X: np.array,
    ensemble_method: str = "bagging"
) -> np.array:
    """
    Ensemble de múltiples modelos.

    Hastie et al: Ensemble reduce variance sin aumentar bias.
    """
    predictions = []

    for model in models:
        pred = model.predict(X)
        predictions.append(pred)

    predictions = np.array(predictions)

    if ensemble_method == "bagging":
        # Simple average (bagging)
        ensemble_pred = predictions.mean(axis=0)

    elif ensemble_method == "median":
        # Median (robusto a outliers)
        ensemble_pred = np.median(predictions, axis=0)

    elif ensemble_method == "stacking":
        # Stacked ensemble
        meta_model = self.train_meta_model(predictions, y_true)
        ensemble_pred = meta_model.predict(predictions.T)

    return ensemble_pred
```

**Regla 15.10 — Learning curve analysis**

```python
def learning_curve_analysis(
    self,
    model: object,
    X: np.array,
    y: np.array,
    train_sizes: np.array = np.linspace(0.1, 1.0, 10)
) -> dict:
    """
    Analizar learning curves.

    Hastie et al: Learning curves revelan underfitting/overfitting.
    """
    from sklearn.model_selection import learning_curve

    train_sizes, train_scores, test_scores = learning_curve(
        model, X, y,
        train_sizes=train_sizes,
        cv=5,
        scoring='neg_mean_squared_error'
    )

    train_mean = -train_scores.mean(axis=1)
    test_mean = -test_scores.mean(axis=1)

    # Diagnóstico
    final_gap = train_mean[-1] - test_mean[-1]

    if final_gap > 0.2:
        logger.warning("⚠️ High variance (overfitting): Add more data or regularize")
    elif train_mean[-1] > 0.3 and test_mean[-1] > 0.3:
        logger.warning("⚠️ High bias (underfitting): Increase model complexity")
    else:
        logger.info("✅ Good fit: Low bias and low variance")

    return {
        'train_sizes': train_sizes,
        'train_scores': train_mean,
        'test_scores': test_mean,
        'final_gap': final_gap
    }
```
