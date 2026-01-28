# 📘 12. "Expected Returns" - Antti Ilmanen

## REGLAS DE ROBUSTEZ TEMPORAL

**Regla 12.1 — Robustez temporal**

Claude DEBE probar la estrategia en:
- distintos periodos
- distintos activos

**Estrategias mono-régimen → rechazadas.**

```python
def validate_temporal_robustness(
    self,
    strategy: Strategy,
    test_periods: List[tuple],
    min_successful_periods: int = 3
) -> bool:
    """
    Probar estrategia en múltiples periodos de mercado.

    Ilmanen: Estrategia debe funcionar en bull, bear, sideways markets.
    """
    successful_periods = 0

    for period_name, (start, end) in test_periods:
        result = self.backtest(
            strategy,
            start_date=start,
            end_date=end
        )

        # Métricas de éxito
        sharpe = result.sharpe_ratio
        max_dd = result.max_drawdown

        if sharpe > 0.5 and max_dd < 0.25:
            successful_periods += 1
            logger.info(
                f"✅ {period_name}: Sharpe={sharpe:.2f}, DD={max_dd:.1%}"
            )
        else:
            logger.warning(
                f"❌ {period_name}: Sharpe={sharpe:.2f}, DD={max_dd:.1%}"
            )

    success_rate = successful_periods / len(test_periods)

    if success_rate < 0.5:
        logger.error(
            f"❌ Low temporal robustness: {successful_periods}/{len(test_periods)} periods passed"
        )
        return False

    logger.info(f"✅ Temporal robustness OK: {success_rate:.0%} periods passed")
    return True
```

**Regla 12.2 — Correlation penalty**

```python
def apply_correlation_penalty(
    self,
    signals: pd.Series,
    correlation_matrix: pd.DataFrame,
    max_correlation: float = 0.7,
    penalty_factor: float = 0.5
) -> pd.Series:
    """
    Penalizar señales altamente correlacionadas.

    Ilmanen: Diversificación real = baja correlación.
    """
    adjusted_signals = signals.copy()

    for asset_i in signals.index:
        for asset_j in signals.index:
            if asset_i >= asset_j:
                continue

            corr = correlation_matrix.loc[asset_i, asset_j]

            # Si correlación alta → penalizar ambos
            if abs(corr) > max_correlation:
                penalty = penalty_factor * (abs(corr) - max_correlation)

                adjusted_signals[asset_i] *= (1 - penalty)
                adjusted_signals[asset_j] *= (1 - penalty)

                logger.debug(
                    f"Correlation penalty: {asset_i}/{asset_j}={corr:.2f}, "
                    f"penalty={penalty:.2%}"
                )

    return adjusted_signals
```

**Regla 12.3 — Feature explosion penalty**

```python
def validate_feature_explosion(
    self,
    features: pd.DataFrame,
    max_correlation: float = 0.9
) -> bool:
    """
    Limitar features correlacionados (Feature Explosion).

    Ilmanen: Demasiados features correlacionados = overfitting.
    """
    # Calcular matriz de correlación
    corr = features.corr().abs()

    # Check si hay correlación excesiva
    high_corr_count = (corr > max_correlation).sum().sum() - len(corr)

    if high_corr_count > 0:
        logger.warning(
            f"⚠️ Feature explosion: {high_corr_count} pairs "
            f"with correlation > {max_correlation:.0%}"
        )

        # Identificar pares problemáticos
        for i in range(len(corr.columns)):
            for j in range(i+1, len(corr.columns)):
                if corr.iloc[i, j] > max_correlation:
                    logger.warning(
                        f"   {corr.columns[i]} ↔ {corr.columns[j]} = "
                        f"{corr.iloc[i, j]:.2f}"
                    )

        return False

    return True
```

**Regla 12.4 — Regime detection**

```python
def detect_market_regime(
    self,
    market_prices: pd.Series,
    lookback_days: int = 252
) -> str:
    """
    Detectar régimen de mercado: Bull, Bear, Volatile, Stable.

    Ilmanen: Estrategias deben adaptarse a regímenes.
    """
    returns = market_prices.pct_change().iloc[-lookback_days:]

    # Trend
    total_return = (1 + returns).prod() - 1

    # Volatility
    volatility = returns.std() * np.sqrt(252)

    # Clasificar régimen
    if total_return > 0.10 and volatility < 0.20:
        regime = "BULL_STABLE"
    elif total_return > 0.10 and volatility >= 0.20:
        regime = "BULL_VOLATILE"
    elif total_return < -0.05:
        regime = "BEAR"
    elif volatility > 0.25:
        regime = "HIGH_VOLATILITY"
    else:
        regime = "SIDEWAYS"

    logger.info(f"Market regime: {regime} (return={total_return:.1%}, vol={volatility:.1%})")

    return regime
```

**Regla 12.5 — Regime-aware strategy allocation**

```python
def regime_aware_allocation(
    self,
    strategies: Dict[str, Strategy],
    current_regime: str
) -> pd.Series:
    """
    Asignar capital basado en régimen de mercado.

    Ilmanen: No todas las estrategias funcionan en todos los regímenes.
    """
    # Regime-strategy mapping
    regime_weights = {
        "BULL_STABLE": {
            "momentum": 0.5,
            "value": 0.3,
            "carry": 0.2
        },
        "BULL_VOLATILE": {
            "momentum": 0.4,
            "value": 0.4,
            "carry": 0.2
        },
        "BEAR": {
            "momentum": 0.1,
            "value": 0.3,
            "trend_following": 0.4,
            "defensive": 0.2
        },
        "HIGH_VOLATILITY": {
            "momentum": 0.3,
            "value": 0.3,
            "mean_reversion": 0.4
        },
        "SIDEWAYS": {
            "momentum": 0.2,
            "value": 0.3,
            "mean_reversion": 0.3,
            "carry": 0.2
        }
    }

    weights = regime_weights.get(current_regime, {})

    return pd.Series(weights)
```

**Regla 12.6 — Long-horizon forecasting**

```python
def validate_long_horizon(
    self,
    returns: pd.Series,
    min_horizon_years: int = 5
) -> bool:
    """
    Validar estrategia en horizonte largo (5+ años).

    Ilmanen: Short-term performance puede ser lucky.
    """
    n_years = len(returns) / 252

    if n_years < min_horizon_years:
        logger.error(
            f"❌ Insufficient history: {n_years:.1f} years "
            f"< {min_horizon_years} years required"
        )
        return False

    # Analizar por años individuales
    yearly_returns = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)

    successful_years = (yearly_returns > 0).sum()

    logger.info(
        f"Long-horizon validation: {successful_years}/{len(yearly_returns)} "
        f"years profitable"
    )

    return successful_years >= len(yearly_returns) * 0.6
```

**Regla 12.7 — Cross-sectional consistency**

```python
def validate_cross_sectional(
    self,
    strategy_results: pd.DataFrame,  # columns: asset, return, sharpe
    min_success_rate: float = 0.6
) -> bool:
    """
    Validar consistencia cross-sectional.

    Ilmanen: Estrategia debe funcionar en mayoría de activos.
    """
    # Sharpe ratio por activo
    successful_assets = (strategy_results['sharpe'] > 0.5).sum()
    total_assets = len(strategy_results)

    success_rate = successful_assets / total_assets

    if success_rate < min_success_rate:
        logger.error(
            f"❌ Low cross-sectional success: {successful_assets}/{total_assets} "
            f"assets ({success_rate:.0%}) have Sharpe > 0.5"
        )
        return False

    logger.info(
        f"✅ Cross-sectional success: {success_rate:.0%} of assets profitable"
    )

    return True
```

**Regla 12.8 — Robustez > Performance (Meta-regla)**

```python
def prefer_robustness_over_performance(
    self,
    strategy_a: dict,  # {"sharpe": 2.0, "robustness": 0.4}
    strategy_b: dict   # {"sharpe": 1.5, "robustness": 0.8}
) -> str:
    """
    Elegir estrategia basado en robustez, no solo performance.

    Ilmanen: Performance alta pero frágil → rechazar.

    Robustez score = consistencia temporal × consistencia cross-sectional
    """
    def score(strategy):
        # Performance score
        perf_score = min(strategy["sharpe"] / 2.0, 1.0)

        # Robustness score
        robust_score = strategy["robustness"]

        # Trade-off: preferir robustez
        combined = robust_score * 0.7 + perf_score * 0.3

        return combined

    score_a = score(strategy_a)
    score_b = score(strategy_b)

    logger.info(
        f"Strategy A: Sharpe={strategy_a['sharpe']:.2f}, "
        f"Robustness={strategy_a['robustness']:.2f}, Score={score_a:.2f}"
    )
    logger.info(
        f"Strategy B: Sharpe={strategy_b['sharpe']:.2f}, "
        f"Robustness={strategy_b['robustness']:.2f}, Score={score_b:.2f}"
    )

    return "A" if score_a > score_b else "B"
```

**Regla 12.9 — Carry trade implementation**

```python
def carry_trade_signal(
    self,
    spot_rate: float,
    forward_rate: float,
    interest_rate_diff: float
) -> float:
    """
    Carry trade signal = interest rate differential - forward premium.

    Ilmanen: Carry = diferencia de tasas - prima forward.
    """
    # Forward premium
    forward_premium = (forward_rate - spot_rate) / spot_rate

    # Carry
    carry = interest_rate_diff - forward_premium

    # Signal basado en carry positivo
    if carry > 0.01:  # >1% carry
        return np.tanh(carry * 10)
    elif carry < -0.01:
        return np.tanh(carry * 10)  # Short carry
    else:
        return 0.0
```

**Regla 12.10 — Value signal robusto**

```python
def value_signal_robust(
    self,
    metrics: dict,
    historical_percentiles: dict
) -> float:
    """
    Value signal usando múltiples métricas.

    Ilmanen: Un solo metric (P/E) es frágil.
    """
    # Multiple value metrics
    pe_ratio = metrics.get('pe', 0)
    pb_ratio = metrics.get('pb', 0)
    dividend_yield = metrics.get('dividend_yield', 0)

    # Normalizar por percentiles históricos
    pe_percentile = historical_percentiles['pe'].rank(pe_ratio) / len(historical_percentiles['pe'])
    pb_percentile = historical_percentiles['pb'].rank(pb_ratio) / len(historical_percentiles['pb'])

    # Dividend yield: higher = better
    div_percentile = historical_percentiles['dividend_yield'].rank(dividend_yield) / len(historical_percentiles['dividend_yield'])

    # Combined value score
    # Low PE/PB = cheap, High dividend = cheap
    value_score = (1 - pe_percentile) * 0.4 + (1 - pb_percentile) * 0.3 + div_percentile * 0.3

    # Convertir a señal [-1, 1]
    signal = (value_score - 0.5) * 2

    return signal
```
