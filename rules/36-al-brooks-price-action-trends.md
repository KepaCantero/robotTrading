# 🟡 36. "Price Action Trends" - Al Brooks

## REGLAS DE PRICE ACTION PARA FEATURES DE ML

**Regla 36.1 — Bar Counting (H1, H2, L1, L2)**

Claude DEBE extraer features de highs/lows en correcciones.

**H1, H2, L1, L2 = variables de entrada para modelos de clasificación.**

```python
def extract_bar_counting_features(
    self,
    price_series: pd.Series,
    window: int = 20
) -> dict:
    """
    Extraer H1, H2, L1, L2 como features ML.

    Brooks: Highs/Lows en correcciones = estructura de tendencia.
    """
    # Encontrar swing highs y lows
    swing_highs = self.find_swing_highs(price_series, order=3)
    swing_lows = self.find_swing_lows(price_series, order=3)

    # Última corrección
    recent_highs = swing_highs.tail(2)
    recent_lows = swing_lows.tail(2)

    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        h1 = recent_highs.iloc[0]
        h2 = recent_highs.iloc[1]
        l1 = recent_lows.iloc[0]
        l2 = recent_lows.iloc[1]

        if h2 > h1 and l2 > l1:
            structure = 'BULLISH_SWING'
        elif h2 < h1 and l2 < l1:
            structure = 'BEARISH_SWING'
        else:
            structure = 'RANGE'

        return {
            'h1_price': h1, 'h2_price': h2,
            'l1_price': l1, 'l2_price': l2,
            'structure': structure
        }

    return {}
```

**Regla 36.2 — Contexto de Rango**

```python
def range_context_feature(
    self,
    ohlcv: pd.DataFrame,
    wick_threshold: float = 0.3
) -> dict:
    """
    Si muchas mechas → desactivar trading de ruptura.

    Brooks: Muchas wicks = indecisión, range.
    """
    recent = ohlcv.tail(10)
    recent['wick_ratio'] = (
        ((recent['high'] - recent[['open', 'close']].max(axis=1)) +
         (recent[['open', 'close']].min(axis=1) - recent['low'])) /
        (recent['high'] - recent['low'])
    )

    high_wick_bars = (recent['wick_ratio'] > wick_threshold).sum()
    wick_feature = high_wick_bars / 10

    if wick_feature > 0.6:
        return {
            'range_detected': True,
            'breakout_appropriate': False
        }

    return {'range_detected': False, 'breakout_appropriate': True}
```

**Regla 36.3 — Major Trend Reversal**

```python
def major_trend_reversal_signal(
    self,
    trendline_break: bool,
    test_failed: bool
) -> dict:
    """
    Ruptura de tendencia + test fallido = entrada alta probabilidad.

    Brooks: MTR = setup de alta probabilidad.
    """
    if trendline_break and test_failed:
        return {
            'signal': 'MTR_BUY',
            'probability': 'HIGH',
            'setup_valid': True
        }

    return {'signal': 'NONE', 'setup_valid': False}
```

**Regla 36.4 — Velas de Tendencia**

```python
def trend_bar_feature(self, bar: dict) -> dict:
    """
    Trend Bar = cuerpo > 50% del rango total.

    Brooks: Trend bars = momentum.
    """
    body = abs(bar['close'] - bar['open'])
    total_range = bar['high'] - bar['low']

    if total_range == 0:
        return {'is_trend_bar': False, 'body_ratio': 0}

    body_ratio = body / total_range
    is_trend_bar = body_ratio > 0.5

    return {
        'is_trend_bar': is_trend_bar,
        'body_ratio': body_ratio,
        'direction': 'BULL' if bar['close'] > bar['open'] else 'BEAR'
    }
```

**Regla 36.5 — Failure to Break (Trap Trading)**

```python
def failure_to_break_signal(
    self,
    break_attempts: List[dict]
) -> dict:
    """
    Si ruptura falla 2 veces → operar en dirección opuesta.

    Brooks: Trap = opportunity contra el crowd.
    """
    consecutive_failures = sum(
        1 for a in break_attempts[-3:] if not a['succeeded']
    )

    if consecutive_failures >= 2:
        return {
            'trap_detected': True,
            'signal': 'OPPOSITE_DIRECTION'
        }

    return {'trap_detected': False}
```

**Regla 36.6 — Measured Move**

```python
def measured_move_projection(
    self,
    first_impulse_size: float,
    second_impulse_start: float,
    direction: str
) -> dict:
    """
    Usar tamaño del primer impulso para proyectar TP del segundo.

    Brooks: Medidas de price action.
    """
    if direction == 'UP':
        projected = second_impulse_start + first_impulse_size
    else:
        projected = second_impulse_start - first_impulse_size

    return {
        'projected_target': projected,
        'risk_reward': 2.0  # 2:1 típico
    }
```

**Regla 36.7 — Rango de Apertura**

```python
def opening_range_levels(
    self,
    first_30min_high: float,
    first_30min_low: float,
    current_price: float
) -> dict:
    """
    Primeros 15-30 min definen S/R del día.

    Brooks: Opening Range = niveles clave.
    """
    if current_price > first_30min_high:
        position = 'ABOVE_OR'
    elif current_price < first_30min_low:
        position = 'BELOW_OR'
    else:
        position = 'INSIDE_OR'

    return {
        'or_high': first_30min_high,
        'or_low': first_30min_low,
        'position': position
    }
```

**Regla 36.8 — Velas de Clímax**

```python
def climax_bar_detection(
    self,
    bar_range: float,
    avg_range: float
) -> dict:
    """
    Velas inusualmente grandes = final del movimiento.

    Brooks: Climax mark = reversión.
    """
    if bar_range > avg_range * 2.0:
        return {
            'climax_detected': True,
            'signal': 'PREPARE_FOR_REVERSAL'
        }

    return {'climax_detected': False}
```

**Regla 36.9 — Support/Resistance Flip**

```python
def support_resistance_flip(
    self,
    broken_level: float
) -> float:
    """
    Nivel roto automáticamente = nuevo Stop Loss.

    Brooks: S/R flip = manejo de riesgo.
    """
    logger.info(f"S/R FLIP: {broken_level:.2f} now acts as SL")
    return broken_level
```
