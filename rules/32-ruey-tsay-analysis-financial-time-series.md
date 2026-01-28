# 🟡 32. "Analysis of Financial Time Series" - Ruey Tsay

## REGLAS DE ANÁLISIS DE SERIES TEMPORALES FINANCIERAS

**Regla 32.1 — Modelado GARCH**

Claude DEBE ajustar el apalancamiento si la volatilidad realizada > predicha.

**GARCH(1,1) obligatorio para Crypto/FX.**

```python
def garch_volatility_forecast(
    self,
    returns: pd.Series,
    current_vol: float,
    garch_model: object = None
) -> dict:
    """
    Forecast de volatilidad usando GARCH(1,1).

    Tsay: Si realized > predicted → reducir apalancamiento.
    """
    from arch import arch_model

    # Fit GARCH(1,1) si no existe
    if garch_model is None:
        garch_model = arch_model(
            returns,
            p=1,
            q=1,
            dist='t'  # distribución t-Student para fat tails
        ).fit(disp='off')

    # Forecast
    forecast = garch_model.forecast(horizon=1)
    predicted_vol = np.sqrt(forecast.variance.values[-1, -1])

    # Volatilidad realizada (20 días)
    realized_vol = returns.iloc[-20:].std()

    # Comparar
    vol_ratio = realized_vol / predicted_vol

    if vol_ratio > 1.5:
        logger.warning(
            f"⚠️ Realized vol ({realized_vol:.2%}) "
            f">> GARCH forecast ({predicted_vol:.2%}). "
            f"Reducing leverage."
        )
        leverage_reduction = 0.5

    elif vol_ratio < 0.7:
        logger.info(
            f"Realized vol ({realized_vol:.2%}) "
            f"< GARCH forecast ({predicted_vol:.2%}). "
            f"Can increase leverage."
        )
        leverage_reduction = 1.2

    else:
        leverage_reduction = 1.0

    return {
        'predicted_vol': predicted_vol,
        'realized_vol': realized_vol,
        'vol_ratio': vol_ratio,
        'leverage_adjustment': leverage_reduction,
        'model': garch_model
    }
```

**Regla 32.2 — Fat-Tails Adjustment**

```python
def fat_tailed_var(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    distribution: str = 't'
) -> dict:
    """
    NO usar distribución normal para VaR. Usar t-Student.

    Tsay: Crypto/FX tienen fat tails.
    """
    from scipy import stats

    # Ajustar distribución t-Student
    params_t = stats.t.fit(returns)

    df, loc, scale = params_t

    # VaR con t-Student
    var_t = stats.t.ppf(1 - confidence_level, df, loc, scale)

    # VaR con normal (para comparación)
    var_normal = stats.norm.ppf(
        1 - confidence_level,
        returns.mean(),
        returns.std()
    )

    # Difference
    var_diff_pct = abs(var_t - var_normal) / abs(var_normal)

    logger.info(
        f"VaR ({confidence_level:.0%}): "
        f"t-Student={var_t:.2%}, Normal={var_normal:.2%} "
        f"(diff={var_diff_pct:.1%})"
    )

    # Expected Shortfall (t-Student)
    es_t = stats.t.expect(
        lambda x: x,
        args=(df,),
        lb=-np.inf,
        ub=var_t,
        loc=loc,
        scale=scale
    ) / (1 - confidence_level)

    return {
        'var_student_t': var_t,
        'var_normal': var_normal,
        'var_difference': var_diff_pct,
        'expected_shortfall': es_t,
        'degrees_of_freedom': df,
        'use_student_t': True
    }
```

**Regla 32.3 — Detección de Estacionariedad**

```python
def stationarity_test(
    self,
    price_series: pd.Series,
    significance: float = 0.05
) -> dict:
    """
    Test de Dickey-Fuller antes de Pairs Trading.

    Tsay: NO hacer pairs trading con series no estacionarias.
    """
    from statsmodels.tsa.stattools import adfuller

    # Test ADF
    result = adfuller(price_series, regression='ct')  # con constante y tendencia

    adf_statistic = result[0]
    p_value = result[1]
    critical_values = result[4]

    # Interpretar
    is_stationary = p_value < significance

    logger.info(
        f"ADF Test: Statistic={adf_statistic:.3f}, "
        f"p-value={p_value:.4f}"
    )

    for key, value in critical_values.items():
        logger.info(f"  Critical Value ({key}): {value:.3f}")

    if not is_stationary:
        logger.error(
            f"❌ Series NOT stationary (p={p_value:.4f}). "
            f"Cannot use for mean reversion strategies."
        )

        # Diferenciar para hacer estacionaria
        returns = price_series.pct_change().dropna()

        result_diff = adfuller(returns, regression='c')

        if result_diff[1] < significance:
            logger.info(
                f"✅ First differences ARE stationary (p={result_diff[1]:.4f})"
            )

            return {
                'original_stationary': False,
                'returns_stationary': True,
                'recommendation': 'Use returns instead of prices'
            }

    return {
        'original_stationary': is_stationary,
        'p_value': p_value,
        'adf_statistic': adf_statistic,
        'recommendation': 'Proceed' if is_stationary else 'Differentiate'
    }
```

**Regla 32.4 — Cointegración Dinámica**

```python
def dynamic_cointegration(
    self,
    price_a: pd.Series,
    price_b: pd.Series,
    initial_hedge_ratio: float = None
) -> dict:
    """
    Recalcular hedge ratio cada 24 horas. NO es constante.

    Tsay: Crypto pares (BTC/ETH) tienen hedge ratio dinámico.
    """
    from statsmodels.tsa.coint import coint

    # Test de cointegración
    score, pvalue, crit_values = coint(price_a, price_b)

    is_cointegrated = pvalue < 0.05

    if not is_cointegrated:
        logger.warning(
            f"⚠️ Series NOT cointegrated (p={pvalue:.4f}). "
            f"Pairs trading not appropriate."
        )

        return {
            'cointegrated': False,
            'p_value': pvalue
        }

    # Calcular hedge ratio usando OLS
    import statsmodels.api as sm

    # Regress price_a on price_b
    X = sm.add_constant(price_b)
    model = sm.OLS(price_a, X).fit()

    hedge_ratio = model.params[1]  # Slope
    intercept = model.params[0]  # Intercept (constant)

    # Spread
    spread = price_a - hedge_ratio * price_b - intercept

    # Comparar con hedge ratio anterior
    if initial_hedge_ratio:
        hr_change_pct = abs(hedge_ratio - initial_hedge_ratio) / initial_hedge_ratio

        if hr_change_pct > 0.10:  # > 10% cambio
            logger.warning(
                f"⚠️ Hedge ratio changed {hr_change_pct:.1%}. "
                f"{initial_hedge_ratio:.3f} → {hedge_ratio:.3f}"
            )

    logger.info(
        f"✅ Cointegrated (p={pvalue:.4f}). "
        f"Hedge ratio: {hedge_ratio:.3f}"
    )

    return {
        'cointegrated': True,
        'p_value': pvalue,
        'hedge_ratio': hedge_ratio,
        'intercept': intercept,
        'spread': spread
    }
```

**Regla 32.5 — Autocorrelación de Residuos**

```python
def residual_autocorrelation_check(
    self,
    residuals: pd.Series,
    max_lags: int = 20
) -> dict:
    """
    Si residuos tienen autocorrelación, modelo está "viendo fantasmas".

    Tsay: Autocorrelación = información no capturada.
    """
    from statsmodels.stats.diagnostic import acorr_ljungbox

    # Ljung-Box test
    lb_result = acorr_ljungbox(residuals, lags=max_lags, return_df=True)

    # Chequear significancia
    significant_lags = []

    for lag in range(1, max_lags + 1):
        p_value = lb_result['lb_pvalue'].iloc[lag - 1]

        if p_value < 0.05:
            significant_lags.append(lag)

    if significant_lags:
        logger.error(
            f"❌ Residuals autocorrelated at lags: {significant_lags}. "
            f"Model has uncaptured information."
        )

        return {
            'valid': False,
            'significant_lags': significant_lags,
            'recommendation': 'Add AR terms or improve model'
        }

    logger.info(
        f"✅ No significant autocorrelation in residuals. "
        f"Model adequate."
    )

    return {
        'valid': True,
        'significant_lags': [],
        'recommendation': 'Model is adequate'
    }
```

**Regla 32.6 — Modelos ARCH para Stop Loss**

```python
def arch_based_stop_loss(
    self,
    entry_price: float,
    returns: pd.Series,
    risk_multiplier: float = 2.0
) -> float:
    """
    Ajustar SL basado en varianza condicional, no porcentaje fijo.

    Tsay: ARCH captura clustering de volatilidad.
    """
    from arch import arch_model

    # Fit ARCH/GARCH
    model = arch_model(returns, p=1, q=1, vol='Garch')
    res = model.fit(disp='off')

    # Última volatilidad condicional
    conditional_vol = np.sqrt(res.conditional_volatility.iloc[-1])

    # SL basado en volatilidad condicional
    # Si la vol es alta, SL más ancho
    sl_distance = conditional_vol * risk_multiplier

    stop_loss = entry_price * (1 - sl_distance)

    logger.info(
        f"ARCH-based SL: Entry={entry_price:.2f}, "
        f"Cond_Vol={conditional_vol:.2%}, "
        f"SL={stop_loss:.2f} ({sl_distance:.2%} away)"
    )

    return stop_loss
```

**Regla 32.7 — Threshold Autoregressive (SETAR)**

```python
def setar_model(
    self,
    returns: pd.Series,
    current_regime: str
) -> dict:
    """
    Dividir mercado en dos estados: Baja Vol vs Alta Vol.

    Tsay: SETAR usa parámetros distintos para cada régimen.
    """
    # Clasificar régimen basado en volatilidad
    volatility = returns.rolling(20).std()

    median_vol = volatility.median()

    # Dos regímenes
    low_vol_mask = volatility <= median_vol
    high_vol_mask = volatility > median_vol

    # Returns en cada régimen
    returns_low_vol = returns[low_vol_mask].dropna()
    returns_high_vol = returns[high_vol_mask].dropna()

    # Modelo AR para cada régimen
    from statsmodels.tsa.ar_model import AutoReg

    # Low volatility regime
    if len(returns_low_vol) > 50:
        model_low = AutoReg(returns_low_vol, lags=1).fit()
        mean_low = model_low.params[0]
        ar_coef_low = model_low.params[1]
    else:
        model_low = None
        mean_low = returns_low_vol.mean() if len(returns_low_vol) > 0 else 0
        ar_coef_low = 0

    # High volatility regime
    if len(returns_high_vol) > 50:
        model_high = AutoReg(returns_high_vol, lags=1).fit()
        mean_high = model_high.params[0]
        ar_coef_high = model_high.params[1]
    else:
        model_high = None
        mean_high = returns_high_vol.mean() if len(returns_high_vol) > 0 else 0
        ar_coef_high = 0

    logger.info(
        f"SETAR: Low Vol μ={mean_low:.4f}, φ={ar_coef_low:.3f} | "
        f"High Vol μ={mean_high:.4f}, φ={ar_coef_high:.3f}"
    )

    return {
        'low_vol_model': model_low,
        'high_vol_model': model_high,
        'low_vol_mean': mean_low,
        'high_vol_mean': mean_high,
        'low_vol_ar_coef': ar_coef_low,
        'high_vol_ar_coef': ar_coef_high
    }
```

**Regla 32.8 — Filtro de Kalman**

```python
def kalman_price_filter(
    self,
    prices: pd.Series,
    process_variance: float = 1e-5,
    measurement_variance: float = 1e-3
) -> pd.Series:
    """
    Limpiar precio antes de calcular indicadores.

    Tsay: Kalman filter separa señal de ruido.
    """
    # Kalman filter implementation
    n = len(prices)

    # State (price estimate)
    x = np.zeros(n)

    # State covariance
    P = np.zeros(n)

    # Initial values
    x[0] = prices.iloc[0]
    P[0] = 1.0

    # Kalman gain
    K = np.zeros(n)

    for i in range(1, n):
        # Prediction
        x_pred = x[i - 1]
        P_pred = P[i - 1] + process_variance

        # Update
        K[i] = P_pred / (P_pred + measurement_variance)
        x[i] = x_pred + K[i] * (prices.iloc[i] - x_pred)
        P[i] = (1 - K[i]) * P_pred

    filtered_prices = pd.Series(x, index=prices.index)

    # Calcular cuánto ruido se filtró
    noise_removed = ((prices - filtered_prices).abs() / prices).mean()

    logger.info(
        f"Kalman filter: Removed {noise_removed:.2%} noise "
        f"from price series"
    )

    return filtered_prices
```

**Regla 32.9 — Jump Diffusion**

```python
def jump_diffusion_risk(
    self,
    returns: pd.Series,
    position_size: float,
    leverage: float
) -> dict:
    """
    En Crypto, incorporar probabilidad de Salto en modelo de riesgo.

    Tsay: Merton Jump Diffusion model.
    """
    # Detectar jumps (returns > 3 SD)
    mean = returns.mean()
    std = returns.std()

    jump_threshold = 3 * std

    jumps = returns[abs(returns - mean) > jump_threshold]

    # Parámetros de jump
    jump_intensity = len(jumps) / len(returns)  # λ (lambda)
    jump_mean = jumps.mean()
    jump_std = jumps.std()

    # Simular jump diffusion
    n_simulations = 10000
    n_days = 1

    simulated_returns = []

    for _ in range(n_simulations):
        # Diffusion component
        diffusion = np.random.normal(mean, std, n_days).sum()

        # Jump component (Poisson process)
        num_jumps = np.random.poisson(jump_intensity * n_days)

        if num_jumps > 0:
            jump_sizes = np.random.normal(jump_mean, jump_std, num_jumps)
            jump_component = jump_sizes.sum()
        else:
            jump_component = 0

        total_return = diffusion + jump_component
        simulated_returns.append(total_return)

    simulated_returns = np.array(simulated_returns)

    # VaR con jump diffusion
    var_99 = np.percentile(simulated_returns, 1)

    # Impacto en posición apalancada
    liquidation_threshold = -1.0 / leverage

    liquidation_prob = (simulated_returns < liquidation_threshold).mean()

    if liquidation_prob > 0.01:  # > 1%
        logger.critical(
            f"🚨 High liquidation risk: {liquidation_prob:.1%} "
            f"with {leverage}x leverage"
        )

    return {
        'jump_intensity': jump_intensity,
        'jump_mean': jump_mean,
        'var_with_jumps': var_99,
        'liquidation_probability': liquidation_prob,
        'reduce_leverage': liquidation_prob > 0.01
    }
```

**Regla 32.10 — Skewness Log**

```python
def log_skewness_filter(
    self,
    log_returns: pd.Series,
    max_skewness: float = -0.5
) -> dict:
    """
    Si log-return tiene asimetría negativa, prohibir LONG con apalancamiento.

    Tsay: Skewness negativa = riesgo de crash.
    """
    from scipy.stats import skew

    log_skew = skew(log_returns.dropna())

    logger.info(
        f"Log-return skewness: {log_skew:.3f}"
    )

    if log_skew < max_skewness:
        logger.warning(
            f"⚠️ Negative skewness ({log_skew:.3f}). "
            f"Leveraged LONG positions prohibited."
        )

        return {
            'allow_leveraged_long': False,
            'skewness': log_skew,
            'reason': 'Negative skewness indicates crash risk'
        }

    return {
        'allow_leveraged_long': True,
        'skewness': log_skew
    }
```

**Regla 32.11 — Wavelet Analysis**

```python
def wavelet_noise_detection(
    self,
    prices: pd.Series,
    max_noise_ratio: float = 0.70
) -> dict:
    """
    Descomponer en frecuencias. Si ruido alta freq > 70%, no operar.

    Tsay: Wavelet separa trends de ciclos y ruido.
    """
    import pywt

    # Wavelet decomposition
    wavelet = 'db4'  # Daubechies 4
    level = 4

    # Decompose
    coeffs = pywt.wavedec(prices, wavelet, level=level)

    # Approximation (trend)
    approximation = coeffs[0]

    # Detail coefficients (diferentes frecuencias)
    details = coeffs[1:]

    # Calcular energía de cada componente
    energy_approx = np.sum(approximation ** 2)
    energy_details = [np.sum(d ** 2) for d in details]

    total_energy = energy_approx + sum(energy_details)

    # Ruido de alta frecuencia (último level detail)
    high_freq_noise = energy_details[-1]
    noise_ratio = high_freq_noise / total_energy

    if noise_ratio > max_noise_ratio:
        logger.warning(
            f"⚠️ High frequency noise: {noise_ratio:.1%}. "
            f"Market appears random. No trading."
        )

        return {
            'trade': False,
            'noise_ratio': noise_ratio,
            'reason': 'Market is random noise'
        }

    logger.info(
        f"Wavelet analysis: Noise ratio {noise_ratio:.1%}. "
        f"Market has signal."
    )

    return {
        'trade': True,
        'noise_ratio': noise_ratio,
        'approximation_energy': energy_approx / total_energy,
        'detail_energies': [e / total_energy for e in energy_details]
    }
```

**Regla 32.12 — Análisis Multivariado**

```python
def multivariate_sector_check(
    self,
    asset_returns: pd.Series,
    sector_returns: pd.Series,
    asset_name: str,
    sector_name: str
) -> dict:
    """
    NO mirar el activo solo. Si sector cae y activo sube → anomalía.

    Tsay: Covarianza con sector es importante.
    """
    # Combinar returns
    combined = pd.DataFrame({
        'asset': asset_returns,
        'sector': sector_returns
    }).dropna()

    # Correlación
    correlation = combined['asset'].corr(combined['sector'])

    # Últimos returns
    asset_last_return = combined['asset'].iloc[-1]
    sector_last_return = combined['sector'].iloc[-1]

    # Divergencia
    divergence = asset_last_return - sector_last_return

    # Normalizar divergencia por volatilidad
    asset_std = combined['asset'].std()
    sector_std = combined['sector'].std()

    divergence_zscore = divergence / np.sqrt(asset_std**2 + sector_std**2)

    # Detectar anomalía
    if divergence_zscore > 2.0:
        logger.warning(
            f"⚠️ Anomaly detected: {asset_name} up while {sector_name} down. "
            f"Divergence: {divergence_zscore:.1f} SD"
        )

        return {
            'anomaly': True,
            'correlation': correlation,
            'divergence_zscore': divergence_zscore,
            'action': 'Reduce position (likely mean reversion)'
        }

    logger.info(
        f"Asset moving with sector: "
        f"Correlation={correlation:.2f}, Z-score={divergence_zscore:.1f}"
    )

    return {
        'anomaly': False,
        'correlation': correlation
    }
```

**Regla 32.13 — AIC/BIC Criteria**

```python
def aic_bic_model_selection(
    self,
    returns: pd.Series,
    max_lags: int = 10
) -> dict:
    """
    Usar AIC/BIC para seleccionar número de lags.

    Tsay: Menos es más (evitar overfitting).
    """
    from statsmodels.tsa.ar_model import AutoReg

    aic_values = []
    bic_values = []

    for lag in range(1, max_lags + 1):
        model = AutoReg(returns, lags=lag)
        result = model.fit()

        aic_values.append(result.aic)
        bic_values.append(result.bic)

    # Encontrar mínimo
    best_aic_lag = np.argmin(aic_values) + 1  # +1 porque lags empieza en 1
    best_bic_lag = np.argmin(bic_values) + 1

    logger.info(
        f"Model selection: AIC suggests {best_aic_lag} lags, "
        f"BIC suggests {best_bic_lag} lags"
    )

    # BIC penaliza complejidad más → usar BIC para parsimonia
    recommended_lag = best_bic_lag

    # Fit modelo final
    final_model = AutoReg(returns, lags=recommended_lag).fit()

    logger.info(f"Using {recommended_lag} lags (BIC criterion)")

    return {
        'aic_lag': best_aic_lag,
        'bic_lag': best_bic_lag,
        'recommended_lag': recommended_lag,
        'aic_values': aic_values,
        'bic_values': bic_values,
        'final_model': final_model
    }
```

**Regla 32.14 — Outlier Detection**

```python
def outlier_detection_and_replacement(
    self,
    ohlcv: pd.DataFrame,
    zscore_threshold: float = 5.0
) -> pd.DataFrame:
    """
    Si vela > 5 SD, ignorarla para cálculo de indicadores.

    Tsay: Limpieza de datos es crítica.
    """
    cleaned = ohlcv.copy()

    # Detectar outliers en returns
    returns = cleaned['close'].pct_change()

    mean = returns.mean()
    std = returns.std()

    z_scores = (returns - mean) / std

    outlier_mask = abs(z_scores) > zscore_threshold

    n_outliers = outlier_mask.sum()

    if n_outliers > 0:
        logger.warning(
            f"⚠️ Found {n_outliers} outliers (> {zscore_threshold} SD). "
            f"Replacing with interpolated values."
        )

        # Reemplazar outliers con interpolación
        cleaned.loc[outlier_mask, 'close'] = np.nan
        cleaned['close'] = cleaned['close'].interpolate()

        # Recalcular high/low afectados
        for idx in cleaned[outlier_mask].index:
            # Usar promedio de vecinos
            if idx > 0 and idx < len(cleaned) - 1:
                cleaned.loc[idx, 'high'] = cleaned['close'].iloc[idx-1:idx+1].max()
                cleaned.loc[idx, 'low'] = cleaned['close'].iloc[idx-1:idx+1].min()

    return cleaned
```

**Regla 32.15 — Long Memory (Hurst Exponent)**

```python
def hurst_exponent_analysis(
    self,
    prices: pd.Series,
    min_hurst_for_trend: float = 0.55
) -> dict:
    """
    Solo aplicar estrategias de tendencia si Hurst > 0.55.

    Tsay: Hurst > 0.5 = persistencia (trend).
    """
    def calculate_hurst(series):
        """Calculate Hurst exponent using R/S analysis."""
        n = len(series)

        # Ranges
        max_lag = int(n / 2)
        lags = range(2, max_lag)

        # Calculate R/S for each lag
        rs_values = []

        for lag in lags:
            # Create subseries
            subset = series[:lag]

            # Cumulative deviation
            mean = np.mean(subset)
            cumulative_deviation = np.cumulate(subset - mean)

            # Range
            r = np.max(cumulative_deviation) - np.min(cumulative_deviation)

            # Standard deviation
            s = np.std(subset)

            if s > 0:
                rs_values.append(r / s)

        # Fit line to log(R/S) vs log(lag)
        log_lags = np.log(list(lags))
        log_rs = np.log(rs_values)

        # Linear regression
        slope, _ = np.polyfit(log_lags, log_rs, 1)

        return slope  # Hurst exponent

    # Calculate on returns (more stationary)
    returns = prices.pct_change().dropna()

    hurst = calculate_hurst(returns.values)

    logger.info(
        f"Hurst exponent: {hurst:.3f}"
    )

    if hurst > 0.65:
        logger.info("Strong persistence → Trend following strategies")
        recommendation = 'TREND_FOLLOWING'

    elif hurst > min_hurst_for_trend:
        logger.info("Moderate persistence → Trend strategies OK")
        recommendation = 'TREND_FOLLOWING'

    elif hurst < 0.45:
        logger.info("Anti-persistence → Mean reversion strategies")
        recommendation = 'MEAN_REVERSION'

    else:
        logger.info("Random walk → No directional edge")
        recommendation = 'NO_DIRECTIONAL_STRATEGY'

    return {
        'hurst_exponent': hurst,
        'recommendation': recommendation,
        'use_trend_strategy': hurst > min_hurst_for_trend,
        'use_mean_reversion': hurst < 0.45
    }
```
