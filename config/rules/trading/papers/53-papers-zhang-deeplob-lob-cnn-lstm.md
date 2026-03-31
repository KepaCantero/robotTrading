# 📄 Papers Fundamentales - DeepLOB (Zhang et al., 2019)

## Deep Learning para Limit Order Book - CNN-LSTM Architecture

**Contexto:** High-Frequency Trading y Microstructure (LOB Analysis).

Zhang et al. revolucionaron el HFT al aplicar visión artificial al libro de órdenes, usando CNN para extraer features espaciales y LSTM para secuencias temporales.

---

### Regla 1 — LOB State Matrix (10×40)

El input DEBE ser una matriz de 10 niveles × 40 eventos, no series temporales planas.

```python
def build_lob_matrix(
    self,
    lob_levels: int = 10,
    history_events: int = 40
) -> np.ndarray:
    """
    Construir matriz de estado del LOB.

    Zhang: Matriz (10, 40) = input para CNN.
    """
    # Estructura: [bid_price_10, bid_vol_10, ..., ask_vol_10, ask_price_10]
    # Total: 20 features × 40 events = 800 elementos

    lob_state = np.zeros((lob_levels * 2, history_events))

    for i in range(history_events):
        # Últimos 40 eventos del LOB
        event = self.lob_history[-(i+1)]

        # Bid levels (0-9)
        for level in range(lob_levels):
            lob_state[level * 2, i] = event['bid_prices'][level]
            lob_state[level * 2 + 1, i] = event['bid_volumes'][level]

        # Ask levels (10-19)
        for level in range(lob_levels):
            lob_state[(lob_levels + level) * 2, i] = event['ask_prices'][level]
            lob_state[(lob_levels + level) * 2 + 1, i] = event['ask_volumes'][level]

    logger.info(
        f"LOB matrix: {lob_state.shape} "
        f"({lob_levels*2} features × {history_events} events)"
    )

    return lob_state
```

### Regla 2 — Inception Modules

Usar convoluciones de múltiples tamaños (1×2, 1×3, 1×5) en paralelo para capturar patrones locales.

```python
def inception_module(
    self,
    input_layer,
    filters: List[int] = [32, 64, 32]
):
    """
    Módulo Inception para extraer features multi-escala.

    Zhang: Convoluciones paralelas = patrones locales óptimos.
    """
    from tensorflow.keras.layers import Conv2D, Concatenate

    # Rama 1: Conv 1×2
    branch1 = Conv2D(
        filters[0],
        kernel_size=(1, 2),
        activation='relu',
        padding='same'
    )(input_layer)

    # Rama 2: Conv 1×3
    branch2 = Conv2D(
        filters[1],
        kernel_size=(1, 3),
        activation='relu',
        padding='same'
    )(input_layer)

    # Rama 3: Conv 1×5
    branch3 = Conv2D(
        filters[2],
        kernel_size=(1, 5),
        activation='relu',
        padding='same'
    )(input_layer)

    # Concatenar
    output = Concatenate()([branch1, branch2, branch3])

    logger.info(f"Inception module: {filters} filters, parallel convs")

    return output
```

### Regla 3 — CNN-LSTM Hybrid Architecture

CNN extrae features espaciales del LOB, LSTM modela la secuencia temporal.

```python
def build_deeplob_model(
    self,
    lob_levels: int = 10,
    history_events: int = 40,
    lstm_units: int = 64
):
    """
    Arquitectura CNN-LSTM para LOB.

    Zhang: CNN para espacio, LSTM para tiempo.
    """
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import (
        Input, Reshape, LSTM, Dense, Dropout
    )

    # Input: (batch, 20 features, 40 events)
    input_layer = Input(shape=(lob_levels * 2, history_events, 1))

    # Reshape para CNN: (batch, 20, 40, 1)
    reshaped = Reshape((lob_levels * 2, history_events, 1))(input_layer)

    # Inception modules (extraer features espaciales)
    x = self.inception_module(reshaped, filters=[32, 64, 32])
    x = self.inception_module(x, filters=[64, 128, 64])

    # Reshape para LSTM: (batch, 40, features)
    # Flatten spatial dimension
    from tensorflow.keras.layers import Flatten, Reshape
    x = Flatten()(x)
    x = Reshape((history_events, -1))(x)

    # LSTM (secuencia temporal)
    lstm_out = LSTM(lstm_units, return_sequences=False)(x)

    # Clasificación
    dense = Dense(32, activation='relu')(lstm_out)
    dropout = Dropout(0.3)(dense)
    output = Dense(3, activation='softmax')(dropout)  # Up, Down, Neutral

    model = Model(inputs=input_layer, outputs=output)

    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    logger.info(
        f"DeepLOB model: CNN-Inception × 2, LSTM {lstm_units} units, "
        f"3-class output"
    )

    return model
```

### Regla 4 — Z-Score Normalization (Rolling Window)

Normalizar usando una ventana móvil de eventos, no de tiempo.

```python
def normalize_lob_rolling(
    self,
    lob_matrix: np.ndarray,
    window_events: int = 100
) -> np.ndarray:
    """
    Normalización Z-score basada en eventos pasados.

    Zhang: Ventana de eventos, no tiempo.
    """
    normalized = np.zeros_like(lob_matrix)

    for i in range(lob_matrix.shape[1]):
        # Ventana de eventos pasados
        start_idx = max(0, i - window_events)
        window = lob_matrix[:, start_idx:i+1]

        # Mean y std de la ventana
        mean = window.mean(axis=1, keepdims=True)
        std = window.std(axis=1, keepdims=True) + 1e-8

        # Z-score
        normalized[:, i:i+1] = (lob_matrix[:, i:i+1] - mean) / std

    logger.info(
        f"Rolling normalization: {window_events} events window"
    )

    return normalized
```

### Regla 5 — Logarithmic Price Changes

Convertir precios a cambios de nivel (ticks) para mantener estacionariedad.

```python
def convert_to_tick_changes(
    self,
    lob_prices: np.ndarray
) -> np.ndarray:
    """
    Precios → cambios de nivel (estacionario).

    Zhang: Input estacionario = entrenamiento estable.
    """
    # Diferencia logarítmica
    log_prices = np.log(lob_prices + 1e-8)
    tick_changes = np.diff(log_prices, axis=1)

    # Pad con ceros al inicio
    tick_changes = np.concatenate([
        np.zeros((tick_changes.shape[0], 1)),
        tick_changes
    ], axis=1)

    logger.info(
        f"Tick changes: Shape {tick_changes.shape}, "
        f"Stationary input"
    )

    return tick_changes
```

### Regla 6 — Multi-Horizon Prediction

Predecir simultáneamente a 10, 50 y 100 ticks adelante.

```python
def multi_horizon_prediction(
    self,
    model,
    lob_matrix: np.ndarray
) -> dict:
    """
    Predecir múltiples horizontes temporales.

    Zhang: Corto, medio, largo plazo simultáneo.
    """
    predictions = {}

    for horizon in [10, 50, 100]:
        # Label: movimiento del mid-price en horizon ticks
        future_mid = self.get_future_mid_price(horizon)
        current_mid = self.get_current_mid_price()

        change = future_mid - current_mid

        # Clasificación
        if change > 0:
            label = 2  # Up
        elif change < 0:
            label = 0  # Down
        else:
            label = 1  # Neutral

        # Predicción del modelo
        pred_proba = model.predict(lob_matrix[np.newaxis, ...])[0]
        pred_label = np.argmax(pred_proba)

        predictions[horizon] = {
            'true_label': label,
            'predicted_label': pred_label,
            'confidence': pred_proba[pred_label],
            'probabilities': {
                'down': pred_proba[0],
                'neutral': pred_proba[1],
                'up': pred_proba[2]
            }
        }

    logger.info(
        f"Multi-horizon: {[f'{h}t' for h in predictions.keys()]}"
    )

    return predictions
```

### Regla 7 — Label Smoothing

Aplicar suavizado a las etiquetas para manejar ruido en micro-movimientos.

```python
def label_smoothing(
    self,
    labels: np.ndarray,
    smoothing: float = 0.1
) -> np.ndarray:
    """
    Suavizar etiquetas para manejar ruido.

    Zhang: Micro-movimientos tienen ruido inherente.
    """
    n_classes = 3

    # One-hot encoding con smoothing
    smoothed = np.full(
        (len(labels), n_classes),
        smoothing / n_classes
    )

    for i, label in enumerate(labels):
        smoothed[i, label] = 1.0 - smoothing + smoothing / n_classes

    logger.info(
        f"Label smoothing: {smoothing}, "
        f"Shape {smoothed.shape}"
    )

    return smoothed
```

### Regla 8 — Residual Connections

Conexiones residuales para entrenar redes más profundas.

```python
def residual_block(
    self,
    input_layer,
    filters: int = 64
):
    """
    Bloque residual con skip connection.

    Zhang: ResNet connections = gradient flow estable.
    """
    from tensorflow.keras.layers import Conv2D, Add, Activation

    # Conv 1×1
    x = Conv2D(filters, kernel_size=(1, 1), padding='same')(input_layer)

    # Conv 1×3
    x = Conv2D(filters, kernel_size=(1, 3), padding='same')(x)

    # Skip connection
    skip = Conv2D(filters, kernel_size=(1, 1), padding='same')(input_layer)

    # Add
    output = Add()([x, skip])
    output = Activation('relu')(output)

    return output
```

### Regla 9 — Order Flow Imbalance (OFI)

Incluir el OFI como feature crítica del libro de órdenes.

```python
def calculate_ofi(
    self,
    lob_snapshot: dict
) -> float:
    """
    Order Flow Imbalance = presión de compra/venta.

    Zhang: OFI es predictor clave del movimiento.
    """
    # Top 5 levels
    bid_vols = np.array([
        lob_snapshot['bid_volumes'][i]
        for i in range(5)
    ])
    ask_vols = np.array([
        lob_snapshot['ask_volumes'][i]
        for i in range(5)
    ])

    # OFI = (bid_vol - ask_vol) / (bid_vol + ask_vol)
    total_bid = bid_vols.sum()
    total_ask = ask_vols.sum()

    ofi = (total_bid - total_ask) / (total_bid + total_ask + 1e-8)

    logger.info(f"OFI: {ofi:+.3f} ({'BUY' if ofi > 0 else 'SELL'} pressure)")

    return ofi
```

### Regla 10 — Attention Mechanism

Añadir atención sobre el LSTM para identificar eventos de liquidez clave.

```python
def attention_layer(
    self,
    lstm_output,
    units: int = 64
):
    """
    Capa de atención para eventos importantes.

    Zhang: Attention = interpretabilidad + performance.
    """
    from tensorflow.keras.layers import Dense, Layer

    class Attention(Layer):
        def __init__(self, units):
            super(Attention, self).__init__()
            self.W = Dense(units)
            self.V = Dense(1)

        def call(self, lstm_output):
            # Score
            score = self.V(tf.nn.tanh(self.W(lstm_output)))

            # Weights
            attention_weights = tf.nn.softmax(score, axis=1)

            # Context vector
            context = attention_weights * lstm_output
            context = tf.reduce_sum(context, axis=1)

            return context, attention_weights

    attention, weights = Attention(units)(lstm_output)

    logger.info(f"Attention layer: {units} units")

    return attention, weights
```

### Regla 11 — Inference Latency Optimization

Optimizar para inferencia < 1ms (critical para HFT).

```python
def optimize_inference_latency(
    self,
    model,
    target_latency_ms: float = 1.0
):
    """
    Optimizar modelo para baja latencia.

    Zhang: HFT requiere inferencia < 1ms.
    """
    import time

    # Warm-up
    dummy_input = np.random.randn(1, 20, 40, 1)
    for _ in range(10):
        _ = model.predict(dummy_input, verbose=0)

    # Medir latencia
    n_iterations = 100
    latencies = []

    for _ in range(n_iterations):
        start = time.time()
        _ = model.predict(dummy_input, verbose=0)
        end = time.time()
        latencies.append((end - start) * 1000)  # ms

    avg_latency = np.mean(latencies)
    p99_latency = np.percentile(latencies, 99)

    logger.info(
        f"Latency: Avg={avg_latency:.3f}ms, "
        f"P99={p99_latency:.3f}ms (Target: {target_latency_ms}ms)"
    )

    if avg_latency > target_latency_ms:
        logger.warning(
            f"⚠️ Latency above target. "
            f"Consider model pruning or quantization."
        )

    return {
        'avg_latency_ms': avg_latency,
        'p99_latency_ms': p99_latency,
        'target_met': avg_latency <= target_latency_ms
    }
```

### Regla 12 — Micro-Price Feature

Incluir el precio ajustado por imbalance del volumen.

```python
def calculate_micro_price(
    self,
    lob_snapshot: dict
) -> float:
    """
    Micro-price = mid ajustado por imbalance.

    Zhang: Mejor predictor que mid-price simple.
    """
    bid_price = lob_snapshot['bid_prices'][0]
    ask_price = lob_snapshot['ask_prices'][0]

    mid_price = (bid_price + ask_price) / 2

    # Imbalance
    bid_vol = lob_snapshot['bid_volumes'][0]
    ask_vol = lob_snapshot['ask_volumes'][0]

    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-8)

    # Micro-price = mid + imbalance * spread/2
    half_spread = (ask_price - bid_price) / 2

    micro_price = mid_price + imbalance * half_spread

    logger.info(
        f"Micro-price: {micro_price:.4f} "
        f"(Mid: {mid_price:.4f}, Adj: {imbalance * half_spread:+.4f})"
    )

    return micro_price
```

### Regla 13 — Cross-Asset Learning

Entrenar con múltiples activos similares para mejorar generalización.

```python
def cross_asset_training(
    self,
    assets: List[str],
    model architecture
):
    """
    Entrenar con múltiple assets (ej. futuros del mismo índice).

    Zhang: Transfer learning mejora generalización.
    """
    all_data = []

    for asset in assets:
        # Obtener LOB data
        asset_lob = self.get_lob_history(asset)

        # Normalizar
        asset_lob_norm = self.normalize_lob_rolling(asset_lob)

        all_data.append(asset_lob_norm)

    # Concatenar
    combined_data = np.concatenate(all_data, axis=0)

    # Entrenar
    logger.info(
        f"Cross-asset training: {len(assets)} assets, "
        f"{combined_data.shape[0]} samples"
    )

    return architecture.fit(combined_data)
```

### Regla 14 — Softmax Output

Clasificación tri-modal: Up, Down, Neutral.

```python
def softmax_output(
    self,
    logits: np.ndarray
) -> dict:
    """
    Output softmax = probabilidades de 3 clases.

    Zhang: Up/Down/Neutral maneja indecisión.
    """
    # Softmax
    exp_logits = np.exp(logits - np.max(logits))
    softmax_probs = exp_logits / exp_logits.sum()

    classes = ['DOWN', 'NEUTRAL', 'UP']

    output = {
        'probabilities': dict(zip(classes, softmax_probs)),
        'prediction': classes[np.argmax(softmax_probs)],
        'confidence': softmax_probs.max()
    }

    # Solo operar si confidence > threshold
    if output['confidence'] < 0.6:
        output['action'] = 'HOLD'
    else:
        output['action'] = f"TRADE_{output['prediction']}"

    logger.info(
        f"Softmax: {output['prediction']} "
        f"(conf={output['confidence']:.2%}, action={output['action']})"
    )

    return output
```

### Regla 15 — Data Augmentation

Generar samples sintéticos para mejorar robustez.

```python
def augment_lob_data(
    self,
    lob_matrix: np.ndarray,
    noise_level: float = 0.01
) -> np.ndarray:
    """
    Augment con ruido gaussiano pequeño.

    Zhang: Mejora generalización sin overfitting.
    """
    # Ruido gaussiano
    noise = np.random.normal(
        0,
        noise_level * lob_matrix.std(),
        lob_matrix.shape
    )

    augmented = lob_matrix + noise

    # Clip para mantener rangos válidos
    augmented = np.clip(
        augmented,
        lob_matrix.min(),
        lob_matrix.max()
    )

    logger.info(
        f"Augmentation: Added {noise_level:.1%} noise, "
        f"{augmented.shape} samples"
    )

    return augmented
```

---

## Aplicación Práctica

### Pipeline Completo DeepLOB

```python
def deeplob_trading_pipeline(
    self,
    symbol: str,
    current_lob: dict
) -> dict:
    """
    Pipeline completo de DeepLOB para HFT.
    """
    # 1. Construir matriz LOB
    lob_matrix = self.build_lob_matrix(
        lob_levels=10,
        history_events=40
    )

    # 2. Convertir a tick changes
    tick_changes = self.convert_to_tick_changes(
        lob_matrix[:, :40]  # Solo precios
    )

    # 3. Normalizar
    normalized = self.normalize_lob_rolling(
        tick_changes,
        window_events=100
    )

    # 4. Calcular features adicionales
    ofi = self.calculate_ofi(current_lob)
    micro_price = self.calculate_micro_price(current_lob)

    # 5. Predicción multi-horizonte
    model = self.load_deeplob_model(symbol)
    predictions = self.multi_horizon_prediction(
        model,
        normalized
    )

    # 6. Decisión de trading
    # Solo operar si todos los horizontes coinciden
    signals = [
        p['predicted_label']
        for p in predictions.values()
    ]

    if len(set(signals)) == 1:  # Todos coinciden
        signal = signals[0]

        if signal == 2:  # Up
            action = 'BUY'
            confidence = np.mean([
                p['confidence']
                for p in predictions.values()
            ])
        elif signal == 0:  # Down
            action = 'SELL'
            confidence = np.mean([
                p['confidence']
                for p in predictions.values()
            ])
        else:
            action = 'HOLD'
            confidence = 0.0

    else:
        action = 'HOLD'
        confidence = 0.0

    return {
        'action': action,
        'confidence': confidence,
        'ofi': ofi,
        'micro_price': micro_price,
        'predictions': predictions,
        'latency_ms': self.measure_inference_latency(model)
    }
```
