# 📄 Papers Fundamentales - NLP para Financial News (Lillo et al.)

## Procesamiento de Lenguaje Natural para Ejecución Algorítmica

**Contexto:** Sentiment Analysis y Event-Driven Trading.

Lillo et al. demostraron que el procesamiento de noticias financieras con NLP puede generar alpha, especialmente cuando se combina con microstructure.

---

### Regla 1 — News Sentiment Scoring

Implementar clasificador NLP que asigne score -1 a 1 en milisegundos.

```python
def news_sentiment_classifier(
    self,
    news_text: str,
    model: str = 'finbert'  # Financial BERT
) -> dict:
    """
    Clasificar sentimiento de noticia financiera.

    Lillo: Score -1 (negativo) a 1 (positivo).
    """
    import torch
    from transformers import pipeline

    # Pipeline de sentimiento financiero
    if model == 'finbert':
        classifier = pipeline(
            'sentiment-analysis',
            model='ProsusAI/finbert',
            device=0 if torch.cuda.is_available() else -1
        )

    # Clasificar
    result = classifier(news_text[:512])[0]  # Truncar a 512 tokens

    # Convertir a escala -1 a 1
    label = result['label']
    confidence = result['score']

    if label == 'positive':
        sentiment_score = confidence
    elif label == 'negative':
        sentiment_score = -confidence
    else:  # neutral
        sentiment_score = 0

    logger.info(
        f"News sentiment: {sentiment_score:+.3f} "
        f"(label={label}, conf={confidence:.2%})"
    )

    return {
        'score': sentiment_score,
        'label': label,
        'confidence': confidence,
        'model': model
    }
```

### Regla 2 — Impact Persistence

El impacto de noticia macro dura más que el de noticia corporativa.

```python
def news_impact_duration(
    self,
    news_type: str,  # 'macro', 'corporate', 'sector'
    sentiment_score: float
) -> dict:
    """
    Estimar duración del impacto según tipo de noticia.

    Lillo: Macro > Sector > Corporate en duración.
    """
    # Duraciones base (en minutos)
    base_duration = {
        'macro': 60,
        'sector': 30,
        'corporate': 10
    }

    # Ajustar por magnitud de sentimiento
    magnitude_factor = min(abs(sentiment_score) * 2, 3)  # Max 3x

    # Duración estimada
    estimated_duration = base_duration[news_type] * magnitude_factor

    # Half-life (cuando decae a 50% del impacto)
    half_life = estimated_duration / 2

    logger.info(
        f"News impact: {news_type}, score={sentiment_score:+.2f}, "
        f"duration={estimated_duration:.0f}min, half-life={half_life:.0f}min"
    )

    return {
        'estimated_duration_minutes': estimated_duration,
        'half_life_minutes': half_life,
        'impact_type': news_type,
        'magnitude_factor': magnitude_factor
    }
```

### Regla 3 — Entropy of Information

Medir la "novedad" de la noticia; si es repetitiva, ignorar movimiento.

```python
def calculate_news_entropy(
    self,
    news_text: str,
    recent_news: List[str] = None
) -> dict:
    """
    Calcular entropía de información.

    Lillo: Noticias repetitivas = menor impacto.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from scipy.spatial.distance import cosine

    if recent_news is None:
        recent_news = self.get_recent_news(hours=24)

    # Vectorizar
    all_texts = recent_news + [news_text]
    vectorizer = TfidfVectorizer(max_features=100)

    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Similaridad con noticias recientes
    current_vector = tfidf_matrix[-1]
    similarities = []

    for i in range(len(recent_news)):
        sim = 1 - cosine(current_vector, tfidf_matrix[i])
        similarities.append(sim)

    # Entropía = 1 - max_similaridad
    # Si es similar a noticia previa, entropía baja
    max_similarity = max(similarities) if similarities else 0
    entropy = 1 - max_similarity

    # Threshold
    if entropy < 0.3:
        novel = False
        recommendation = 'ignore_repetitive'

    elif entropy < 0.6:
        novel = True
        recommendation = 'moderate_impact'

    else:
        novel = True
        recommendation = 'high_impact_expected'

    logger.info(
        f"News entropy: {entropy:.2f}, novel={novel}, "
        f"{recommendation}"
    )

    return {
        'entropy': entropy,
        'novel': novel,
        'max_similarity': max_similarity,
        'recommendation': recommendation
    }
```

### Regla 4 — Lead-Lag News Relationship

Identificar si noticia sigue al precio o viceversa.

```python
def news_price_leadership(
    self,
    news_timestamp: pd.Timestamp,
    price_movement: dict,
    window_minutes: int = 5
) -> dict:
    """
    Determinar si noticia lidera o sigue al precio.

    Lillo: Lead-lag = tipo de señal diferente.
    """
    # Retorno de precio en ventana previa
    price_before = self.get_price_at_time(
        news_timestamp - pd.Timedelta(minutes=window_minutes)
    )
    price_at_news = self.get_price_at_time(news_timestamp)

    price_change_before = (price_at_news - price_before) / price_before

    # Clasificar
    if abs(price_change_before) < 0.001:  # < 0.1% movimiento
        relationship = 'independent'
        signal_type = 'pure_news_signal'

    elif price_change_before > 0:
        relationship = 'price_leads'
        signal_type = 'confirmation_or_momentum'

    else:
        relationship = 'price_leads_negative'
        signal_type = 'correction_or_capitulation'

    logger.info(
        f"News-price relationship: {relationship}, "
        f"price_ch={price_change_before:+.2%}, "
        f"signal={signal_type}"
    )

    return {
        'relationship': relationship,
        'signal_type': signal_type,
        'price_change_before': price_change_before,
        'window_minutes': window_minutes
    }
```

### Regla 5 — High-Frequency News Response

Usar órdenes de mercado inmediatas si sentimiento > 0.8 en < 1s.

```python
def breaking_news_execution(
    self,
    news: dict,
    sentiment_threshold: float = 0.8,
    max_delay_seconds: float = 1.0
) -> dict:
    """
    Ejecución de alta frecuencia para noticias urgentes.

    Lillo: < 1s delay = capturar alpha completo.
    """
    sentiment_score = news['sentiment_score']
    urgency = news.get('urgency', 'normal')

    # Criterios para ejecución inmediata
    if abs(sentiment_score) > sentiment_threshold and urgency == 'high':
        immediate_action = True

        if sentiment_score > 0:
            side = 'BUY'
            aggressiveness = 'market_order'
        else:
            side = 'SELL'
            aggressiveness = 'market_order'

    elif abs(sentiment_score) > 0.5 and urgency == 'high':
        immediate_action = True
        aggressiveness = 'limit_aggressive'
        side = 'BUY' if sentiment_score > 0 else 'SELL'

    else:
        immediate_action = False
        aggressiveness = None
        side = None

    if immediate_action:
        # Calcular latencia
        news_age = (pd.Timestamp.now() - news['timestamp']).total_seconds()

        if news_age > max_delay_seconds:
            logger.warning(
                f"⚠️ News too old: {news_age:.2f}s > {max_delay_seconds}s. "
                f"Alpha may be gone."
            )

            execution_decision = 'skip'
        else:
            execution_decision = 'execute_immediately'

    else:
        execution_decision = 'normal_processing'

    logger.info(
        f"Breaking news: {execution_decision}, "
        f"side={side}, sent={sentiment_score:+.2f}"
    )

    return {
        'execution_decision': execution_decision,
        'side': side,
        'aggressiveness': aggressiveness,
        'news_age_seconds': news_age if 'news_age' in locals() else None
    }
```

### Regla 6 — Metadata Extraction

Extraer entidades (CEO, Ticker, Divisa) para dirigir la señal.

```python
def extract_financial_entities(
    self,
    news_text: str
) -> dict:
    """
    Extraer entidades financieras con NER.

    Lillo: Entidades correctas = señal al activo correcto.
    """
    import spacy

    # NLP model con entidades financieras
    nlp = spacy.load('en_core_web_sm')

    doc = nlp(news_text)

    entities = {
        'tickers': [],
        'companies': [],
        'persons': [],
        'currencies': [],
        'sectors': []
    }

    for ent in doc.ents:
        if ent.label_ == 'ORG' and self.is_ticker(ent.text):
            entities['tickers'].append(ent.text.upper())

        elif ent.label_ == 'ORG':
            entities['companies'].append(ent.text)

        elif ent.label_ == 'PERSON':
            entities['persons'].append(ent.text)

        elif ent.label_ == 'MONEY' or ent.label_ == 'CURRENCY':
            entities['currencies'].append(ent.text)

    # Mapear companies a tickers
    for company in entities['companies']:
        ticker = self.company_to_ticker(company)
        if ticker and ticker not in entities['tickers']:
            entities['tickers'].append(ticker)

    # Detectar sector
    entities['sectors'] = list(set([
        self.get_ticker_sector(t) for t in entities['tickers']
    ]))

    logger.info(
        f"Entities extracted: {len(entities['tickers'])} tickers, "
        f"{len(entities['companies'])} companies"
    )

    return entities
```

### Regla 7 — Source Weighting

Ponderar más noticias de terminales premium que redes sociales.

```python
def source_credibility_weight(
    self,
    news_source: str
) -> dict:
    """
    Asignar peso según credibilidad de la fuente.

    Lillo: Bloomberg/Reuters > Twitter/Reddit.
    """
    # Categorías de fuentes
    tier_1 = ['bloomberg', 'reuters', 'wsj', 'ft']  # Premium
    tier_2 = ['cnbc', 'marketwatch', 'yahoo']  # Mainstream finance
    tier_3 = ['twitter', 'reddit', 'seeking alpha']  # Social/crowd

    source_lower = news_source.lower()

    if any(t in source_lower for t in tier_1):
        tier = 1
        weight = 1.0
        reliability = 'high'
        delay_tolerance_seconds = 5

    elif any(t in source_lower for t in tier_2):
        tier = 2
        weight = 0.7
        reliability = 'medium'
        delay_tolerance_seconds = 10

    elif any(t in source_lower for t in tier_3):
        tier = 3
        weight = 0.4
        reliability = 'low'
        delay_tolerance_seconds = 30

    else:
        tier = 4
        weight = 0.2
        reliability = 'unknown'
        delay_tolerance_seconds = 60

    logger.info(
        f"Source weighting: {news_source} → Tier {tier}, "
        f"weight={weight:.1f}, reliability={reliability}"
    )

    return {
        'tier': tier,
        'weight': weight,
        'reliability': reliability,
        'delay_tolerance_seconds': delay_tolerance_seconds
    }
```

### Regla 8 — Event Window Analysis

Definir ventana de 30 minutos post-noticia donde indicadores técnicos quedan suspendidos.

```python
def event_window_mode(
    self,
    news_timestamp: pd.Timestamp,
    current_timestamp: pd.Timestamp,
    window_minutes: int = 30
) -> dict:
    """
    Activar modo de ventana de evento post-noticia.

    Lillo: Suspender indicadores técnicos durante ventana.
    """
    time_diff = (current_timestamp - news_timestamp).total_seconds() / 60

    in_window = time_diff < window_minutes

    if in_window:
        mode = 'event_window_active'

        # Suspender
        suspend_indicators = [
            'rsi',
            'macd',
            'bollinger_bands',
            'momentum'
        ]

        # Mantener activos
        active_indicators = [
            'volume',
            'vwap',
            'order_flow'
        ]

        # Decaying weight
        weight_in_window = 1 - (time_diff / window_minutes)

    else:
        mode = 'normal_trading'
        suspend_indicators = []
        active_indicators = 'all'
        weight_in_window = 0

    logger.info(
        f"Event window: {mode}, "
        f"elapsed={time_diff:.1f}min, weight={weight_in_window:.2f}"
    )

    return {
        'mode': mode,
        'suspend_indicators': suspend_indicators,
        'active_indicators': active_indicators,
        'weight_in_window': weight_in_window,
        'minutes_remaining': max(0, window_minutes - time_diff)
    }
```

### Regla 9 — Volatility Jump Prediction

Usar volumen de noticias por minuto para predecir saltos de volatilidad.

```python
def news_volume_volatility_prediction(
    self,
    news_count_per_minute: int,
    threshold_high: int = 5,
    threshold_extreme: int = 10
) -> dict:
    """
    Predecir salto de vol basado en volumen de noticias.

    Lillo: News clustering → volatilidad inminente.
    """
    if news_count_per_minute >= threshold_extreme:
        regime = 'extreme_news_flow'
        vol_multiplier = 3.0
        action = 'reduce_positions_significantly'
        implied_move_expected = '> 2%'

    elif news_count_per_minute >= threshold_high:
        regime = 'elevated_news_flow'
        vol_multiplier = 1.5
        action = 'widen_stops'
        implied_move_expected = '1-2%'

    else:
        regime = 'normal_news_flow'
        vol_multiplier = 1.0
        action = 'normal_trading'
        implied_move_expected = '< 1%'

    logger.info(
        f"News volume: {news_count_per_minute}/min → {regime}, "
        f"vol×{vol_multiplier:.1f}, {action}"
    )

    return {
        'regime': regime,
        'volatility_multiplier': vol_multiplier,
        'action': action,
        'implied_move_expected': implied_move_expected
    }
```

### Regla 10 — Tone Analysis (Uncertainty vs Certainty)

Analizar uso de palabras de incertidumbre vs certeza en comunicados.

```python
def analyze_tone_certainty(
    self,
    text: str
) -> dict:
    """
    Analizar tono de incertidumbre vs certeza.

    Lillo: Incertidumbre = volatilidad, Certeza = dirección.
    """
    # Listas de palabras clave
    uncertainty_words = [
        'may', 'might', 'could', 'uncertain', 'unclear',
        'potentially', 'possibly', 'risk', 'uncertainty'
    ]

    certainty_words = [
        'will', 'definitely', 'certainly', 'confirmed',
        'announced', 'declared', 'assured', 'guaranteed'
    ]

    # Contar
    words = text.lower().split()
    total_words = len(words)

    uncertainty_count = sum(1 for w in words if w in uncertainty_words)
    certainty_count = sum(1 for w in words if w in certainty_words)

    # Ratios
    uncertainty_ratio = uncertainty_count / max(total_words, 1)
    certainty_ratio = certainty_count / max(total_words, 1)

    # Clasificar
    if uncertainty_ratio > 0.05:  # > 5% palabras de incertidumbre
        tone = 'uncertain'
        implication = 'high_volatility_expected'
        trading_implication = 'reduce_size'

    elif certainty_ratio > 0.05:
        tone = 'certain'
        implication = 'directional_signal'
        trading_implication = 'can_size_aggressively'

    else:
        tone = 'neutral'
        implication = 'no_clear_signal'
        trading_implication = 'normal_sizing'

    logger.info(
        f"Tone analysis: {tone}, "
        f"unc={uncertainty_ratio:.2%}, cer={certainty_ratio:.2%}, "
        f"imp={trading_implication}"
    )

    return {
        'tone': tone,
        'uncertainty_ratio': uncertainty_ratio,
        'certainty_ratio': certainty_ratio,
        'implication': implication,
        'trading_implication': trading_implication
    }
```

### Regla 11 — False News Filtering

Implementar verificación cruzada (mínimo 2 fuentes para alta confianza).

```python
def verify_news_cross_source(
    self,
    news_item: dict,
    min_sources: int = 2,
    time_window_minutes: int = 10
) -> dict:
    """
    Verificar noticia cross-source para evitar fake news.

    Lillo: Confirmación múltiple = señal confiable.
    """
    # Buscar noticias similares en ventana de tiempo
    similar_news = self.search_similar_news(
        keywords=news_item['keywords'],
        timestamp=news_item['timestamp'],
        time_window_minutes=time_window_minutes
    )

    # Contar fuentes únicas
    unique_sources = set(
        n['source'] for n in similar_news
    )

    n_sources = len(unique_sources)

    if n_sources >= min_sources:
        verified = True
        confidence_level = 'high'
        action = 'trade_with_confidence'

    elif n_sources == 1:
        verified = False
        confidence_level = 'low'
        action = 'verify_or_wait'

    else:
        verified = False
        confidence_level = 'unconfirmed'
        action = 'ignore'

    logger.info(
        f"Cross-source verification: {n_sources} sources, "
        f"verified={verified}, {action}"
    )

    return {
        'verified': verified,
        'n_sources': n_sources,
        'unique_sources': list(unique_sources),
        'confidence_level': confidence_level,
        'action': action,
        'similar_news': similar_news
    }
```

### Regla 12 — Market Context Filtering

Noticia positiva en mercado bajista tratarse con cautela.

```python
def market_context_adjustment(
    self,
    news_sentiment: float,
    market_regime: str,  # 'bull', 'bear', 'sideways'
    market_trend_strength: float  # -1 to 1
) -> dict:
    """
    Ajustar señal de noticia por contexto de mercado.

    Lillo: Contexto matters más que la noticia misma.
    """
    if market_regime == 'bear' and news_sentiment > 0:
        # Noticia positiva en bear market = menos efectiva
        adjustment_factor = 0.5
        rationale = 'Positive news less effective in bear market'

    elif market_regime == 'bull' and news_sentiment < 0:
        # Noticia negativa en bull market = menos efectiva
        adjustment_factor = 0.5
        rationale = 'Negative news less effective in bull market'

    elif abs(market_trend_strength) > 0.7:
        # Trend fuerte = noticias tienen menos efecto
        adjustment_factor = 0.7
        rationale = 'Strong trend dominates news impact'

    else:
        adjustment_factor = 1.0
        rationale = 'Normal news effectiveness'

    adjusted_sentiment = news_sentiment * adjustment_factor

    logger.info(
        f"Market context adjustment: {news_sentiment:+.2f} → "
        f"{adjusted_sentiment:+.2f} (factor={adjustment_factor:.1f}), "
        f"{rationale}"
    )

    return {
        'original_sentiment': news_sentiment,
        'adjusted_sentiment': adjusted_sentiment,
        'adjustment_factor': adjustment_factor,
        'rationale': rationale,
        'market_regime': market_regime
    }
```

### Regla 13 — Language Detection

Procesar noticias en idioma original del mercado del activo.

```python
def multilingual_news_processing(
    self,
    news_text: str,
    target_market: str  # 'US', 'JP', 'DE', etc.
) -> dict:
    """
    Detectar idioma y procesar en original.

    Lillo: Traducción pierde matices de sentimiento.
    """
    from langdetect import detect

    detected_lang = detect(news_text)

    # Mapeo de idioma a mercado
    lang_to_market = {
        'en': 'US',
        'ja': 'JP',
        'de': 'DE',
        'fr': 'FR',
        'es': 'ES'
    }

    detected_market = lang_to_market.get(detected_lang, 'OTHER')

    if detected_market == target_market:
        # Procesar en idioma original
        sentiment = self.news_sentiment_classifier(news_text)
        processing_method = 'original_language'

    else:
        # Noticia de mercado extranjero
        sentiment = {'score': 0, 'label': 'foreign', 'confidence': 0}
        processing_method = 'foreign_market_ignore'
        # Opcional: traducir y procesar con peso menor

    logger.info(
        f"Multilingual: lang={detected_lang}, "
        f"market={detected_market}, target={target_market}, "
        f"method={processing_method}"
    )

    return {
        'detected_language': detected_lang,
        'detected_market': detected_market,
        'matches_target': detected_market == target_market,
        'processing_method': processing_method,
        'sentiment': sentiment
    }
```

### Regla 14 — Topic Modeling

Agrupar noticias por temas y aplicar reglas diferenciadas.

```python
def news_topic_classification(
    self,
    news_text: str
) -> dict:
    """
    Clasificar noticia por topic con reglas específicas.

    Lillo: Diferentes topics = diferentes impactos.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation

    # Topics financieros comunes
    topic_keywords = {
        'M&A': ['merger', 'acquisition', 'buyout', 'takeover', 'deal'],
        'earnings': ['earnings', 'revenue', 'profit', 'guidance', 'beat', 'miss'],
        'dividend': ['dividend', 'payout', 'yield', 'distribution'],
        'litigation': ['lawsuit', 'legal', 'settlement', 'litigation', 'charges'],
        'regulation': ['regulation', 'sec', 'fined', 'compliance', 'approval'],
        'management': ['ceo', 'executive', 'appointed', 'resigned', 'board'],
        'product': ['launch', 'product', 'release', 'innovation', 'patent']
    }

    # Clasificar por keywords
    text_lower = news_text.lower()

    topic_scores = {}
    for topic, keywords in topic_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        topic_scores[topic] = score

    # Topic dominante
    dominant_topic = max(topic_scores, key=topic_scores.get)

    if topic_scores[dominant_topic] == 0:
        dominant_topic = 'general'

    # Reglas específicas por topic
    topic_rules = {
        'M&A': {'vol_multiplier': 2.0, 'drift': 'positive_to_acquirer'},
        'earnings': {'vol_multiplier': 1.5, 'drift': 'post_earnings_drift'},
        'dividend': {'vol_multiplier': 1.2, 'drift': 'income_focus'},
        'litigation': {'vol_multiplier': 1.8, 'drift': 'negative_bias'},
        'regulation': {'vol_multiplier': 1.5, 'drift': 'sector_wide'},
        'management': {'vol_multiplier': 1.3, 'drift': 'sentiment_driven'},
        'product': {'vol_multiplier': 1.2, 'drift': 'growth_story'},
        'general': {'vol_multiplier': 1.0, 'drift': 'neutral'}
    }

    rules = topic_rules.get(dominant_topic, topic_rules['general'])

    logger.info(
        f"Topic: {dominant_topic}, "
        f"vol×{rules['vol_multiplier']}, drift={rules['drift']}"
    )

    return {
        'topic': dominant_topic,
        'topic_scores': topic_scores,
        'vol_multiplier': rules['vol_multiplier'],
        'expected_drift': rules['drift'],
        'rules': rules
    }
```

### Regla 15 — Historical Impact Learning

Almacenar noticias pasadas y testear reacción para ajustar modelo.

```python
def historical_news_impact_learning(
    self,
    news_item: dict,
    lookback_similar: int = 10
) -> dict:
    """
    Aprender de noticias similares históricas.

    Lillo: Historical impact = mejor predicción futura.
    """
    # Buscar noticias similares
    similar_news = self.search_similar_news(
        topic=news_item['topic'],
        sentiment_range=(
            news_item['sentiment'] - 0.2,
            news_item['sentiment'] + 0.2
        ),
        limit=lookback_similar
    )

    if len(similar_news) < 3:
        return {
            'sufficient_data': False,
            'recommendation': 'use_generic_rules'
        }

    # Analizar impacto histórico
    impacts = []

    for past_news in similar_news:
        # Retorno post-noticia (5min, 30min, 1d)
        impact_5m = self.get_post_news_return(
            past_news['timestamp'],
            minutes=5
        )
        impact_30m = self.get_post_news_return(
            past_news['timestamp'],
            minutes=30
        )
        impact_1d = self.get_post_news_return(
            past_news['timestamp'],
            minutes=1440
        )

        impacts.append({
            '5m': impact_5m,
            '30m': impact_30m,
            '1d': impact_1d
        })

    # Estadísticas de impacto
    avg_impact_5m = np.mean([i['5m'] for i in impacts])
    std_impact_5m = np.std([i['5m'] for i in impacts])

    avg_impact_30m = np.mean([i['30m'] for i in impacts])
    std_impact_30m = np.std([i['30m'] for i in impacts])

    # Predicción de impacto
    expected_move_5m = avg_impact_5m * news_item['sentiment']
    expected_move_30m = avg_impact_30m * news_item['sentiment']

    # Confianza basada en consistencia
    consistency = 1 - (std_impact_5m / (abs(avg_impact_5m) + 1e-8))
    confidence = max(0, min(consistency, 1))

    logger.info(
        f"Historical impact: {len(similar_news)} similar news, "
        f"E[5m]={expected_move_5m:+.2%}, conf={confidence:.2%}"
    )

    return {
        'sufficient_data': True,
        'n_similar_news': len(similar_news),
        'expected_impact_5m': expected_move_5m,
        'expected_impact_30m': expected_move_30m,
        'confidence': confidence,
        'historical_impacts': impacts
    }
```

---

## Aplicación Práctica

### Pipeline Completo NLP Trading

```python
def nlp_trading_pipeline(
    self,
    news_item: dict
) -> dict:
    """
    Pipeline completo de trading con NLP de noticias.
    """
    # 1. Extraer entidades
    entities = self.extract_financial_entities(news_item['text'])

    if not entities['tickers']:
        return {'action': 'NO_TARGET', 'reason': 'No tickers identified'}

    primary_ticker = entities['tickers'][0]

    # 2. Sentiment scoring
    sentiment = self.news_sentiment_classifier(news_item['text'])

    # 3. Source weighting
    source_weight = self.source_credibility_weight(news_item['source'])

    # 4. Verificación cross-source
    verification = self.verify_news_cross_source(news_item)

    # 5. Topic classification
    topic = self.news_topic_classification(news_item['text'])

    # 6. Market context adjustment
    market_context = self.market_context_adjustment(
        sentiment['score'] * source_weight['weight'],
        self.get_market_regime(),
        self.get_market_trend()
    )

    # 7. Historical learning
    historical = self.historical_news_impact_learning(news_item)

    # 8. Decisión final
    if not verification['verified']:
        decision = 'WAIT'
        size = 0
        reason = 'Unverified news'

    elif historical['sufficient_data']:
        # Usar impacto histórico
        if abs(historical['expected_impact_5m']) > 0.005:  # > 0.5%
            decision = 'TRADE'
            direction = 'BUY' if historical['expected_impact_5m'] > 0 else 'SELL'
            size = min(abs(market_context['adjusted_sentiment']) * historical['confidence'], 1.0)
            reason = 'historical_edge'
        else:
            decision = 'HOLD'
            size = 0
            reason = 'weak_historical_signal'

    else:
        # Usar reglas genéricas
        if abs(market_context['adjusted_sentiment']) > 0.6:
            decision = 'TRADE'
            direction = 'BUY' if market_context['adjusted_sentiment'] > 0 else 'SELL'
            size = abs(market_context['adjusted_sentiment']) * 0.5
            reason = 'generic_sentiment'
        else:
            decision = 'HOLD'
            size = 0
            reason = 'weak_sentiment'

    return {
        'action': decision,
        'direction': direction if decision == 'TRADE' else None,
        'size': size,
        'ticker': primary_ticker,
        'reason': reason,
        'confidence': historical.get('confidence', sentiment['confidence']),
        'metadata': {
            'sentiment': sentiment['score'],
            'topic': topic['topic'],
            'vol_multiplier': topic['vol_multiplier'],
            'source_weight': source_weight['weight']
        }
    }
```
