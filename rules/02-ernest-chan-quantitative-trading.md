# 📕 2. "Quantitative Trading" - Ernest P. Chan

## REGLAS DE DISEÑO DE ESTRATEGIAS

**Mean Reversion: Half-life debe ser < 1 año**

```python
def calculate_half_life(self, prices: np.array) -> float:
    """Half-life de mean reversion usando AR(1)."""
    price_lag = np.roll(prices, 1)[1:]
    price_diff = np.diff(prices)

    # Regresión: price_diff = lambda * price_lag + epsilon
    lambda_coef = np.polyfit(price_lag, price_diff, 1)[0]

    half_life = -np.log(2) / lambda_coef

    if half_life > 252:  # > 1 año
        logger.warning("⚠️ Half-life > 1 year - Mean reversion too slow")
        return None

    return half_life
```

**Hurst Exponent: H < 0.5 = mean reversion, H > 0.5 = trending**

```python
def hurst_exponent(self, prices: np.array) -> float:
    """Hurst exponent para detectar mean reversion vs trending."""
    lags = range(2, 20)
    tau = [np.std(np.subtract(prices[lag:], prices[:-lag])) for lag in lags]

    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    hurst = poly[0] * 2.0

    return hurst

# Uso
h = hurst_exponent(prices)
if h < 0.5:
    strategy_type = "MEAN_REVERSION"
elif h > 0.5:
    strategy_type = "MOMENTUM"
else:
    strategy_type = "RANDOM_WALK"  # No tradeable
```

**Stationarity Test: Augmented Dickey-Fuller**

```python
from statsmodels.tsa.stattools import adfuller

def is_stationary(self, prices: np.array) -> bool:
    """Test si serie es estacionaria (requerido para mean reversion)."""
    result = adfuller(prices)
    p_value = result[1]

    if p_value < 0.05:
        logger.info("✅ Series is stationary (p-value: {p_value:.4f})")
        return True
    else:
        logger.warning("⚠️ Series is NOT stationary (p-value: {p_value:.4f})")
        return False
```

**Calmar Ratio > 1.0 para estrategias aceptables**

```python
def calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
    """Calmar = Annual Return / Max Drawdown."""
    if max_drawdown == 0:
        return float('inf')

    calmar = annual_return / abs(max_drawdown)

    if calmar < 1.0:
        logger.warning(f"⚠️ Calmar ratio {calmar:.2f} < 1.0 threshold")

    return calmar
```

**NUNCA uses data mining sin validación estadística**

```python
def bonferroni_correction(self, p_values: List[float]) -> List[float]:
    """Ajustar p-values para múltiples tests."""
    n_tests = len(p_values)
    corrected = [min(p * n_tests, 1.0) for p in p_values]

    return corrected

# Ejemplo
raw_pvalues = [0.01, 0.03, 0.04]  # 3 estrategias testeadas
corrected = bonferroni_correction(raw_pvalues)
# [0.03, 0.09, 0.12] - Solo la primera sigue siendo significativa
```

**Entry/Exit timing: Espera confirmación**

```python
def confirm_signal(self, signal: str, prices: List[float]) -> bool:
    """NO entrar inmediatamente - esperar confirmación."""
    if signal == "BUY":
        # Esperar 2 días consecutivos de subida
        return prices[-1] > prices[-2] and prices[-2] > prices[-3]
    elif signal == "SELL":
        # Esperar 2 días consecutivos de bajada
        return prices[-1] < prices[-2] and prices[-2] < prices[-3]
    else:
        return False
```

**Backtesting period: Mínimo 5 años de datos**

```python
MIN_BACKTEST_DAYS = 252 * 5  # 5 años

def validate_data_sufficiency(self, quotes: List[Quote]) -> bool:
    """Verificar suficientes datos para backtest."""
    if len(quotes) < MIN_BACKTEST_DAYS:
        logger.error(f"❌ Insufficient data: {len(quotes)} days < {MIN_BACKTEST_DAYS} required")
        return False

    return True
```

**Walk-Forward Optimization: 70/30 train/test split**

```python
def walk_forward_optimize(
    self,
    quotes: List[Quote],
    param_ranges: Dict[str, tuple]
) -> Dict:
    """Optimizar con walk-forward para evitar overfitting."""
    results = []

    # Ventana móvil: 70% train, 30% test
    train_size = int(len(quotes) * 0.7)

    for start_idx in range(0, len(quotes) - train_size, 90):  # Step cada 3 meses
        train_data = quotes[start_idx:start_idx + train_size]
        test_data = quotes[start_idx + train_size:start_idx + train_size + 90]

        # Optimizar en train
        best_params = self.optimize(train_data, param_ranges)

        # Validar en test
        test_result = self.backtest(test_data, best_params)
        results.append(test_result)

    # Promedio de resultados
    avg_sharpe = np.mean([r.sharpe_ratio for r in results])

    return {"avg_sharpe": avg_sharpe, "windows": results}
```

**NUNCA uses más de 3-4 parámetros optimizables**

```python
def validate_parameter_count(self, params: Dict) -> bool:
    """Demasiados parámetros = overfitting."""
    if len(params) > 4:
        logger.error(f"❌ Too many parameters ({len(params)}) - Max 4 recommended")
        return False

    return True
```

**Transaction frequency: 1-10 trades/month es óptimo**

```python
def validate_trade_frequency(self, trades: List[Trade], days: int) -> bool:
    """Verificar frecuencia de trading razonable."""
    trades_per_month = len(trades) / (days / 30)

    if trades_per_month < 1:
        logger.warning("⚠️ < 1 trade/month - Strategy too inactive")
        return False

    if trades_per_month > 10:
        logger.warning("⚠️ > 10 trades/month - High transaction costs")

    return True
```

**SIEMPRE testea en múltiples mercados**

```python
def cross_market_validation(self, symbols: List[str]) -> bool:
    """Estrategia debe funcionar en múltiples instrumentos."""
    successful_markets = 0

    for symbol in symbols:
        quotes = self.get_quotes(symbol)
        result = self.backtest(quotes)

        if result.sharpe_ratio > 1.0:
            successful_markets += 1

    success_rate = successful_markets / len(symbols)

    if success_rate < 0.6:  # Al menos 60% de mercados
        logger.warning(f"⚠️ Only {success_rate:.0%} markets profitable")
        return False

    return True
```

**Rebalancing: No más frecuente que mensual**

```python
def should_rebalance(self, last_rebalance: datetime) -> bool:
    """Rebalancear max 1 vez al mes (evitar churning)."""
    days_since_rebalance = (datetime.now() - last_rebalance).days

    return days_since_rebalance >= 30
```
