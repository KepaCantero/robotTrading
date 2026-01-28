# 🟡 31. "Art of Currency Trading" - Brent Donnelly

## REGLAS DE TRADING DE DIVISAS (FOREX)

**Regla 31.1 — Calendario Económico**

Claude DEBE estar FLAT 5 minutos antes/después de eventos de alto impacto.

**NFP, CPI, Tasas de interés → NO POSICIONES.**

```python
def economic_calendar_filter(
    self,
    current_time: datetime,
    upcoming_events: List[dict],
    flat_window_minutes: int = 5
) -> dict:
    """
    Filtrar trading alrededor de eventos económicos.

    Donnelly: Estar flat antes de news importantes.
    """
    trading_allowed = True
    warnings = []

    for event in upcoming_events:
        event_time = event['timestamp']
        impact = event['impact']  # 'HIGH', 'MEDIUM', 'LOW'

        # Solo eventos de alto impacto
        if impact != 'HIGH':
            continue

        # Ventana de tiempo alrededor del evento
        time_diff = abs((current_time - event_time).total_seconds() / 60)

        if time_diff <= flat_window_minutes:
            trading_allowed = False
            warnings.append({
                'event': event['name'],
                'time_until': time_diff,
                'currencies': event['currencies_affected']
            })

            logger.warning(
                f"🚨 HIGH IMPACT EVENT: {event['name']} "
                f"in {time_diff:.0f}min. "
                f"Go FLAT."
            )

    return {
        'trading_allowed': trading_allowed,
        'warnings': warnings
    }
```

**Regla 31.2 — Session Awareness**

```python
def session_filter(
    self,
    currency_pair: str,
    current_time: datetime
) -> dict:
    """
    Solo operar pares cuando las sesiones relevantes están abiertas.

    Donnelly: EUR/USD solo en overlap Londres-NY.
    """
    # Convertir a UTC
    utc_hour = current_time.hour

    # Sesiones (en UTC)
    sessions = {
        'SYDNEY': (22, 7),    # 22:00-07:00 UTC
        'TOKYO': (23, 8),     # 23:00-08:00 UTC
        'LONDON': (7, 16),    # 07:00-16:00 UTC
        'NEW_YORK': (13, 22)  # 13:00-22:00 UTC
    }

    # Determinar qué pares operar en cada sesión
    session_pairs = {
        'SYDNEY': ['AUD/USD', 'NZD/USD'],
        'TOKYO': ['USD/JPY', 'EUR/JPY', 'AUD/JPY'],
        'LONDON': ['EUR/USD', 'GBP/USD', 'EUR/GBP', 'USD/CHF'],
        'NEW_YORK': ['EUR/USD', 'GBP/USD', 'USD/CAD', 'USD/JPY']
    }

    # Overlap Londres-NY (mejor liquidez)
    london_ny_overlap_start = 13
    london_ny_overlap_end = 16

    active_sessions = []

    for session, (start, end) in sessions.items():
        if start <= utc_hour < end:
            active_sessions.append(session)

    # Regla especial: EUR/USD solo en overlap
    if currency_pair == 'EUR/USD':
        if not (london_ny_overlap_start <= utc_hour < london_ny_overlap_end):
            logger.info(
                f"EUR/USD: Outside London-NY overlap "
                f"({utc_hour}:00 UTC). Skip."
            )
            return {'trade': False, 'reason': 'Outside optimal session'}

    if not active_sessions:
        logger.info(f"No active session at {utc_hour}:00 UTC")
        return {'trade': False, 'reason': 'No active session'}

    logger.info(f"Active sessions: {active_sessions}")

    return {'trade': True, 'active_sessions': active_sessions}
```

**Regla 31.3 — Mean Reversion en Rango**

```python
def range_vs_breakout_strategy(
    self,
    current_price: float,
    lookback_days: int = 20
) -> str:
    """
    Si en rango (20% central) → RSI. Si en extremos → Breakout.

    Donnelly: Adaptar estrategia según ubicación en rango.
    """
    # Obtener highs/lows del periodo
    price_series = self.get_price_series(lookback_days)

    highest_high = price_series.max()
    lowest_low = price_series.min()
    range_size = highest_high - lowest_low

    # Zonas
    # Top 20%: zona de venta potencial
    top_zone = highest_high - range_size * 0.2

    # Bottom 20%: zona de compra potencial
    bottom_zone = lowest_low + range_size * 0.2

    # Central 60%: rango
    if bottom_zone <= current_price <= top_zone:
        logger.info("Price in range: Use mean reversion (RSI)")
        return 'MEAN_REVERSION'

    elif current_price > top_zone:
        logger.info("Price at top: Use breakout strategy")
        return 'BREAKOUT_LONG'

    else:  # current_price < bottom_zone
        logger.info("Price at bottom: Use breakout strategy")
        return 'BREAKOUT_SHORT'
```

**Regla 31.4 — Correlación USD**

```python
def usd_correlation_filter(
    self,
    currency_pair: str,
    dxy_momentum: float,  # momentum del Dollar Index
    trade_direction: str
) -> bool:
    """
    Si DXY tiene momentum fuerte, no operar contra esa tendencia.

    Donnelly: Respetar la fuerza del dólar.
    """
    # Pares que contienen USD
    usd_pairs = ['EUR/USD', 'GBP/USD', 'AUD/USD', 'USD/JPY',
                 'USD/CHF', 'USD/CAD', 'NZD/USD']

    if currency_pair not in usd_pairs:
        return True  # No aplica

    # Momentum fuerte del DXY
    strong_dxy_momentum = abs(dxy_momentum) > 0.02  # 2%

    if not strong_dxy_momentum:
        return True

    # DXY subiendo → USD fortaleciéndose
    if dxy_momentum > 0:
        # DXY up = USD up
        # EUR/USD, GBP/USD, AUD/USD, NZD/USD deberían bajar
        # USD/JPY, USD/CHF, USD/CAD deberían subir

        weak_against_usd = ['EUR/USD', 'GBP/USD', 'AUD/USD', 'NZD/USD']
        strong_with_usd = ['USD/JPY', 'USD/CHF', 'USD/CAD']

        if currency_pair in weak_against_usd and trade_direction == 'LONG':
            logger.warning(
                f"❌ DXY rising ({dxy_momentum:.1%}). "
                f"No go LONG {currency_pair}"
            )
            return False

        if currency_pair in strong_with_usd and trade_direction == 'SHORT':
            logger.warning(
                f"❌ DXY rising ({dxy_momentum:.1%}). "
                f"No go SHORT {currency_pair}"
            )
            return False

    # DXY bajando → USD debilitándose
    else:
        weak_against_usd = ['EUR/USD', 'GBP/USD', 'AUD/USD', 'NZD/USD']
        strong_with_usd = ['USD/JPY', 'USD/CHF', 'USD/CAD']

        if currency_pair in weak_against_usd and trade_direction == 'SHORT':
            logger.warning(
                f"❌ DXY falling ({dxy_momentum:.1%}). "
                f"No go SHORT {currency_pair}"
            )
            return False

        if currency_pair in strong_with_usd and trade_direction == 'LONG':
            logger.warning(
                f"❌ DXY falling ({dxy_momentum:.1%}). "
                f"No go LONG {currency_pair}"
            )
            return False

    return True
```

**Regla 31.5 — Stop Loss Realista**

```python
def realistic_stop_loss(
    self,
    entry_price: float,
    direction: str,
    pip_size: float = 0.0001
) -> float:
    """
    Colocar SL fuera de niveles psicológicos.

    Donnelly: Los HFT barren liquidez en .00 y .50.
    """
    # Calcular distancia base del SL
    base_distance_pips = 20  # 20 pips base

    # Nivel psicológico más cercano
    # Números redondos: 1.1000, 1.1050, 1.1100
    price_decimals = int(-np.log10(pip_size))
    rounded_level = round(entry_price, price_decimals - 2)

    # Calcular SL
    if direction == 'LONG':
        # Long: SL por debajo del entry
        sl_base = entry_price - base_distance_pips * pip_size

        # Si el SL está cerca de un nivel psicológico, moverlo más abajo
        sl_rounded = round(sl_base, price_decimals - 2)

        if abs(sl_base - sl_rounded) / sl_base < 0.001:
            # Mover 5 pips más abajo del nivel
            sl_price = sl_rounded - 5 * pip_size
            logger.info(f"SL moved below psychological level: {sl_rounded}")

        else:
            sl_price = sl_base

    else:  # SHORT
        # Short: SL por encima del entry
        sl_base = entry_price + base_distance_pips * pip_size

        sl_rounded = round(sl_base, price_decimals - 2)

        if abs(sl_base - sl_rounded) / sl_base < 0.001:
            # Mover 5 pips más arriba del nivel
            sl_price = sl_rounded + 5 * pip_size
            logger.info(f"SL moved above psychological level: {sl_rounded}")

        else:
            sl_price = sl_base

    return sl_price
```

**Regla 31.6 — Flujos de Fin de Mes**

```python
def month_end_flow_adjustment(
    self,
    current_date: datetime,
    position_size: float
) -> float:
    """
    Reducir tamaño los últimos 2 días del mes.

    Donnelly: Rebalanceos corporativos erráticos.
    """
    # Últimos 2 días del mes
    days_until_month_end = (
        (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) -
        current_date
    ).days

    if days_until_month_end <= 2:
        reduction_factor = 0.5  # Reducir 50%

        adjusted_size = position_size * reduction_factor

        logger.info(
            f"Month-end flow: Reducing position {position_size:.2f} → "
            f"{adjusted_size:.2f} ({days_until_month_end} days to EOM)"
        )

        return adjusted_size

    return position_size
```

**Regla 31.7 — Relative Strength FX**

```python
def relative_strength_fx_trading(
    self,
    currency_strength: dict,  # {'USD': 1.2, 'EUR': -0.5, 'JPY': -1.0, ...}
    min_strength_diff: float = 1.0
) -> List[dict]:
    """
    Comprar divisa más fuerte / vender más débil.

    Donnelly: Relative Strength FX.
    """
    # Ordenar por fuerza
    sorted_currencies = sorted(
        currency_strength.items(),
        key=lambda x: x[1]
    )

    weakest = sorted_currencies[0][0]  # Ej: JPY
    strongest = sorted_currencies[-1][0]  # Ej: AUD

    strength_diff = sorted_currencies[-1][1] - sorted_currencies[0][1]

    trades = []

    if strength_diff >= min_strength_diff:
        # Buscar par que combine estas divisas
        pair = f"{strongest}/{weakest}"  # Ej: AUD/JPY

        if self.pair_exists(pair):
            trades.append({
                'pair': pair,
                'direction': 'LONG',  # Comprar fuerte, vender débil
                'strength_diff': strength_diff,
                'strongest': strongest,
                'weakest': weakest
            })

            logger.info(
                f"RS signal: LONG {pair} "
                f"({strongest} strength={currency_strength[strongest]:.1f} vs "
                f"{weakest} strength={currency_strength[weakest]:.1f})"
            )

    return trades
```

**Regla 31.8 — Interest Rate Carry**

```python
def carry_trade_signal(
    self,
    currency_pair: str,
    interest_rate_diff: float,  # Diferencia de tasas
    profile_horizon: str  # 'SHORT', 'MEDIUM', 'LONG'
) -> float:
    """
    Perfiles de largo plazo: favorecer Carry Trade positivo.

    Donnelly: Interest Rate Carry.
    """
    # Solo para perfiles de largo plazo
    if profile_horizon != 'LONG':
        return 0.0

    # Swap positivo
    if interest_rate_diff > 0.01:  # > 1% differential
        carry_signal = np.tanh(interest_rate_diff * 10)

        logger.info(
            f"Carry trade: {currency_pair} has positive swap "
            f"({interest_rate_diff:.1%})"
        )

        return carry_signal

    # Swap negativo: evitar en largo plazo
    elif interest_rate_diff < -0.01:
        logger.warning(
            f"Negative carry: {currency_pair} ({interest_rate_diff:.1%})"
        )

        return 0.0

    return 0.0
```

**Regla 31.9 — Lógica de Viernes**

```python
def friday_position_filter(
    self,
    current_time: datetime,
    position_type: str  # 'SCALP', 'SWING', 'POSITION'
) -> bool:
    """
    Cerrar posiciones de scalping el viernes a las 20:00 UTC.

    Donnelly: Evitar gaps de fin de semana.
    """
    # Viernes después de las 20:00 UTC
    is_friday_evening = (
        current_time.weekday() == 4 and  # Viernes
        current_time.hour >= 20
    )

    if is_friday_evening and position_type == 'SCALP':
        logger.warning(
            "Friday evening: Close scalping positions to avoid weekend gaps"
        )
        return False

    return True
```

**Regla 31.10 — News Sentiment Filter**

```python
def news_sentiment_filter(
    self,
    strategy: str,  # 'CARRY_TRADE', 'MOMENTUM', etc.
    current_sentiment: str  # 'RISK_ON', 'RISK_OFF', 'NEUTRAL'
) -> bool:
    """
    Noticias geopolíticas negativas → desactivar Carry Trade.

    Donnelly: Carry trade no funciona en crisis.
    """
    # Eventos de riesgo geopolítico
    if current_sentiment == 'RISK_OFF':
        if strategy == 'CARRY_TRADE':
            logger.critical(
                "🚨 Geopolitical risk: Deactivating CARRY_TRADE. "
                "Flight to safety expected."
            )
            return False

        # En Risk-Off, refugiarse en USD o JPY
        logger.info("Risk-Off: Prefer USD/JPY safe havens")

    return True
```

**Regla 31.11 — Volatilidad vs Rango**

```python
def vol_based_strategy_activation(
    self,
    symbol: str,
    atr_current: float,
    atr_ma: float,
    strategy_type: str
) -> bool:
    """
    Si ATR < 50% de media, apagar estrategia de breakout.

    Donnelly: Breakout necesita volatilidad.
    """
    atr_ratio = atr_current / atr_ma if atr_ma > 0 else 1.0

    if strategy_type == 'BREAKOUT':
        if atr_ratio < 0.5:
            logger.info(
                f"Low volatility ({atr_ratio:.1%} of average). "
                f"Breakout strategy deactivated."
            )
            return False

    elif strategy_type == 'MEAN_REVERSION':
        if atr_ratio > 1.5:
            logger.info(
                f"High volatility ({atr_ratio:.1%} of average). "
                f"Mean reversion deactivated."
            )
            return False

    return True
```

**Regla 31.12 — Risk-On / Risk-Off**

```python
def risk_on_off_monitor(
    self,
    spy_return_pct: float,
    fx_positions: List[dict]
) -> dict:
    """
    Monitorear SPY. Si cae > 2%, refugiarse en USD/JPY.

    Donnelly: Risk-Off = Flight to safety.
    """
    spy_threshold = -0.02  # -2%

    if spy_return_pct < spy_threshold:
        logger.critical(
            f"🚨 SPY down {spy_return_pct:.1%}: Risk-Off mode. "
            f"Flight to USD/JPY safe havens."
        )

        # Safe haven currencies
        safe_havens = ['USD', 'JPY', 'CHF']

        # Acciones:
        # 1. Reducir posiciones de riesgo
        # 2. Aumentar exposición a safe havens

        adjustments = []

        for position in fx_positions:
            base, quote = position['pair'].split('/')

            # Si ninguna de las divisas es safe haven
            if base not in safe_havens and quote not in safe_havens:
                adjustments.append({
                    'pair': position['pair'],
                    'action': 'REDUCE',
                    'reason': 'Risk currency in Risk-Off environment'
                })

            # Si estamos LONG safe haven
            elif (position['direction'] == 'LONG' and base in safe_havens) or \
                 (position['direction'] == 'SHORT' and quote in safe_havens):
                adjustments.append({
                    'pair': position['pair'],
                    'action': 'HOLD',
                    'reason': 'Safe haven position'
                })

        return {'mode': 'RISK_OFF', 'adjustments': adjustments}

    return {'mode': 'NEUTRAL', 'adjustments': []}
```

**Regla 31.13 — Time-of-Day Filter**

```python
def time_of_day_filter(
    self,
    current_time: datetime,
    utc_hour: int = None
) -> bool:
    """
    Evitar operar entre 22:00-23:00 UTC (rollover).

    Donnelly: Spreads masivos en rollover.
    """
    if utc_hour is None:
        utc_hour = current_time.hour

    # Ventana de rollover
    if 22 <= utc_hour < 23:
        logger.info(
            f"Rollover hour ({utc_hour}:00 UTC): "
            f"Wide spreads. Skip trading."
        )
        return False

    return True
```

**Regla 31.14 — Señales de Opciones (FX Options Pain)**

```python
def fx_options_pain_levels(
    self,
    currency_pair: str,
    options_data: dict
) -> dict:
    """
    Usar niveles de "Pain" de opciones como S/R.

    Donnelly: Options pain indica niveles institucionales.
    """
    # Niveles de max pain
    call_pain = options_data.get('call_pain_level')
    put_pain = options_data.get('put_pain_level')

    current_price = self.get_current_price(currency_pair)

    levels = {
        'support': None,
        'resistance': None,
        'near_support': False,
        'near_resistance': False
    }

    # Put pain = soporte (max dolor para put holders)
    if put_pain:
        levels['support'] = put_pain

        if abs(current_price - put_pain) / current_price < 0.005:
            levels['near_support'] = True
            logger.info(
                f"Near options pain support: {put_pain:.4f}"
            )

    # Call pain = resistencia
    if call_pain:
        levels['resistance'] = call_pain

        if abs(current_price - call_pain) / current_price < 0.005:
            levels['near_resistance'] = True
            logger.info(
                f"Near options pain resistance: {call_pain:.4f}"
            )

    return levels
```

**Regla 31.15 — Position Sizing por Pip Value**

```python
def position_sizing_by_pip_value(
    self,
    currency_pair: str,
    entry_price: float,
    stop_loss_price: float,
    account_equity: float,
    risk_per_trade_pct: float = 0.005  # 0.5%
) -> float:
    """
    Calcular lote exacto para que SL = 0.5% del capital.

    Donnelly: NO operar por lotes fijos.
    """
    # Distancia del SL en pips
    pip_size = 0.0001 if 'JPY' not in currency_pair else 0.01

    sl_distance_pips = abs(entry_price - stop_loss_price) / pip_size

    # Riesgo monetario
    risk_amount = account_equity * risk_per_trade_pct

    # Pip value del par
    # Standard lot (100,000 units) = $10/pip para多数 pares
    pip_value_per_lot = self.get_pip_value_per_lot(currency_pair)

    # Número de lotes
    lots = risk_amount / (sl_distance_pips * pip_value_per_lot)

    logger.info(
        f"Position sizing: {lots:.2f} lots for {currency_pair}. "
        f"SL={sl_distance_pips:.0f} pips = ${risk_amount:.2f} "
        f"({risk_per_trade_pct:.1%} of equity)"
    )

    return lots
```
