# 🟠 30. "Factor-Based Investing" - Berkin & Swedroe

## REGLAS DE INVERSIÓN BASADA EN FACTORES

**Regla 30.1 — Filtro de Calidad (Quality Screen)**

Claude DEBE filtrar empresas de baja calidad ANTES de seleccionar por dividendos.

**Dividendos altos + ROE decreciente → rechazar.**

```python
def quality_screen(
    self,
    dividend_yield: float,
    roe_history: pd.Series,  # últimos 8 trimestres
    min_roe: float = 0.10  # 10% ROE mínimo
) -> bool:
    """
    Filtro de calidad: ROE debe ser estable o creciente.

    Berkin & Swedroe: No compres dividendos si ROE cae.
    """
    # ROE promedio
    avg_roe = roe_history.mean()

    # Tendencia de ROE (regresión lineal)
    x = np.arange(len(roe_history))
    slope, _ = np.polyfit(x, roe_history, 1)

    # Dividend yield alto
    high_dividend = dividend_yield > 0.04  # > 4%

    # Validar
    if high_dividend:
        if avg_roe < min_roe:
            logger.warning(
                f"❌ REJECT: High dividend ({dividend_yield:.1%}) "
                f"but low ROE ({avg_roe:.1%})"
            )
            return False

        if slope < 0:
            logger.warning(
                f"❌ REJECT: High dividend ({dividend_yield:.1%}) "
                f"but declining ROE (slope={slope:.3f})"
            )
            return False

    logger.info(
        f"✅ PASS: Dividend={dividend_yield:.1%}, "
        f"ROE={avg_roe:.1%}, Trend={'↑' if slope > 0 else '↓'}"
    )

    return True
```

**Regla 30.2 — Profitability Factor**

```python
def profitability_filter(
    self,
    operating_cash_flows: pd.Series,  # últimos 8 trimestres
    dividend_yield: float
) -> bool:
    """
    Excluir empresas con flujos de caja operativos negativos.

    Berkin & Swedroe: Cash flow negativo = dividendos insostenibles.
    """
    # Últimos 4 trimestres
    recent_cfs = operating_cash_flows.iloc[-4:]

    # Todos positivos?
    all_positive = (recent_cfs > 0).all()

    # Tendencia
    x = np.arange(len(recent_cfs))
    slope, _ = np.polyfit(x, recent_cfs, 1)

    if not all_positive:
        logger.error(
            f"❌ REJECT: Negative operating cash flow. "
            f"Dividend not sustainable."
        )
        return False

    if slope < 0:
        logger.warning(
            f"⚠️ WARNING: Declining cash flow. "
            f"Dividend at risk."
        )

    return True
```

**Regla 30.3 — Low Volatility Anomaly**

```python
def low_volatility_screening(
    self,
    universe: pd.DataFrame,  # columns: symbol, beta, sector, dividend_yield
    risk_profile: str,  # 'LOW', 'MEDIUM', 'HIGH'
    max_beta: float = 0.8
) -> pd.DataFrame:
    """
    En perfiles BAJO riesgo, priorizar baja Beta.

    Berkin & Swedroe: Low volatility anomaly.
    """
    if risk_profile != 'LOW':
        # Para perfiles de alto riesgo, no filtrar por volatilidad
        return universe

    # Filtrar por Beta sectorial
    screened = []

    for sector in universe['sector'].unique():
        sector_stocks = universe[universe['sector'] == sector]

        # Beta más bajo del sector
        min_beta = sector_stocks['beta'].min()

        # Solo mantener acciones con Beta cercano al mínimo
        low_beta_stocks = sector_stocks[
            sector_stocks['beta'] <= min_beta + 0.1
        ]

        screened.append(low_beta_stocks)

    result = pd.concat(screened)

    logger.info(
        f"Low volatility screen: {len(result)}/{len(universe)} "
        f"stocks passed (max beta={max_beta:.1f})"
    )

    return result
```

**Regla 30.4 — Dividend Payout Cap**

```python
def dividend_payout_validation(
    self,
    dividend_per_share: float,
    earnings_per_share: float,
    max_payout_ratio: float = 0.70
) -> bool:
    """
    Limitar ratio de payout a 70%.

    Berkin & Swedroe: Payout > 70% = riesgo de recorte.
    """
    if earnings_per_share <= 0:
        logger.error("❌ REJECT: Negative EPS")
        return False

    payout_ratio = dividend_per_share / earnings_per_share

    if payout_ratio > max_payout_ratio:
        logger.warning(
            f"⚠️ WARNING: Payout ratio {payout_ratio:.1%} "
            f"> {max_payout_ratio:.0%}. Dividend cut risk."
        )
        return False

    logger.info(
        f"✅ Payout ratio: {payout_ratio:.1%} (sustainable)"
    )

    return True
```

**Regla 30.5 — Size Factor Adjustment**

```python
def size_factor_filter(
    self,
    market_cap: float,
    risk_profile_size: str,  # 'MICRO', 'SMALL', 'LARGE'
    min_large_cap: float = 2e9  # 2B€
) -> bool:
    """
    Perfiles MICRO pueden operar Small Caps.
    Perfiles LARGE prohibidos < 2B€.

    Berkin & Swedroe: Size factor según perfil.
    """
    if risk_profile_size == 'LARGE':
        # Perfiles grandes: solo large caps
        if market_cap < min_large_cap:
            logger.warning(
                f"❌ REJECT: Market cap ${market_cap/1e9:.1f}B "
                f"< ${min_large_cap/1e9:.0f}B minimum for LARGE profile"
            )
            return False

    elif risk_profile_size == 'MICRO':
        # Perfiles pequeños: pueden operar small caps
        min_micro_cap = 200e6  # 200M€
        if market_cap < min_micro_cap:
            logger.warning(
                f"⚠️ WARNING: Market cap ${market_cap/1e6:.0f}M "
                f"too small even for MICRO"
            )
            return False

    return True
```

**Regla 30.6 — Value Momentum Combined**

```python
def value_momentum_combined(
    self,
    pe_ratio: float,
    pb_ratio: float,
    momentum_6m: float  # retorno últimos 6 meses
) -> bool:
    """
    Solo entrar en Value si momentum ya no es negativo.

    Berkin & Swedroe: Value + Momentum combinados.
    """
    # Value signal
    # PE y PB bajos = value
    pe_percentile = self.get_pe_percentile(pe_ratio)
    pb_percentile = self.get_pb_percentile(pb_ratio)

    value_score = (1 - pe_percentile) * 0.6 + (1 - pb_percentile) * 0.4

    # Si es Value
    if value_score > 0.7:  # Top 30% value
        # Chequear momentum
        if momentum_6m < 0:
            logger.warning(
                f"⚠️ Value stock but negative momentum "
                f"({momentum_6m:.1%}). Wait."
            )
            return False

        logger.info(
            f"✅ Value + Positive momentum: "
            f"Value={value_score:.2f}, Mom={momentum_6m:.1%}"
        )
        return True

    return False
```

**Regla 30.7 — Investment Factor**

```python
def investment_factor_filter(
    self,
    total_debt: float,
    shareholders_equity: float,
    dividend_yield: float
) -> bool:
    """
    Evitar empresas emitiendo deuda masiva para pagar dividendos.

    Berkin & Swedroe: Debt/Equity > 2.0 = peligro.
    """
    if shareholders_equity <= 0:
        logger.error("❌ REJECT: Negative equity")
        return False

    debt_to_equity = total_debt / shareholders_equity

    if debt_to_equity > 2.0:
        if dividend_yield > 0.03:  # 3%+
            logger.warning(
                f"❌ REJECT: High dividend ({dividend_yield:.1%}) "
                f"funded by debt (D/E={debt_to_equity:.1f})"
            )
            return False

    logger.info(
        f"Debt/Equity: {debt_to_equity:.1f} "
        f"({('OK' if debt_to_equity < 1.0 else 'HIGH')})"
    )

    return True
```

**Regla 30.8 — Earnings Stability**

```python
def earnings_stability_filter(
    self,
    quarterly_earnings: pd.Series,
    max_volatility: float = 0.20,  # 20%
    strategy: str = 'INCOME'
) -> bool:
    """
    Volatilidad de ganancias anuales < 20% para INCOME.

    Berkin & Swedroe: Estabilidad de earnings es crítica.
    """
    if strategy != 'INCOME':
        return True

    # Volatilidad de earnings
    earnings_std = quarterly_earnings.std()
    earnings_mean = quarterly_earnings.mean()

    earnings_volatility = earnings_std / earnings_mean if earnings_mean > 0 else float('inf')

    if earnings_volatility > max_volatility:
        logger.warning(
            f"❌ REJECT: Earnings volatility {earnings_volatility:.1%} "
            f"> {max_volatility:.0%} for INCOME strategy"
        )
        return False

    logger.info(
        f"✅ Earnings stability: {earnings_volatility:.1%} "
        f"volatility"
    )

    return True
```

**Regla 30.9 — Multifactor Scoring**

```python
def multifactor_score(
    self,
    symbol: str,
    factors: dict
) -> dict:
    """
    Cada activo recibe score (Value + Quality + Momentum).
    Solo top 10% entra en universo.

    Berkin & Swedroe: Multifactor scoring.
    """
    # Normalizar cada factor (percentil 0-1)
    value_score = self.get_factor_percentile('value', factors['value'])
    quality_score = self.get_factor_percentile('quality', factors['quality'])
    momentum_score = self.get_factor_percentile('momentum', factors['momentum'])

    # Pesos (ajustables)
    weights = {
        'value': 0.4,
        'quality': 0.3,
        'momentum': 0.3
    }

    # Score combinado
    combined_score = (
        value_score * weights['value'] +
        quality_score * weights['quality'] +
        momentum_score * weights['momentum']
    )

    # Top 10% threshold
    top_10_threshold = 0.90

    passed = combined_score >= top_10_threshold

    if passed:
        logger.info(
            f"✅ {symbol}: Score={combined_score:.2f} "
            f"(V={value_score:.2f}, Q={quality_score:.2f}, M={momentum_score:.2f})"
        )

    return {
        'symbol': symbol,
        'combined_score': combined_score,
        'value_score': value_score,
        'quality_score': quality_score,
        'momentum_score': momentum_score,
        'passed': passed
    }
```

**Regla 30.10 — Rebalanceo por Desviación**

```python
def deviation_based_rebalance(
    self,
    current_weights: pd.Series,  # symbol -> weight
    target_weights: pd.Series,
    deviation_threshold: float = 0.05  # 5%
) -> dict:
    """
    Rebalancear solo si desviación > 5% del objetivo.

    Berkin & Swedroe: NO rebalancear por fecha.
    """
    rebalance_trades = {}

    for symbol in target_weights.index:
        current_weight = current_weights.get(symbol, 0)
        target_weight = target_weights[symbol]

        deviation = abs(current_weight - target_weight)

        if deviation > deviation_threshold:
            # Calcular trade
            trade_size = target_weight - current_weight

            rebalance_trades[symbol] = {
                'current': current_weight,
                'target': target_weight,
                'deviation': deviation,
                'trade': trade_size
            }

            logger.info(
                f"Rebalance {symbol}: {current_weight:.1%} → {target_weight:.1%} "
                f"(dev={deviation:.1%})"
            )

    if not rebalance_trades:
        logger.info("No rebalancing needed (all within threshold)")

    return rebalance_trades
```

**Regla 30.11 — Tax Awareness (España)**

```python
def tax_aware_dividend_selection(
    self,
    symbol: str,
    dividend_yield: float,
    withholding_tax: float,
    country: str
) -> float:
    """
    Priorizar activos con retenciones favorables (UE vs USA).

    Berkin & Swedroe: Tax awareness es Alpha.
    """
    # Residentes españoles
    # UE: 0-15% withholding (con convenio)
    # USA: 30% withholding (sin convenio directo)

    # Dividend yield neto de impuestos
    net_yield = dividend_yield * (1 - withholding_tax)

    if country == 'USA':
        logger.info(
            f"USA stock: {dividend_yield:.1%} gross → "
            f"{net_yield:.1%} net (30% withholding)"
        )

    elif country in ['ES', 'DE', 'FR', 'IT', 'NL']:
        # UE con convenio
        logger.info(
            f"EU stock: {dividend_yield:.1%} gross → "
            f"{net_yield:.1%} net ({withholding_tax:.0%} withholding)"
        )

    # Penalty por alta retención
    if withholding_tax > 0.20:
        tax_penalty = (withholding_tax - 0.15) * 0.5
        adjusted_yield = net_yield * (1 - tax_penalty)
    else:
        adjusted_yield = net_yield

    return adjusted_yield
```

**Regla 30.12 — Sector Cap**

```python
def sector_concentration_limit(
    self,
    holdings: pd.DataFrame,  # columns: symbol, sector, weight
    max_sector_exposure: float = 0.25  # 25%
) -> dict:
    """
    Ningún sector > 25% de la exposición a factores.

    Berkin & Swedroe: Diversificación sectorial obligatoria.
    """
    # Exposición por sector
    sector_exposure = holdings.groupby('sector')['weight'].sum()

    violations = []

    for sector, exposure in sector_exposure.items():
        if exposure > max_sector_exposure:
            violations.append({
                'sector': sector,
                'exposure': exposure,
                'excess': exposure - max_sector_exposure
            })

            logger.warning(
                f"⚠️ Sector concentration: {sector} = {exposure:.1%} "
                f"> {max_sector_exposure:.0%}"
            )

    if violations:
        # Reducir exposición
        for v in violations:
            # Encontrar holdings en sector y reducir
            sector_holdings = holdings[holdings['sector'] == v['sector']]

            for _, holding in sector_holdings.iterrows():
                reduction_factor = (max_sector_exposure / v['exposure'])

                logger.info(
                    f"Reduce {holding['symbol']}: "
                    f"{holding['weight']:.1%} → "
                    f"{holding['weight'] * reduction_factor:.1%}"
                )

    return {
        'sector_exposure': sector_exposure.to_dict(),
        'violations': violations,
        'max_exceeded': len(violations) > 0
    }
```

**Regla 30.13 — Liquidity Screen**

```python
def liquidity_screen(
    self,
    symbol: str,
    avg_daily_volume: float,
    position_value: float,
    exit_days: int = 1
) -> bool:
    """
    Si no se puede salir en 1 día, descartar.

    Berkin & Swedroe: Liquidez es crítica.
    """
    # Volumen que necesitamos salir (1% del ADV)
    max_position_value = avg_daily_volume * 0.01 * exit_days

    if position_value > max_position_value:
        logger.warning(
            f"❌ REJECT {symbol}: Position ${position_value:,.0f} "
            f"> ${max_position_value:,.0f} (1% ADV)"
        )
        return False

    logger.info(
        f"✅ {symbol}: Position ${position_value:,.0f} "
        f"within 1% ADV (${max_position_value:,.0f})"
    )

    return True
```

**Regla 30.14 — Factor Crowding**

```python
def factor_crowding_adjustment(
    self,
    factor: str,  # 'value', 'momentum', 'quality'
    current_valuation: float,
    historical_percentiles: pd.Series
) -> float:
    """
    Si factor en máximos históricos, reducir exposición 20%.

    Berkin & Swedroe: Regla de prudencia.
    """
    # Percentil actual
    current_percentile = (
        historical_percentiles.rank(pct=True).iloc[-1]
    )

    # Si en top 10% histórico
    if current_percentile > 0.90:
        logger.warning(
            f"⚠️ Factor crowding: {factor} at "
            f"{current_percentile:.1%} percentile. "
            f"Reducing exposure 20%."
        )
        reduction = 0.20

    elif current_percentile > 0.75:
        logger.info(
            f"Factor {factor} elevated ({current_percentile:.1%} pct). "
            f"Reducing exposure 10%."
        )
        reduction = 0.10

    else:
        reduction = 0.0

    return 1.0 - reduction
```

**Regla 30.15 — Survivorship Bias Check**

```python
def survivorship_bias_adjusted_returns(
    self,
    backtest_returns: pd.Series,
    delisted_returns: pd.Series,
    dividend_universe: List[str]
) -> dict:
    """
    Incluir empresas que quebraron o dejaron de pagar.

    Berkin & Swedroe: Survivorship bias infla Sharpe.
    """
    # Original backtest (con survivorship bias)
    original_sharpe = self.calculate_sharpe(backtest_returns)

    # Añadir returns de empresas quebradas/de-listed
    all_returns = pd.concat([backtest_returns, delisted_returns])

    # Recalcular métricas
    adjusted_sharpe = self.calculate_sharpe(all_returns)
    adjusted_cagr = self.calculate_cagr(all_returns)

    # Diferencia
    sharpe_inflation = original_sharpe - adjusted_sharpe
    inflation_pct = sharpe_inflation / adjusted_sharpe

    if inflation_pct > 0.10:
        logger.warning(
            f"⚠️ Survivorship bias: Sharpe inflated by "
            f"{inflation_pct:.1%} "
            f"({original_sharpe:.2f} → {adjusted_sharpe:.2f})"
        )

    return {
        'original_sharpe': original_sharpe,
        'adjusted_sharpe': adjusted_sharpe,
        'sharpe_inflation': sharpe_inflation,
        'inflation_pct': inflation_pct
    }
```
