# 📄 Papers Fundamentales - Artzner, Delbaen, Eber & Heath: Expected Shortfall (1999)

## Coherent Risk Measures: Expected Shortfall (CVaR)

**Contexto:** Gestión de Riesgos Extremos (Fat Tails) y Perfiles Agresivos (RiskEngine/TailRisk).

Artzner et al. revolucionaron la gestión de riesgos al introducir el concepto de "medidas de riesgo coherentes", demostrando que VaR no cumple con la propiedad de subaditividad, mientras que Expected Shortfall (CVaR) sí.

---

### Regla 1 — Coherencia del Riesgo

El sistema DEBE usar Expected Shortfall (CVaR) como métrica principal, ya que cumple con la propiedad de subaditividad: `Riesgo(A + B) ≤ Riesgo(A) + Riesgo(B)`.

```python
def verify_coherence(
    self,
    returns_a: pd.Series,
    returns_b: pd.Series,
    confidence_level: float = 0.95
) -> dict:
    """
    Verificar coherencia de la medida de riesgo.

    Artzner et al: CVaR es coherente, VaR no lo es.
    """
    # Calcular VaR y ES individual
    var_a = np.percentile(returns_a, (1 - confidence_level) * 100)
    var_b = np.percentile(returns_b, (1 - confidence_level) * 100)

    es_a = returns_a[returns_a <= var_a].mean()
    es_b = returns_b[returns_b <= var_b].mean()

    # Portfolio
    returns_portfolio = (returns_a + returns_b) / 2

    var_portfolio = np.percentile(returns_portfolio, (1 - confidence_level) * 100)
    es_portfolio = returns_portfolio[returns_portfolio <= var_portfolio].mean()

    # Verificar subaditividad
    # VaR: VaR(A+B) ≤ VaR(A) + VaR(B) ? No siempre
    var_sum = (var_a + var_b) / 2

    var_is_subadditive = var_portfolio <= var_sum

    # ES: ES(A+B) ≤ ES(A) + ES(B) ? Siempre
    es_sum = (es_a + es_b) / 2

    es_is_subadditive = es_portfolio <= es_sum

    logger.info(
        f"Coherence check: VaR subadditive={var_is_subadditive}, "
        f"ES subadditive={es_is_subadditive}"
    )

    return {
        'var_is_coherent': var_is_subadditive,
        'es_is_coherent': es_is_subadditive,
        'var_portfolio': var_portfolio,
        'var_sum': var_sum,
        'es_portfolio': es_portfolio,
        'es_sum': es_sum
    }
```

### Regla 2 — Cálculo de la Cola (Expected Shortfall)

Definir `ES_α` como la media de las pérdidas que exceden el umbral `VaR_α` (usualmente `α = 95%`).

```python
def calculate_expected_shortfall(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95
) -> dict:
    """
    Calcular Expected Shortfall (CVaR/ES).

    Artzner et al: ES = media de pérdidas en cola α.
    """
    # VaR
    var = np.percentile(returns, (1 - confidence_level) * 100)

    # ES: media de retornos ≤ VaR
    tail_losses = returns[returns <= var]

    if len(tail_losses) == 0:
        logger.warning("No tail losses found")
        expected_shortfall = var
    else:
        expected_shortfall = tail_losses.mean()

    # Métricas adicionales
    n_tail = len(tail_losses)
    tail_percentage = n_tail / len(returns)

    logger.info(
        f"ES({confidence_level:.0%}): VaR={var:.2%}, "
        f"ES={expected_shortfall:.2%}, "
        f"Tail={n_tail} obs ({tail_percentage:.1%})"
    )

    return {
        'var': var,
        'expected_shortfall': expected_shortfall,
        'tail_losses': tail_losses.values if len(tail_losses) > 0 else np.array([]),
        'n_tail': n_tail,
        'confidence_level': confidence_level
    }
```

### Regla 3 — Fat Tail Check

Si el ratio `ES_95 / VaR_95 > 1.5`, clasificar el activo como "Fat Tailed" y reducir el apalancamiento máximo permitido a la mitad.

```python
def classify_fat_tails(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    fat_tail_threshold: float = 1.5
) -> dict:
    """
    Detectar colas pesadas (fat tails).

    Artzner et al: Ratio ES/VaR > 1.5 = fat tails.
    """
    # Calcular VaR y ES
    var = np.percentile(returns, (1 - confidence_level) * 100)
    es = returns[returns <= var].mean()

    # Ratio (en valor absoluto)
    ratio = abs(es / var) if var != 0 else 1.0

    if ratio > fat_tail_threshold:
        logger.critical(
            f"🚨 FAT TAILS DETECTED: ES/VaR ratio={ratio:.2f} > {fat_tail_threshold:.1f}. "
            f"Reducing max leverage to 50%."
        )

        return {
            'fat_tailed': True,
            'es_var_ratio': ratio,
            'max_leverage_multiplier': 0.5,
            'distribution': 'Fat-tailed (non-normal)'
        }

    logger.info(
        f"Normal tails: ES/VaR ratio={ratio:.2f}"
    )

    return {
        'fat_tailed': False,
        'es_var_ratio': ratio,
        'max_leverage_multiplier': 1.0,
        'distribution': 'Normal-ish'
    }
```

### Regla 4 — Optimización CVaR

En el optimizador de portafolio, sustituir la minimización de varianza por la minimización de Expected Shortfall para protegerse contra colapsos sistémicos.

```python
def optimize_portfolio_cvar(
    self,
    returns: pd.DataFrame,
    confidence_level: float = 0.95
) -> pd.Series:
    """
    Optimizar portafolio minimizando CVaR.

    Artzner et al: CVaR optimization > Mean-Variance.
    """
    from scipy.optimize import minimize

    n_assets = len(returns.columns)

    # Función objetivo: CVaR del portafolio
    def portfolio_cvar(weights):
        # Retornos del portafolio
        portfolio_returns = returns @ weights

        # CVaR
        var = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        cvar = portfolio_returns[portfolio_returns <= var].mean()

        return cvar

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Suma = 1
    ]

    bounds = [(0, 1) for _ in range(n_assets)]

    x0 = np.ones(n_assets) / n_assets

    # Optimizar
    result = minimize(
        portfolio_cvar,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        logger.error(f"CVaR optimization failed: {result.message}")
        return None

    weights = pd.Series(result.x, index=returns.columns)

    # Calcular métricas del portafolio óptimo
    portfolio_returns = returns @ weights
    var_95 = np.percentile(portfolio_returns, 5)
    es_95 = portfolio_returns[portfolio_returns <= var_95].mean()

    logger.info(
        f"CVaR-optimal portfolio: VaR(95%)={var_95:.2%}, "
        f"ES(95%)={es_95:.2%}"
    )

    return weights
```

### Regla 5 — Stress Testing Histórico

El ES DEBE incluir obligatoriamente el peor escenario de la crisis de 2008 o 2020 en su ventana de cálculo.

```python
def stress_test_with_cvar(
    self,
    returns: pd.DataFrame,
    stress_periods: dict,
    confidence_level: float = 0.95
) -> dict:
    """
    Stress testing con CVaR para escenarios históricos.

    Artzner et al: ES debe incluir crisis históricas.
    """
    stress_results = {}

    for period_name, (start, end) in stress_periods.items():
        # Filtrar periodo de estrés
        stress_returns = returns.loc[start:end]

        # Calcular CVaR durante el periodo
        period_stress = {}

        for asset in returns.columns:
            asset_returns = stress_returns[asset].dropna()

            var = np.percentile(asset_returns, (1 - confidence_level) * 100)
            cvar = asset_returns[asset_returns <= var].mean()

            period_stress[asset] = {
                'var': var,
                'cvar': cvar,
                'max_loss': asset_returns.min()
            }

        stress_results[period_name] = period_stress

        logger.info(
            f"Stress {period_name}: "
            f"Max loss={max(v['max_loss'] for v in period_stress.values()):.2%}"
        )

    # Validar: si pérdida > 20% en cualquier escenario
    max_loss_across_scenarios = max(
        max(v['max_loss'] for v in period.values())
        for period in stress_results.values()
    )

    if max_loss_across_scenarios < -0.20:
        logger.critical(
            f"🚨 STRESS TEST FAIL: Loss {max_loss_across_scenarios:.1%} < -20% in stress scenario"
        )

        return {
            'passes': False,
            'max_loss': max_loss_across_scenarios,
            'results': stress_results
        }

    return {
        'passes': True,
        'max_loss': max_loss_across_scenarios,
        'results': stress_results
    }
```

### Regla 6 — Liquidity Risk Integration

Sumar un componente de "Liquidez en Estrés" al ES: si el mercado se seca, la pérdida esperada aumenta un 20%.

```python
def liquidity_adjusted_cvar(
    self,
    returns: pd.Series,
    avg_daily_volume: float,
    position_size: float,
    avg Spread: float,
    confidence_level: float = 0.95
) -> dict:
    """
    Ajustar CVaR por riesgo de liquidez.

    Artzner et al: LVaR = VaR + costo de liquidación forzosa.
    """
    # CVaR estándar
    var = np.percentile(returns, (1 - confidence_level) * 100)
    es = returns[returns <= var].mean()

    # Costo de liquidez (bid-ask spread)
    # Si posición grande, spread se ensancha
    participation_rate = position_size / avg_daily_volume

    if participation_rate > 0.05:  # > 5% ADV
        # Spread se ensancha proporcionalmente
        liquidity_adjustment = avg_Spread * (1 + participation_rate * 10)

    else:
        liquidity_adjustment = avg_Spread

    # LVaR = ES + ajuste de liquidez
    les = es + liquidity_adjustment

    logger.info(
        f"LVaR({confidence_level:.0%}): ES={es:.2%}, "
        f"LiqAdj={liquidity_adjustment:.2%}, LVaR={les:.2%}"
    )

    return {
        'es': es,
        'liquidity_adjustment': liquidity_adjustment,
        'liquidity_adjusted_es': les,
        'participation_rate': participation_rate
    }
```

### Regla 7 — Sizing por CVaR

`PositionSize = AccountRisk / CVaR`. Esto asignará menos capital a activos con historial de "gaps" (como BioTech o Crypto).

```python
def cvar_position_sizing(
    self,
    account_value: float,
    asset_returns: pd.Series,
    account_risk_pct: float = 0.02,
    confidence_level: float = 0.95
) -> dict:
    """
    Sizing por CVaR (Risk Parity por riesgo de cola).

    Artzner et al: Position = AccountRisk / CVaR.
    """
    # Calcular CVaR del activo
    cvar_result = self.calculate_expected_shortfall(asset_returns, confidence_level)
    cvar = abs(cvar_result['expected_shortfall'])

    if cvar == 0:
        logger.warning("Zero CVaR - using fallback")
        cvar = asset_returns.std()

    # Position sizing
    account_risk = account_value * account_risk_pct
    position_value = account_risk / cvar

    # Validar contra posición máxima
    max_position = account_value * 0.20  # Max 20%

    position_value = min(position_value, max_position)

    n_shares = int(position_value / asset_returns.iloc[-1])

    logger.info(
        f"CVaR sizing: CVaR={cvar:.2%}, "
        f"Position=${position_value:,.0f} ({n_shares} shares)"
    )

    return {
        'cvar': cvar,
        'position_value': position_value,
        'n_shares': n_shares,
        'account_risk_used': account_risk_pct
    }
```

### Regla 8 — Re-calibración Diaria

El ES debe recalcularse cada 24h para capturar cambios en la curtosis de la distribución de retornos.

```python
def daily_cvar_recalibration(
    self,
    returns: pd.Series,
    last_calibration: pd.Timestamp,
    current_time: pd.Timestamp,
    max_hours: int = 24
) -> dict:
    """
    Verificar si se necesita recalibración diaria.

    Artzner et al: ES debe recalcularse diariamente.
    """
    hours_since_calibration = (current_time - last_calibration).total_seconds() / 3600

    if hours_since_calibration > max_hours:
        logger.info("Triggering daily CVaR recalibration")

        # Calcular nuevo CVaR
        cvar_result = self.calculate_expected_shortfall(returns.iloc[-252:])

        return {
            'recalibrate': True,
            'new_cvar': cvar_result['expected_shortfall'],
            'hours_since': hours_since_calibration
        }

    return {
        'recalibrate': False,
        'hours_since': hours_since_calibration
    }
```

### Regla 9 — Alpha Decay vs ES

Si el Alpha esperado del trade es menor que el `ES_99` dividido por 10, descartar el trade (ratio Riesgo/Recompensa de cola pobre).

```python
def validate_tail_risk_reward(
    self,
    expected_alpha: float,
    returns: pd.Series,
    min_ratio: float = 10.0
) -> dict:
    """
    Validar ratio reward/tail risk.

    Artzner et al: Alpha >> ES_99/10 para ser viable.
    """
    # ES_99 (cola pesada)
    cvar_99 = self.calculate_expected_shortfall(returns, confidence_level=0.99)
    es_99 = abs(cvar_99['expected_shortfall'])

    # Ratio
    tail_risk_reward_ratio = expected_alpha / es_99 if es_99 != 0 else 0

    if tail_risk_reward_ratio < (1 / min_ratio):
        logger.error(
            f"❌ POOR TAIL RISK/REWARD: Alpha={expected_alpha:.2%}, "
            f"ES_99={es_99:.2%}, Ratio={tail_risk_reward_ratio:.2f} < {1/min_ratio:.3f}"
        )

        return {
            'passes': False,
            'expected_alpha': expected_alpha,
            'es_99': es_99,
            'ratio': tail_risk_reward_ratio,
            'action': 'Reject trade'
        }

    logger.info(
        f"✅ Acceptable tail risk/reward: Ratio={tail_risk_reward_ratio:.2f}"
    )

    return {
        'passes': True,
        'expected_alpha': expected_alpha,
        'es_99': es_99,
        'ratio': tail_risk_reward_ratio
    }
```

### Regla 10 — Tail Correlation

NO usar correlaciones de Pearson normales. Usar Correlación de Cola (probabilidad de que A caiga si B ya ha caído).

```python
def calculate_tail_correlation(
    self,
    returns_a: pd.Series,
    returns_b: pd.Series,
    tail_quantile: float = 0.05
) -> dict:
    """
    Calcular correlación de cola.

    Artzner et al: Correlación en cola > correlación normal.
    """
    # Combinar retornos
    combined = pd.DataFrame({'A': returns_a, 'B': returns_b}).dropna()

    # Threshold para cola (peor 5%)
    threshold_a = combined['A'].quantile(tail_quantile)
    threshold_b = combined['B'].quantile(tail_quantile)

    # Eventos de cola
    tail_events_a = combined['A'] <= threshold_a
    tail_events_b = combined['B'] <= threshold_b

    # Correlación normal
    normal_corr = combined['A'].corr(combined['B'])

    # Correlación de cola (cuando ambos están en cola)
    both_in_tail = tail_events_a & tail_events_b

    if both_in_tail.sum() > 10:  # Mínima muestra
        tail_returns = combined[both_in_tail]
        tail_corr = tail_returns['A'].corr(tail_returns['B'])
    else:
        tail_corr = np.nan

    logger.info(
        f"Correlation: Normal={normal_corr:.2f}, "
        f"Tail={tail_corr:.2f if not np.isnan(tail_corr) else 'N/A'}"
    )

    return {
        'normal_correlation': normal_corr,
        'tail_correlation': tail_corr,
        'correlation_increase': tail_corr - normal_corr if not np.isnan(tail_corr) else 0
    }
```

### Regla 11 — Granularidad de Datos (Intraday)

Para ES, usar datos de 1 minuto o 5 minutos para capturar micro-crashes que los datos diarios ocultan.

```python
def intraday_cvar_calculation(
    self,
    returns_intraday: pd.Series,  # 1-min or 5-min returns
    confidence_level: float = 0.95
) -> dict:
    """
    Calcular CVaR con datos intraday.

    Artzner et al: Datos granulares capturan colas reales.
    """
    # Calcular ES con datos intraday
    var = np.percentile(returns_intraday, (1 - confidence_level) * 100)
    es = returns_intraday[returns_intraday <= var].mean()

    # Comparar con datos diarios
    returns_daily = returns_intraday.resample('D').apply(
        lambda x: (1 + x).prod() - 1
    )

    var_daily = np.percentile(returns_daily.dropna(), (1 - confidence_level) * 100)
    es_daily = returns_daily[returns_daily <= var_daily].mean()

    # Ratio intraday vs daily
    es_ratio = abs(es) / abs(es_daily) if es_daily != 0 else 1.0

    logger.info(
        f"Intraday CVaR: ES={es:.2%} (intraday) vs {es_daily:.2%} (daily), "
        f"Ratio={es_ratio:.2f}x"
    )

    return {
        'intraday_es': es,
        'daily_es': es_daily,
        'granularity_ratio': es_ratio,
        'use_intraday': es_ratio > 1.1
    }
```

### Regla 12 — Non-Normal Assumption

Prohibido usar la distribución Normal para ES. Usar Distribución t de Student o Cornish-Fisher Expansion.

```python
def parametric_cvar_non_normal(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    distribution: str = 't-student'
) -> dict:
    """
    CVaR con distribución no-normal.

    Artzner et al: Normal subestima riesgo de cola.
    """
    from scipy import stats

    if distribution == 't-student':
        # Ajustar t-Student
        params = stats.t.fit(returns)
        df, loc, scale = params

        # VaR con t-Student
        var_t = stats.t.ppf(1 - confidence_level, df, loc, scale)

        # CVaR con t-Student (Expected Shortfall)
        # ES = E[X | X ≤ VaR]
        from scipy.integrate import quad

        def tail_expectation(x):
            return x * stats.t.pdf(x, df, loc, scale)

        integral, _ = quad(
            tail_expectation,
            -np.inf,
            var_t
        )

        cvar_t = integral / (1 - confidence_level)

        logger.info(
            f"t-Student CVaR: df={df:.1f}, VaR={var_t:.2%}, ES={cvar_t:.2%}"
        )

        return {
            'var': var_t,
            'cvar': cvar_t,
            'distribution': 't-student',
            'degrees_of_freedom': df
        }

    elif distribution == 'cornish-fisher':
        # Cornish-Fisher expansion (no implementado aquí)
        raise NotImplementedError("Cornish-Fisher not implemented")

    else:
        raise ValueError(f"Unknown distribution: {distribution}")
```

### Regla 13 — Breach Protocol (Pánico Controlado)

Si el drawdown actual de la cuenta > `ES_95` calculado ayer, cerrar el 50% de las posiciones.

```python
def cvar_breach_protocol(
    self,
    current_drawdown: float,
    es_95_yesterday: float,
    positions: dict
) -> dict:
    """
    Protocolo de breach de CVaR.

    Artzner et al: Si DD > ES_95 → cerrar 50% posiciones.
    """
    if current_drawdown < es_95_yesterday:
        return {'action': 'NONE', 'reason': 'No breach'}

    logger.critical(
        f"🚨 CVAR BREACH: Current DD={current_drawdown:.2%} > ES_95={es_95_yesterday:.2%}. "
        f"CLOSING 50% of positions."
    )

    # Cerrar 50% de cada posición
    liquidation_plan = {}

    for symbol, current_size in positions.items():
        liquidation_size = current_size * 0.5

        liquidation_plan[symbol] = {
            'current_size': current_size,
            'liquidate_size': liquidation_size,
            'action': 'CLOSE'
        }

    return {
        'action': 'EMERGENCY_CLOSING',
        'close_percentage': 0.5,
        'liquidation_plan': liquidation_plan
    }
```

### Regla 14 — Diversificación ES

Validar que los activos del portafolio no tengan sus "peores días" en las mismas fechas históricas.

```python
def validate_tail_diversification(
    self,
    returns: pd.DataFrame,
    worst_n_days: int = 10
) -> dict:
    """
    Validar diversificación en cola.

    Artzner et al: Peores días no deben coincidir.
    """
    # Identificar peores días (menores retornos del portfolio)
    portfolio_returns = returns.mean(axis=1)

    worst_days = portfolio_returns.nsmallest(worst_n_days)

    # Retornos de activos individuales en esos días
    worst_days_returns = returns.loc[worst_days.index]

    # ¿Todos los activos caen en los peores días?
    all_down_in_worst = (worst_days_returns < 0).all(axis=1)

    # Días donde todos cayeron
    n_simultaneous_crashes = all_down_in_worst.sum()

    if n_simultaneous_crashes > worst_n_days * 0.8:  # > 80%
        logger.critical(
            f"🚨 POOR TAIL DIVERSIFICATION: {n_simultaneous_crashes}/{worst_n_days} "
            f"worst days had all assets down"
        )

        return {
            'diversified': False,
            'simultaneous_crashes': n_simultaneous_crashes,
            'action': 'Add uncorrelated assets or reduce concentration'
        }

    logger.info(
        f"✅ Tail diversification OK: {n_simultaneous_crashes}/{worst_n_days} "
        f"simultaneous crashes"
    )

    return {
        'diversified': True,
        'simultaneous_crashes': n_simultaneous_crashes
    }
```

### Regla 15 — Reporting Visual

Generar un gráfico de la "Distribución de Pérdidas" resaltando el área del ES para visualización del riesgo.

```python
def plot_cvar_distribution(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    save_path: str = None
) -> str:
    """
    Generar visualización de distribución con CVaR.

    Artzner et al: Visualizar riesgo de cola.
    """
    import matplotlib.pyplot as plt

    # Histograma de pérdidas
    losses = returns[returns < 0]

    plt.figure(figsize=(12, 6))

    # Histograma
    plt.hist(losses, bins=100, alpha=0.7, color='red', density=True)

    # VaR line
    var = np.percentile(returns, (1 - confidence_level) * 100)
    plt.axvline(var, color='orange', linestyle='--', linewidth=2, label=f'VaR({confidence_level:.0%}) = {var:.2%}')

    # ES area
    es_losses = losses[losses <= var]
    if len(es_losses) > 0:
        plt.axvspan(es_losses.min(), var, alpha=0.3, color='red', label=f'ES({confidence_level:.0%}) Area')

    # Mean ES
    es = es_losses.mean()
    plt.axvline(es, color='darkred', linestyle='-', linewidth=2, label=f'ES = {es:.2%}')

    plt.xlabel('Losses')
    plt.ylabel('Density')
    plt.title('Loss Distribution with CVaR')
    plt.legend()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"CVaR plot saved to {save_path}")

    plt.close()

    return save_path
```

---

## Aplicación Práctica

### Pipeline Completo de Riesgo de Cola

```python
def cvar_risk_management_pipeline(
    self,
    portfolio_returns: pd.Series,
    positions: dict,
    account_value: float,
    current_drawdown: float
) -> dict:
    """
    Pipeline completo de gestión de riesgo con CVaR.
    """
    # 1. Verificar coherencia
    coherence_check = self.verify_coherence(
        portfolio_returns,
        portfolio_returns,  # Simplificado
        confidence_level=0.95
    )

    # 2. Clasificar fat tails
    tail_classification = self.classify_fat_tails(portfolio_returns)

    # 3. Calcular CVaR actual
    cvar_result = self.calculate_expected_shortfall(portfolio_returns, confidence_level=0.95)

    # 4. Verificar breach protocol
    breach_result = self.cvar_breach_protocol(
        current_drawdown,
        abs(cvar_result['expected_shortfall']),
        positions
    )

    # 5. Validar diversificación de cola
    div_result = self.validate_tail_diversification(
        pd.DataFrame(positions),
        worst_n_days=10
    )

    # 6. Generar reporte visual
    plot_path = self.plot_cvar_distribution(
        portfolio_returns,
        confidence_level=0.95,
        save_path='./reports/cvar_distribution.png'
    )

    return {
        'cvar_95': cvar_result['expected_shortfall'],
        'var_95': cvar_result['var'],
        'fat_tailed': tail_classification['fat_tailed'],
        'breach_action': breach_result['action'],
        'tail_diversified': div_result['diversified'],
        'coherent': coherence_check['es_is_coherent'],
        'plot_path': plot_path
    }
```
