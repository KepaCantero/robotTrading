# 📄 Papers Fundamentales - Temporal Fusion Transformers (Lim et al., 2021)

## Transformers para Predicción de Series Temporales Multi-Horizonte

**Contexto:** Deep Learning para Forecasting y Attention Mechanisms.

Lim et al. crearon TFT, una arquitectura que combina lo mejor de Transformers con interpretabilidad para predecir series temporales financieras.

---

### Regla 1 — Multi-Horizon Forecast

Predecir toda la curva de precios futura, no solo el siguiente paso.

```python
def multi_horizon_forecast(
    self,
    model,
    input_data: dict,
    horizons: List[int] = [1, 5, 10, 20]  # Días adelante
) -> dict:
    """
    Predecir múltiples horizontes simultáneamente.

    Lim: Curva completa de predicciones = mejor planificación.
    """
    predictions = {}

    for horizon in horizons:
        # Input encoding para este horizonte
        encoded = self.encode_input(input_data, horizon)

        # Predicción
        pred = model.predict(encoded)

        # Cuantiles (10%, 50%, 90%)
        predictions[horizon] = {
            'p10': pred[0],  # Percentil 10
            'p50': pred[1],  # Mediana
            'p90': pred[2],  # Percentil 90
            'mean': pred.mean()
        }

    logger.info(
        f"Multi-horizon forecast: {horizons} days, "
        f"uncertainty quantiles included"
    )

    return predictions
```

### Regla 2 — Static Covariates Integration

Incluir datos que no cambian (ticker, sector) como inputs estáticos.

```python
def encode_static_covariates(
    self,
    ticker: str,
    sector: str,
    market_cap: float
) -> np.ndarray:
    """
    Codificar variables estáticas del activo.

    Lim: Static covariates = identidad del activo.
    """
    # One-hot encoding para sector
    sectors = ['Technology', 'Finance', 'Healthcare', 'Energy', 'Consumer']
    sector_encoding = [1 if s == sector else 0 for s in sectors]

    # Log market cap (normalizado)
    log_mc = np.log(market_cap) / 30  # Aprox max log cap

    # Ticker embedding (simplificado: hash)
    ticker_embedding = hash(ticker) % 100 / 100

    static_vector = np.array([
        ticker_embedding,
        log_mc
    ] + sector_encoding)

    logger.info(
        f"Static covariates: {ticker}, {sector}, "
        f"vector dim={len(static_vector)}"
    )

    return static_vector
```

### Regla 3 — Variable Selection Networks

Usar capas que seleccionen qué indicadores son relevantes en cada momento.

```python
def variable_selection_network(
    self,
    static_covariates: np.ndarray,
    time_varying: np.ndarray,
    n_features: int
):
    """
    Red que selecciona variables importantes.

    Lim: Gated units = selección automática de features.
    """
    import tensorflow as tf
    from tensorflow.keras.layers import Dense, Layer

    class GatedResidualNetwork(Layer):
        def __init__(self, units):
            super(GatedResidualNetwork, self).__init__()
            self.dense1 = Dense(units, activation='elu')
            self.dense2 = Dense(units, activation='elu')
            self.gate = Dense(units, activation='sigmoid')

        def call(self, x):
            skip = x
            x = self.dense1(x)
            x = self.dense2(x)
            g = self.gate(skip)
            return g * x + (1 - g) * skip

    # Variable selection
    vsn = GatedResidualNetwork(n_features)

    # Aplicar
    selected_features = vsn(time_varying)

    logger.info(
        f"VSN: Input dim={time_varying.shape}, "
        f"Output dim={selected_features.shape}"
    )

    return selected_features
```

### Regla 4 — Gated Residual Units

Implementar puertas estilo LSTM dentro del Transformer.

```python
def gated_residual_unit(
    self,
    x,
    units: int
):
    """
    GRU para filtrar ruido.

    Lim: Gating = interpretabilidad + performance.
    """
    from tensorflow.keras.layers import Dense, Multiply, Add

    # Skip connection
    skip = x

    # Dense layer
    hidden = Dense(units, activation='elu')(x)

    # Gate
    gate = Dense(units, activation='sigmoid')(x)

    # Gated output
    gated = Multiply()([gate, hidden])

    # Residual connection
    output = Add()([gated, skip])

    return output
```

### Regla 5 — Interpretable Attention

Guardar pesos de atención para reportar qué eventos causaron la decisión.

```python
def interpretable_attention(
    self,
    query,
    key,
    value,
    return_weights: bool = True
) -> tuple:
    """
    Attention con pesos interpretables.

    Lim: Attention weights = explicabilidad.
    """
    import tensorflow as tf

    # Score
    scores = tf.matmul(query, key, transpose_b=True)

    # Scale
    dk = tf.cast(tf.shape(key)[-1], tf.float32)
    scores = scores / tf.math.sqrt(dk)

    # Softmax
    attention_weights = tf.nn.softmax(scores, axis=-1)

    # Context
    context = tf.matmul(attention_weights, value)

    if return_weights:
        return context, attention_weights
    return context
```

### Regla 6 — Quantile Loss

Predecir cuantiles (10%, 50%, 90%) para medir incertidumbre.

```python
def quantile_loss(
    self,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    quantile: float
) -> float:
    """
    Quantile loss = Pinball loss.

    Lim: Predecir distribución, no solo punto.
    """
    error = y_true - y_pred

    # Pinball loss
    loss = np.maximum(
        quantile * error,
        (quantile - 1) * error
    ).mean()

    return loss
```

### Regla 7 — Temporal Self-Attention

Identificar patrones estacionales de forma automática.

```python
def temporal_self_attention(
    self,
    input_sequence: np.ndarray,
    n_heads: int = 4
) -> tuple:
    """
    Self-attention temporal para patrones.

    Lim: Auto-detectar estacionalidad.
    """
    import tensorflow as tf
    from tensorflow.keras.layers import MultiHeadAttention

    # Multi-head attention
    mha = MultiHeadAttention(
        num_heads=n_heads,
        key_dim=64
    )

    # Self-attention
    attention_output, attention_weights = mha(
        query=input_sequence,
        key=input_sequence,
        value=input_sequence,
        return_attention_scores=True
    )

    logger.info(
        f"Temporal self-attention: {n_heads} heads, "
        f"output shape={attention_output.shape}"
    )

    return attention_output, attention_weights
```

### Regla 8 — Future Covariates

Incluir datos conocidos del futuro (calendario económico).

```python
def encode_future_covariates(
    self,
    future_dates: pd.DatetimeIndex
) -> np.ndarray:
    """
    Codificar eventos futuros conocidos.

    Lim: Future covariates mejoran forecast.
    """
    features = []

    for date in future_dates:
        # Features de fecha
        features.append([
            date.dayofweek / 7,        # Día de semana
            date.day / 31,             # Día del mes
            date.month / 12,           # Mes
            self.is_earnings_day(date),  # Earnings
            self.is_fomc_day(date),    # FOMC
            self.is_cpi_day(date)      # CPI
        ])

    future_covariates = np.array(features)

    logger.info(
        f"Future covariates: {len(future_dates)} steps, "
        f"{future_covariates.shape[1]} features"
    )

    return future_covariates
```

### Regla 9 — Log-Return Input

Alimentar con retornos logarítmicos normalizados.

```python
def preprocess_log_returns(
    self,
    prices: pd.Series,
    window: int = 252
) -> dict:
    """
    Retornos log normalizados para TFT.

    Lim: Stationary input = stable training.
    """
    # Log returns
    log_returns = np.log(prices / prices.shift(1)).dropna()

    # Normalización rolling
    mean = log_returns.rolling(window).mean()
    std = log_returns.rolling(window).std()

    normalized = (log_returns - mean) / std

    # Clip outliers
    normalized = normalized.clip(-3, 3)

    logger.info(
        f"Log returns: μ={log_returns.mean():.4f}, "
        f"σ={log_returns.std():.4f}, "
        f"normalized shape={normalized.shape}"
    )

    return {
        'log_returns': log_returns,
        'normalized': normalized,
        'mean': mean,
        'std': std
    }
```

### Regla 10 — Dropout en Attention

Aplicar dropout en capas de attention para evitar overfitting.

```python
def attention_with_dropout(
    self,
    query,
    key,
    value,
    dropout_rate: float = 0.1
):
    """
    Attention con dropout regularización.

    Lim: Dropout en attention = previene overfitting.
    """
    import tensorflow as tf
    from tensorflow.keras.layers import Dropout

    # Attention
    context, weights = self.interpretable_attention(
        query, key, value, return_weights=True
    )

    # Dropout en attention weights
    dropped_weights = Dropout(dropout_rate)(weights)

    # Recalcular context con dropped weights
    context = tf.matmul(dropped_weights, value)

    return context, dropped_weights
```

### Regla 11 — Sequence Length

Usar ventana de contexto de al menos 128 periodos.

```python
def prepare_tft_sequence(
    self,
    data: pd.DataFrame,
    context_length: int = 128,
    prediction_length: int = 10
) -> dict:
    """
    Preparar secuencias para TFT.

    Lim: Context largo = captura ciclos completos.
    """
    sequences = []

    for i in range(len(data) - context_length - prediction_length):
        # Context (encoder input)
        context = data.iloc[i:i+context_length]

        # Future (decoder input)
        future = data.iloc[i+context_length:i+context_length+prediction_length]

        sequences.append({
            'context': context.values,
            'future': future.values,
            'target': data.iloc[i+context_length+prediction_length-1]
        })

    logger.info(
        f"TFT sequences: {len(sequences)} samples, "
        f"context={context_length}, pred={prediction_length}"
    )

    return sequences
```

### Regla 12 — Time-Based Embeddings

Añadir minuto del día y día de semana como features cíclicas.

```python
def cyclic_time_encoding(
    self,
    timestamps: pd.DatetimeIndex
) -> np.ndarray:
    """
    Encoding cíclico de tiempo (seno/coseno).

    Lim: Tiempo cíclico = preserva continuidad.
    """
    features = []

    for ts in timestamps:
        # Hora del día (para intraday)
        hour_sin = np.sin(2 * np.pi * ts.hour / 24)
        hour_cos = np.cos(2 * np.pi * ts.hour / 24)

        # Día de semana
    dow_sin = np.sin(2 * np.pi * ts.dayofweek / 7)
        dow_cos = np.cos(2 * np.pi * ts.dayofweek / 7)

        # Mes del año
        month_sin = np.sin(2 * np.pi * ts.month / 12)
        month_cos = np.cos(2 * np.pi * ts.month / 12)

        features.append([
            hour_sin, hour_cos,
            dow_sin, dow_cos,
            month_sin, month_cos
        ])

    return np.array(features)
```

### Regla 13 — Encoder-Decoder Structure

Usar encoder para histórico y decoder para proyección.

```python
def tft_encoder_decoder(
    self,
    context: np.ndarray,
    future_covariates: np.ndarray,
    d_model: int = 64
) -> dict:
    """
    Arquitectura Encoder-Decoder TFT.

    Lim: Encoder histórico, Decoder proyección.
    """
    # Encoder (procesa contexto)
    encoder_output = self.process_encoder_context(
        context, d_model=d_model
    )

    # Decoder (procesa future + attention)
    decoder_output = self.process_decoder_future(
        encoder_output,
        future_covariates,
        d_model=d_model
    )

    logger.info(
        f"TFT Encoder-Decoder: context={context.shape}, "
        f"future={future_covariates.shape}, "
        f"d_model={d_model}"
    )

    return {
        'encoder_output': encoder_output,
        'decoder_output': decoder_output
    }
```

### Regla 14 — Step-Wise Training

Entrenar para minimizar error acumulado en todos los horizontes.

```python
def stepwise_loss(
    self,
    y_true: np.ndarray,
    y_pred_all_horizons: dict,
    horizons: List[int]
) -> float:
    """
    Loss ponderado por horizonte.

    Lim: Optimizar todos los horizontes simultáneamente.
    """
    total_loss = 0

    for horizon in horizons:
        y_pred_h = y_pred_all_horizons[horizon]

        # Quantile loss para este horizonte
        loss_p10 = self.quantile_loss(y_true, y_pred_h['p10'], 0.1)
        loss_p50 = self.quantile_loss(y_true, y_pred_h['p50'], 0.5)
        loss_p90 = self.quantile_loss(y_true, y_pred_h['p90'], 0.9)

        # Promedio de quantiles
        horizon_loss = (loss_p10 + loss_p50 + loss_p90) / 3

        # Ponderar por horizonte (más peso a corto plazo)
        weight = 1 / horizon

        total_loss += weight * horizon_loss

    return total_loss
```

### Regla 15 — Attention Visualization

Generar mapas de calor para interpretabilidad.

```python
def visualize_attention_weights(
    self,
    attention_weights: np.ndarray,
    timestamps: pd.DatetimeIndex,
    top_k: int = 5
) -> dict:
    """
    Visualizar qué eventos pasados influyeron más.

    Lim: Attention plots = explicabilidad.
    """
    # Promediar attention weights across heads
    avg_attention = attention_weights.mean(axis=0)

    # Top-K timestamps con mayor attention
    top_indices = avg_attention.argsort()[-top_k:][::-1]

    top_events = []
    for idx in top_indices:
        top_events.append({
            'timestamp': timestamps[idx],
            'weight': avg_attention[idx],
            'date': timestamps[idx].strftime('%Y-%m-%d')
        })

    logger.info(
        f"Top-{top_k} attention events: "
        f"{[e['date'] for e in top_events]}"
    )

    return {
        'top_events': top_events,
        'attention_weights': avg_attention,
        'heatmap_data': {
            'x': timestamps.strftime('%Y-%m-%d').tolist(),
            'y': avg_attention.tolist()
        }
    }
```

---

## Aplicación Práctica

### Pipeline Completo TFT

```python
def tft_forecasting_pipeline(
    self,
    historical_data: pd.DataFrame,
    ticker: str,
    sector: str,
    forecast_horizons: List[int]
) -> dict:
    """
    Pipeline completo TFT para forecasting.
    """
    # 1. Preprocesar log-returns
    log_ret = self.preprocess_log_returns(
        historical_data['close'],
        window=252
    )

    # 2. Static covariates
    static = self.encode_static_covariates(
        ticker=ticker,
        sector=sector,
        market_cap=self.get_market_cap(ticker)
    )

    # 3. Time encoding
    time_encoding = self.cyclic_time_encoding(
        historical_data.index
    )

    # 4. Preparar secuencias
    sequences = self.prepare_tft_sequence(
        historical_data,
        context_length=128,
        prediction_length=max(forecast_horizons)
    )

    # 5. Future covariates
    future_dates = pd.date_range(
        start=historical_data.index[-1],
        periods=max(forecast_horizons)+1,
        freq='B'
    )[1:]

    future_cov = self.encode_future_covariates(future_dates)

    # 6. Multi-horizon forecast
    model = self.load_tft_model(ticker)
    predictions = self.multi_horizon_forecast(
        model,
        {
            'context': sequences[-1]['context'],
            'static': static,
            'future_cov': future_cov
        },
        horizons=forecast_horizons
    )

    # 7. Extraer attention weights
    _, attention_weights = model.predict_with_attention(
        sequences[-1]['context']
    )

    # 8. Visualizar attention
    attention_viz = self.visualize_attention_weights(
        attention_weights,
        historical_data.index[-128:],
        top_k=5
    )

    return {
        'predictions': predictions,
        'attention_events': attention_viz['top_events'],
        'model_confidence': {
            h: p['p90'] - p['p10']  # Spred = incertidumbre
            for h, p in predictions.items()
        }
    }
```
