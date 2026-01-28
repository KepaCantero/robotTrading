# 📄 Papers Fundamentales - Online Portfolio Selection (Li & Hoi, 2014)

## Rebalanceo Diario de Alta Velocidad sin Predicción

**Contexto:** Portfolio Management y Online Learning.

Li & Hoi demostraron que los algoritmos de "Online Learning" pueden superar a estrategias buy-and-hold sin necesidad de predecir el futuro.

---

### Regla 1 — No-Forecasting Rule

El robot NO debe intentar predecir el futuro, sino reaccionar a retornos relativos actuales.

```python
def online_portfolio_no_forecast(
    self,
    current_prices: pd.Series,
    previous_prices: pd.Series
) -> dict:
    """
    Actualizar portafolio basado en retornos relativos actuales.

    Li & Hoi: Reaccionar, no predecir.
    """
    # Retornos relativos (price / prev_price)
    relative_returns = current_prices / previous_prices

    # Actualizar pesos proporcionalmente a retornos relativos
    # (Sin predecir qué activo hará mejor)

    logger.info(
        f"No-forecast update: {len(relative_returns)} assets, "
        f"rel_returns_mean={relative_returns.mean():.4f}"
    )

    return {
        'relative_returns': relative_returns,
        'forecasting_used': False,
        'method': 'passive_rebalance'
    }
```

### Regla 2 — Mean Reversion (Passive Aggressive)

Comprar activos que cayeron hoy esperando que suban mañana.

```python
def passive_aggressive_mean_reversion(
    self,
    current_weights: np.ndarray,
    relative_returns: pd.Series,
    epsilon: float = 0.5
) -> np.ndarray:
    """
    Estrategia Passive Aggressive (PA).

    Li & Hoi: Comprar los que bajaron = mean reversion.
    """
    # Identificar losers (retornos más bajos)
    losers_mask = relative_returns < relative_returns.median()

    # PA: Transferir peso de ganadores a perdedores
    n_assets = len(current_weights)

    new_weights = current_weights.copy()

    # Calcular transferencia
    transfer_amount = epsilon / n_assets

    for i in range(n_assets):
        if losers_mask.iloc[i]:
            # Aumentar peso de loser
            new_weights[i] += transfer_amount
        else:
            # Reducir peso de winner
            new_weights[i] -= transfer_amount

    # Asegurar simplex (pesos suman 1)
    new_weights = np.clip(new_weights, 0, None)
    new_weights = new_weights / new_weights.sum()

    logger.info(
        f"PA rebalance: {losers_mask.sum()} losers bought, "
        f"epsilon={epsilon}"
    )

    return new_weights
```

### Regla 3 — Constant Rebalanced Portfolios (CRP)

Mantener proporción fija de capital en cada activo pase lo que pase.

```python
def constant_rebalanced_portfolio(
    self,
    n_assets: int,
    target_weights: np.ndarray = None
) -> dict:
    """
    CRP: Pesos constantes, rebalanceo diario.

    Li & Hoi: CRP = baseline para online learning.
    """
    if target_weights is None:
        # Equal weight default
        target_weights = np.ones(n_assets) / n_assets

    # Verificar simplex
    assert abs(target_weights.sum() - 1.0) < 1e-6, "Weights must sum to 1"

    logger.info(
        f"CRP: {n_assets} assets, "
        f"target_weights={target_weights.round(3)}"
    )

    return {
        'target_weights': target_weights,
        'strategy': 'crp',
        'rebalance_frequency': 'daily'
    }
```

### Regla 4 — Transaction Cost Optimization

Solo rebalancear si cambio esperado supera costo de comisión.

```python
def transaction_cost_threshold(
    self,
    current_weights: np.ndarray,
    target_weights: np.ndarray,
    transaction_cost: float = 0.001  # 0.1%
) -> dict:
    """
    Solo rebalancear si el beneficio supera el costo.

    Li & Hoi: Threshold = reduce overtrading.
    """
    # Cambio en pesos (L1 norm)
    weight_change = np.abs(target_weights - current_weights).sum() / 2

    # Costo esperado
    expected_cost = weight_change * transaction_cost

    # Beneficio esperado (usar retour relativo como proxy)
    # En producción, usar estimación más sofisticada
    expected_benefit = weight_change * 0.002  # Asumir 0.2% edge

    # Net benefit
    net_benefit = expected_benefit - expected_cost

    if net_benefit > 0:
        rebalance = True
        final_weights = target_weights

    else:
        rebalance = False
        final_weights = current_weights

    logger.info(
        f"Cost threshold: change={weight_change:.3f}, "
        f"cost={expected_cost:.4f}, benefit={expected_benefit:.4f}, "
        f"net={net_benefit:.4f}, rebalance={rebalance}"
    )

    return {
        'rebalance': rebalance,
        'final_weights': final_weights,
        'expected_cost': expected_cost,
        'net_benefit': net_benefit
    }
```

### Regla 5 — Universal Portfolios

Implementar estrategia de Cover que promedia todas las combinaciones posibles.

```python
def universal_portfolio(
    self,
    returns_history: pd.DataFrame,
    n_samples: int = 1000
) -> np.ndarray:
    """
    Universal Portfolio: promedio de todos los CRPs.

    Li & Hoi: Universal = asymptóticamente óptimo.
    """
    n_assets = returns_history.shape[1]

    # Generar muestras aleatorias de pesos (simplex)
    weight_samples = []

    for _ in range(n_samples):
        # Dirichlet random (simplex)
        w = np.random.dirichlet(np.ones(n_assets))
        weight_samples.append(w)

    weight_samples = np.array(weight_samples)

    # Calcular retorno de cada CRP muestral
    crp_returns = []

    for w in weight_samples:
        # Retorno compuesto
        portfolio_return = (1 + (returns_history * w).sum(axis=1)).prod() - 1
        crp_returns.append(portfolio_return)

    crp_returns = np.array(crp_returns)

    # Pesos universales = promedio ponderado por rendimiento
    weights = (weight_samples.T * (1 + crp_returns)).T
    universal_weights = weights.mean(axis=0)

    # Normalizar
    universal_weights = universal_weights / universal_weights.sum()

    logger.info(
        f"Universal portfolio: {n_samples} samples, "
        f"best CRP return={crp_returns.max():.2%}"
    )

    return universal_weights
```

### Regla 6 — Log-Optimal Portfolio

Maximizar crecimiento del capital mediante reinversión total.

```python
def log_optimal_portfolio(
    self,
    returns: pd.DataFrame,
    window: int = 252
) -> dict:
    """
    Optimizar portafolio log-óptimo (Kelly).

    Li & Hoi: Log-optimal = crecimiento máximo.
    """
    # Retornos medios y covarianza
    mu = returns.iloc[-window:].mean()
    Sigma = returns.iloc[-window:].cov()

    # Resolver: max w'mu - 0.5 * w'Sigma*w
    # (Markowitz con risk_free_rate=0)

    from scipy.optimize import minimize

    def negative_log_growth(w):
        return - (w @ mu) + 0.5 * (w @ Sigma @ w)

    constraints = [
        {'type': 'eq', 'fun': lambda w: w.sum() - 1.0}
    ]

    bounds = [(0, 1) for _ in range(len(mu))]

    result = minimize(
        negative_log_growth,
        x0=np.ones(len(mu)) / len(mu),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if result.success:
        optimal_weights = result.x

        expected_log_return = -result.fun

    else:
        logger.error("Log-optimal optimization failed")
        optimal_weights = np.ones(len(mu)) / len(mu)
        expected_log_return = 0

    logger.info(
        f"Log-optimal: E[log_r]={expected_log_return:.4f}, "
        f"max_weight={optimal_weights.max():.2f}"
    )

    return {
        'weights': optimal_weights,
        'expected_log_return': expected_log_return,
        'success': result.success
    }
```

### Regla 7 — Online Gradient Descent

Ajustar pesos siguiendo el gradiente del log-retorno.

```python
def online_gradient_descent(
    self,
    current_weights: np.ndarray,
    relative_returns: pd.Series,
    learning_rate: float = 0.1
) -> np.ndarray:
    """
    OGD: Seguir gradiente de log-retorno.

    Li & Hoi: OGD = simple y efectivo.
    """
    # Gradiente de log-return
    # ∇w log(1 + w·x) = x / (1 + w·x)

    current_return = (current_weights * relative_returns).sum()
    gradient = relative_returns / (1 + current_return)

    # Actualizar: w = w + η * ∇
    new_weights = current_weights + learning_rate * gradient

    # Proyectar al simplex
    new_weights = self.project_to_simplex(new_weights)

    logger.info(
        f"OGD update: η={learning_rate}, "
        f"return={current_return:+.4f}"
    )

    return new_weights
```

### Regla 8 — Projection into Simplex

Asegurar que suma de pesos sea exactamente 1.

```python
def project_to_simplex(
    self,
    weights: np.ndarray
) -> np.ndarray:
    """
    Proyectar vector al simplex (suma=1, weights>=0).

    Li & Hoi: Simplex projection = constraint básico.
    """
    n = len(weights)

    # Algoritmo de proyección al simplex
    u = np.sort(weights)[::-1]

    # Encontrar ρ
    cumsum = np.cumsum(u)
    rho = np.max(np.where(u > (cumsum - 1) / np.arange(1, n + 1))[0])

    theta = (cumsum[rho] - 1) / (rho + 1)

    # Proyectar
    projected = np.maximum(weights - theta, 0)

    # Verificar
    assert abs(projected.sum() - 1.0) < 1e-10, "Projection failed"

    logger.debug(
        f"Simplex projection: {weights.round(3)} → {projected.round(3)}"
    )

    return projected
```

### Regla 9 — Anti-Correlation Strategy

Transferir capital de activos que subieron mucho a los que bajaron.

```python
def anti_correlation_rebalance(
    self,
    current_weights: np.ndarray,
    returns: pd.Series,
    threshold: float = 0.02  # 2%
) -> np.ndarray:
    """
    Anti-correlation: comprar bajantes, vender subientes.

    Li & Hoi: Anti-correlation = reversión a la media.
    """
    # Clasificar retornos
    gainers = returns[returns > threshold].index
    losers = returns[returns < -threshold].index

    new_weights = current_weights.copy()

    if len(gainers) > 0 and len(losers) > 0:
        # Transferir capital de gainers a losers
        transfer_amount = 0.05  # 5% transfer

        # Reducir gainers
        for idx in gainers:
            i = returns.index.get_loc(idx)
            new_weights[i] = max(0, new_weights[i] - transfer_amount / len(gainers))

        # Aumentar losers
        for idx in losers:
            i = returns.index.get_loc(idx)
            new_weights[i] += transfer_amount / len(losers)

        # Renormalizar
        new_weights = new_weights / new_weights.sum()

        logger.info(
            f"Anti-correlation: {len(gainers)} gainers → {len(losers)} losers"
        )

    return new_weights
```

### Regla 10 — Exploiting Volatility

Aprovechar oscilaciones intradía para aumentar capital acumulado.

```python
def volatility_exploitation(
    self,
    intraday_prices: pd.DataFrame,
    rebalance_frequency: str = 'hourly'
) -> dict:
    """
    Explotar volatilidad intradía.

    Li & Hoi: Más rebalanceos = capturar volatilidad.
    """
    if rebalance_frequency == 'hourly':
        # Rebancear cada hora
        timestamps = intraday_prices.index
        hourly_returns = []

        for hour in range(1, 24):
            hour_start = intraday_prices[intraday_prices.index.hour == hour - 1]
            hour_end = intraday_prices[intraday_prices.index.hour == hour]

            if len(hour_start) > 0 and len(hour_end) > 0:
                ret = hour_end['close'].iloc[-1] / hour_start['close'].iloc[0] - 1
                hourly_returns.append(ret)

        hourly_returns = pd.Series(hourly_returns)

        # Volatilidad horaria
        hourly_vol = hourly_returns.std()

        # Si volatilidad alta, aumentar frecuencia de rebalanceo
        if hourly_vol > 0.01:  # > 1% vol por hora
            action = 'increase_rebalance_frequency'
            new_frequency = '30min'

        else:
            action = 'maintain_frequency'
            new_frequency = rebalance_frequency

    logger.info(
        f"Volatility exploitation: hourly_vol={hourly_vol:.3f}, "
        f"{action} → {new_frequency}"
    )

    return {
        'hourly_volatility': hourly_vol,
        'action': action,
        'new_frequency': new_frequency
    }
```

### Regla 11 — Zero-Inertia Rebalancing

Estar preparado para cambiar toda la cartera en un paso si retornos cambian drásticamente.

```python
def zero_inertia_rebalance(
    self,
    current_weights: np.ndarray,
    market_regime_change: bool
) -> np.ndarray:
    """
    Cambio drástico si hay cambio de régimen.

    Li & Hoi: Zero inertia = adaptación rápida.
    """
    if market_regime_change:
        # Cambio completo a equal weight
        n_assets = len(current_weights)
        new_weights = np.ones(n_assets) / n_assets

        logger.warning(
            f"🔄 Zero-inertia rebalance: regime change detected, "
            f"resetting to equal weights"
        )

    else:
        # Normal OGD update
        new_weights = current_weights

    return new_weights
```

### Regla 12 — Risk-Bounded Learning

Limitar máxima pérdida permitida en cada paso de rebalanceo.

```python
def risk_bounded_online_learning(
    self,
    proposed_weights: np.ndarray,
    current_weights: np.ndarray,
    max_risk: float = 0.05,  # 5% max loss
    returns_cov: np.ndarray
) -> dict:
    """
    Limitar riesgo de cambio de portafolio.

    Li & Hoi: Risk bound = protección en online learning.
    """
    # Calcular riesgo del cambio
    weight_diff = proposed_weights - current_weights

    # Varianza del cambio
    change_variance = weight_diff @ returns_cov @ weight_diff

    # Std del cambio (riesgo)
    change_risk = np.sqrt(change_variance)

    if change_risk > max_risk:
        # Escalar propuesta para cumplir riesgo máximo
        scale_factor = max_risk / change_risk

        adjusted_weights = current_weights + weight_diff * scale_factor

        logger.warning(
            f"⚠️ Risk limit: change_risk={change_risk:.3f} > {max_risk:.3f}, "
            f"scaling by {scale_factor:.2f}"
        )

    else:
        adjusted_weights = proposed_weights

    return {
        'weights': adjusted_weights,
        'change_risk': change_risk,
        'scaled': change_risk > max_risk
    }
```

### Regla 13 — Kernel-Based Selection

Usar similitud histórica para seleccionar pesos que funcionaron en situaciones parecidas.

```python
def kernel_based_portfolio_selection(
    self,
    current_returns: pd.Series,
    historical_returns: pd.DataFrame,
    kernel: str = 'rbf',
    sigma: float = 1.0
) -> dict:
    """
    Seleccionar portafolio basado en similitud histórica.

    Li & Hoi: Kernel = pesos adaptativos al régimen.
    """
    from sklearn.metrics.pairwise import rbf_kernel

    # Calcular similitud con cada período histórico
    similarities = []

    for i in range(len(historical_returns)):
        hist_ret = historical_returns.iloc[i]

        if kernel == 'rbf':
            # RBF kernel: exp(-||x-y||² / σ²)
            sim = np.exp(
                -np.sum((current_returns - hist_ret) ** 2) / (2 * sigma ** 2)
            )

        similarities.append(sim)

    similarities = np.array(similarities)

    # Pesos = promedio ponderado por similitud
    # (En producción, esto retornaría los mejores pesos históricos)
    # Aquí simplificamos

    # Normalizar similitudes
    similarity_weights = similarities / similarities.sum()

    logger.info(
        f"Kernel selection: max_sim={similarities.max():.3f}, "
        f"mean_sim={similarities.mean():.3f}"
    )

    return {
        'similarity_weights': similarity_weights,
        'most_similar_period': similarities.argmax(),
        'kernel_type': kernel
    }
```

### Regla 14 — Ensemble Online Learning

Promediar decisiones de múltiples algoritmos online.

```python
def ensemble_online_learning(
    self,
    returns: pd.Series,
    algorithms: List[str] = ['OGD', 'ONS', 'PAMR']
) -> np.ndarray:
    """
    Ensemble de algoritmos online.

    Li & Hoi: Ensemble = reducción de varianza.
    """
    weight_predictions = []

    for alg in algorithms:
        if alg == 'OGD':
            w = self.online_gradient_descent(
                self.current_weights,
                returns,
                learning_rate=0.1
            )

        elif alg == 'ONS':
            # Online Newton Step
            w = self.online_newton_step(
                self.current_weights,
                returns
            )

        elif alg == 'PAMR':
            # Passive Aggressive Mean Reversion
            w = self.passive_aggressive_mean_reversion(
                self.current_weights,
                returns,
                epsilon=0.5
            )

        weight_predictions.append(w)

    # Promedio
    ensemble_weights = np.mean(weight_predictions, axis=0)

    # Proyectar a simplex
    ensemble_weights = self.project_to_simplex(ensemble_weights)

    logger.info(
        f"Ensemble: {len(algorithms)} algos, "
        f"weights_std={np.std(weight_predictions, axis=0).mean():.3f}"
    )

    return ensemble_weights
```

### Regla 15 — Online Newton Step (ONS)

Algoritmo de segundo orden para convergencia más rápida.

```python
def online_newton_step(
    self,
    current_weights: np.ndarray,
    relative_returns: pd.Series,
    beta: float = 1.0,
    gamma: float = 0.1
) -> np.ndarray:
    """
    Online Newton Step: algoritmo de segundo orden.

    Li & Hoi: ONS = convergencia O(log T) vs O(sqrt(T)).
    """
    n_assets = len(current_weights)

    # Gradiente
    current_return = (current_weights * relative_returns).sum()
    gradient = relative_returns / (1 + current_return)

    # Aproximación de Hessiana (diagonal para simplificar)
    # H ≈ diag(1 / (1 + w·x)²) * x²

    hessian_diag = (relative_returns ** 2) / ((1 + current_return) ** 2 + 1e-8)

    # Actualizar usando información de segundo orden
    # w = w - H^(-1) * g

    # Inversa aproximada
    hessian_inv = 1 / (hessian_diag + gamma)

    # Newton step
    step = beta * hessian_inv * gradient

    # Actualizar pesos
    new_weights = current_weights + step

    # Proyectar a simplex
    new_weights = self.project_to_simplex(new_weights)

    logger.info(
        f"ONS update: β={beta}, γ={gamma}, "
        f"step_norm={np.linalg.norm(step):.3f}"
    )

    return new_weights
```

---

## Aplicación Práctica

### Pipeline Completo Online Portfolio Selection

```python
def online_portfolio_pipeline(
    self,
    current_prices: pd.Series,
    previous_prices: pd.Series,
    current_weights: np.ndarray
) -> dict:
    """
    Pipeline completo de Online Portfolio Selection.
    """
    # 1. Calcular retornos relativos
    relative_returns = current_prices / previous_prices

    # 2. Detectar cambio de régimen
    regime_change = self.detect_regime_change(relative_returns)

    # 3. Seleccionar algoritmo(s)
    if regime_change:
        # Zero-inertia si cambio drástico
        new_weights = self.zero_inertia_rebalance(
            current_weights,
            market_regime_change=True
        )

    else:
        # Ensemble de algoritmos online
        proposed_weights = self.ensemble_online_learning(
            relative_returns,
            algorithms=['OGD', 'ONS', 'PAMR']
        )

        # 4. Verificar costo de transacción
        cost_check = self.transaction_cost_threshold(
            current_weights,
            proposed_weights,
            transaction_cost=0.001
        )

        if cost_check['rebalance']:
            new_weights = cost_check['final_weights']
        else:
            new_weights = current_weights

    # 5. Verificar límites de riesgo
    risk_check = self.risk_bounded_online_learning(
        new_weights,
        current_weights,
        max_risk=0.05,
        returns_cov=self.get_recent_covariance()
    )

    final_weights = risk_check['weights']

    # 6. Ejecutar rebalanceo
    trades = self.calculate_rebalance_trades(
        current_weights,
        final_weights,
        current_prices
    )

    return {
        'new_weights': final_weights,
        'trades': trades,
        'regime_change': regime_change,
        'rebalance_executed': not np.allclose(current_weights, final_weights),
        'algorithm_used': 'ensemble_online' if not regime_change else 'zero_inertia'
    }
```
