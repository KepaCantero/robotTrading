# 🟡 33. "Asset Management" - Andrew Ang

## REGLAS DE GESTIÓN DE CARTERAS PARA 180 PERFILES

**Regla 33.1 — Factores, no Activos**

Claude DEBE mostrar exposición a factores, no solo "Stocks".

**50 Tech stocks NO es diversificación.**

```python
def factor_exposure_dashboard(
    self,
    portfolio: pd.DataFrame,  # columns: symbol, weight, sector
    factor_loadings: pd.DataFrame  # symbol -> factor columns
) -> dict:
    """
    Dashboard debe mostrar exposición a Inflación, Crecimiento, Volatilidad.

    Ang: Mirar factores, no solo activos.
    """
    # Factor loadings comunes
    factors = [
        'value',      # Value factor
        'size',       # Size factor (small cap)
        'momentum',   # Momentum factor
        'quality',    # Quality factor
        'low_vol',    # Low volatility factor
        'growth',     # Growth factor
        'inflation',  # Inflation sensitivity
        'duration',   # Interest rate duration
    ]

    # Calcular exposición ponderada del portfolio
    portfolio_factor_exposure = {}

    for factor in factors:
        if factor in factor_loadings.columns:
            # Exposición = Σ(weight × loading)
            exposure = (
                portfolio.set_index('symbol')['weight'] @
                factor_loadings[factor]
            )
            portfolio_factor_exposure[factor] = exposure

    # Detectar concentración de factores
    max_exposure = max(abs(v) for v in portfolio_factor_exposure.values())

    if max_exposure > 0.8:
        logger.warning(
            f"⚠️ High factor concentration: "
            f"{max(portfolio_factor_exposure.items(), key=lambda x: abs(x[1]))[0]} "
            f"= {max_exposure:.2f}"
        )

    # Detectar si es "closet indexing"
    # Si todas las exposiciones son cercanas a las del mercado
    market_factor_exposure = {
        'value': 0.0,
        'size': 0.0,
        'momentum': 0.0,
        'quality': 0.0,
        'low_vol': 0.0
    }

    tracking_error = np.sqrt(sum(
        (portfolio_factor_exposure.get(f, 0) - market_factor_exposure[f]) ** 2
        for f in market_factor_exposure
    ))

    logger.info(
        f"Portfolio factor exposures: "
        f"Value={portfolio_factor_exposure.get('value', 0):.2f}, "
        f"Momentum={portfolio_factor_exposure.get('momentum', 0):.2f}, "
        f"Quality={portfolio_factor_exposure.get('quality', 0):.2f}"
    )

    return {
        'factor_exposures': portfolio_factor_exposure,
        'tracking_error': tracking_error,
        'is_closet_indexer': tracking_error < 0.1
    }
```

**Regla 33.2 — Factor Diversification**

```python
def true_diversification_check(
    self,
    portfolio: pd.DataFrame,
    factor_loadings: pd.DataFrame
) -> dict:
    """
    50 acciones de tecnología = UNA sola apuesta (Growth).

    Ang: Diversificación real = factores diversificados.
    """
    # Agrupar por sector
    sector_weights = portfolio.groupby('sector')['weight'].sum()

    # Concentración sectorial
    max_sector_weight = sector_weights.max()
    max_sector = sector_weights.idxmax()

    if max_sector_weight > 0.40:
        logger.warning(
            f"⚠️ Sector concentration: {max_sector} = {max_sector_weight:.1%}. "
            f"NOT diversified."
        )

    # Factor concentration
    portfolio_factor_exp = self.calculate_factor_exposures(
        portfolio, factor_loadings
    )

    # Normalizar exposiciones
    total_factor_exposure = sum(abs(v) for v in portfolio_factor_exp.values())

    if total_factor_exposure > 0:
        factor_concentrations = {
            f: abs(v) / total_factor_exposure
            for f, v in portfolio_factor_exp.items()
        }

        max_factor_concentration = max(factor_concentrations.values())

        if max_factor_concentration > 0.6:
            logger.warning(
                f"⚠️ Factor concentration: "
                f"{max(factor_concentrations.items(), key=lambda x: x[1])[0]} = "
                f"{max_factor_concentration:.1%}"
            )

    return {
        'sector_concentration': max_sector_weight,
        'factor_concentration': max_factor_concentration,
        'truly_diversified': max_sector_weight < 0.40 and max_factor_concentration < 0.6
    }
```

**Regla 33.3 — Illiquidity Premium**

```python
def illiquidity_premium_allocation(
    self,
    profile_horizon_years: float,
    illiquid_assets: List[dict],
    max_illiquid_allocation: float = 0.10
) -> float:
    """
    Horizonte > 5 años → permitir 10% illiquids.

    Ang: Illiquidity premium captura retornos adicionales.
    """
    if profile_horizon_years < 5:
        logger.info(
            f"Horizon {profile_horizon_years:.1f}y < 5y. "
            f"No illiquid assets."
        )
        return 0.0

    # Asignar hasta 10% a illiquids
    illiquid_allocation = min(
        max_illiquid_allocation,
        0.02 * (profile_horizon_years - 5)  # 2% por año adicional
    )

    logger.info(
        f"Horizon {profile_horizon_years:.1f}y allows "
        f"{illiquid_allocation:.1%} illiquid allocation "
        f"(illiquidity premium)"
    )

    return illiquid_allocation
```

**Regla 33.4 — Dynamic Rebalancing**

```python
def dynamic_rebalancing_trigger(
    self,
    current_weights: pd.Series,
    target_weights: pd.Series,
    transaction_costs: dict,
    tax_benefits: dict
) -> dict:
    """
    Rebalancear SOLO si beneficios fiscales > costo de deriva.

    Ang: NO rebalancear por fecha.
    """
    # Calcular desviación
    drift = abs(current_weights - target_weights).sum()

    # Costo de transacción
    total_txn_cost = sum(
        transaction_costs[symbol] * abs(current_weights[symbol] - target_weights[symbol])
        for symbol in target_weights.index
    )

    # Beneficios fiscales (loss harvesting)
    total_tax_benefit = sum(tax_benefits.values())

    # Costo de deriva (tracking error)
    drift_cost = drift * 0.5  # 50 bps por 1% de drift

    # Decisión
    net_benefit = total_tax_benefit - total_txn_cost - drift_cost

    if net_benefit > 0:
        logger.info(
            f"Rebalance: Net benefit = ${net_benefit:,.0f} "
            f"(Tax=${total_tax_benefit:,.0f}, Txn=${total_txn_cost:,.0f}, "
            f"Drift=${drift_cost:,.0f})"
        )
        return {'rebalance': True, 'reason': 'Net benefit positive'}

    logger.info(
        f"No rebalance: Net benefit = ${net_benefit:,.0f} "
        f"(Drift cost too low)"
    )

    return {'rebalance': False, 'reason': 'Net benefit negative'}
```

**Regla 33.5 — Liability Driven Investing**

```python
def liability_driven_objective(
    self,
    profile_type: str,
    inflation_real: float,
    real_return_target: float
) -> dict:
    """
    CAPITAL_PRESERVATION: no perder poder adquisitivo vs inflación REAL.

    Ang: Objetivo ≠ ganar dinero, = mantener poder de compra.
    """
    if profile_type != 'CAPITAL_PRESERVATION':
        return {'applicable': False}

    # Inflación real (no CPI)
    # Para capital preservation, usar inflación personal (ej: retired, healthcare)
    personal_inflation = inflation_real + 0.01  # +1% para gastos médicos

    # Return objetivo = mantener poder de compra
    target_return = personal_inflation

    logger.info(
        f"LDI objective: Maintain purchasing power. "
        f"Target={target_return:.2%} (Inflation={personal_inflation:.2%})"
    )

    return {
        'objective': 'MAINTAIN_PURCHASING_POWER',
        'target_return': target_return,
        'inflation_assumption': personal_inflation,
        'max_acceptable_loss': -0.02,  # -2% real
        'assets_focus': ['TIPS', 'Short-term bonds', 'Inflation-protected']
    }
```

**Regla 33.6 — Benchmark-Relative Risk**

```python
def benchmark_relative_risk(
    self,
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    benchmark_name: str = 'S&P 500 Dividend Aristocrats'
) -> dict:
    """
    Riesgo = Tracking Error vs objetivo.

    Ang: Medir riesgo relativo al benchmark, no absoluto.
    """
    # Excess returns
    excess_returns = portfolio_returns - benchmark_returns

    # Tracking Error (desviación estándar de excess returns)
    tracking_error = excess_returns.std() * np.sqrt(252)

    # Information Ratio
    information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

    # Beta relativo
    covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
    benchmark_variance = benchmark_returns.var()
    relative_beta = covariance / benchmark_variance

    logger.info(
        f"Benchmark-relative: TE={tracking_error:.2%}, "
        f"IR={information_ratio:.2f}, Beta={relative_beta:.2f}"
    )

    # Tracking Error máximo aceptable
    max_te = 0.05  # 5%

    if tracking_error > max_te:
        logger.warning(
            f"⚠️ Tracking Error {tracking_error:.2%} > {max_te:.0%}"
        )

    return {
        'tracking_error': tracking_error,
        'information_ratio': information_ratio,
        'relative_beta': relative_beta,
        'within_limit': tracking_error <= max_te
    }
```

**Regla 33.7 — Factor Carry**

```python
def factor_carry_allocation(
    self,
    market_trend: str,  # 'BULL', 'BEAR', 'SIDEWAYS'
    carry_assets: List[dict]
) -> dict:
    """
    En mercados laterales, buscar activos con Carry sistemáticamente.

    Ang: Carry compensa falta de capital gains.
    """
    if market_trend != 'SIDEWAYS':
        return {'carry_boost': 0}

    # Identificar activos con carry positivo
    carry_signals = []

    for asset in carry_assets:
        carry_yield = asset.get('dividend_yield', 0) + asset.get('swap_yield', 0)

        if carry_yield > 0.02:  # > 2% carry
            carry_signals.append({
                'symbol': asset['symbol'],
                'carry_yield': carry_yield,
                'boost_factor': min(1.5, 1 + carry_yield * 5)  # Boost proporcional
            })

    if carry_signals:
        logger.info(
            f"Sideways market: Boosting {len(carry_signals)} carry assets "
            f"to compensate for lack of capital gains"
        )

    return {
        'carry_boost': len(carry_signals) > 0,
        'assets_to_boost': carry_signals
    }
```

**Regla 33.8 — Rebalanceo de Volatilidad**

```python
def volatility_based_rebalancing(
    self,
    current_weights: pd.Series,
    current_volatilities: pd.Series,  # symbol -> vol
    target_weights: pd.Series
) -> dict:
    """
    Si volatilidad se duplica → peso a la mitad inmediatamente.

    Ang: Mantener presupuesto de riesgo constante.
    """
    # Calcular risk contribution de cada activo
    risk_contributions = current_weights * current_volatilities

    # Risk budget total
    total_risk = risk_contributions.sum()

    # Detectar cambios drásticos
    trades = []

    for symbol in current_weights.index:
        current_vol = current_volatilities[symbol]
        target_vol = self.get_historical_volatility(symbol, lookback=252)

        vol_ratio = current_vol / target_vol

        if vol_ratio >= 2.0:
            # Volatilidad se duplicó → reducir peso a la mitad
            new_weight = target_weights[symbol] / vol_ratio

            trades.append({
                'symbol': symbol,
                'old_weight': current_weights[symbol],
                'new_weight': new_weight,
                'reason': f'Volatility increased {vol_ratio:.1f}x'
            })

            logger.warning(
                f"⚠️ {symbol}: Vol {vol_ratio:.1f}x. "
                f"Reducing weight {current_weights[symbol]:.2%} → {new_weight:.2%}"
            )

    return trades
```

**Regla 33.9 — Downside Correlation**

```python
def downside_correlation_stress_test(
    self,
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> dict:
    """
    En crisis, correlaciones → 1.0. Prepararse para "fin del mundo".

    Ang: Diversificación desaparece en crash.
    """
    # Correlación normal
    normal_corr = portfolio_returns.corr(benchmark_returns)

    # Correlación en días negativos (downside)
    portfolio_down = portfolio_returns[portfolio_returns < 0]
    benchmark_down = benchmark_returns[benchmark_returns < 0]

    # Align
    combined = pd.DataFrame({
        'portfolio': portfolio_down,
        'benchmark': benchmark_down
    }).dropna()

    downside_corr = combined['portfolio'].corr(combined['benchmark'])

    # Correlación en crashes (bottom 5% days)
    crash_threshold = portfolio_returns.quantile(0.05)

    portfolio_crash = portfolio_returns[portfolio_returns < crash_threshold]
    benchmark_crash = benchmark_returns[portfolio_returns < crash_threshold]

    combined_crash = pd.DataFrame({
        'portfolio': portfolio_crash,
        'benchmark': benchmark_crash
    }).dropna()

    crash_corr = combined_crash['portfolio'].corr(combined_crash['benchmark'])

    logger.info(
        f"Correlation: Normal={normal_corr:.2f}, "
        f"Downside={downside_corr:.2f}, Crash={crash_corr:.2f}"
    )

    # Si downside corr > 0.9, diversificación falla
    if downside_corr > 0.9:
        logger.warning(
            f"⚠️ Downside correlation {downside_corr:.2f}. "
            f"Diversification fails in stress."
        )

    return {
        'normal_correlation': normal_corr,
        'downside_correlation': downside_corr,
        'crash_correlation': crash_corr,
        'diversification_works_in_crash': crash_corr < 0.9
    }
```

**Regla 33.10 — Risk Parity Lite**

```python
def risk_parity_allocation(
    self,
    assets: List[str],
    volatilities: pd.Series,
    correlations: pd.DataFrame
) -> pd.Series:
    """
    Cada activo aporta igualdad de RIESGO, no de dinero.

    Ang: Risk Parity Lite.
    """
    n_assets = len(assets)

    # Si no hay datos de correlación, asumir correlación = 0
    if correlations.empty:
        # Pesos inversamente proporcionales a volatilidad
        inv_vols = 1 / volatilities[assets]
        weights = inv_vols / inv_vols.sum()

    else:
        # Risk Parity completo: usar optimizador
        # Para simplificar, usar inverso de varianza como aproximación
        inv_vars = 1 / (volatilities[assets] ** 2)
        weights = inv_vars / inv_vars.sum()

    # Validar risk contribution
    risk_contributions = weights * volatilities[assets]
    max_rc = risk_contributions.max()
    min_rc = risk_contributions.min()

    rc_ratio = max_rc / min_rc if min_rc > 0 else float('inf')

    logger.info(
        f"Risk Parity: RC ratio={rc_ratio:.2f} "
        f"(ideal=1.0, acceptable=<2.0)"
    )

    if rc_ratio > 2.0:
        logger.warning("⚠️ Risk contributions not balanced")

    return pd.Series(weights, index=assets)
```

**Regla 33.11 — Exposición a Inflación**

```python
def inflation_hedge_allocation(
    self,
    profile_type: str,
    profile_size: str,
    horizon_years: float
) -> dict:
    """
    Perfiles LARGE de largo plazo → 5-10% materias primas o TIPS.

    Ang: Proteger contra inflación es crítico.
    """
    # Solo para perfiles LARGE de largo plazo
    if profile_type != 'LARGE' or horizon_years < 10:
        return {'inflation_allocation': 0}

    # Asignar 5-10%
    inflation_allocation = 0.05 + 0.05 * min(1.0, (horizon_years - 10) / 10)

    logger.info(
        f"Long-term LARGE profile: {inflation_allocation:.1%} "
        f"to inflation hedges (TIPS, commodities)"
    )

    return {
        'inflation_allocation': inflation_allocation,
        'assets': [
            {'type': 'TIPS', 'weight': inflation_allocation * 0.6},
            {'type': 'Commodities', 'weight': inflation_allocation * 0.4}
        ]
    }
```

**Regla 33.12 — Optimización de Media-Varianza Robusta**

```python
def robust_mean_variance_optimization(
    self,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    shrinkage_intensity: float = 0.5
) -> pd.Series:
    """
    NO usar estimadores de punto. Bayesian Shrinkage.

    Ang: Estimadores puntuales son erráticos.
    """
    from sklearn.covariance import LedoitWolf

    n_assets = len(expected_returns)

    # Shrinkage de covarianza (Ledoit-Wolf)
    lw = LedoitWolf()
    shrunk_cov, _ = lw.fit(cov_matrix.values).covariance_, lw.shrinkage_

    shrunk_cov = pd.DataFrame(shrunk_cov, index=cov_matrix.index, columns=cov_matrix.columns)

    # Shrinkage de retornos esperados hacia el promedio
    market_return = expected_returns.mean()

    shrunk_returns = (
        (1 - shrinkage_intensity) * expected_returns +
        shrinkage_intensity * market_return
    )

    # Optimización simple (equal risk contribution como base)
    # Para producción, usar CVXPY
    inv_vols = 1 / np.sqrt(np.diag(shrunk_cov))
    weights = inv_vols / inv_vols.sum()

    logger.info(
        f"Robust optimization: Shrinkage={shrinkage_intensity:.0%}, "
        f"Cov conditioned number={np.linalg.cond(shrunk_cov.values):.1f}"
    )

    return pd.Series(weights, index=expected_returns.index)
```

**Regla 33.13 — Active Share**

```python
def active_share_check(
    self,
    portfolio_weights: pd.Series,
    benchmark_weights: pd.Series
) -> dict:
    """
    Si estrategia parece al índice → apagar.

    Ang: No pagues fees por ser Closet Indexer.
    """
    # Active Share = 0.5 × Σ|w_portfolio - w_benchmark|
    active_share = 0.5 * abs(portfolio_weights - benchmark_weights).sum()

    logger.info(f"Active Share: {active_share:.1%}")

    if active_share < 0.20:
        logger.critical(
            f"🚨 CLOSET INDEXER: Active Share {active_share:.1%} < 20%. "
            f"Why pay active fees?"
        )

        return {
            'is_closet_indexer': True,
            'active_share': active_share,
            'recommendation': 'Switch to passive index fund'
        }

    elif active_share < 0.60:
        logger.warning(
            f"Low Active Share: {active_share:.1%}. "
            f"Consider increasing active positions."
        )

    return {
        'is_closet_indexer': False,
        'active_share': active_share,
        'active_management_justified': active_share >= 0.60
    }
```

**Regla 33.14 — Factor Momentum**

```python
def factor_momentum_allocation(
    self,
    factor_returns: dict,  # {'value': [...], 'momentum': [...], ...}
    profile_risk: str  # 'LOW', 'MEDIUM', 'HIGH'
) -> dict:
    """
    Si Value funcionó 3 meses → aumentar peso en HIGH RISK.

    Ang: Factor Momentum.
    """
    # Returns de factores últimos 3 meses
    factor_3m_returns = {}

    for factor, returns_history in factor_returns.items():
        if len(returns_history) >= 63:  # 3 meses ~ 63 días
            factor_3m_returns[factor] = returns_history.iloc[-63:].sum()

    # Ordenar factores por performance
    sorted_factors = sorted(
        factor_3m_returns.items(),
        key=lambda x: x[1],
        reverse=True
    )

    best_factor = sorted_factors[0][0] if sorted_factors else None
    best_return = sorted_factors[0][1] if sorted_factors else 0

    # Solo ajustar en perfiles de alto riesgo
    if profile_risk == 'HIGH' and best_factor and best_return > 0.02:
        # Aumentar peso del mejor factor
        boost_factor = 1.2  # +20%

        logger.info(
            f"Factor Momentum: {best_factor} +{best_return:.1%} (3M). "
            f"Boosting {boost_factor:.0%} in HIGH risk profiles"
        )

        return {
            'factor_to_boost': best_factor,
            'boost_factor': boost_factor
        }

    return {}
```

**Regla 33.15 — Regla del 5%**

```python
def max_position_limit(
    self,
    proposed_weights: pd.Series,
    portfolio_risk_budget: float,
    max_single_position: float = 0.05  # 5%
) -> dict:
    """
    NINGÚN activo > 5% del riesgo total.

    Ang: Concentración excesiva = peligro.
    """
    violations = []

    for symbol, weight in proposed_weights.items():
        # Calcular contribución al riesgo
        asset_vol = self.get_volatility(symbol)
        risk_contribution = weight * asset_vol

        # Si > 5% del riesgo total
        if risk_contribution > max_single_position:
            violations.append({
                'symbol': symbol,
                'proposed_weight': weight,
                'risk_contribution': risk_contribution,
                'max_allowed': max_single_position,
                'reduced_weight': max_single_position / asset_vol
            })

            logger.error(
                f"❌ {symbol}: Risk contribution {risk_contribution:.1%} "
                f"> {max_single_position:.0%} limit. "
                f"Reduce to {max_single_position / asset_vol:.2%}"
            )

    if violations:
        # Ajustar pesos
        adjusted_weights = proposed_weights.copy()

        for v in violations:
            adjusted_weights[v['symbol']] = v['reduced_weight']

        # Renormalizar
        adjusted_weights = adjusted_weights / adjusted_weights.sum()

        return {
            'violations': violations,
            'adjusted_weights': adjusted_weights,
            'original_weights': proposed_weights
        }

    return {
        'violations': [],
        'weights': proposed_weights
    }
```
