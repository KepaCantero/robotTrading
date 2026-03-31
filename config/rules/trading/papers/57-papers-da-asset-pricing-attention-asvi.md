# 📄 Papers Fundamentales - Asset Pricing with Attention (Da, Engelberg & Gao, 2011)

## Sentimiento y Atención de Masas como Alpha Factor

**Contexto:** Alternative Data y Sentiment Analysis.

Da et al. demostraron que el volumen de búsqueda de Google (ASVI) es un predictor poderoso de retornos futuros, especialmente para retail investors.

---

### Regla 1 — ASVI Integration (Abnormal Search Volume Index)

Usar Google Trends como feature de entrada para el modelo.

```python
def calculate_asvi(
    self,
    ticker: str,
    window: int = 4  # 4 semanas
) -> dict:
    """
    Calcular Abnormal Search Volume Index.

    Da: ASVI = (search_vol - avg_search_vol) / std_search_vol
    """
    # Obtener search volume de Google Trends
    search_volumes = self.get_google_trends_data(ticker, weeks=12)

    # Promedio móvil
    avg_volume = search_volumes.rolling(window).mean()

    # Desviación estándar
    std_volume = search_volumes.rolling(window).std()

    # ASVI
    asvi = (search_volumes - avg_volume) / std_volume

    # Último valor
    current_asvi = asvi.iloc[-1]

    logger.info(
        f"ASVI for {ticker}: {current_asvi:.2f} "
        f"({'HIGH' if abs(current_asvi) > 2 else 'normal'})"
    )

    return {
        'asvi': asvi,
        'current': current_asvi,
        'search_volume': search_volumes.iloc[-1],
        'avg_volume': avg_volume.iloc[-1]
    }
```

### Regla 2 — Retail Attention Proxy

Tratar los picos de búsqueda como indicadores de sentimiento retail.

```python
def retail_attention_signal(
    self,
    asvi: float,
    threshold: float = 2.0
) -> dict:
    """
    Señal de atención retail basada en ASVI.

    Da: Picos de búsqueda = interés retail extremo.
    """
    if asvi > threshold:
        signal = 'HIGH_ATTENTION'
        sentiment = 'bullish_retail'
        implication = 'possible_reversal'

    elif asvi < -threshold:
        signal = 'LOW_ATTENTION'
        sentiment = 'bearish_retail'
        implication = 'possible_bargain'

    else:
        signal = 'NORMAL_ATTENTION'
        sentiment = 'neutral'
        implication = 'no_edge'

    logger.info(
        f"Retail attention: {signal}, "
        f"sentiment={sentiment}, ASVI={asvi:.2f}"
    )

    return {
        'signal': signal,
        'sentiment': sentiment,
        'implication': implication,
        'asvi': asvi
    }
```

### Regla 3 — Short-Term Reversal

Si hay pico masivo de atención en small cap, buscar reversión.

```python
def attention_reversal_strategy(
    self,
    ticker: str,
    market_cap: float,
    asvi: float,
    lookback_days: int = 5
) -> dict:
    """
    Reversión tras pico de atención en small caps.

    Da: Retail attention → overreaction → reversión.
    """
    # Small cap threshold
    is_small_cap = market_cap < 2e9  # < $2B

    if is_small_cap and asvi > 2.0:
        # Buscar reversión
        recent_return = self.get_recent_return(ticker, lookback_days)

        if recent_return > 0.10:  # Subió > 10%
            signal = 'SHORT'
            confidence = min(asvi / 2, 1.0)
            rationale = 'Pico atención + subida forte → probable reversión'

        else:
            signal = 'HOLD'
            confidence = 0.5
            rationale = 'Atención alta pero sin movimiento price'

    else:
        signal = 'HOLD'
        confidence = 0.0
        rationale = 'No cumple criterios (small cap + ASVI alto)'

    logger.info(
        f"Attention reversal: {signal}, "
        f"conf={confidence:.2%}, {rationale}"
    )

    return {
        'signal': signal,
        'confidence': confidence,
        'rationale': rationale,
        'asvi': asvi,
        'recent_return': recent_return if is_small_cap else None
    }
```

### Regla 4 — IPO Attention Strategy

Usar atención para predecir volatilidad en primeras 48h post-IPO.

```python
def ipo_attention_volatility(
    self,
    ticker: str,
    days_since_ipo: int
) -> dict:
    """
    Predecir volatilidad post-IPO usando atención.

    Da: ASVI alto pre-IPO → volatilidad alta post-IPO.
    """
    if days_since_ipo > 30:
        return {'relevant': False, 'reason': 'Too long since IPO'}

    # ASVI en semanas previas a IPO
    asvi = self.calculate_asvi(ticker, window=4)['current']

    # Predicción de volatilidad
    expected_vol = 0.02 + 0.01 * max(asvi, 0)  # Base + ASVI contribution

    # Umbral para trading
    if expected_vol > 0.05:  # > 5% vol diaria esperada
        recommendation = 'avoid_or_hedge'
        rationale = 'Volatilidad extrema esperada'

    elif expected_vol > 0.03:
        recommendation = 'reduce_position'
        rationale = 'Volatilidad elevada esperada'

    else:
        recommendation = 'normal'
        rationale = 'Volatilidad normal'

    logger.info(
        f"IPO attention: ASVI={asvi:.2f}, "
        f"exp_vol={expected_vol:.2%}, {recommendation}"
    )

    return {
        'relevant': True,
        'asvi': asvi,
        'expected_volatility': expected_vol,
        'recommendation': recommendation,
        'rationale': rationale
    }
```

### Regla 5 — Sentiment Polarity (Search × Price)

Cruzar volumen de búsqueda con precio para determinar miedo/codicia.

```python
def search_price_sentiment(
    self,
    ticker: str,
    asvi: float,
    price_change: float  # Cambio de precio reciente
) -> dict:
    """
    Polaridad de sentimiento = búsqueda × precio.

    Da: Búsqueda + price = sentimiento más preciso.
    """
    # Clasificar
    if asvi > 1.0 and price_change > 0.05:
        sentiment = 'euphoria'
        signal = 'contrarian_sell'
        implication = 'Possible top'

    elif asvi > 1.0 and price_change < -0.05:
        sentiment = 'panic_search'
        signal = 'contrarian_buy'
        implication = 'Possible capitulation'

    elif asvi < -1.0 and price_change > 0.05:
        sentiment = 'quiet_rally'
        signal = 'hold_or_add'
        implication = 'Sustainable move'

    elif asvi < -1.0 and price_change < -0.05:
        sentiment = 'neglect_decline'
        signal = 'avoid'
        implication = 'No support yet'

    else:
        sentiment = 'neutral'
        signal = 'hold'
        implication = 'No clear sentiment'

    logger.info(
        f"Search-price sentiment: {sentiment}, "
        f"signal={signal}, ASVI={asvi:.2f}, "
        f"price_ch={price_change:+.2%}"
    )

    return {
        'sentiment': sentiment,
        'signal': signal,
        'implication': implication,
        'asvi': asvi,
        'price_change': price_change
    }
```

### Regla 6 — Attention Overspill

Monitorizar búsquedas de sectores para predecir movimientos en activos.

```python
def sector_overspill_attention(
    self,
    sector_keywords: List[str],
    tickers_in_sector: List[str]
) -> dict:
    """
    Detectar atención spillover de sector a activos.

    Da: Sector attention → movimiento en activos individuales.
    """
    # ASVI de keywords de sector
    sector_asvi = []

    for keyword in sector_keywords:
        asvi = self.calculate_asvi(keyword, window=4)['current']
        sector_asvi.append(asvi)

    avg_sector_asvi = np.mean(sector_asvi)

    # Si atención del sector es alta
    if avg_sector_asvi > 2.0:
        # Buscar activos con baja atención individual
        opportunities = []

        for ticker in tickers_in_sector:
            ticker_asvi = self.calculate_asvi(ticker, window=4)['current']

            if ticker_asvi < 1.0:  # Baja atención individual
                opportunities.append({
                    'ticker': ticker,
                    'individual_asvi': ticker_asvi,
                    'sector_asvi': avg_sector_asvi,
                    'opportunity': 'sector_attention_overspill'
                })

        logger.info(
            f"Sector overspill: {len(opportunities)} opportunities "
            f"(sector ASVI={avg_sector_asvi:.2f})"
        )

        return {
            'signal': 'sector_momentum',
            'opportunities': opportunities,
            'sector_asvi': avg_sector_asvi
        }

    return {'signal': 'no_opportunity'}
```

### Regla 7 — Threshold Trading

Operar solo cuando volumen de búsqueda excede 1.5 SD.

```python
def attention_threshold_filter(
    self,
    ticker: str,
    min_asvi: float = 1.5
) -> dict:
    """
    Filtro: operar solo con atención significativa.

    Da: Threshold reduce señales falsas.
    """
    asvi_result = self.calculate_asvi(ticker)
    current_asvi = asvi_result['current']

    if abs(current_asvi) >= min_asvi:
        tradeable = True
        signal_strength = abs(current_asvi) / min_asvi

        if current_asvi > 0:
            direction = 'long_bias'
        else:
            direction = 'short_bias'

    else:
        tradeable = False
        signal_strength = 0
        direction = 'neutral'

    logger.info(
        f"Attention threshold: ASVI={current_asvi:.2f}, "
        f"tradeable={tradeable}, strength={signal_strength:.2f}"
    )

    return {
        'tradeable': tradeable,
        'signal_strength': signal_strength,
        'direction': direction,
        'asvi': current_asvi
    }
```

### Regla 8 — Earnings Announcement Lead

Usar incremento de búsquedas previo a resultados como predictor.

```python
def earnings_attention_surge(
    self,
    ticker: str,
    days_to_earnings: int
) -> dict:
    """
    Detectar sorpresa de earnings via búsqueda.

    Da: Búsqueda alta pre-earnings = sorpresa probable.
    """
    if days_to_earnings > 14:
        return {'relevant': False}

    # ASVI reciente vs histórico
    recent_asvi = self.calculate_asvi(ticker, window=2)['current']
    historical_asvi = self.calculate_asvi(ticker, window=8)['current']

    asvi_surge = recent_asvi - historical_asvi

    if asvi_surge > 1.0:
        expectation = 'high_surprise_expected'
        vol_prediction = 'elevated'
        recommendation = 'reduce_exposure'

    elif asvi_surge < -1.0:
        expectation = 'low_interest_expected'
        vol_prediction = 'normal'
        recommendation = 'normal_position'

    else:
        expectation = 'normal'
        vol_prediction = 'baseline'
        recommendation = 'hold'

    logger.info(
        f"Earnings attention: surge={asvi_surge:.2f}, "
        f"expect={expectation}, {recommendation}"
    )

    return {
        'relevant': True,
        'asvi_surge': asvi_surge,
        'expectation': expectation,
        'volatility_prediction': vol_prediction,
        'recommendation': recommendation,
        'days_to_earnings': days_to_earnings
    }
```

### Regla 9 — Market-Wide Attention

Usar búsquedas de "recesión" o "crisis" para reducir apalancamiento.

```python
def market_fear_attention(
    self,
    fear_keywords: List[str] = ['recession', 'crisis', 'crash', 'bear market']
) -> dict:
    """
    Monitorear miedo del mercado vía búsquedas.

    Da: Fear keywords → reducción de apalancamiento global.
    """
    asvi_values = []

    for keyword in fear_keywords:
        asvi = self.calculate_asvi(keyword, window=4)['current']
        asvi_values.append(asvi)

    avg_fear_asvi = np.mean(asvi_values)

    # Umbrales
    if avg_fear_asvi > 2.0:
        fear_level = 'EXTREME'
        leverage_multiplier = 0.5  # Reducir a 50%
        action = 'significantly_reduce_leverage'

    elif avg_fear_asvi > 1.0:
        fear_level = 'ELEVATED'
        leverage_multiplier = 0.75
        action = 'moderately_reduce_leverage'

    elif avg_fear_asvi > 0.5:
        fear_level = 'MODERATE'
        leverage_multiplier = 0.9
        action = 'slightly_reduce_leverage'

    else:
        fear_level = 'NORMAL'
        leverage_multiplier = 1.0
        action = 'maintain_leverage'

    logger.warning(
        f"Market fear attention: {fear_level}, "
        f"ASVI={avg_fear_asvi:.2f}, {action}"
    )

    return {
        'fear_level': fear_level,
        'avg_asvi': avg_fear_asvi,
        'leverage_multiplier': leverage_multiplier,
        'action': action
    }
```

### Regla 10 — News vs Search

Diferenciar entre medios (noticias) y búsqueda (atención real).

```python
def news_vs_search_divergence(
    self,
    ticker: str
) -> dict:
    """
    Divergencia news volume vs search volume.

    Da: Search = retail, News = media. Divergencia = edge.
    """
    # News volume
    news_count = self.get_news_count(ticker, days=7)

    # Search volume (ASVI)
    asvi = self.calculate_asvi(ticker)['current']

    # Normalizar ambos
    news_norm = (news_count - news_count.mean()) / news_count.std()
    search_norm = asvi

    # Divergencia
    divergence = search_norm - news_norm

    if divergence > 1.0:
        signal = 'retail_interest_unreported'
        implication = 'Possible retail momentum'

    elif divergence < -1.0:
        signal = 'media_hype_low_interest'
        implication = 'Possible fade'

    else:
        signal = 'aligned'
        implication = 'No edge from divergence'

    logger.info(
        f"News vs search: News={news_norm:.2f}, "
        f"Search={search_norm:.2f}, Div={divergence:.2f}, "
        f"signal={signal}"
    )

    return {
        'signal': signal,
        'implication': implication,
        'news_normalized': news_norm,
        'search_normalized': search_norm,
        'divergence': divergence
    }
```

### Regla 11 — Lagged Response

Programar delay de ejecución; atención retail tarda 1-3 días en reflejarse.

```python
def attention_lag_adjustment(
    self,
    asvi: float,
    optimal_lag_days: int = 2
) -> dict:
    """
    Ajustar estrategia por lag de atención retail.

    Da: Search → price con lag de 1-3 días.
    """
    if abs(asvi) < 1.0:
        return {'action': 'no_signal'}

    # Planificar trade para futuro
    execution_date = pd.Timestamp.now() + pd.Timedelta(days=optimal_lag_days)

    if asvi > 2.0:
        planned_action = 'enter_position'
        direction = 'opposite_to_attention'  # Contrarian

    elif asvi > 1.0:
        planned_action = 'monitor'
        direction = 'neutral'

    else:
        planned_action = 'no_action'
        direction = None

    logger.info(
        f"Attention lag: ASVI={asvi:.2f}, "
        f"execute_in={optimal_lag_days}d, action={planned_action}"
    )

    return {
        'asvi': asvi,
        'optimal_lag_days': optimal_lag_days,
        'execution_date': execution_date,
        'planned_action': planned_action,
        'direction': direction
    }
```

### Regla 12 — Search Term Selection

Usar solo términos específicos (tickers) para evitar ruido.

```python
def select_search_terms(
    self,
    ticker: str,
    exclude_generic: bool = True
) -> List[str]:
    """
    Seleccionar términos de búsqueda óptimos.

    Da: Ticker específico = mejor señal que genérico.
    """
    # Términos primarios
    primary_terms = [ticker]

    # Términos secundarios (nombre completo)
    company_name = self.get_company_name(ticker)
    secondary_terms = [company_name]

    # Excluir genéricos si se desea
    if exclude_generic:
        # Excluir términos como "stock", "price", etc.
        generic_terms = ['stock', 'price', 'news', 'chart']
    else:
        generic_terms = []

    # Términos de sector (para contexto)
    sector = self.get_company_sector(ticker)
    sector_terms = [sector] if sector else []

    all_terms = primary_terms + secondary_terms + sector_terms
    filtered_terms = [t for t in all_terms if t.lower() not in generic_terms]

    logger.info(
        f"Search terms selected: {len(filtered_terms)} "
        f"for {ticker}"
    )

    return filtered_terms
```

### Regla 13 — Geography Bias

Filtrar búsquedas por regiones relevantes al mercado del activo.

```python
def geographic_search_filter(
    self,
    ticker: str,
    target_countries: List[str] = ['US', 'GB', 'JP']
) -> dict:
    """
    Filtrar búsquedas por geografía relevante.

    Da: Atención local = más relevante que global.
    """
    asvi_by_country = {}

    for country in target_countries:
        # Google Trends por geografía
        asvi = self.get_google_trends_by_geo(
            ticker,
            country=country,
            window=4
        )

        asvi_by_country[country] = asvi

    # Promedio ponderado por relevancia
    # (US más relevante para stocks listados en US)
    weights = {'US': 0.6, 'GB': 0.2, 'JP': 0.2}

    weighted_asvi = sum(
        asvi_by_country[c] * weights.get(c, 0)
        for c in target_countries
    )

    logger.info(
        f"Geographic ASVI: {weighted_asvi:.2f} "
        f"(US={asvi_by_country.get('US', 0):.2f})"
    )

    return {
        'weighted_asvi': weighted_asvi,
        'by_country': asvi_by_country,
        'primary_market': max(asvi_by_country, key=asvi_by_country.get)
    }
```

### Regla 14 — Normalization of Search Data

Escalar datos para que sean comparables con volumen de trading.

```python
def normalize_search_to_volume(
    self,
    search_volume: pd.Series,
    trading_volume: pd.Series,
    window: int = 20
) -> dict:
    """
    Normalizar búsqueda vs volumen de trading.

    Da: Search/volume ratio = medida de interés por dólar.
    """
    # Ambos normalizados a z-score
    search_z = (search_volume - search_volume.rolling(window).mean()) / \
               search_volume.rolling(window).std()

    volume_z = (trading_volume - trading_volume.rolling(window).mean()) / \
               trading_volume.rolling(window).std()

    # Ratio
    search_volume_ratio = search_z / (volume_z + 1e-8)

    # Interpretación
    current_ratio = search_volume_ratio.iloc[-1]

    if current_ratio > 1.5:
        signal = 'high_interest_per_dollar'
        implication = 'Retail accumulation'

    elif current_ratio < 0.5:
        signal = 'low_interest_per_dollar'
        implication = 'Institutional activity'

    else:
        signal = 'normal'
        implication = 'Balanced activity'

    logger.info(
        f"Search/volume ratio: {current_ratio:.2f}, "
        f"signal={signal}"
    )

    return {
        'ratio': search_volume_ratio,
        'current': current_ratio,
        'signal': signal,
        'implication': implication,
        'search_z': search_z.iloc[-1],
        'volume_z': volume_z.iloc[-1]
    }
```

### Regla 15 — Attention Decay Modeling

Modelar el decaimiento de atención tras un pico.

```python
def attention_decay_model(
    self,
    ticker: str,
    peak_date: pd.Timestamp,
    current_date: pd.Timestamp
) -> dict:
    """
    Modelar decaimiento de atención post-pico.

    Da: Attention decae exponencialmente.
    """
    days_since_peak = (current_date - peak_date).days

    # ASVI en el pico y actual
    peak_asvi = self.get_historical_asvi(ticker, peak_date)
    current_asvi = self.calculate_asvi(ticker)['current']

    # Modelo de decaimiento exponencial: ASVI(t) = ASVI_0 * exp(-λt)
    # Calcular λ (tasa de decaimiento)
    if peak_asvi > 0 and days_since_peak > 0:
        decay_rate = -np.log(current_asvi / peak_asvi) / days_since_peak

        # Predicción de decaimiento futuro
        future_days = [1, 3, 7, 14]
        predicted_asvi = []

        for d in future_days:
            pred = peak_asvi * np.exp(-decay_rate * d)
            predicted_asvi.append(pred)

    else:
        decay_rate = 0
        predicted_asvi = [current_asvi] * 4

    logger.info(
        f"Attention decay: λ={decay_rate:.3f}, "
        f"current={current_asvi:.2f}, "
        f"predicted 7d={predicted_asvi[2]:.2f}"
    )

    return {
        'decay_rate': decay_rate,
        'days_since_peak': days_since_peak,
        'peak_asvi': peak_asvi,
        'current_asvi': current_asvi,
        'predicted_asvi': dict(zip([1, 3, 7, 14], predicted_asvi)),
        'attention_still_significant': current_asvi > 1.0
    }
```

---

## Aplicación Práctica

### Pipeline Completo Attention-Based Trading

```python
def attention_trading_pipeline(
    self,
    ticker: str,
    current_date: pd.Timestamp = None
) -> dict:
    """
    Pipeline completo usando señales de atención.
    """
    if current_date is None:
        current_date = pd.Timestamp.now()

    # 1. Calcular ASVI
    asvi_result = self.calculate_asvi(ticker)

    # 2. Filtro de threshold
    threshold = self.attention_threshold_filter(ticker)

    if not threshold['tradeable']:
        return {'action': 'NO_SIGNAL', 'reason': 'Attention below threshold'}

    # 3. Sentiment polarity
    price_change = self.get_recent_return(ticker, 5)
    sentiment = self.search_price_sentiment(
        ticker, asvi_result['current'], price_change
    )

    # 4. Market fear context
    market_fear = self.market_fear_attention()

    # 5. Decisión final
    if sentiment['signal'] == 'contrarian_sell':
        base_action = 'REDUCE'

    elif sentiment['signal'] == 'contrarian_buy':
        base_action = 'ACCUMULATE'

    else:
        base_action = 'HOLD'

    # Ajustar por fear del mercado
    if market_fear['fear_level'] == 'EXTREME':
        final_action = f"{base_action}_REDUCED"
        size_multiplier = 0.5
    elif market_fear['fear_level'] == 'ELEVATED':
        final_action = f"{base_action}_MODERATE"
        size_multiplier = 0.75
    else:
        final_action = base_action
        size_multiplier = 1.0

    return {
        'action': final_action,
        'size_multiplier': size_multiplier,
        'asvi': asvi_result['current'],
        'sentiment': sentiment['sentiment'],
        'market_fear': market_fear['fear_level'],
        'confidence': threshold['signal_strength']
    }
```
