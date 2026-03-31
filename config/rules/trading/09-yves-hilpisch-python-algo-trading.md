# 📘 9. "Python for Algorithmic Trading" - Yves Hilpisch

## REGLAS DE PYTHON PRODUCTIVO PARA TRADING

**Regla 9.1 — Python productivo**

Claude DEBE:
- vectorizar con NumPy/Pandas
- evitar loops innecesarios
- usar operaciones vectorizadas

**Código lento sin justificación → inválido.**

```python
# ❌ MAL - Loop lento
for i in range(len(returns)):
    if returns[i] > 0:
        result[i] = returns[i] * 1.1

# ✅ BIEN - Vectorizado
result = np.where(returns > 0, returns * 1.1, returns)
```

**Regla 9.2 — Numpy/Pandas vectorization es obligatorio**

```python
def calculate_returns_vectorized(prices: pd.Series) -> pd.Series:
    """
    Returns calculados con vectorización - 100x más rápido.
    """
    return prices.pct_change()

def calculate_rolling_volatility_vectorized(
    returns: pd.Series,
    window: int = 20
) -> pd.Series:
    """
    Volatilidad rolling con vectorización.
    """
    return returns.rolling(window).std()

def calculate_signals_vectorized(
    features: pd.DataFrame,
    thresholds: dict
) -> pd.Series:
    """
    Generar señales para miles de activos simultáneamente.
    """
    # Vectorized comparison
    conditions = []

    for feature, threshold in thresholds.items():
        if threshold['operator'] == '>':
            conditions.append(features[feature] > threshold['value'])
        elif threshold['operator'] == '<':
            conditions.append(features[feature] < threshold['value'])

    # Combine conditions
    if conditions:
        combined = pd.concat(conditions, axis=1).all(axis=1)
        return combined.astype(int)
    else:
        return pd.Series(0, index=features.index)
```

**Regla 9.3 — Evita iterrows(), usa apply() o vectorización**

```python
# ❌ MAL - Muy lento
for index, row in df.iterrows():
    df.loc[index, 'result'] = row['a'] * row['b']

# ✅ MEJOR - apply
df['result'] = df.apply(lambda row: row['a'] * row['b'], axis=1)

# ✅✅ MEJOR - Vectorizado (más rápido)
df['result'] = df['a'] * df['b']
```

**Regla 9.4 - Usa groupby() para agregaciones por grupo**

```python
def calculate_portfolio_metrics_by_strategy(
    returns: pd.DataFrame,
    strategies: pd.Series  # Mismo index que returns
) -> pd.DataFrame:
    """
    Calcular métricas por estrategia usando groupby.
    """
    # Combinar returns con strategy assignments
    data = returns.to_frame('return').copy()
    data['strategy'] = strategies

    # Agrupar y calcular métricas
    metrics = data.groupby('strategy')['return'].agg([
        ('mean', 'mean'),
        ('std', 'std'),
        ('sharpe', lambda x: np.sqrt(252) * x.mean() / x.std()),
        ('total_return', lambda x: (1 + x).prod() - 1)
    ])

    return metrics
```

**Regla 9.5 — Maneja missing data eficientemente**

```python
def handle_missing_data_vectorized(
    data: pd.DataFrame,
    method: str = 'ffill'
) -> pd.DataFrame:
    """
    Manejo eficiente de missing data.

    Forward-fill es O(n), loops son O(n²) o peor.
    """
    if method == 'ffill':
        return data.ffill()
    elif method == 'bfill':
        return data.bfill()
    elif method == 'drop':
        return data.dropna()
    elif method == 'interpolate':
        return data.interpolate()
    else:
        raise ValueError(f"Unknown method: {method}")
```

**Regla 9.6 — Usa Numba para hot paths**

```python
from numba import jit

@jit(nopython=True)
def calculate_kelly_fraction_numba(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Kelly criterion compilado con Numba.

    100x más rápido que Python puro.
    """
    # Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

    # Half-Kelly, max 25%
    return max(0.0, min(kelly * 0.5, 0.25))
```

**Regla 9.7 — Memory efficiency: Usa tipos correctos**

```python
def optimize_memory_usage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reducir uso de memoria usando tipos correctos.
    """
    memory_before = df.memory_usage(deep=True).sum() / 1024**2  # MB

    # Optimizar tipos numéricos
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')

    # Optimizar strings a category si tiene pocos valores únicos
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() / len(df[col]) < 0.5:  # <50% valores únicos
            df[col] = df[col].astype('category')

    memory_after = df.memory_usage(deep=True).sum() / 1024**2  # MB

    logger.info(f"Memory optimization: {memory_before:.1f} MB → {memory_after:.1f} MB")

    return df
```

**Regla 9.8 — Multiprocessing para backtesting paralelo**

```python
from multiprocessing import Pool
from functools import partial

def parallel_backtest(
    self,
    strategy: Strategy,
    param_combinations: List[Dict],
    n_processes: int = 4
) -> pd.DataFrame:
    """
    Ejecutar múltiples backtests en paralelo.

    Crucial para walk-forward optimization.
    """
    with Pool(n_processes) as pool:
        results = pool.map(
            partial(self.run_single_backtest, strategy=strategy),
            param_combinations
        )

    return pd.DataFrame(results)
```

**Regla 9.9 — Caching inteligente de cálculos costosos**

```python
from functools import lru_cache

class CachedCalculations:
    """
    Cache de cálculos costosos que se reusan.
    """

    @staticmethod
    @lru_cache(maxsize=1024)
    def factorial(n: int) -> int:
        """Función pura con cache."""
        if n <= 1:
            return 1
        return n * CachedCalculations.factorial(n - 1)

    @staticmethod
    def cached_feature_calculation(
        data_hash: int,  # Hash de los datos de entrada
        feature_func: callable,
        data: pd.DataFrame
    ):
        """
    Cache de features basado en hash de input data.
        """
        cache_key = f"{feature_func.__name__}_{data_hash}"

        if cache_key in CachedCalculations._feature_cache:
            return CachedCalculations._feature_cache[cache_key]

        result = feature_func(data)
        CachedCalculations._feature_cache[cache_key] = result

        return result
```

**Regla 9.10 — Time series operations eficientes**

```python
def efficient_resampling(
    prices: pd.Series,
    from_freq: str = '1min',
    to_freq: str = '5min',
    method: str = 'ohlc'
) -> pd.DataFrame:
    """
    Resampling eficiente de time series.

    Usa resample() de Pandas, no loops.
    """
    if method == 'ohlc':
        return prices.resample(to_freq).ohlc()
    elif method == 'last':
        return prices.resample(to_freq).last()
    elif method == 'mean':
        return prices.resample(to_freq).mean()
    elif method == 'sum':
        return prices.resample(to_freq).sum()
    else:
        raise ValueError(f"Unknown method: {method}")

def efficient_time_shifts(
    data: pd.DataFrame,
    shifts: List[int]
) -> pd.DataFrame:
    """
    Crear múltiples shifted columns eficientemente.
    """
    result = data.copy()

    for shift in shifts:
        result[f'shifted_{shift}'] = data.shift(shift)

    return result
```
