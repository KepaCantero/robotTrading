# 📄 Papers Fundamentales - Markowitz Portfolio Selection (1952)

## Modern Portfolio Theory - Reglas de Optimización

**Contexto:** Construcción del Portafolio y Optimización (Core RiskEngine).

Harry Markowitz revolucionó las finanzas al demostrar que los inversores deben optimizar la relación riesgo-retorno, no solo maximizar el retorno.

---

### Regla 1 — Matriz de Covarianza Obligatoria

El sistema DEBE calcular la matriz de covarianza usando un lookback window mínimo de 252 días hábiles.

```python
def calculate_covariance_matrix(
    self,
    returns: pd.DataFrame,
    lookback_days: int = 252
) -> pd.DataFrame:
    """
    Calcular matriz de covarianza para optimización MVO.

    Markowitz: 252 días = 1 año de trading (mínimo).
    """
    if len(returns) < lookback_days:
        raise ValueError(
            f"Insufficient data: {len(returns)} < {lookback_days} required"
        )

    # Usar ventana rodante de 252 días
    recent_returns = returns.iloc[-lookback_days:]

    # Matriz de covarianza anualizada
    cov_matrix = recent_returns.cov() * 252

    logger.info(
        f"Covariance matrix: {cov_matrix.shape[0]} assets, "
        f"{lookback_days} days lookback"
    )

    return cov_matrix
```

### Regla 2 — Mean-Variance Optimization (MVO)

Implementar la función objetivo: `min(w.T @ Sigma @ w)` sujeto a retorno esperado objetivo.

```python
def mean_variance_optimization(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    target_return: float = None,
    risk_free_rate: float = 0.02
) -> pd.Series:
    """
    Optimización Media-Varianza.

    Markowitz: Minimizar varianza para un retorno objetivo.
    """
    n_assets = len(expected_returns)

    # Si no se especifica target_return, buscar Max Sharpe
    if target_return is None:
        return self.max_sharpe_portfolio(
            expected_returns, cov_matrix, risk_free_rate
        )

    from scipy.optimize import minimize

    # Función objetivo: varianza del portfolio
    def portfolio_variance(weights):
        return weights.T @ cov_matrix.values @ weights

    # Constraints
    constraints = [
        # Suma de pesos = 1
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        # Retorno objetivo
        {'type': 'eq', 'fun': lambda w: w @ expected_returns.values - target_return}
    ]

    # Bounds: long-only (0 <= weight <= 1)
    bounds = [(0, 1) for _ in range(n_assets)]

    # Initial guess: equal weight
    x0 = np.ones(n_assets) / n_assets

    # Optimizar
    result = minimize(
        portfolio_variance,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        logger.error(f"MVO failed: {result.message}")
        return None

    weights = pd.Series(result.x, index=expected_returns.index)

    logger.info(
        f"MVO: Target return={target_return:.2%}, "
        f"Exp return={(weights @ expected_returns):.2%}, "
        f"Exp risk={np.sqrt(portfolio_variance(weights)):.2%}"
    )

    return weights
```

### Regla 3 — Restricción de Pesos Long-Only

Para perfiles standard, imponer restricción: `0 <= weight <= 1` (sin apalancamiento, sin cortos).

```python
def apply_long_only_constraint(
    self,
    weights: pd.Series
) -> pd.Series:
    """
    Forzar long-only: 0 <= weight <= 1.

    Markowitz: Para perfiles standard, no short selling.
    """
    # Clipping a [0, 1]
    weights_constrained = weights.clip(lower=0, upper=1)

    # Renormalizar para suma = 1
    weights_constrained = weights_constrained / weights_constrained.sum()

    logger.info(
        f"Long-only constraint applied: "
        f"{(weights_constrained == 0).sum()} assets set to 0"
    )

    return weights_constrained
```

### Regla 4 — Suma Unitaria (Hard Constraint)

Restricción dura: `sum(weights) == 1.0` (o `1.0 - cash_buffer`).

```python
def validate_sum_constraint(
    self,
    weights: pd.Series,
    tolerance: float = 1e-6
) -> bool:
    """
    Validar que suma de pesos = 1.0.

    Markowitz: Hard constraint crítica.
    """
    sum_weights = weights.sum()

    if abs(sum_weights - 1.0) > tolerance:
        logger.error(
            f"❌ Sum constraint violated: {sum_weights:.6f} ≠ 1.0"
        )
        return False

    return True
```

### Regla 5 — Diversificación Forzada

Ningún activo individual puede superar `max_weight = 0.20` (20%) en la solución óptima.

```python
def apply_diversification_constraint(
    self,
    weights: pd.Series,
    max_weight: float = 0.20
) -> pd.Series:
    """
    Limitar concentración: max 20% por activo.

    Markowitz: Forzar diversificación real.
    """
    violations = weights[weights > max_weight]

    if len(violations) > 0:
        logger.warning(
            f"⚠️ Concentration violations: {len(violations)} assets "
            f"exceed {max_weight:.0%} limit"
        )

        # Cap pesos a max_weight
        weights_capped = weights.clip(upper=max_weight)

        # Redistribuir exceso proporcionalmente
        excess = 1.0 - weights_capped.sum()
        n_below_max = (weights < max_weight).sum()

        if n_below_max > 0:
            weights_capped[weights < max_weight] += excess / n_below_max

        logger.info(f"Weights capped and redistributed")

        return weights_capped

    return weights
```

### Regla 6 — Frontera Eficiente

Calcular al menos 20 puntos de la frontera eficiente para visualizar el trade-off riesgo/retorno.

```python
def calculate_efficient_frontier(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    n_points: int = 20
) -> pd.DataFrame:
    """
    Calcular Frontera Eficiente.

    Markowitz: Visualizar trade-off riesgo-retorno.
    """
    # Rango de retornos: min/max retornos esperados
    min_ret = expected_returns.min()
    max_ret = expected_returns.max()

    target_returns = np.linspace(min_ret, max_ret, n_points)

    frontier = []

    for target_return in target_returns:
        weights = self.mean_variance_optimization(
            expected_returns, cov_matrix, target_return
        )

        if weights is not None:
            portfolio_return = weights @ expected_returns
            portfolio_risk = np.sqrt(weights.T @ cov_matrix.values @ weights)
            sharpe = portfolio_return / portfolio_risk

            frontier.append({
                'return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe': sharpe,
                'weights': weights
            })

    frontier_df = pd.DataFrame(frontier)

    # Encontrar Max Sharpe
    max_sharpe_idx = frontier_df['sharpe'].idxmax()
    max_sharpe_portfolio = frontier_df.loc[max_sharpe_idx]

    logger.info(
        f"Efficient Frontier: {len(frontier_df)} points, "
        f"Max Sharpe at return={max_sharpe_portfolio['return']:.2%}, "
        f"risk={max_sharpe_portfolio['risk']:.2%}"
    )

    return frontier_df
```

### Regla 7 — Sharpe Ratio Objective (Max Sharpe/Tangency)

Por defecto, el optimizador debe buscar el portafolio de Tangencia (Max Sharpe Ratio).

```python
def max_sharpe_portfolio(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    risk_free_rate: float = 0.02
) -> pd.Series:
    """
    Portafolio de Tangencia (Max Sharpe).

    Markowitz: Óptimo para todos los inversores racionales.
    """
    from scipy.optimize import minimize

    n_assets = len(expected_returns)

    # Función objetivo: negative Sharpe ratio
    def negative_sharpe(weights):
        portfolio_return = weights @ expected_returns.values
        portfolio_risk = np.sqrt(weights.T @ cov_matrix.values @ weights)

        excess_return = portfolio_return - risk_free_rate

        return -excess_return / portfolio_risk

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
    ]

    # Bounds: long-only o permitir short
    bounds = [(0, 1) for _ in range(n_assets)]

    # Initial guess
    x0 = np.ones(n_assets) / n_assets

    # Optimizar
    result = minimize(
        negative_sharpe,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        logger.error(f"Max Sharpe optimization failed: {result.message}")
        return None

    weights = pd.Series(result.x, index=expected_returns.index)

    portfolio_return = weights @ expected_returns.values
    portfolio_risk = np.sqrt(weights.T @ cov_matrix.values @ weights)
    sharpe = (portfolio_return - risk_free_rate) / portfolio_risk

    logger.info(
        f"Max Sharpe Portfolio: Return={portfolio_return:.2%}, "
        f"Risk={portfolio_risk:.2%}, Sharpe={sharpe:.2f}"
    )

    return weights
```

### Regla 8 — Regularización L2

Usar regularización L2 (gamma) para evitar pesos extremos inestables (corner solutions).

```python
def regularized_mvo(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    gamma: float = 0.01
) -> pd.Series:
    """
    MVO con regularización L2 para evitar corner solutions.

    Markowitz moderno: PyPortfolioOpt con L2 penalty.
    """
    from scipy.optimize import minimize

    n_assets = len(expected_returns)

    # Función objetivo: varianza + penalty L2
    def regularized_variance(weights):
        variance = weights.T @ cov_matrix.values @ weights
        penalty = gamma * np.sum(weights ** 2)

        return variance + penalty

    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
    ]

    bounds = [(0, 1) for _ in range(n_assets)]

    x0 = np.ones(n_assets) / n_assets

    result = minimize(
        regularized_variance,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        logger.error(f"Regularized MVO failed: {result.message}")
        return None

    weights = pd.Series(result.x, index=expected_returns.index)

    logger.info(
        f"Regularized MVO: gamma={gamma}, "
        f"max weight={weights.max():.2%} (vs {(1/n_assets):.2%} equal)"
    )

    return weights
```

### Regla 9 — Rebalanceo por Desviación

Si current_weight se desvía > 20% del target_weight óptimo, activar señal de rebalanceo.

```python
def check_rebalance_trigger(
    self,
    current_weights: pd.Series,
    target_weights: pd.Series,
    threshold: float = 0.20
) -> dict:
    """
    Trigger de rebalanceo por desviación.

    Markowitz: Mantener asignación óptima.
    """
    # Desviación absoluta
    deviation = (current_weights - target_weights).abs()

    # Desviación porcentual relativa al target
    relative_deviation = deviation / target_weights.abs()

    # Assets que necesitan rebalanceo
    rebalance_assets = relative_deviation[relative_deviation > threshold]

    if len(rebalance_assets) > 0:
        logger.info(
            f"Rebalance trigger: {len(rebalance_assets)} assets "
            f"deviated > {threshold:.0%}"
        )

        return {
            'rebalance': True,
            'assets': rebalance_assets.index.tolist(),
            'max_deviation': relative_deviation.max()
        }

    return {'rebalance': False}
```

### Regla 10 — Shrinkage Estimators (Ledoit-Wolf)

NO usar la matriz de covarianza muestral simple. Usar estimadores de contracción para reducir ruido.

```python
def shrink_covariance_matrix(
    self,
    returns: pd.DataFrame,
    method: str = 'ledoit-wolf'
) -> pd.DataFrame:
    """
    Aplicar shrinkage a la matriz de covarianza.

    Markowitz moderno: Reducir error de estimación.
    """
    from sklearn.covariance import LedoitWolf

    if method == 'ledoit-wolf':
        lw = LedoitWolf()
        shrunk_cov, _ = lw.fit(returns.values).covariance_, lw.shrinkage_

        logger.info(f"Ledoit-Wolf shrinkage: shrinkage={_.1%}")

    elif method == 'oracle-approximating':
        from sklearn.covariance import OAS
        oas = OAS()
        shrunk_cov, _ = oas.fit(returns.values).covariance_, oas.shrinkage_

        logger.info(f"OAS shrinkage: shrinkage={_.1%}")

    else:
        # Default: sample covariance
        shrunk_cov = returns.cov().values
        logger.warning("Using sample covariance (no shrinkage)")

    # Convertir a DataFrame
    shrunk_cov_df = pd.DataFrame(
        shrunk_cov,
        index=returns.columns,
        columns=returns.columns
    )

    return shrunk_cov_df
```

### Regla 11 — Beta Constraints

El portafolio resultante debe tener Beta ponderada vs SPY < 1.0 para perfiles conservadores.

```python
def apply_beta_constraint(
    self,
    weights: pd.Series,
    betas: pd.Series,  # symbol -> beta vs SPY
    max_beta: float = 1.0
) -> pd.Series:
    """
    Limitar Beta del portafolio.

    Markowitz aplicado: Controlar exposición al mercado.
    """
    portfolio_beta = (weights * betas).sum()

    if portfolio_beta > max_beta:
        logger.warning(
            f"⚠️ Portfolio beta {portfolio_beta:.2f} > {max_beta:.2f}. "
            f"Reducing weights."
        )

        # Reducir pesos proporcionalmente
        scale_factor = max_beta / portfolio_beta

        weights_adjusted = weights * scale_factor

        # Ajustar cash allocation
        cash_weight = 1.0 - weights_adjusted.sum()

        logger.info(
            f"Beta constraint: scaled weights by {scale_factor:.2f}, "
            f"cash={cash_weight:.2f}"
        )

        return weights_adjusted

    return weights
```

### Regla 12 — Transaction Cost Penalty

Restar un estimado de costos de transacción (bps) de los retornos esperados dentro del optimizador.

```python
def net_returns_with_costs(
    self,
    gross_returns: pd.Series,
    weights: pd.Series,
    turnover: float,
    transaction_cost_bps: float = 10.0
) -> float:
    """
    Retornos netos de costos de transacción.

    Markowitz con costs: Incluir costs en optimización.
    """
    # Costo esperado = turnover * cost_bps / 10000
    expected_cost = turnover * transaction_cost_bps / 10000

    # Retorno bruto del portfolio
    gross_return = (weights * gross_returns).sum()

    # Retorno neto
    net_return = gross_return - expected_cost

    logger.info(
        f"Net returns: Gross={gross_return:.2%}, "
        f"Cost={expected_cost:.2%}, Net={net_return:.2%}"
    )

    return net_return
```

### Regla 13 — Risk Parity Fallback

Si MVO falla (matriz no definida positiva), revertir automáticamente a Risk Parity (Inverse Volatility).

```python
def robust_portfolio_optimization(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame
) -> pd.Series:
    """
    Optimización robusta con fallback a Risk Parity.

    Markowitz: Si MVO falla, usar alternativa robusta.
    """
    try:
        # Intentar MVO
        weights = self.max_sharpe_portfolio(expected_returns, cov_matrix)

        if weights is not None:
            return weights

    except Exception as e:
        logger.warning(f"MVO failed: {e}. Falling back to Risk Parity.")

    # Fallback: Risk Parity (Inverse Volatility)
    volatilities = np.sqrt(np.diag(cov_matrix.values))
    inv_vols = 1 / volatilities
    weights_rp = inv_vols / inv_vols.sum()

    weights_rp = pd.Series(weights_rp, index=expected_returns.index)

    logger.info("Using Risk Parity fallback (Inverse Volatility)")

    return weights_rp
```

### Regla 14 — Correlation Alert

Si la correlación promedio del portafolio > 0.85, emitir advertencia de "Falsa Diversificación".

```python
def check_false_diversification(
    self,
    cov_matrix: pd.DataFrame,
    threshold: float = 0.85
) -> dict:
    """
    Detectar falsa diversificación.

    Markowitz: Alta correlación = no diversificación real.
    """
    # Convertir covarianza a correlación
    vols = np.sqrt(np.diag(cov_matrix.values))
    corr_matrix = cov_matrix.values / np.outer(vols, vols)

    # Correlación promedio (excluyendo diagonal)
    mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
    avg_correlation = corr_matrix[mask].mean()

    if avg_correlation > threshold:
        logger.error(
            f"🚨 FALSE DIVERSIFICATION: Avg correlation={avg_correlation:.2f} "
            f"> {threshold:.2f}. Portfolio not truly diversified."
        )

        return {
            'false_diversification': True,
            'avg_correlation': avg_correlation,
            'recommendation': 'Reduce number of assets or add uncorrelated assets'
        }

    return {
        'false_diversification': False,
        'avg_correlation': avg_correlation
    }
```

### Regla 15 — Input Sanitation

Validar que no existan NaN o precios planos (volatilidad 0) en la serie de tiempo antes de optimizar.

```python
def sanitize_inputs(
    self,
    returns: pd.DataFrame
) -> tuple:
    """
    Limpiar inputs antes de optimización.

    Markowitz: Garbage in = garbage out.
    """
    initial_n_assets = returns.shape[1]

    # 1. Eliminar activos con NaN
    returns_clean = returns.dropna(axis=1)

    n_nans = initial_n_assets - returns_clean.shape[1]
    if n_nans > 0:
        logger.warning(f"Dropped {n_nans} assets with NaN values")

    # 2. Eliminar activos con volatilidad ~0
    vols = returns_clean.std()
    zero_vol_assets = vols[vols < 1e-10].index

    if len(zero_vol_assets) > 0:
        logger.warning(f"Dropped {len(zero_vol_assets)} assets with ~0 volatility")
        returns_clean = returns_clean.drop(columns=zero_vol_assets)

    # 3. Validar suficientes activos restantes
    if returns_clean.shape[1] < 2:
        raise ValueError(
            f"Insufficient assets after sanitization: {returns_clean.shape[1]} < 2"
        )

    logger.info(
        f"Input sanitization: {initial_n_assets} → {returns_clean.shape[1]} assets"
    )

    # 4. Calcular retornos esperados y covarianza
    expected_returns = returns_clean.mean() * 252
    cov_matrix = returns_clean.cov() * 252

    return expected_returns, cov_matrix
```

---

## Aplicación Práctica

### Flujo Completo de Optimización MVO

```python
def markowitz_optimization_pipeline(
    self,
    returns: pd.DataFrame,
    profile_type: str = 'STANDARD'
) -> dict:
    """
    Pipeline completo de optimización Markowitz.
    """
    # 1. Sanitizar inputs
    expected_returns, cov_matrix = self.sanitize_inputs(returns)

    # 2. Aplicar shrinkage a covarianza
    cov_shrunk = self.shrink_covariance_matrix(returns)

    # 3. Calcular Frontera Eficiente
    frontier = self.calculate_efficient_frontier(
        expected_returns, cov_shrunk, n_points=20
    )

    # 4. Obtener Max Sharpe Portfolio
    weights = self.max_sharpe_portfolio(
        expected_returns, cov_shrunk, risk_free_rate=0.02
    )

    # 5. Aplicar diversificación forzada
    weights = self.apply_diversification_constraint(weights, max_weight=0.20)

    # 6. Validar falsa diversificación
    div_check = self.check_false_diversification(cov_shrunk)

    # 7. Aplicar constraints según perfil
    if profile_type == 'CONSERVATIVE':
        # Limitar beta
        betas = self.get_betas_vs_spy()
        weights = self.apply_beta_constraint(weights, betas, max_beta=0.8)

    return {
        'weights': weights,
        'frontier': frontier,
        'expected_return': (weights @ expected_returns),
        'expected_risk': np.sqrt(weights.T @ cov_shrunk.values @ weights),
        'sharpe_ratio': (weights @ expected_returns) / np.sqrt(weights.T @ cov_shrunk.values @ weights),
        'diversification_check': div_check
    }
```
