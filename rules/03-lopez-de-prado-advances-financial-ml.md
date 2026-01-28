# 📗 3. "Advances in Financial Machine Learning" - Marcos López de Prado

## REGLAS DE MACHINE LEARNING PARA FINANZAS

**NUNCA uses returns simples como labels** - Usa Triple Barrier Method

```python
def triple_barrier_labeling(
    self,
    prices: pd.Series,
    t0: int,
    target_return: float = 0.02,  # 2%
    stop_loss: float = 0.01,      # 1%
    max_holding_period: int = 20   # 20 días
) -> int:
    """
    Labels: 1 (hit target first), -1 (hit SL first), 0 (timeout).
    Evita usar solo "precio subió/bajó" que ignora magnitud.
    """
    entry_price = prices.iloc[t0]

    upper_barrier = entry_price * (1 + target_return)
    lower_barrier = entry_price * (1 - stop_loss)

    for i in range(t0 + 1, min(t0 + max_holding_period, len(prices))):
        price = prices.iloc[i]

        # ¿Tocó target primero?
        if price >= upper_barrier:
            return 1  # WIN

        # ¿Tocó SL primero?
        if price <= lower_barrier:
            return -1  # LOSS

    # Timeout sin tocar barreras
    final_return = (prices.iloc[min(t0 + max_holding_period, len(prices) - 1)] - entry_price) / entry_price
    return 1 if final_return > 0 else -1
```

**Meta-Labeling: Usa ML para SIZING, no solo dirección**

```python
def meta_labeling(
    self,
    primary_signal: int,  # 1 (BUY) o -1 (SELL) de estrategia primaria
    features: np.array,
    actual_return: float
) -> int:
    """
    Meta-label: ¿La señal primaria fue correcta?

    ML predice P(señal correcta), luego:
    - P > 0.6 → Tomar posición FULL SIZE
    - P > 0.5 → Tomar posición HALF SIZE
    - P < 0.5 → NO tomar posición
    """
    # Entrenar clasificador
    # X = features, Y = (actual_return * primary_signal > 0)

    # Label = 1 si señal fue correcta, 0 si fue incorrecta
    if (actual_return > 0 and primary_signal == 1) or \
       (actual_return < 0 and primary_signal == -1):
        return 1  # Señal correcta
    else:
        return 0  # Señal incorrecta
```

**Fractional Differentiation: Mantén stationarity SIN perder memoria**

```python
def frac_diff(self, series: pd.Series, d: float = 0.5, threshold: float = 0.01) -> pd.Series:
    """
    Diferenciación fraccionaria: hace serie estacionaria preservando memoria.

    d = 0.5 → Balance entre memoria y stationarity
    d = 1.0 → Diferenciación completa (pierde toda la memoria)
    """
    weights = [1.0]
    k = 1

    # Calcular pesos
    while True:
        weight = -weights[-1] / k * (d - k + 1)
        if abs(weight) < threshold:
            break
        weights.append(weight)
        k += 1

    weights = np.array(weights[::-1]).cumsum()
    weights /= weights[-1]

    # Aplicar convolución
    result = pd.Series(index=series.index)
    for i in range(len(weights), len(series)):
        result.iloc[i] = np.dot(weights, series.iloc[i - len(weights):i])

    return result.dropna()
```

**Purging: Elimina overlap entre train/test en cross-validation**

```python
def purged_cv_split(
    self,
    n_samples: int,
    n_folds: int = 5,
    embargo_pct: float = 0.01
) -> List[tuple]:
    """
    Purged K-Fold: elimina samples cercanos a train/test boundary.

    Embargo = 1% de datos después de cada fold (evita data leakage).
    """
    from sklearn.model_selection import KFold

    kfold = KFold(n_splits=n_folds, shuffle=False)
    embargo = int(n_samples * embargo_pct)

    purged_splits = []

    for train_idx, test_idx in kfold.split(range(n_samples)):
        # Purge: eliminar samples de train que overlap con test
        train_idx = train_idx[train_idx < test_idx[0] - embargo]

        # Embargo: eliminar samples de test cercanos a train
        test_idx = test_idx[test_idx > train_idx[-1] + embargo]

        purged_splits.append((train_idx, test_idx))

    return purged_splits
```

**Sequential Bootstrap: Genera samples sintéticos respetando autocorrelación**

```python
def sequential_bootstrap(
    self,
    returns: pd.Series,
    n_samples: int,
    avg_uniqueness: float = 0.5
) -> pd.Series:
    """
    Bootstrap que respeta estructura temporal (no IID).

    avg_uniqueness = fracción promedio de samples únicos en cada draw.
    """
    sample_length = int(len(returns) * avg_uniqueness)

    bootstrapped = []

    for _ in range(n_samples):
        # Random start point
        start_idx = np.random.randint(0, len(returns) - sample_length)

        # Sample continuous segment (preserva autocorrelación)
        segment = returns.iloc[start_idx:start_idx + sample_length]
        bootstrapped.append(segment.mean())

    return pd.Series(bootstrapped)
```

**Feature Importance: Usa MDI, MDA Y SFI (no solo Gini)**

```python
def calculate_feature_importance(
    self,
    model: RandomForestClassifier,
    X_train: np.array,
    y_train: np.array,
    X_test: np.array,
    y_test: np.array
) -> pd.DataFrame:
    """
    3 métodos de feature importance:
    - MDI (Mean Decrease Impurity) - rápido pero biased
    - MDA (Mean Decrease Accuracy) - más robusto
    - SFI (Single Feature Importance) - sin interacciones
    """
    feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]

    # MDI (de sklearn)
    mdi = pd.Series(model.feature_importances_, index=feature_names)

    # MDA (permutation importance)
    baseline_score = model.score(X_test, y_test)
    mda = {}

    for i, feat in enumerate(feature_names):
        X_test_permuted = X_test.copy()
        np.random.shuffle(X_test_permuted[:, i])  # Permute feature

        permuted_score = model.score(X_test_permuted, y_test)
        mda[feat] = baseline_score - permuted_score

    mda = pd.Series(mda)

    # SFI (entrenar con cada feature individualmente)
    sfi = {}

    for i, feat in enumerate(feature_names):
        single_model = RandomForestClassifier()
        single_model.fit(X_train[:, [i]], y_train)
        sfi[feat] = single_model.score(X_test[:, [i]], y_test)

    sfi = pd.Series(sfi)

    return pd.DataFrame({
        'MDI': mdi,
        'MDA': mda,
        'SFI': sfi
    })
```

**Sample Weights: Ponderar por uniqueness (no todas las observaciones son iguales)**

```python
def calculate_sample_weights(
    self,
    timestamps: pd.Series,
    holding_periods: pd.Series
) -> pd.Series:
    """
    Weight inversamente proporcional a overlap con otros samples.

    Sample con muchos overlaps → peso menor.
    """
    weights = pd.Series(index=timestamps.index, dtype=float)

    for idx in timestamps.index:
        t_start = timestamps[idx]
        t_end = t_start + holding_periods[idx]

        # Contar cuántos otros samples overlap con este
        overlaps = 0

        for other_idx in timestamps.index:
            if other_idx == idx:
                continue

            other_start = timestamps[other_idx]
            other_end = other_start + holding_periods[other_idx]

            # Check overlap
            if not (t_end <= other_start or t_start >= other_end):
                overlaps += 1

        # Weight = 1 / (1 + overlaps)
        weights[idx] = 1.0 / (1 + overlaps)

    # Normalize
    weights /= weights.sum()

    return weights
```

**NUNCA uses accuracy en problemas desbalanceados** - Usa F1 o MCC

```python
from sklearn.metrics import f1_score, matthews_corrcoef

def evaluate_classifier(
    self,
    y_true: np.array,
    y_pred: np.array
) -> Dict[str, float]:
    """
    Métricas apropiadas para clasificación desbalanceada.

    MCC (Matthews Correlation Coefficient) > F1 > Accuracy
    """
    # Accuracy (engañosa si classes desbalanceadas)
    accuracy = np.mean(y_true == y_pred)

    # F1-score (mejor)
    f1 = f1_score(y_true, y_pred, average='weighted')

    # MCC (mejor de todas, rango -1 a 1)
    mcc = matthews_corrcoef(y_true, y_pred)

    return {
        'accuracy': accuracy,  # NO usar para decisiones
        'f1_score': f1,
        'mcc': mcc  # USAR ESTO
    }
```

**Cross-Validation: NUNCA uses KFold estándar en series temporales**

```python
from sklearn.model_selection import TimeSeriesSplit

def time_series_cv(
    self,
    X: np.array,
    y: np.array,
    n_splits: int = 5
):
    """
    Time Series Cross-Validation respeta orden temporal.

    ❌ NO usar: KFold (rompe orden temporal)
    ✅ USAR: TimeSeriesSplit
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)

    for train_idx, test_idx in tscv.split(X):
        # NUNCA test_idx < train_idx (respeta temporalidad)
        assert train_idx.max() < test_idx.min()

        yield X[train_idx], X[test_idx], y[train_idx], y[test_idx]
```

**Bet Sizing con ML: Predecir no solo dirección, sino TAMAÑO**

```python
def ml_bet_sizing(
    self,
    ml_probability: float,  # P(dirección correcta)
    kelly_fraction: float = 0.5
) -> float:
    """
    Usar ML para bet sizing dinámico.

    P(correct) * bet_size - P(wrong) * bet_size = edge
    """
    # Convertir probabilidad a size
    # P > 0.6 → size mayor
    # P < 0.5 → no apostar

    if ml_probability < 0.5:
        return 0.0  # No bet

    # Kelly-inspired sizing
    edge = 2 * ml_probability - 1  # 0 cuando P=0.5, 1 cuando P=1.0

    bet_size = kelly_fraction * edge

    return min(bet_size, 0.25)  # Cap a 25%
```
