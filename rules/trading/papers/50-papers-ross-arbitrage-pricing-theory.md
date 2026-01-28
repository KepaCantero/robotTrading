# 📄 Papers Fundamentales - Stephen Ross: Arbitrage Pricing Theory (1976)

## APT: Modelado de Riesgo Macro y Factorial

**Contexto:** RiskEngine / MacroModule.

Stephen Ross revolucionó la teoría de activos con la Arbitrage Pricing Theory (APT), que extiende el modelo CAPM usando múltiples factores macroeconómicos en lugar de solo el mercado.

---

### Regla 1 — Macro Factor Selection

El modelo DEBE regresar los retornos del activo contra al menos 4 variables macro:
- Δ Tipos de Interés
- Δ Inflación (CPI)
- Δ Precio Petróleo
- Δ Producción Industrial

```python
def get_macro_factors(
    self,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Obtener factores macroeconómicos.

    Ross: Mínimo 4 factores macro para APT.
    """
    # 1. Tipos de interés (e.g., 10Y Treasury)
    interest_rates = self.get_treasury_rates(start_date, end_date)

    # 2. Inflación (CPI)
    inflation = self.get_cpi_data(start_date, end_date)

    # 3. Precio del petróleo (WTI/Brent)
    oil_prices = self.get_oil_prices(start_date, end_date)

    # 4. Producción industrial
    industrial_production = self.get_industrial_production(start_date, end_date)

    # Calcular cambios (diferencias)
    factors = pd.DataFrame({
        'interest_rate': interest_rates.diff(),
        'inflation': inflation.diff(),
        'oil_price': oil_prices.pct_change(),
        'ind_production': industrial_production.pct_change()
    }).dropna()

    logger.info(
        f"Macro factors: {len(factors)} observations, "
        f"{len(factors.columns)} factors"
    )

    return factors
```

### Regla 2 — Beta Sensitivity Check

Si un activo tiene `β_oil > 0.5`, clasificarlo automáticamente como "Energy-Dependent" independientemente de su sector oficial.

```python
def classify_by_macro_beta(
    self,
    betas: pd.Series,
    factor_name: str,
    threshold: float = 0.5
) -> dict:
    """
    Clasificar activos por sensibilidad macro.

    Ross: Beta alto = exposición al factor.
    """
    if factor_name == 'oil_price':
        classification = 'Energy-Dependent'

    elif factor_name == 'inflation':
        classification = 'Inflation-Sensitive'

    elif factor_name == 'interest_rate':
        classification = 'Rate-Sensitive'

    else:
        classification = 'General'

    # Identificar activos sobre threshold
    sensitive_assets = betas[betas.abs() > threshold].index.tolist()

    logger.info(
        f"{factor_name}: {len(sensitive_assets)} assets "
        f"with |β| > {threshold} classified as {classification}"
    )

    return {
        'classification': classification,
        'sensitive_assets': sensitive_assets,
        'betas': betas[sensitive_assets].to_dict()
    }
```

### Regla 3 — Linear Factor Model

Implementar `R_i = α + β_1·f_1 + β_2·f_2 + ... + ε`. Usar regresión lineal múltiple (OLS).

```python
def estimate Apt_betas(
    self,
    asset_returns: pd.Series,
    macro_factors: pd.DataFrame
) -> dict:
    """
    Estimar betas del modelo APT.

    Ross: Regresión lineal múltiple sobre factores macro.
    """
    import statsmodels.api as sm

    # Asegurar mismo índice temporal
    combined = pd.DataFrame({
        'asset': asset_returns
    }).join(macro_factors, how='inner').dropna()

    if len(combined) < 60:  # Mínimo 5 años mensuales o 60 días
        raise ValueError("Insufficient data for APT regression")

    # X = factores, y = retornos del activo
    X = sm.add_constant(combined[macro_factors.columns])
    y = combined['asset']

    # Regresión OLS
    model = sm.OLS(y, X).fit()

    # Extraer coeficientes
    alpha = model.params['const']
    betas = model.params.drop('const')

    # Métricas de ajuste
    r_squared = model.rsquared
    p_values = model.pvalues

    logger.info(
        f"APT Regression: α={alpha:.4f}, R²={r_squared:.2f}, "
        f"factors={list(betas.index)}"
    )

    return {
        'alpha': alpha,
        'betas': betas.to_dict(),
        'r_squared': r_squared,
        'p_values': p_values.to_dict(),
        'model': model
    }
```

### Regla 4 — No-Arbitrage Condition

Si un portafolio sintético replicante tiene un retorno esperado mayor que el activo real (ajustado por riesgo), activar señal de arbitraje.

```python
def check_no_arbitrage(
    self,
    asset_return: float,
    synthetic_return: float,
    asset_risk: float,
    synthetic_risk: float
) -> dict:
    """
    Verificar condición de no-arbitraje.

    Ross: Arbitraje si sintético > activo (ajustado por riesgo).
    """
    # Ajustar por riesgo (Sharpe ratio)
    risk_free_rate = 0.02

    asset_sharpe = (asset_return - risk_free_rate) / asset_risk
    synthetic_sharpe = (synthetic_return - risk_free_rate) / synthetic_risk

    # Si el sintético tiene Sharpe mayor significativamente
    if synthetic_sharpe > asset_sharpe * 1.1:  # 10% buffer
        logger.critical(
            f"🚨 ARBITRAGE OPPORTUNITY: "
            f"Synthetic Sharpe={synthetic_sharpe:.2f} > Asset Sharpe={asset_sharpe:.2f}"
        )

        return {
            'arbitrage': True,
            'action': 'Buy synthetic, sell real',
            'synthetic_sharpe': synthetic_sharpe,
            'asset_sharpe': asset_sharpe
        }

    return {'arbitrage': False}
```

### Regla 5 — Unexpected Shocks (Sorpresas)

El APT modela las sorpresas. Usar la diferencia entre el dato macro publicado y el "Consenso de Mercado" (Forecast) como input.

```python
def calculate_macro_surprises(
    self,
    actual_values: pd.Series,
    forecast_values: pd.Series
) -> pd.Series:
    """
    Calcular sorpresas macro (actual - esperado).

    Ross: APT responde a sorpresas, no niveles absolutos.
    """
    surprises = actual_values - forecast_values

    # Normalizar por volatilidad histórica
    historical_std = forecast_values.rolling(20).std()
    standardized_surprises = surprises / historical_std

    logger.info(
        f"Macro surprises: Mean={surprises.mean():.4f}, "
        f"Std={surprises.std():.4f}, "
        f"Max surprise={surprises.abs().max():.4f}"
    )

    return standardized_surprises
```

### Regla 6 — Inflation Hedging

En perfiles de Capital Preservation, rechazar activos con correlación negativa significativa con la inflación inesperada.

```python
def inflation_hedge_filter(
    self,
    asset_betas: dict,
    inflation_beta: str = 'inflation',
    min_beta: float = 0.0,
    profile_type: str = 'CAPITAL_PRESERVATION'
) -> dict:
    """
    Filtrar activos por hedging de inflación.

    Ross: Capital preservation necesita protección vs inflación.
    """
    if profile_type != 'CAPITAL_PRESERVATION':
        return {'applicable': False}

    beta_inflation = asset_betas.get(inflation_beta, 0.0)

    if beta_inflation < min_beta:
        logger.warning(
            f"❌ Inflation risk: Asset β_inflation={beta_inflation:.2f} < {min_beta:.2f}. "
            f"Reject for Capital Preservation."
        )

        return {
            'pass': False,
            'beta_inflation': beta_inflation,
            'reason': 'Negative inflation exposure'
        }

    logger.info(
        f"✅ Inflation hedge OK: β_inflation={beta_inflation:.2f} >= {min_beta:.2f}"
    )

    return {
        'pass': True,
        'beta_inflation': beta_inflation
    }
```

### Regla 7 — Systematic vs Idiosyncratic Risk

Calcular la varianza explicada por los factores macro. Si `R² < 0.2`, el riesgo es idiosincrático (diversificable). Si `R² > 0.7`, el riesgo es sistémico (no diversificable).

```python
def decompose_risk(
    self,
    r_squared: float
) -> dict:
    """
    Descomponer riesgo en sistemático vs idiosincrático.

    Ross: R² alta = riesgo sistemático (no diversificable).
    """
    systematic_ratio = r_squared
    idiosyncratic_ratio = 1 - r_squared

    if r_squared < 0.2:
        risk_type = 'Idiosyncratic'
        implication = 'Diversifiable'

    elif r_squared > 0.7:
        risk_type = 'Systematic'
        implication = 'Non-diversifiable'

    else:
        risk_type = 'Mixed'
        implication = 'Partially diversifiable'

    logger.info(
        f"Risk decomposition: R²={r_squared:.2f} → "
        f"{risk_type} ({implication})"
    )

    return {
        'systematic_pct': systematic_ratio * 100,
        'idiosyncratic_pct': idiosyncratic_ratio * 100,
        'risk_type': risk_type,
        'implication': implication
    }
```

### Regla 8 — Risk Premium Estimation

Asignar una prima de riesgo (λ) a cada factor. Si la prima de riesgo del mercado baja, reducir exposición a factores de alta beta.

```python
def estimate_factor_risk_premiums(
    self,
    factor_returns: pd.DataFrame
) -> pd.Series:
    """
    Estimar primas de riesgo de factores.

    Ross: Prima de riesgo = retorno esperado del factor.
    """
    risk_premiums = factor_returns.mean() * 252  # Anualizar

    logger.info(
        f"Factor risk premiums: "
        f"{risk_premiums.to_dict()}"
    )

    return risk_premiums
```

### Regla 9 — Orthogonalization (Factores Independientes)

Ortogonalizar los factores macro (usando PCA o Gram-Schmidt) para evitar multicolinealidad en la regresión.

```python
def orthogonalize_factors(
    self,
    factors: pd.DataFrame,
    method: str = 'pca'
) -> pd.DataFrame:
    """
    Ortogonalizar factores para evitar multicolinealidad.

    Ross: Factores correlacionados = betas inestables.
    """
    if method == 'pca':
        from sklearn.decomposition import PCA

        pca = PCA(n_components=len(factors.columns))
        factors_orthogonal = pca.fit_transform(factors)

        factors_orthogonal = pd.DataFrame(
            factors_orthogonal,
            index=factors.index,
            columns=[f'{col}_orth' for col in factors.columns]
        )

        logger.info(
            f"PCA orthogonalization: Explained variance = {pca.explained_variance_ratio_}"
        )

    elif method == 'gram-schmidt':
        # Implementación manual de Gram-Schmidt
        factors_orthogonal = factors.copy()

        for i in range(1, len(factors.columns)):
            for j in range(i):
                # Proyectar factor i sobre factor j
                col_i = factors_orthogonal.iloc[:, i]
                col_j = factors_orthogonal.iloc[:, j]

                projection = ((col_i * col_j).sum() / (col_j ** 2).sum()) * col_j

                factors_orthogonal.iloc[:, i] -= projection

        # Renombrar columnas
        factors_orthogonal.columns = [f'{col}_orth' for col in factors.columns]

        logger.info("Gram-Schmidt orthogonalization complete")

    return factors_orthogonal
```

### Regla 10 — Term Structure Factor

Incluir la pendiente de la curva de tipos (10Y - 2Y) como factor predictor de ciclo económico.

```python
def get_term_structure_factor(
    self,
    start_date: str,
    end_date: str
) -> pd.Series:
    """
    Pendiente de la curva de tipos como factor.

    Ross: 10Y-2Y slope predictor de ciclo económico.
    """
    # Obtener tasas 10Y y 2Y
    rate_10y = self.get_treasury_rate(start_date, end_date, maturity='10Y')
    rate_2y = self.get_treasury_rate(start_date, end_date, maturity='2Y')

    # Pendiente (spread)
    term_structure = rate_10y - rate_2y

    logger.info(
        f"Term structure: Mean={term_structure.mean():.2%}, "
        f"Steepness indicator={term_structure.iloc[-1]:.2%}"
    )

    return term_structure
```

### Regla 11 — Credit Spread Factor

Incluir el spread High Yield (HYG) vs Treasury (IEF) como proxy de riesgo de crédito sistémico.

```python
def get_credit_spread_factor(
    self,
    start_date: str,
    end_date: str
) -> pd.Series:
    """
    Spread de crédito como factor.

    Ross: HY vs Treasury = riesgo de crédito sistémico.
    """
    # Yield HYG (High Yield)
    hyg_yield = self.get_etf_yield(start_date, end_date, 'HYG')

    # Yield Treasury
    treasury_yield = self.get_treasury_rate(start_date, end_date, maturity='10Y')

    # Credit spread
    credit_spread = hyg_yield - treasury_yield

    logger.info(
        f"Credit spread: Mean={credit_spread.mean():.2%}, "
        f"Current={credit_spread.iloc[-1]:.2%}"
    )

    return credit_spread
```

### Regla 12 — Pure Play Portfolios

Construir portafolios que tengan Beta=1 a un factor (ej. Inflación) y Beta=0 al resto, para coberturas quirúrgicas.

```python
def construct_pure_play_portfolio(
    self,
    asset_betas: pd.DataFrame,  # assets x factors
    target_factor: str,
    target_beta: float = 1.0
) -> dict:
    """
    Construir portafolio puro para un factor.

    Ross: Beta=1 al factor objetivo, Beta=0 a otros.
    """
    from scipy.optimize import minimize

    n_assets = len(asset_betas)

    # Función objetivo: minimizar exposición a otros factores
    def objective(weights):
        portfolio_betas = weights @ asset_betas.values

        # Queremos: target_factor = target_beta, otros = 0
        target_betas = np.zeros(len(asset_betas.columns))
        factor_idx = list(asset_betas.columns).index(target_factor)
        target_betas[factor_idx] = target_beta

        # Error vs target
        error = np.sum((portfolio_betas - target_betas) ** 2)

        return error

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Suma = 1
    ]

    bounds = [(0, 1) for _ in range(n_assets)]

    x0 = np.ones(n_assets) / n_assets

    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        logger.error(f"Pure play optimization failed: {result.message}")
        return None

    weights = pd.Series(result.x, index=asset_betas.index)

    # Verificar betas resultantes
    portfolio_betas = weights @ asset_betas.values

    logger.info(
        f"Pure play {target_factor}: "
        f"Betas={dict(zip(asset_betas.columns, portfolio_betas))}"
    )

    return {
        'weights': weights,
        'portfolio_betas': dict(zip(asset_betas.columns, portfolio_betas)),
        'target_factor': target_factor
    }
```

### Regla 13 — Rolling Betas

Calcular las sensibilidades en ventanas de 60 meses. Los regímenes macro cambian lento.

```python
def calculate_rolling_betas(
    self,
    asset_returns: pd.Series,
    macro_factors: pd.DataFrame,
    window_months: int = 60
) -> pd.DataFrame:
    """
    Betas rodantes para capturar cambios de régimen.

    Ross: Sensibilidades macro cambian lentamente (60 meses).
    """
    import statsmodels.api as sm

    rolling_betas = []

    # Ventana rodante (usando meses aproximados como 21 días)
    window_days = window_months * 21

    for i in range(window_days, len(asset_returns)):
        # Datos en ventana
        window_returns = asset_returns.iloc[i-window_days:i]
        window_factors = macro_factors.iloc[i-window_days:i]

        # Regresión
        combined = pd.DataFrame({
            'asset': window_returns
        }).join(window_factors, how='inner').dropna()

        if len(combined) < 30:  # Mínimo observaciones
            continue

        X = sm.add_constant(combined[macro_factors.columns])
        y = combined['asset']

        model = sm.OLS(y, X).fit()

        # Guardar betas (excluyendo constante)
        betas = model.params.drop('const')
        betas['date'] = asset_returns.index[i]

        rolling_betas.append(betas)

    betas_df = pd.DataFrame(rolling_betas).set_index('date')

    logger.info(
        f"Rolling betas: {len(betas_df)} periods, "
        f"factors={list(betas_df.columns)}"
    )

    return betas_df
```

### Regla 14 — Residual Analysis (Autocorrelación)

Si los residuos (ε) muestran autocorrelación, faltan factores en el modelo (Búsqueda de Alpha).

```python
def analyze_residuals(
    self,
    apt_model: object,
    residuals: pd.Series
) -> dict:
    """
    Analizar residuos para detectar factores faltantes.

    Ross: Autocorrelación de residuos = missing factors.
    """
    from statsmodels.stats.diagnostic import acorr_ljungbox

    # Test Ljung-Box
    lb_result = acorr_ljungbox(residuals, lags=10, return_df=True)

    # P-values
    p_values = lb_result['lb_pvalue']

    # ¿Hay autocorrelación significativa?
    significant_lags = (p_values < 0.05).sum()

    if significant_lags > 0:
        logger.warning(
            f"⚠️ Residual autocorrelation: {significant_lags}/10 lags significant. "
            f"Missing factors in model."
        )

        return {
            'valid': False,
            'significant_lags': significant_lags,
            'recommendation': 'Add missing factors to APT model'
        }

    logger.info("✅ No residual autocorrelation: Model adequate")

    return {
        'valid': True,
        'recommendation': 'Model captures systematic risk'
    }
```

### Regla 15 — Event Study Logic (Shock Macro)

Si ocurre un shock macro > 3 SD (ej. subida de tipos sorpresa), re-optimizar el portafolio inmediatamente usando los nuevos betas estimados.

```python
def macro_shock_detection(
    self,
    macro_surprises: pd.Series,
    threshold_sd: float = 3.0
) -> dict:
    """
    Detectar shocks macro significativos.

    Ross: Shocks > 3 SD = re-optimizar portafolio.
    """
    # Normalizar sorpresas por SD histórica
    historical_std = macro_surprises.rolling(252).std()
    z_scores = macro_surprises / historical_std

    # Detectar shocks
    shock_mask = z_scores.abs() > threshold_sd
    shocked_factors = z_scores[shock_mask]

    if len(shocked_factors) > 0:
        logger.critical(
            f"🚨 MACRO SHOCK DETECTED: "
            f"{len(shocked_factors)} factors > {threshold_sd} SD. "
            f"Re-optimizing portfolio."
        )

        return {
            'shock_detected': True,
            'shocked_factors': shocked_factors.to_dict(),
            'action': 'Re-optimize portfolio with new betas'
        }

    return {'shock_detected': False}
```

---

## Aplicación Práctica

### Pipeline Completo APT

```python
def apt_portfolio_optimization(
    self,
    assets: list,
    start_date: str,
    end_date: str,
    profile_type: str = 'STANDARD'
) -> dict:
    """
    Pipeline completo de optimización APT.
    """
    # 1. Obtener factores macro
    macro_factors = self.get_macro_factors(start_date, end_date)

    # 2. Añadir factores adicionales
    term_structure = self.get_term_structure_factor(start_date, end_date)
    credit_spread = self.get_credit_spread_factor(start_date, end_date)

    macro_factors['term_structure'] = term_structure
    macro_factors['credit_spread'] = credit_spread

    # 3. Ortogonalizar factores
    macro_factors_orth = self.orthogonalize_factors(macro_factors, method='pca')

    # 4. Estimar betas para cada activo
    asset_betas = {}

    for asset in assets:
        asset_returns = self.get_asset_returns(asset, start_date, end_date)

        apt_result = self.estimate_apt_betas(asset_returns, macro_factors_orth)

        asset_betas[asset] = apt_result['betas']

    # 5. Crear DataFrame de betas
    betas_df = pd.DataFrame(asset_betas).T

    # 6. Analizar residuos (missing factors)
    for asset in assets:
        asset_returns = self.get_asset_returns(asset, start_date, end_date)

        # Reconstruir modelo para obtener residuos
        apt_result = self.estimate_apt_betas(asset_returns, macro_factors_orth)

        residuals = asset_returns - apt_result['alpha'] - sum(
            apt_result['betas'][f] * macro_factors_orth[f]
            for f in macro_factors_orth.columns
        )

        residual_analysis = self.analyze_residuals(apt_result, residuals)

    # 7. Optimizar portafolio considerando exposición a factores
    # (Esto se integra con el optimizador Markowitz)

    return {
        'asset_betas': betas_df,
        'factors': list(macro_factors_orth.columns),
        'n_factors': len(macro_factors_orth.columns)
    }
```
