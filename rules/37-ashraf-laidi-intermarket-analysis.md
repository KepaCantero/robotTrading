# 🟡 37. "Intermarket Analysis" - Ashraf Laidi

## REGLAS DE ANÁLISIS INTERMERCADO (FOREX)

**Regla 37.1 — Regla del Oro/AUD**

Claude DEBE detectar divergencias entre Oro y AUD.

**Si Oro sube y AUD no → largos en AUD/USD.**

```python
def gold_aud_divergence(
    self,
    gold_price: float,
    gold_change: float,
    aud_usd_price: float,
    aud_usd_change: float
) -> dict:
    """
    Divergencia Oro/AUD = oportunidad.

    Laidi: AUD suele seguir al oro (commodity currency).
    """
    # Correlación esperada: positiva
    correlation_expected = True

    # Divergencia: Oro sube, AUD no
    if gold_change > 0.005 and aud_usd_change < 0:  # Oro +0.5%, AUD negativo
        logger.info(
            f"🟢 DIVERGENCE: Gold +{gold_change:.2%}, "
            f"AUD/USD {aud_usd_change:+.2%}. "
            f"Long AUD/USD setup."
        )

        return {
            'divergence': True,
            'signal': 'LONG_AUD_USD',
            'reason': 'Gold_up_AUD_down'
        }

    # Divergencia opuesta
    elif gold_change < -0.005 and aud_usd_change > 0:
        logger.info(
            f"🔴 DIVERGENCE: Gold {gold_change:.2%}, "
            f"AUD/USD +{aud_usd_change:.2%}. "
            f"Short AUD/USD setup."
        )

        return {
            'divergence': True,
            'signal': 'SHORT_AUD_USD',
            'reason': 'Gold_down_AUD_up'
        }

    return {'divergence': False}
```

**Regla 37.2 — Yield Differentials**

```python
def yield_differential_signal(
    self,
    country_1_2y_yield: float,
    country_2_2y_yield: float,
    currency_pair: str
) -> dict:
    """
    Diferencial de tipos 2 años = señal principal de FX.

    Laidi: Capital fluye a mayor yield.
    """
    differential = country_1_2y_yield - country_2_2y_yield

    if abs(differential) > 0.01:  # > 1% diferencia
        logger.info(
            f"Yield differential: {differential:+.2%} "
            f"({currency_pair}). "
            f"Capital flows to higher yield."
        )

        # Mayor yield → apreciación esperada
        if differential > 0:
            return {
                'signal': 'LONG_FIRST_CURRENCY',
                'differential': differential,
                'strength': 'STRONG' if differential > 0.02 else 'MODERATE'
            }
        else:
            return {
                'signal': 'SHORT_FIRST_CURRENCY',
                'differential': differential
            }

    return {'signal': 'NEUTRAL'}
```

**Regla 37.3 — Oil/CAD Correlation**

```python
def oil_cad_correlation_lag(
    self,
    oil_price: float,
    oil_break_level: float,
    cad_usd_price: float,
    lag_minutes: int = 30
) -> dict:
    """
    Petróleo rompe nivel → CAD sigue con lag 15-30 min.

    Laidi: CAD = petro-currency con lag.
    """
    # Petróleo rompió resistencia
    if oil_price > oil_break_level:
        logger.info(
            f"Oil broke above ${oil_break_level:.2f}. "
            f"CAD expected to strengthen in {lag_minutes}min."
        )

        return {
            'oil_breakout': 'BULLISH',
            'cad_expected': 'BULLISH',
            'lag_minutes': lag_minutes,
            'action': 'PREPARE_LONG_CAD'
        }

    elif oil_price < oil_break_level:
        logger.info(
            f"Oil broke below ${oil_break_level:.2f}. "
            f"CAD expected to weaken."
        )

        return {
            'oil_breakout': 'BEARISH',
            'cad_expected': 'BEARISH',
            'action': 'PREPARE_SHORT_CAD'
        }

    return {'oil_breakout': None}
```

**Regla 37.4 — Risk-On (Equities/JPY)**

```python
def risk_on_jpy_filter(
    self,
    sp500_change: float,
    jpy_pairs: List[str]
) -> dict:
    """
    S&P cae > 1.5% → cerrar largos en pares de riesgo, buscar refugio JPY.

    Laidi: JPY = safe haven.
    """
    if sp500_change < -0.015:  # -1.5%
        logger.critical(
            f"🔴 RISK-OFF: S&P {sp500_change:.2%}. "
            f"Close risk pairs, buy JPY."
        )

        return {
            'regime': 'RISK_OFF',
            'action': 'CLOSE_LONG_AUD_NZD',
            'safe_haven': 'JPY',
            'jpy_action': 'BUY_JPY'
        }

    elif sp500_change > 0.015:  # +1.5%
        logger.info(f"🟢 RISK-ON: S&P {sp500_change:.2%}")

        return {
            'regime': 'RISK_ON',
            'action': 'BUY_AUD_NZD',
            'jpy_action': 'REDUCE_JPY'
        }

    return {'regime': 'NEUTRAL'}
```

**Regla 37.5 — Nikkei/USDJPY Correlation**

```python
def nikkei_usdjpy_correlation(
    self,
    nikkei_change: float,
    usdjpy_change: float,
    threshold: float = 0.005
) -> dict:
    """
    USD/JPY correlacionado con Nikkei (flujos de capital japonés).

    Laidi: Japanese investors repatrian/exports según Nikkei.
    """
    # Divergencia
    divergence = abs(nikkei_change - usdjpy_change)

    if divergence > threshold:
        logger.info(
            f"Nikkei/USDJPY divergence: "
            f"Nikkei {nikkei_change:+.2%}, "
            f"USD/JPY {usdjpy_change:+.2%}"
        )

        # Si Nikkei sube mucho y USD/JPY no → USD/JPY debe subir
        if nikkei_change > 0.01 and usdjpy_change < 0.005:
            return {
                'divergence': True,
                'expected': 'USDJPY_UP',
                'signal': 'LONG_USDJPY'
            }

    return {'divergence': False}
```

**Regla 37.6 — Copper/Growth Indicator**

```python
def copper_em_signal(
    self,
    copper_price: float,
    copper_change: float,
    emerging_market_pairs: List[str]
) -> dict:
    """
    Cobre = indicador adelantado de monedas emergentes.

    Laidi: Dr. Copper = economista global.
    """
    if copper_change > 0.02:  # +2%
        logger.info(
            f"Copper +{copper_change:.1%}: Growth expected. "
            f"Emerging market currencies bullish."
        )

        return {
            'copper_signal': 'BULLISH',
            'em_fx_action': 'BUY',
            'pairs': emerging_market_pairs
        }

    elif copper_change < -0.02:
        logger.warning(
            f"Copper {copper_change:.1%}: Growth slowing. "
            f"EM currencies bearish."
        )

        return {
            'copper_signal': 'BEARISH',
            'em_fx_action': 'SELL'
        }

    return {'copper_signal': 'NEUTRAL'}
```

**Regla 37.7 — Inversión de Curva**

```python
def curve_inversion_usd(
    self,
    us_2y_yield: float,
    us_10y_yield: float
) -> dict:
    """
    Curva invertida → USD estructuralmente fuerte (safe haven).

    Laidi: Inversión = fear → USD demand.
    """
    curve_slope = us_10y_yield - us_2y_yield

    if curve_slope < 0:
        logger.warning(
            f"🔴 YIELD CURVE INVERTED: 2y={us_2y_yield:.2%}, "
            f"10y={us_10y_yield:.2%}. "
            f"USD structural strength expected."
        )

        return {
            'curve_inverted': True,
            'usd_outlook': 'BULLISH',
            'reason': 'SAFE_HAVEN_DEMAND'
        }

    return {'curve_inverted': False}
```

**Regla 37.8 — Dollar Index (DXY) Anchor**

```python
def dxy_filter(
    self,
    dxy_trend: str,  # 'UP', 'DOWN', 'NEUTRAL'
    currency_pair: str
) -> bool:
    """
    NO operar pares menores sin verificar tendencia DXY.

    Laidi: DXY = anchor para todos los pares USD.
    """
    if dxy_trend == 'UP' and 'USD' not in currency_pair:
        # DXY subiendo → USD fuerte → cuidado shorts USD
        logger.info("DXY UP: Be careful shorting USD pairs")
        return True

    elif dxy_trend == 'DOWN' and 'USD' not in currency_pair:
        logger.info("DXY DOWN: USD weakness expected")
        return True

    return True
```

**Regla 37.9 — Central Bank Sentiment (NLP)**

```python
def central_bank_sentiment_nlp(
    self,
    statement_text: str,
    previous_sentiment: str
) -> dict:
    """
    NLP para analizar comunicados; cambio "neutral" a "hawkish" = señal.

    Laidi: Central bank language = trading signals.
    """
    # Análisis de sentimiento simplificado
    hawkish_words = ['inflation', 'overheating', 'tighten', 'hike']
    dovish_words = ['accommodate', 'support', 'stimulus', 'patient']

    hawkish_count = sum(1 for w in hawkish_words if w in statement_text.lower())
    dovish_count = sum(1 for w in dovish_words if w in statement_text.lower())

    if hawkish_count > dovish_count and previous_sentiment != 'HAWKISH':
        logger.info(
            f"🦅 SHIFT TO HAWKISH: {hawkish_count} vs {dovish_count} words. "
            f"Buy signal 48-72h."
        )

        return {
            'sentiment_shift': 'TO_HAWKISH',
            'signal': 'BUY_CURRENCY',
            'duration_hours': 72
        }

    elif dovish_count > hawkish_count and previous_sentiment != 'DOVISH':
        logger.info(f"🕊️ SHIFT TO DOVISH: Sell signal")
        return {'sentiment_shift': 'TO_DOVISH', 'signal': 'SELL_CURRENCY'}

    return {'sentiment_shift': None}
```

**Regla 37.10 — VIX Filter**

```python
def vix_carry_trade_filter(
    self,
    vix_level: float,
    carry_trade_positions: List[str]
) -> dict:
    """
    VIX > 25 → apagar Carry Trade.

    Laidi: Volatilidad alta = carry trade unwinding.
    """
    if vix_level > 25:
        logger.critical(
            f"🚨 VIX {vix_level:.1f} > 25. "
            f"Carry trade OFF. Unwind positions."
        )

        return {
            'vix_status': 'ELEVATED',
            'carry_trade_allowed': False,
            'action': 'UNWIND_HIGH_YIELD'
        }

    elif vix_level < 15:
        logger.info(f"VIX {vix_level:.1f}: Carry trade ON")
        return {'vix_status': 'LOW', 'carry_trade_allowed': True}

    return {'vix_status': 'NORMAL', 'carry_trade_allowed': True}
```

**Regla 37.11 — Commodity Currencies Block**

```python
def commodity_currency_block(
    self,
    aud_change: float,
    cad_change: float,
    nzd_change: float
) -> dict:
    """
    AUD, CAD, NZD = bloque. Si divergen, rezagado alcanza al líder.

    Laidi: Commodity currencies mueven juntas.
    """
    changes = {
        'AUD': aud_change,
        'CAD': cad_change,
        'NZD': nzd_change
    }

    # Identificar líder y rezagado
    leader = max(changes.items(), key=lambda x: x[1])
    laggard = min(changes.items(), key=lambda x: x[1])

    divergence = leader[1] - laggard[1]

    if divergence > 0.01:  # > 1% divergencia
        logger.info(
            f"Commodity block divergence: {leader[0]} +{leader[1]:.2%}, "
            f"{laggard[0]} {laggard[1]:.2%}. "
            f"{laggard[0]} expected to catch up."
        )

        return {
            'divergence': True,
            'leader': leader[0],
            'laggard': laggard[0],
            'trade': f'LONG_{laggard[0]}'
        }

    return {'divergence': False}
```

**Regla 37.12 — Bunds vs Treasuries**

```python
def bunds_treasury_eurusd(
    self,
    bund_10y_yield: float,
    treasury_10y_yield: float
) -> dict:
    """
    Diferencial Bono Alemania/USA = rumbo EUR/USD medio plazo.

    Laidi: Yield spread = capital flows.
    """
    spread = bund_10y_yield - treasury_10y_yield

    # Spread narrowing = EUR bullish
    spread_ma = self.get_spread_ma(lookback=20)
    spread_change = spread - spread_ma

    if spread_change < -0.002:  # Spread narrowing > 0.2%
        logger.info(
            f"Spread narrowing: {spread_change:+.3f}. "
            f"EUR/USD bullish."
        )

        return {
            'signal': 'LONG_EURUSD',
            'reason': 'SPREAD_NARROWING'
        }

    elif spread_change > 0.002:
        logger.info(f"Spread widening: EUR/USD bearish")
        return {'signal': 'SHORT_EURUSD', 'reason': 'SPREAD_WIDENING'}

    return {'signal': 'NEUTRAL'}
```

**Regla 37.13 — Efecto Inflación**

```python
def inflation_breakaway(
    self,
    inflation_rate: float,
    inflation_trend: str,  # 'ACCELERATING', 'STABLE', 'DECELERATING'
    central_bank_reaction: str
) -> dict:
    """
    País con inflación creciente + BC reacciona = moneda aprecia.

    Laidi: Real yield = attracción.
    """
    if inflation_trend == 'ACCELERATING' and central_bank_reaction == 'HAWKISH':
        logger.info(
            f"Inflation + Hawkish BC = currency appreciation expected"
        )

        return {
            'currency_outlook': 'BULLISH',
            'reason': 'REAL_YIELD_ATTRACTION'
        }

    elif inflation_trend == 'ACCELERATING' and central_bank_reaction == 'NEUTRAL':
        logger.warning(
            f"Inflation + Dovish BC = currency weakness"
        )

        return {
            'currency_outlook': 'BEARISH',
            'reason': 'NEGATIVE_REAL_YIELDS'
        }

    return {'currency_outlook': 'NEUTRAL'}
```

**Regla 37.14 — Safe Haven Flow**

```python
def safe_haven_allocation(
    self,
    geopolitical_risk: str,  # 'LOW', 'MEDIUM', 'HIGH'
    current_positions: dict
) -> dict:
    """
    Crisis geopolíticas → solo CHF y JPY permitidos.

    Laidi: Safe haven rotation = predictable.
    """
    if geopolitical_risk == 'HIGH':
        logger.critical(
            "🚨 GEOPOLITICAL CRISIS: "
            "Rotate to CHF/JPY only."
        )

        return {
            'allowed_currencies': ['CHF', 'JPY'],
            'action': 'CLOSE_OTHER_POSITIONS',
            'safe_havens': ['USD', 'JPY', 'CHF']
        }

    return {'allowed_currencies': 'ALL'}
```

**Regla 37.15 — Lag de Commodities**

```python
def commodity_lag_arbitrage(
    self,
    commodity_change: float,  # ej: Oil +2%
    currency_lag: float,       # CAD +0.5% (rezagado)
    expected_lag_minutes: int = 30
) -> dict:
    """
    Monedas tardan más en reaccionar que futuros.

    Laidi: Lag = alpha opportunity.
    """
    # Si commodity ya se movió y moneda no
    if abs(commodity_change) > 0.01 and abs(currency_lag) < 0.003:
        logger.info(
            f"Commodity lag: Commodity {commodity_change:+.2%}, "
            f"Currency {currency_lag:+.2%}. "
            f"Expected catch-up."
        )

        direction = 'LONG' if commodity_change > 0 else 'SHORT'

        return {
            'lag_detected': True,
            'signal': direction,
            'confidence': 'HIGH'
        }

    return {'lag_detected': False}
```
