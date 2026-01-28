# 📗 13. "Risk Management and Financial Institutions" - John Hull

## REGLAS DE GESTIÓN DE RIESGO INSTITUCIONAL

**Regla 13.1 — Kill switch**

Claude DEBE implementar:
- max drawdown hard stop
- pérdida diaria máxima

**Sin kill switch → NO PRODUCCIÓN.**

```python
def kill_switch(
    self,
    current_equity: float,
    peak_equity: float,
    max_drawdown_pct: float = 0.20,
    daily_loss_limit_pct: float = 0.05,
    starting_equity: float = None
) -> dict:
    """
    Kill switch: Detener trading si se exceden límites de riesgo.

    Hull: Kill switch es obligatorio para trading institucional.
    """
    alerts = []
    trading_halted = False

    # 1. Maximum Drawdown Check
    if peak_equity > 0:
        current_drawdown = (peak_equity - current_equity) / peak_equity

        if current_drawdown > max_drawdown_pct:
            critical_msg = (
                f"🚨 CRITICAL: Max drawdown exceeded! "
                f"Current: {current_drawdown:.1%} > Limit: {max_drawdown_pct:.0%}"
            )
            logger.critical(critical_msg)
            alerts.append(critical_msg)
            trading_halted = True

    # 2. Daily Loss Limit Check
    if starting_equity:
        daily_pnl = current_equity - starting_equity
        daily_loss_pct = daily_pnl / starting_equity

        if daily_loss_pct < -daily_loss_limit_pct:
            critical_msg = (
                f"🚨 CRITICAL: Daily loss limit exceeded! "
                f"Loss: {daily_loss_pct:.1%} < Limit: -{daily_loss_limit_pct:.0%}"
            )
            logger.critical(critical_msg)
            alerts.append(critical_msg)
            trading_halted = True

    if trading_halted:
        self.emergency_halt("Risk limit exceeded")

    return {
        'trading_halted': trading_halted,
        'alerts': alerts
    }
```

**Regla 13.2 — Risk overrides alpha**

```python
def risk_overrides_alpha(
    self,
    signals: pd.Series,
    risk_limits: dict
) -> pd.Series:
    """
    Risk model domina alpha model.

    Hull: Cuando risk constraints violadas → signal = 0.
    """
    adjusted_signals = signals.copy()

    # Check cada constraint
    for constraint_name, limit in risk_limits.items():
        current_exposure = self.get_current_exposure(constraint_name)

        if abs(current_exposure) > abs(limit):
            # Violación de risk limit → liquidar signals
            logger.warning(
                f"⚠️ Risk limit exceeded: {constraint_name} = "
                f"{current_exposure:.2%} > {limit:.2%}"
            )

            # Zero out affected signals
            adjusted_signals = adjusted_signals * 0.0

            return adjusted_signals

    return adjusted_signals
```

**Regla 13.3 — Value at Risk (VaR) calculation**

```python
def calculate_var(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    holding_period_days: int = 1
) -> float:
    """
    Value at Risk: Pérdida máxima esperada con X% confianza.

    Hull: VaR es estándar para medir risk de mercado.
    """
    # Historical VaR
    var_pct = np.percentile(returns, (1 - confidence_level) * 100)

    # Scale para holding period (square-root rule)
    var_scaled = var_pct * np.sqrt(holding_period_days)

    logger.info(
        f"VaR ({confidence_level:.0%}, {holding_period_days}d): {var_scaled:.2%}"
    )

    return var_scaled
```

**Regla 13.4 — Expected Shortfall (ES/CVaR)**

```python
def calculate_expected_shortfall(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95
) -> float:
    """
    Expected Shortfall: Promedio de pérdidas más allá de VaR.

    Hull: ES es coherent risk measure, VaR no lo es.
    """
    var = np.percentile(returns, (1 - confidence_level) * 100)

    # Promedio de returns peor que VaR
    tail_losses = returns[returns <= var]
    expected_shortfall = tail_losses.mean()

    logger.info(
        f"Expected Shortfall ({confidence_level:.0%}): {expected_shortfall:.2%}"
    )

    return expected_shortfall
```

**Regla 13.5 — Position limits por instrumento**

```python
def validate_position_limits(
    self,
    positions: Dict[str, float],
    portfolio_value: float,
    max_position_pct: float = 0.20,
    max_concentration_pct: float = 0.30
) -> bool:
    """
    Limitar exposición por instrumento.

    Hull: No sobre-concentrarse en ningún position.
    """
    for symbol, position_value in positions.items():
        position_pct = position_value / portfolio_value

        if position_pct > max_position_pct:
            logger.error(
                f"❌ Position limit exceeded: {symbol} = {position_pct:.1%} "
                f"> {max_position_pct:.0%}"
            )
            return False

    # Check concentración total en top 3
    sorted_positions = sorted(positions.values(), reverse=True)
    top3_concentration = sum(sorted_positions[:3]) / portfolio_value

    if top3_concentration > max_concentration_pct:
        logger.warning(
            f"⚠️ High concentration: Top 3 = {top3_concentration:.1%}"
        )

    return True
```

**Regla 13.6 — Greeks monitoring (options)**

```python
def validate_option_greeks(
    self,
    portfolio_greeks: dict,
    portfolio_value: float
) -> dict:
    """
    Monitorear Greeks de portfolio de opciones.

    Hull: Delta, Gamma, Vega, Theta deben monitorearse.
    """
    limits = {
        'delta': 0.50,      # Max 50% del portfolio en delta
        'gamma': 0.10,      # Max 10% gamma exposure
        'vega_pct': 0.05,   # Max 5% vega exposure
        'theta_daily': 0.01 # Max 1% pérdida diaria por theta
    }

    violations = []

    # Delta limit
    delta_value = portfolio_greeks.get('delta', 0) * portfolio_value
    delta_pct = delta_value / portfolio_value

    if abs(delta_pct) > limits['delta']:
        violations.append(f"Delta: {delta_pct:.1%} > {limits['delta']:.0%}")

    # Vega limit
    vega_value = portfolio_greeks.get('vega', 0)
    vega_pct = vega_value / portfolio_value

    if abs(vega_pct) > limits['vega_pct']:
        violations.append(f"Vega: {vega_pct:.1%} > {limits['vega_pct']:.0%}")

    # Theta limit
    theta_daily = portfolio_greeks.get('theta', 0) / 365  # Daily theta
    theta_pct = theta_daily / portfolio_value

    if theta_pct < -limits['theta_daily']:
        violations.append(f"Theta: {theta_pct:.2%} < -{limits['theta_daily']:.0%}")

    if violations:
        logger.error(f"❌ Greeks violations: {', '.join(violations)}")
        return {'valid': False, 'violations': violations}

    return {'valid': True, 'violations': []}
```

**Regla 13.7 — Stress testing**

```python
def stress_test_portfolio(
    self,
    positions: Dict[str, float],
    scenarios: List[dict]
) -> dict:
    """
    Stress testing: Simular escenarios adversos.

    Hull: Stress tests son obligatorios para risk management.
    """
    results = {}

    for scenario in scenarios:
        scenario_name = scenario['name']
        shocks = scenario['shocks']  # {"SPY": -0.20, "TLT": 0.05}

        # Calcular P&L bajo escenario
        scenario_pnl = 0.0

        for symbol, position_value in positions.items():
            if symbol in shocks:
                shock = shocks[symbol]
                pnl = position_value * shock
                scenario_pnl += pnl

        results[scenario_name] = {
            'pnl': scenario_pnl,
            'pnl_pct': scenario_pnl / sum(positions.values())
        }

        logger.info(
            f"Stress test '{scenario_name}': PnL = {scenario_pnl:,.0f} "
            f"({results[scenario_name]['pnl_pct']:.1%})"
        )

    return results
```

**Regla 13.8 — Volatility targeting**

```python
def volatility_targeting(
    self,
    signal: float,
    current_volatility: float,
    target_volatility: float = 0.15,
    max_leverage: float = 2.0
) -> float:
    """
    Ajustar posición para target de volatilidad.

    Hull: Volatility targeting es más robusto que position sizing fijo.
    """
    if current_volatility < 0.01:
        current_volatility = 0.01  # Minimum vol

    # Vol scalar
    vol_scalar = target_volatility / current_volatility

    # Limitar leverage
    vol_scalar = min(vol_scalar, max_leverage)

    # Ajustar signal
    sized_signal = signal * vol_scalar

    return sized_signal
```

**Regla 13.9 — Correlation stress test**

```python
def correlation_stress_test(
    self,
    positions: Dict[str, float],
    normal_correlation: pd.DataFrame,
    stressed_correlation: pd.DataFrame
) -> dict:
    """
    Stress test con correlaciones extremas.

    Hull: Correlations pueden aumentar durante crisis.
    """
    # Portfolio variance bajo correlación normal
    weights = pd.Series(positions) / sum(positions.values())
    var_normal = weights.T @ normal_correlation @ weights

    # Portfolio variance bajo correlación estresada
    var_stressed = weights.T @ stressed_correlation @ weights

    # Aumento de risk
    risk_increase = (var_stressed - var_normal) / var_normal

    logger.warning(
        f"Correlation stress: Risk increases by {risk_increase:.0%} "
        f"under stress scenario"
    )

    return {
        'var_normal': var_normal,
        'var_stressed': var_stressed,
        'risk_increase_pct': risk_increase
    }
```

**Regla 13.10 — Circuit breaker**

```python
def circuit_breaker(
    self,
    intraday_pnl: float,
    starting_equity: float,
    circuit_breaker_pct: float = -0.03
) -> bool:
    """
    Circuit breaker: Detener si pérdida intradía excede límite.

    Hull: Circuit breaker protege contra pérdidas catastróficas.
    """
    loss_pct = intraday_pnl / starting_equity

    if loss_pct <= circuit_breaker_pct:
        logger.critical(
            f"🚨 CIRCUIT BREAKER TRIGGERED: Loss {loss_pct:.1%} "
            f"< {circuit_breaker_pct:.0%}"
        )
        self.emergency_halt("Circuit breaker triggered")
        return True

    return False
```
