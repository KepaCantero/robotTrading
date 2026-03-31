# 📄 Papers Fundamentales - Rough Volatility (Bayer, Friz & Gatheral, 2016)

## Matemática Fractal para Gestión de Riesgos y Volatilidad Rugosa

**Contexto:** Advanced Risk Management y Volatility Modeling.

Bayer et al. revolucionaron la modelización de volatilidad al demostrar que la volatilidad es un proceso "rugoso" con memoria larga, no un proceso difusivo standard.

---

### Regla 1 — Fractional Brownian Motion (fBm)

Modelar la log-volatilidad usando fBm con Hurst H < 0.5.

```python
def fractional_brownian_motion(
    self,
    n_steps: int,
    hurst: float = 0.1,
    dt: float = 1/252
) -> np.ndarray:
    """
    Simular fBm para volatilidad rugosa.

    Bayer: H < 0.5 = anti-persistencia (rough).
    """
    # Método de Cholesky simplificado (para producción usar circulant)
    # Generar fBm usando el método de Davies-Harte

    # Autocovarianza de fBm
    def fbm_covariance(i, j, h):
        return 0.5 * (i**(2*h) + j**(2*h) - abs(i-j)**(2*h))

    # Matriz de covarianza
    n = n_steps
    cov_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            cov_matrix[i, j] = fbm_covariance(i, j, hurst)

    # Cholesky
    L = np.linalg.cholesky(cov_matrix + 1e-8 * np.eye(n))

    # Simular
    Z = np.random.standard_normal(n)
    fbm = L @ Z

    # Escalar por dt^H
    fbm_scaled = fbm * (dt ** hurst)

    logger.info(
        f"fBm generated: H={hurst}, steps={n_steps}, "
        f"rough={'YES' if hurst < 0.5 else 'NO'}"
    )

    return fbm_scaled
```

### Regla 2 — Hurst Exponent Estimation

Estimar H diariamente usando R/S analysis o variogramas.

```python
def estimate_hurst_exponent(
    self,
    time_series: pd.Series,
    method: str = 'rs'
) -> dict:
    """
    Estimar exponente de Hurst H.

    Bayer: H < 0.1 → extremadamente rugoso.
    """
    if method == 'rs':
        # R/S Analysis (Range over Standard Deviation)
        n = len(time_series)

        # Ranges de diferentes tamaños
        max_lag = int(n / 2)
        lags = range(10, max_lag, 10)

        rs_values = []

        for lag in lags:
            # Subseries
            subset = time_series[:lag]

            # Rango
            mean = subset.mean()
            cumulative_dev = (subset - mean).cumsum()
            r = cumulative_dev.max() - cumulative_dev.min()

            # Standard deviation
            s = subset.std()

            if s > 0:
                rs_values.append(r / s)

        # Fit log-log
        log_lags = np.log(list(lags))
        log_rs = np.log(rs_values)

        slope, _ = np.polyfit(log_lags, log_rs, 1)
        hurst = slope

    elif method == 'variogram':
        # Variogram method
        max_lag = int(len(time_series) / 4)
        lags = range(1, max_lag)

        variogram = []

        for lag in lags:
            diff = (time_series.values[lag:] - time_series.values[:-lag]) ** 2
            variogram.append(diff.mean())

        # Fit: variogram ~ lag^(2H)
        log_lags = np.log(list(lags))
        log_vario = np.log(variogram)

        slope, _ = np.polyfit(log_lags, log_vario, 1)
        hurst = slope / 2

    logger.info(
        f"Hurst exponent: H={hurst:.3f} "
        f"({'Rough' if hurst < 0.5 else 'Smooth'})"
    )

    return {
        'hurst': hurst,
        'rough': hurst < 0.5,
        'method': method
    }
```

### Regla 3 — Rough Volatility Simulation

Simular trayectorias de volatilidad rugosa usando el modelo R-Bergomi.

```python
def simulate_rough_volatility(
    self,
    n_steps: int = 252,
    hurst: float = 0.1,
    xi: float = 0.235,  # Parámetro de volatilidad inicial
    eta: float = 1.9,   # Vol of vol
    dt: float = 1/252
) -> dict:
    """
    Simular volatilidad rugosa (Rough Bergomi).

    Bayer: R-Bergomi = modelo de rough volatility.
    """
    # Simular fBm para la volatilidad
    dW = np.random.standard_normal(n_steps) * np.sqrt(dt)

    # Volatilidad integrada rough
    # V_t = xi * exp(eta * W_t^H - 0.5 * eta^2 * t^(2H))

    t = np.arange(n_steps) * dt

    # fBm para la volatilidad
    W_H = self.fractional_brownian_motion(n_steps, hurst, dt)

    # Volatilidad
    V = xi * np.exp(
        eta * W_H -
        0.5 * eta**2 * t**(2*hurst)
    )

    # Precio (SDE rough)
    S = np.zeros(n_steps)
    S[0] = 100

    for i in range(1, n_steps):
        drift = 0
        diffusion = np.sqrt(V[i]) * dW[i]
        S[i] = S[i-1] * (1 + drift * dt + diffusion)

    logger.info(
        f"Rough vol simulated: H={hurst}, "
        f"V_mean={V.mean():.4f}, V_std={V.std():.4f}"
    )

    return {
        'prices': S,
        'volatility': V,
        'fbm': W_H,
        'hurst': hurst
    }
```

### Regla 4 — Anti-Persistence Detection

Detectar anti-persistencia para predecir reversión rápida de vol.

```python
def detect_anti_persistence(
    self,
    volatility: pd.Series,
    threshold_hurst: float = 0.2
) -> dict:
    """
    Detectar anti-persistencia en volatilidad.

    Bayer: Anti-persistencia → reversión rápida.
    """
    hurst = self.estimate_hurst_exponent(volatility)['hurst']

    if hurst < threshold_hurst:
        anti_persistent = True

        # Predecir reversión
        # Si vol subió mucho, esperamos que baje pronto

        recent_change = (
            volatility.iloc[-1] - volatility.iloc[-5:]
        ).mean() / volatility.iloc[-5:].mean()

        if recent_change > 0.2:  # Vol subió > 20%
            prediction = 'vol_decrease'
            confidence = 1 - hurst/threshold_hurst

        elif recent_change < -0.2:  # Vol bajó > 20%
            prediction = 'vol_increase'
            confidence = 1 - hurst/threshold_hurst

        else:
            prediction = 'neutral'
            confidence = 0.5

    else:
        anti_persistent = False
        prediction = 'neutral'
        confidence = 0.5

    logger.info(
        f"Anti-persistence: {anti_persistent}, "
        f"Prediction={prediction}, Conf={confidence:.2%}"
    )

    return {
        'anti_persistent': anti_persistent,
        'hurst': hurst,
        'prediction': prediction,
        'confidence': confidence
    }
```

### Regla 5 — Power-Law Volatility Decay

El spread de volatilidad decae con ley de potencia según tiempo.

```python
def power_law_volatility_skew(
    self,
    ttm: np.ndarray,  # Time to maturity
    xi: float = 0.235,
    eta: float = 1.9,
    rho: float = -0.9,  # Correlación precio-vol
    hurst: float = 0.1
) -> dict:
    """
    Calcular skew de volatilidad con decaimiento power-law.

    Bayer: Skew ~ ttm^(H - 0.5).
    """
    # ATM vol
    atm_vol = xi * ttm ** (hurst - 0.5)

    # Skew slope (simplificado)
    skew_slope = eta * rho * ttm ** (hurst - 0.5)

    logger.info(
        f"Power-law skew: ATM={atm_vol:.3f}, "
        f"Slope={skew_slope:.3f} @ ttm={ttm.mean():.2f}"
    )

    return {
        'atm_volatility': atm_vol,
        'skew_slope': skew_slope,
        'roughness_exponent': hurst - 0.5
    }
```

### Regla 6 — Volatility Forecasting with Roughness

Usar la rugosidad para predecir picos de volatilidad a corto plazo.

```python
def forecast_rough_volatility(
    self,
    historical_vol: pd.Series,
    forecast_horizon: int = 5  # días
) -> dict:
    """
    Forecast de vol usando propiedades rough.

    Bayer: Rough = mean reversion rápida.
    """
    hurst = self.estimate_hurst_exponent(historical_vol)['hurst']

    # Si H es bajo, la vol tiende a revertir
    # Forecast = regresión a la media de largo plazo

    long_term_vol = historical_vol.rolling(252).mean().iloc[-1]
    current_vol = historical_vol.iloc[-1]

    # Velocidad de reversión ~ (1 - H)
    reversion_speed = 1 - hurst

    # Forecast exponencial a la media
    forecast = []

    for h in range(1, forecast_horizon + 1):
        # Vol_h = long_term + (current - long_term) * exp(-speed * h)
        vol_h = long_term_vol + (current_vol - long_term_vol) * np.exp(-reversion_speed * h)
        forecast.append(vol_h)

    forecast = pd.Series(forecast)

    logger.info(
        f"Rough vol forecast: H={hurst:.3f}, "
        f"Current={current_vol:.3f}, "
        f"Mean={long_term_vol:.3f}, "
        f"Forecast[{forecast_horizon}d]={forecast.iloc[-1]:.3f}"
    )

    return {
        'hurst': hurst,
        'reversion_speed': reversion_speed,
        'current_vol': current_vol,
        'long_term_vol': long_term_vol,
        'forecast': forecast
    }
```

### Regla 7 — Leverage Effect with Roughness

Incorporar la correlación negativa fuerte entre precio y vol.

```python
def rough_leverage_effect(
    self,
    returns: pd.Series,
    volatility: pd.Series
) -> dict:
    """
    Calcular leverage effect ajustado por roughness.

    Bayer: Leverage es más fuerte en mercados rugosos.
    """
    # Correlación rolling
    window = 20
    rolling_corr = returns.rolling(window).corr(volatility)

    current_corr = rolling_corr.iloc[-1]

    # Ajuste por roughness
    hurst_returns = self.estimate_hurst_exponent(returns)['hurst']
    hurst_vol = self.estimate_hurst_exponent(volatility)['hurst']

    # Leverage más fuerte cuando ambos son rough
    rough_leverage = -1 * (1 - hurst_returns) * (1 - hurst_vol)

    # Expected correlation negativa
    expected_corr = rough_leverage

    logger.info(
        f"Leverage effect: Actual corr={current_corr:.3f}, "
        f"Expected={expected_corr:.3f} "
        f"(H_r={hurst_returns:.3f}, H_v={hurst_vol:.3f})"
    )

    return {
        'current_correlation': current_corr,
        'expected_correlation': expected_corr,
        'leverage_strength': abs(rough_leverage),
        'hurst_returns': hurst_returns,
        'hurst_volatility': hurst_vol
    }
```

### Regla 8 — Option Pricing with Rough Vol

Pricer de opciones usando volatilidad rugosa (R-Bergomi).

```python
def rough_bergomi_pricer(
    self,
    S: float,
    K: float,
    T: float,
    r: float,
    xi: float = 0.235,
    eta: float = 1.9,
    rho: float = -0.9,
    hurst: float = 0.1,
    n_simulations: int = 10000
) -> dict:
    """
    Pricer de opciones europeas con R-Bergomi.

    Bayer: Rough volatility = pricing más preciso.
    """
    # Simular n trayectorias
    n_steps = int(T * 252)

    payoffs = []

    for _ in range(n_simulations):
        # Simular rough vol
        sim = self.simulate_rough_volatility(
            n_steps=n_steps,
            hurst=hurst,
            xi=xi,
            eta=eta
        )

        S_path = sim['prices']
        S_T = S_path[-1]

        # Payoff
        payoff = max(S_T - K, 0)  # Call
        payoffs.append(payoff)

    payoffs = np.array(payoffs)

    # Precio = discounted expected payoff
    option_price = np.exp(-r * T) * payoffs.mean()

    # Std error
    std_error = payoffs.std() / np.sqrt(n_simulations)

    logger.info(
        f"R-Bergomi price: {option_price:.4f} "
        f"± {std_error:.4f} (S={S}, K={K}, T={T})"
    )

    return {
        'price': option_price,
        'std_error': std_error,
        'parameters': {
            'hurst': hurst,
            'xi': xi,
            'eta': eta,
            'rho': rho
        }
    }
```

### Regla 9 — Roughness Regime Detection

Detectar cambios en el régimen de rugosidad del mercado.

```python
def detect_roughness_regime(
    self,
    returns: pd.Series,
    window: int = 60
) -> dict:
    """
    Detectar cambios en rugosidad (H).

    Bayer: Cambios de régimen = recalibración necesaria.
    """
    hurst_rolling = []

    for i in range(window, len(returns)):
        subset = returns.iloc[i-window:i]
        hurst = self.estimate_hurst_exponent(subset)['hurst']
        hurst_rolling.append(hurst)

    hurst_rolling = pd.Series(hurst_rolling)

    # Regímenes
    mean_hurst = hurst_rolling.mean()
    std_hurst = hurst_rolling.std()
    current_hurst = hurst_rolling.iloc[-1]

    # Clasificar
    if current_hurst < mean_hurst - 2 * std_hurst:
        regime = 'VERY_ROUGH'
        description = 'Extremely rough, high mean reversion'
    elif current_hurst < mean_hurst - std_hurst:
        regime = 'ROUGH'
        description = 'Below average roughness'
    elif current_hurst > mean_hurst + 2 * std_hurst:
        regime = 'SMOOTH'
        description = 'Trending behavior'
    elif current_hurst > mean_hurst + std_hurst:
        regime = 'NORMAL_SMOOTH'
        description = 'Above average smoothness'
    else:
        regime = 'NORMAL'
        description = 'Average roughness'

    logger.info(
        f"Roughness regime: {regime} (H={current_hurst:.3f})"
    )

    return {
        'regime': regime,
        'description': description,
        'hurst': current_hurst,
        'hurst_mean': mean_hurst,
        'hurst_std': std_hurst
    }
```

### Regla 10 — Fat-Tail Integration

El modelo rough genera colas más pesadas que Black-Scholes.

```python
def rough_fat_tail_adjustment(
    self,
    returns: pd.Series,
    hurst: float = None
) -> dict:
    """
    Ajustar risk models por colas pesadas de rough vol.

    Bayer: Rough → fatter tails than Gaussian.
    """
    if hurst is None:
        hurst = self.estimate_hurst_exponent(returns)['hurst']

    # Kurtosis esperada aumenta cuando H disminuye
    # Kurtosis ~ 1 / H (aprox)

    expected_kurtosis = 3 / max(hurst, 0.05)

    # Kurtosis empírica
    from scipy.stats import kurtosis
    empirical_kurtosis = kurtosis(returns, fisher=False)

    # Ajuste de VaR
    # VaR_rough = VaR_normal * sqrt(kurtosis_empírica / 3)

    var_normal = returns.quantile(0.01)
    var_rough_adjusted = var_normal * np.sqrt(empirical_kurtosis / 3)

    logger.info(
        f"Fat tail: H={hurst:.3f}, "
        f"Kurt_emp={empirical_kurtosis:.1f}, "
        f"Kurt_exp={expected_kurtosis:.1f}, "
        f"VaR_adj={var_rough_adjusted:.3f} vs {var_normal:.3f}"
    )

    return {
        'hurst': hurst,
        'empirical_kurtosis': empirical_kurtosis,
        'expected_kurtosis': expected_kurtosis,
        'var_normal': var_normal,
        'var_rough_adjusted': var_rough_adjusted,
        'adjustment_factor': empirical_kurtosis / 3
    }
```

### Regla 11 — Hedging Error Minimization

Ajustar frecuencia de rebalanceo según rugosidad.

```python
def optimal_hedging_frequency_rough(
    self,
    hurst: float,
    transaction_cost: float = 0.001
) -> dict:
    """
    Calcular frecuencia óptima de hedging con rough vol.

    Bayer: Más rough → más frecuente el rebalanceo.
    """
    # Trade-off: rebalance cost vs hedging error
    # Hedging error ~ dt^(2H)
    # Transaction cost ~ 1/dt

    # Optimizar: total cost = a * dt^(2H) + b / dt

    def total_cost(dt, H, a=1, b=transaction_cost):
        hedging_error = a * dt ** (2 * H)
        tx_cost = b / dt
        return hedging_error + tx_cost

    # Grid search para dt óptimo
    dt_values = np.logspace(-5, -1, 100)  # 1s a 0.1 día

    costs = [total_cost(dt, hurst) for dt in dt_values]
    optimal_dt = dt_values[np.argmin(costs)]

    # Frecuencia en minutos
    freq_minutes = optimal_dt * 24 * 60

    logger.info(
        f"Optimal hedging: H={hurst:.3f}, "
        f"dt={optimal_dt:.4f} ({freq_minutes:.1f} min)"
    )

    return {
        'hurst': hurst,
        'optimal_dt': optimal_dt,
        'frequency_minutes': freq_minutes,
        'total_cost': min(costs)
    }
```

### Regla 12 — Rough Volatility Surface

Calibrar superficie de volatilidad consistente con rough vol.

```python
def calibrate_rough_vol_surface(
    self,
    market_vols: dict,  # {(ttm, strike): vol}
    S: float,
    r: float
) -> dict:
    """
    Calibrar parámetros R-Bergomi a superficie de mercado.

    Bayer: Rough parameters fitted to smile.
    """
    from scipy.optimize import minimize

    def objective(params):
        xi, eta, rho, hurst = params

        total_error = 0

        for (ttm, strike), market_vol in market_vols.items():
            # Pricer con estos params
            result = self.rough_bergomi_pricer(
                S=S, K=strike, T=ttm, r=r,
                xi=xi, eta=eta, rho=rho, hurst=hurst,
                n_simulations=1000  # Menos para velocidad
            )

            # Calcular vol implícita inversa (simplificado)
            # Usar diferencia de precios como proxy
            # (para producción usar Newton-Raphson)

            model_price = result['price']
            bs_price = self.black_scholes_price(
                S, strike, ttm, r, market_vol
            )

            error = (model_price - bs_price) ** 2
            total_error += error

        return total_error

    # Initial guess
    x0 = [0.235, 1.9, -0.9, 0.1]

    # Bounds
    bounds = [
        (0.01, 1.0),   # xi
        (0.1, 5.0),    # eta
        (-1.0, 0.0),   # rho
        (0.01, 0.49)   # hurst
    ]

    result = minimize(objective, x0, bounds=bounds, method='L-BFGS-B')

    xi_opt, eta_opt, rho_opt, hurst_opt = result.x

    logger.info(
        f"Rough vol calibrated: xi={xi_opt:.3f}, "
        f"eta={eta_opt:.3f}, rho={rho_opt:.3f}, H={hurst_opt:.3f}"
    )

    return {
        'xi': xi_opt,
        'eta': eta_opt,
        'rho': rho_opt,
        'hurst': hurst_opt,
        'calibration_error': result.fun
    }
```

### Regla 13 — Rough Volatility Clustering

Agrupar periodos de alta vol basados en intensidad fractal.

```python
def rough_vol_clustering(
    self,
    volatility: pd.Series,
    hurst: float = None
) -> dict:
    """
    Detectar clusters de volatilidad usando roughness.

    Bayer: Clustering es más marcado en rough vol.
    """
    if hurst is None:
        hurst = self.estimate_hurst_exponent(volatility)['hurst']

    # Umbral: vol > media + 1*std
    vol_mean = volatility.rolling(20).mean()
    vol_std = volatility.rolling(20).std()

    high_vol_mask = volatility > (vol_mean + vol_std)

    # Encontrar clusters
    clusters = []
    current_cluster = []

    for i, is_high in enumerate(high_vol_mask.items()):
        if is_high[1]:
            current_cluster.append(i)
        elif current_cluster:
            clusters.append(current_cluster)
            current_cluster = []

    if current_cluster:
        clusters.append(current_cluster)

    # Estadísticas
    n_clusters = len(clusters)
    avg_cluster_length = np.mean([len(c) for c in clusters]) if clusters else 0

    logger.info(
        f"Rough vol clusters: {n_clusters} clusters, "
        f"avg length={avg_cluster_length:.1f}, H={hurst:.3f}"
    )

    return {
        'n_clusters': n_clusters,
        'avg_cluster_length': avg_cluster_length,
        'clusters': clusters,
        'hurst': hurst
    }
```

### Regla 14 — Memory Decay for Forecasting

Usar el decaimiento de autocorrelación para definir horizonte de forecast.

```python
def memory_decay_horizon(
    self,
    volatility: pd.Series,
    hurst: float = None
) -> dict:
    """
    Calcular horizonte útil de forecast basado en memoria.

    Bayer: Rough = memoria decae rápido.
    """
    if hurst is None:
        hurst = self.estimate_hurst_exponent(volatility)['hurst']

    # Autocorrelación decae ~ t^(2H-2)
    # Encontrar lag donde autocorr < significancia

    from statsmodels.tsa.stattools import acf

    max_lag = 100
    autocorr = acf(volatility, nlags=max_lag)

    # Encontrar donde cae por debajo de 0.1
    significant_lags = np.where(np.abs(autocorr) > 0.1)[0]

    if len(significant_lags) > 0:
        memory_horizon = significant_lags[-1]
    else:
        memory_horizon = 0

    # En rough vol, el horizonte es corto
    forecast_horizon = min(memory_horizon, 5)  # Max 5 periodos

    logger.info(
        f"Memory horizon: {memory_horizon} lags, "
        f"Forecast horizon: {forecast_horizon} periods, H={hurst:.3f}"
    )

    return {
        'hurst': hurst,
        'memory_horizon': memory_horizon,
        'forecast_horizon': forecast_horizon,
        'autocorr_decay': autocorr[:10]
    }
```

### Regla 15 — Rough Volatility Risk Premium

Calcular el risk premium asociado a volatilidad rugosa.

```python
def rough_vol_risk_premium(
    self,
    realized_vol: float,
    implied_vol: float,
    hurst: float = 0.1
) -> dict:
    """
    Risk premium de vol ajustado por roughness.

    Bayer: VRP = implied - realized (ajustado).
    """
    # VRP standard
    vrp_standard = implied_vol - realized_vol

    # Ajuste por roughness
    # Cuando H es bajo, el VRP tiende a ser positivo
    expected_vrp = (0.5 - hurst) * realized_vol

    # VRP ajustado
    vrp_adjusted = vrp_standard - expected_vrp

    # Interpretación
    if vrp_adjusted > 0:
        signal = 'overpriced_vol'
        recommendation = 'sell_volatility'
    elif vrp_adjusted < 0:
        signal = 'underpriced_vol'
        recommendation = 'buy_volatility'
    else:
        signal = 'fair'
        recommendation = 'neutral'

    logger.info(
        f"Rough VRP: Real={realized_vol:.3f}, "
        f"Impl={implied_vol:.3f}, VRP_adj={vrp_adjusted:.3f}, "
        f"Signal={signal}"
    )

    return {
        'realized_vol': realized_vol,
        'implied_vol': implied_vol,
        'vrp_standard': vrp_standard,
        'vrp_adjusted': vrp_adjusted,
        'expected_vrp': expected_vrp,
        'signal': signal,
        'recommendation': recommendation,
        'hurst': hurst
    }
```

---

## Aplicación Práctica

### Pipeline Completo Rough Volatility

```python
def rough_volatility_pipeline(
    self,
    returns: pd.Series,
    prices: pd.Series,
    current_vol: float
) -> dict:
    """
    Pipeline completo de rough volatility.
    """
    # 1. Estimar Hurst
    hurst_result = self.estimate_hurst_exponent(returns)
    H = hurst_result['hurst']

    # 2. Detectar régimen
    regime = self.detect_roughness_regime(returns)

    # 3. Forecast de volatilidad
    vol_forecast = self.forecast_rough_volatility(
        returns ** 2,  # Usar squared returns como proxy de vol
        forecast_horizon=5
    )

    # 4. Ajustar risk models por fat tails
    fat_tail = self.rough_fat_tail_adjustment(returns, H)

    # 5. Calcular hedging óptimo
    hedge_freq = self.optimal_hedging_frequency_rough(H)

    # 6. Risk premium
    vrp = self.rough_vol_risk_premium(
        realized_vol=current_vol,
        implied_vol=self.get_implied_vol(),
        hurst=H
    )

    return {
        'hurst': H,
        'regime': regime['regime'],
        'volatility_forecast': vol_forecast['forecast'].tolist(),
        'var_adjusted': fat_tail['var_rough_adjusted'],
        'hedging_frequency_minutes': hedge_freq['frequency_minutes'],
        'vrp_signal': vrp['signal'],
        'recommendation': vrp['recommendation']
    }
```
