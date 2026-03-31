# 📄 Papers Fundamentales - Gatev, Goetzmann & Rouwenhorst: Pairs Trading (2006)

## Pairs Trading: Arbitraje Estadístico y Mean Reversion

**Contexto:** Estrategias de Arbitraje Estadístico (Strategies/StatArb).

Gatev et al. demostraron que los pares de acciones cointegradas generan retornos anormales consistentes, proporcionando un framework sistemático para el pairs trading.

---

### Regla 1 — Formation Period

Usar 12 meses de datos diarios para identificar pares candidatos.

```python
def formation_period_selection(
    self,
    prices: pd.DataFrame,
    formation_days: int = 252
) -> dict:
    """
    Periodo de formación: 12 meses de datos históricos.

    Gatev et al: Usar 12 meses para identificar cointegración.
    """
    if len(prices) < formation_days:
        raise ValueError(
            f"Insufficient data for formation: {len(prices)} < {formation_days}"
        )

    formation_prices = prices.iloc[-formation_days:]

    logger.info(
        f"Formation period: {formation_days} days "
        f"({len(prices.columns)} potential pairs)"
    )

    return {
        'formation_prices': formation_prices,
        'formation_start': formation_prices.index[0],
        'formation_end': formation_prices.index[-1]
    }
```

### Regla 2 — Trading Period (Walk-Forward)

Usar los 6 meses siguientes para operar el par (Walk-Forward validation).

```python
def walk_forward_pairs(
    self,
    prices: pd.DataFrame,
    formation_months: int = 12,
    trading_months: int = 6
) -> list:
    """
    Walk-Forward: Formación 12 meses, Trading 6 meses.

    Gatev et al: Validar fuera de muestra (walk-forward).
    """
    pairs_periods = []

    # Convertir índice a meses
    monthly_dates = prices.resample('M').last().index

    for i in range(0, len(monthly_dates) - formation_months - trading_months, trading_months):
        formation_end = monthly_dates[i + formation_months]
        trading_end = monthly_dates[i + formation_months + trading_months]

        formation_data = prices[:formation_end]
        trading_data = prices[formation_end:trading_end]

        pairs_periods.append({
            'formation': formation_data,
            'trading': trading_data,
            'formation_end': formation_end,
            'trading_end': trading_end
        })

    logger.info(
        f"Walk-forward: {len(pairs_periods)} periods "
        f"({formation_months}m formation + {trading_months}m trading)"
    )

    return pairs_periods
```

### Regla 3 — Normalized Price

Trabajar siempre con precios normalizados acumulados (índice base 1.0) para comparar activos de distinto precio nominal.

```python
def normalize_prices(
    self,
    prices: pd.DataFrame
) -> pd.DataFrame:
    """
    Normalizar precios a base 1.0.

    Gatev et al: Comparar activos de distinto precio nominal.
    """
    normalized = prices / prices.iloc[0]

    logger.info(
        f"Normalized prices: Base = 1.0, "
        f"Range = [{normalized.min().min():.2f}, {normalized.max().max():.2f}]"
    )

    return normalized
```

### Regla 4 — SSD Selection (Sum of Squared Differences)

Seleccionar pares minimizando la SSD entre los precios normalizados.

```python
def select_pairs_by_ssd(
    self,
    normalized_prices: pd.DataFrame,
    top_n: int = 20
) -> list:
    """
    Seleccionar pares por SSD (Sum of Squared Differences).

    Gatev et al: SSD = distance metric para elegir pares.
    """
    n_assets = len(normalized_prices.columns)
    pair_scores = []

    for i in range(n_assets):
        for j in range(i + 1, n_assets):
            asset_a = normalized_prices.columns[i]
            asset_b = normalized_prices.columns[j]

            # SSD entre precios normalizados
            price_a = normalized_prices[asset_a].values
            price_b = normalized_prices[asset_b].values

            ssd = np.sum((price_a - price_b) ** 2)

            pair_scores.append({
                'pair': (asset_a, asset_b),
                'ssd': ssd
            })

    # Ordenar por SSD (menor = mejor)
    pair_scores.sort(key=lambda x: x['ssd'])

    # Top N pares
    selected_pairs = pair_scores[:top_n]

    logger.info(
        f"SSD Selection: Top {top_n} pairs from {n_assets} assets"
    )

    return selected_pairs
```

### Regla 5 — Cointegration Test (OBLIGATORIO)

Aplicar el test de Engle-Granger o Johansen. El p-value debe ser < 0.05.

```python
def test_cointegration(
    self,
    prices_a: pd.Series,
    prices_b: pd.Series,
    method: str = 'engle-granger'
) -> dict:
    """
    Test de Cointegración OBLIGATORIO.

    Gatev et al: Solo operar pares cointegrados.
    """
    from statsmodels.tsa.stattools import coint

    if method == 'engle-granger':
        score, pvalue, crit_values = coint(prices_a, prices_b)

        is_cointegrated = pvalue < 0.05

    elif method == 'johansen':
        from statsmodels.tsa.vector_ar.vecm import coint_johansen

        combined = pd.DataFrame({'A': prices_a, 'B': prices_b})

        result = coint_johansen(
            combined.values,
            det_order=0,
            k_ar_diff=1
        )

        # Trace statistic y eigen statistic
        trace_stat = result.lr1
        eigen_stat = result.lr2

        # Para 1 cointegrating vector al 95%
        is_cointegrated = trace_stat[0] > result.cvt[0, 1]  # 95% CV

        pvalue = None  # Johansen no da p-value directo

    if is_cointegrated:
        logger.info(
            f"✅ Cointegrated: {prices_a.name}/{prices_b.name} "
            f"(p={pvalue:.4f if pvalue else 'N/A'})"
        )
    else:
        logger.warning(
            f"❌ NOT cointegrated: {prices_a.name}/{prices_b.name} "
            f"(p={pvalue:.4f if pvalue else 'N/A'})"
        )

    return {
        'cointegrated': is_cointegrated,
        'p_value': pvalue,
        'method': method
    }
```

### Regla 6 — Spread Calculation

Definir el spread como `S_t = P_A - β · P_B` (donde β viene de OLS) o `P_A/P_B` ratio logarítmico.

```python
def calculate_spread(
    self,
    prices_a: pd.Series,
    prices_b: pd.Series,
    method: str = 'ols'
) -> dict:
    """
    Calcular spread del par.

    Gatev et al: Spread = señal de trading.
    """
    import statsmodels.api as sm

    if method == 'ols':
        # Regresión OLS: P_A = α + β·P_B + ε
        X = sm.add_constant(prices_b)
        model = sm.OLS(prices_a, X).fit()

        hedge_ratio = model.params[1]  # β
        intercept = model.params[0]    # α

        # Spread = P_A - β·P_B - α
        spread = prices_a - hedge_ratio * prices_b - intercept

        logger.info(
            f"OLS Spread: α={intercept:.4f}, β={hedge_ratio:.4f}"
        )

    elif method == 'log-ratio':
        # Spread logarítmico: ln(P_A/P_B)
        spread = np.log(prices_a / prices_b)

        hedge_ratio = 1.0  # Para log ratio
        intercept = 0.0

    return {
        'spread': spread,
        'hedge_ratio': hedge_ratio,
        'intercept': intercept
    }
```

### Regla 7 — Z-Score Trigger

Calcular la media y desviación estándar del spread en ventana rodante. Abrir posición cuando `|Z| > 2.0`.

```python
def z_score_signal(
    self,
    spread: pd.Series,
    entry_threshold: float = 2.0,
    lookback: int = 20
) -> dict:
    """
    Señal basada en Z-Score del spread.

    Gatev et al: Entrada cuando |Z| > 2.0.
    """
    # Media y SD móvil del spread
    spread_mean = spread.rolling(lookback).mean()
    spread_std = spread.rolling(lookback).std()

    # Z-Score
    z_score = (spread - spread_mean) / spread_std

    # Señal
    current_z = z_score.iloc[-1]

    if current_z > entry_threshold:
        signal = 'SHORT_SPREAD'  # Spread alto → short A, long B
        action = 'Open Pair Short'

    elif current_z < -entry_threshold:
        signal = 'LONG_SPREAD'   # Spread bajo → long A, short B
        action = 'Open Pair Long'

    else:
        signal = 'NEUTRAL'
        action = 'No action'

    logger.info(
        f"Z-Score: {current_z:.2f} | Signal: {signal}"
    )

    return {
        'z_score': current_z,
        'signal': signal,
        'action': action,
        'spread_mean': spread_mean.iloc[-1],
        'spread_std': spread_std.iloc[-1]
    }
```

### Regla 8 — Exit Rule

Cerrar la posición obligatoriamente cuando el spread cruce su media (`Z = 0.0`).

```python
def exit_signal(
    self,
    z_score: float,
    exit_threshold: float = 0.0
) -> str:
    """
    Regla de salida: Z = 0.

    Gatev et al: Cerrar cuando spread cruza media.
    """
    if abs(z_score) <= exit_threshold:
        logger.info(f"Exit triggered: Z={z_score:.2f} crossed 0")
        return 'CLOSE'

    return 'HOLD'
```

### Regla 9 — Stop-Loss (Divergence)

Si el spread se amplía a `|Z| > 4.0` (o 2x la señal de entrada), cerrar por ruptura de cointegración.

```python
def divergence_stop_loss(
    self,
    z_score: float,
    entry_threshold: float = 2.0,
    stop_multiplier: float = 2.0
) -> dict:
    """
    Stop-loss por divergencia.

    Gatev et al: Si spread se amplía → cointegración rota.
    """
    stop_threshold = entry_threshold * stop_multiplier

    if abs(z_score) > stop_threshold:
        logger.critical(
            f"🚨 DIVERGENCE STOP: Z={z_score:.2f} > {stop_threshold:.2f}. "
            f"Closing position."
        )

        return {
            'stop_triggered': True,
            'reason': 'Divergence',
            'z_score': z_score,
            'action': 'CLOSE_EMERGENCY'
        }

    return {'stop_triggered': False}
```

### Regla 10 — Time Limit

Si la posición no converge en 30 días hábiles, cerrarla forzosamente (costo de oportunidad).

```python
def time_limit_exit(
    self,
    entry_date: pd.Timestamp,
    current_date: pd.Timestamp,
    max_days: int = 30
) -> dict:
    """
    Límite de tiempo: 30 días para converger.

    Gatev et al: Costo de oportunidad.
    """
    days_held = (current_date - entry_date).days

    if days_held > max_days:
        logger.warning(
            f"⏱️ TIME LIMIT: Position open {days_held} days > {max_days}. "
            f"Closing."
        )

        return {
            'time_exit': True,
            'days_held': days_held,
            'reason': 'Time limit exceeded'
        }

    return {'time_exit': False, 'days_held': days_held}
```

### Regla 11 — Correlation Filter

El par debe tener una correlación de Pearson > 0.90 en el periodo de formación.

```python
def correlation_filter(
    self,
    prices_a: pd.Series,
    prices_b: pd.Series,
    min_correlation: float = 0.90
) -> dict:
    """
    Filtrar por correlación alta.

    Gatev et al: Corr > 0.90 para pairs trading.
    """
    correlation = prices_a.corr(prices_b)

    if correlation < min_correlation:
        logger.warning(
            f"❌ Low correlation: {correlation:.2f} < {min_correlation:.2f}. "
            f"Reject pair."
        )

        return {
            'pass': False,
            'correlation': correlation
        }

    logger.info(
        f"✅ Correlation OK: {correlation:.2f} >= {min_correlation:.2f}"
    )

    return {
        'pass': True,
        'correlation': correlation
    }
```

### Regla 12 — Sector Constraint

Priorizar pares dentro del mismo sector industrial (GICS) para cubrir riesgo macroeconómico.

```python
def sector_filter(
    self,
    asset_a: str,
    asset_b: str,
    sector_mapping: dict,
    prefer_same_sector: bool = True
) -> dict:
    """
    Priorizar pares del mismo sector.

    Gatev et al: Sector neutrality reduce riesgo macro.
    """
    sector_a = sector_mapping.get(asset_a, 'Unknown')
    sector_b = sector_mapping.get(asset_b, 'Unknown')

    same_sector = sector_a == sector_b

    if prefer_same_sector and same_sector:
        logger.info(
            f"✅ Same sector: {asset_a}/{asset_b} = {sector_a}"
        )

        return {
            'same_sector': True,
            'sector': sector_a,
            'priority': 'HIGH'
        }

    elif prefer_same_sector and not same_sector:
        logger.info(
            f"⚠️ Different sectors: {asset_a}={sector_a}, {asset_b}={sector_b}"
        )

        return {
            'same_sector': False,
            'sectors': (sector_a, sector_b),
            'priority': 'LOW'
        }

    return {'same_sector': same_sector}
```

### Regla 13 — Market Neutrality

Ajustar los tamaños de posición (`Dollars_A = Dollars_B · β`) para mantener Dollar Neutrality.

```python
def calculate_position_sizes(
    self,
    signal: str,
    hedge_ratio: float,
    portfolio_value: float,
    asset_a_price: float,
    asset_b_price: float
) -> dict:
    """
    Calcular tamaños para dollar neutrality.

    Gatev et al: Dollars_A = Dollars_B · β.
    """
    # Asignación half del portfolio por lado
    capital_per_side = portfolio_value / 2

    if signal == 'LONG_SPREAD':
        # Long A, Short B
        dollars_a = capital_per_side
        dollars_b = capital_per_side

        shares_a = int(dollars_a / asset_a_price)
        shares_b = int(dollars_b / asset_b_price)

    elif signal == 'SHORT_SPREAD':
        # Short A, Long B
        dollars_a = capital_per_side
        dollars_b = capital_per_side

        shares_a = int(dollars_a / asset_a_price)
        shares_b = int(dollars_b / asset_b_price)

    # Ajustar por hedge ratio
    shares_b = int(shares_b * hedge_ratio)

    # Dollar neutrality check
    dollar_a = shares_a * asset_a_price
    dollar_b = shares_b * asset_b_price

    dollar_imbalance = abs(dollar_a - dollar_b) / portfolio_value

    logger.info(
        f"Position sizes: A={shares_a} (${dollar_a:,.0f}), "
        f"B={shares_b} (${dollar_b:,.0f}), "
        f"Imbalance={dollar_imbalance:.2%}"
    )

    return {
        'shares_a': shares_a,
        'shares_b': shares_b,
        'dollar_a': dollar_a,
        'dollar_b': dollar_b,
        'dollar_imbalance': dollar_imbalance
    }
```

### Regla 14 — Zero-Crossing Count

Contar cuántas veces el spread cruzó el cero en el periodo de formación. Si < 4 veces, descartar el par (poca reversión).

```python
def count_zero_crossings(
    self,
    spread: pd.Series,
    min_crossings: int = 4
) -> dict:
    """
    Contar cruces del spread por cero.

    Gatev et al: Poca reversión = mal candidato.
    """
    # Detectar cruces de cero
    sign_changes = np.sign(spread)
    zero_crossings = (sign_changes.diff().abs() > 1).sum()

    if zero_crossings < min_crossings:
        logger.warning(
            f"❌ Low mean reversion: {zero_crossings} crossings < {min_crossings}. "
            f"Discard pair."
        )

        return {
            'pass': False,
            'crossings': zero_crossings,
            'reason': 'Insufficient mean reversion'
        }

    logger.info(
        f"✅ Mean reversion OK: {zero_crossings} crossings >= {min_crossings}"
    )

    return {
        'pass': True,
        'crossings': zero_crossings
    }
```

### Regla 15 — Corporate Action Handler

Si uno de los pares tiene split o dividendo especial, ajustar el precio histórico antes de recalcular el spread.

```python
def adjust_for_corporate_actions(
    self,
    prices: pd.DataFrame,
    corporate_actions: dict
) -> pd.DataFrame:
    """
    Ajustar precios por splits/dividendos.

    Gatev et al: Corporate actions rompen spreads.
    """
    adjusted_prices = prices.copy()

    for symbol, actions in corporate_actions.items():
        if symbol not in adjusted_prices.columns:
            continue

        for action in actions:
            action_date = action['date']
            action_type = action['type']  # 'split', 'dividend'
            factor = action.get('factor', 1.0)

            if action_type == 'split':
                # Ajustar precios históricos antes del split
                mask = adjusted_prices.index < action_date
                adjusted_prices.loc[mask, symbol] *= factor

                logger.info(
                    f"Adjusted {symbol} for {factor}x split on {action_date}"
                )

            elif action_type == 'dividend':
                # Ajustar por dividendo especial
                mask = adjusted_prices.index < action_date
                dividend_amount = action.get('amount', 0)

                adjusted_prices.loc[mask, symbol] -= dividend_amount

                logger.info(
                    f"Adjusted {symbol} for ${dividend_amount} dividend on {action_date}"
                )

    return adjusted_prices
```

---

## Aplicación Práctica

### Pipeline Completo de Pairs Trading

```python
def pairs_trading_pipeline(
    self,
    prices: pd.DataFrame,
    sector_mapping: dict,
    portfolio_value: float = 100_000
) -> dict:
    """
    Pipeline completo de Pairs Trading.
    """
    # 1. Formation period
    formation = self.formation_period_selection(prices, formation_days=252)
    formation_prices = formation['formation_prices']

    # 2. Normalizar precios
    normalized_prices = self.normalize_prices(formation_prices)

    # 3. Seleccionar pares por SSD
    ssd_pairs = self.select_pairs_by_ssd(normalized_prices, top_n=50)

    # 4. Filtrar pares válidos
    valid_pairs = []

    for pair_info in ssd_pairs:
        asset_a, asset_b = pair_info['pair']

        # Correlation filter
        corr_result = self.correlation_filter(
            formation_prices[asset_a],
            formation_prices[asset_b],
            min_correlation=0.90
        )

        if not corr_result['pass']:
            continue

        # Sector filter
        sector_result = self.sector_filter(
            asset_a, asset_b, sector_mapping, prefer_same_sector=True
        )

        if sector_result['priority'] == 'LOW':
            continue

        # Cointegration test
        coint_result = self.test_cointegration(
            formation_prices[asset_a],
            formation_prices[asset_b]
        )

        if not coint_result['cointegrated']:
            continue

        # Zero crossing count
        spread_info = self.calculate_spread(
            formation_prices[asset_a],
            formation_prices[asset_b]
        )

        crossing_result = self.count_zero_crossings(
            spread_info['spread'],
            min_crossings=4
        )

        if not crossing_result['pass']:
            continue

        valid_pairs.append({
            'pair': (asset_a, asset_b),
            'ssd': pair_info['ssd'],
            'correlation': corr_result['correlation'],
            'hedge_ratio': spread_info['hedge_ratio'],
            'intercept': spread_info['intercept']
        })

    logger.info(f"Valid pairs: {len(valid_pairs)} from {len(ssd_pairs)} candidates")

    # 5. Generar señales para trading
    signals = []

    for pair in valid_pairs:
        asset_a, asset_b = pair['pair']

        # Calcular spread actual
        current_prices = prices.iloc[-1]
        spread_series = self.calculate_spread_series(
            prices[asset_a].iloc[-252:],
            prices[asset_b].iloc[-252:],
            pair['hedge_ratio'],
            pair['intercept']
        )

        # Z-score signal
        z_signal = self.z_score_signal(
            spread_series,
            entry_threshold=2.0,
            lookback=20
        )

        if z_signal['signal'] != 'NEUTRAL':
            # Calcular position sizes
            position_sizes = self.calculate_position_sizes(
                z_signal['signal'],
                pair['hedge_ratio'],
                portfolio_value / len(valid_pairs),  # Dividir capital
                current_prices[asset_a],
                current_prices[asset_b]
            )

            signals.append({
                'pair': (asset_a, asset_b),
                'signal': z_signal['signal'],
                'z_score': z_signal['z_score'],
                'shares_a': position_sizes['shares_a'],
                'shares_b': position_sizes['shares_b'],
                'hedge_ratio': pair['hedge_ratio']
            })

    return {
        'n_valid_pairs': len(valid_pairs),
        'n_active_signals': len(signals),
        'signals': signals
    }
```
