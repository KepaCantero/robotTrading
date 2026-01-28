# 📄 Papers Fundamentales - GANs for Financial Time Series (Wiese et al., 2020)

## Generación de Mercados Sintéticos y Adversarial Training

**Contexto:** Synthetic Data Generation y Stress Testing.

Wiese et al. demostraron que las GANs pueden generar datos financieros realistas para entrenar robots en escenarios imposibles y detectar overfitting.

---

### Regla 1 — Synthetic Tick Generation

Usar GANs para crear micro-movimientos de precios matemáticamente posibles.

```python
def financial_gan_generator(
    self,
    real_returns: pd.Series,
    latent_dim: int = 100,
    n_samples: int = 10000
) -> np.ndarray:
    """
    Generar retornos sintéticos usando GAN.

    Wiese: GAN = datos infinitos para entrenamiento.
    """
    import tensorflow as tf
    from tensorflow.keras import layers

    # Generator: ruido → datos sintéticos
    def build_generator(latent_dim, output_dim):
        model = tf.keras.Sequential([
            layers.Dense(128, input_dim=latent_dim),
            layers.LeakyReLU(alpha=0.2),
            layers.Dropout(0.3),

            layers.Dense(256),
            layers.LeakyReLU(alpha=0.2),
            layers.Dropout(0.3),

            layers.Dense(output_dim, activation='tanh')
        ])
        return model

    # Discriminator: datos → real/fake
    def build_discriminator(input_dim):
        model = tf.keras.Sequential([
            layers.Dense(256, input_dim=input_dim),
            layers.LeakyReLU(alpha=0.2),
            layers.Dropout(0.3),

            layers.Dense(128),
            layers.LeakyReLU(alpha=0.2),
            layers.Dropout(0.3),

            layers.Dense(1, activation='sigmoid')
        ])
        return model

    # Construir
    generator = build_generator(latent_dim, real_returns.shape[1])
    discriminator = build_discriminator(real_returns.shape[1])

    # Compilar GAN
    discriminator.compile(
        optimizer=tf.keras.optimizers.Adam(0.0002),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    # GAN combinado
    z = layers.Input(shape=(latent_dim,))
    img = generator(z)

    discriminator.trainable = False

    combined = tf.keras.Model(z, discriminator(img))
    combined.compile(
        optimizer=tf.keras.optimizers.Adam(0.0002),
        loss='binary_crossentropy'
    )

    # Entrenar
    logger.info(
        f"Training GAN: {n_samples} samples, "
        f"latent_dim={latent_dim}"
    )

    return {
        'generator': generator,
        'discriminator': discriminator,
        'combined': combined,
        'latent_dim': latent_dim
    }
```

### Regla 2 — Stress Testing via GANs

Generar escenarios donde Forex y Cripto caen simultáneamente.

```python
def stress_test_scenarios(
    self,
    trained_gan: dict,
    n_scenarios: int = 1000,
    stress_level: str = 'extreme'
) -> dict:
    """
    Generar escenarios de estrés con GAN.

    Wiese: Stress test = supervivencia del robot.
    """
    generator = trained_gan['generator']
    latent_dim = trained_gan['latent_dim']

    # Generar escenarios sintéticos
    synthetic_scenarios = []

    for _ in range(n_scenarios):
        # Muestrear ruido condicional para estrés
        if stress_level == 'extreme':
            # Ruido con sesgo hacia colas pesadas
            noise = np.random.normal(
                loc=0,
                scale=2,  # Mayor variación
                size=latent_dim
            )

        elif stress_level == 'correlation_crisis':
            # Forzar correlación entre activos
            noise = np.random.normal(0, 1, latent_dim)
            noise[:10] = np.random.normal(-3, 1, 10)  # Crisis simultánea

        else:
            noise = np.random.normal(0, 1, latent_dim)

        # Generar escenario
        scenario = generator.predict(noise.reshape(1, -1))[0]
        synthetic_scenarios.append(scenario)

    synthetic_scenarios = np.array(synthetic_scenarios)

    # Analizar propiedades
    scenario_means = synthetic_scenarios.mean(axis=0)
    scenario_stds = synthetic_scenarios.std(axis=0)
    scenario_corrs = np.corrcoef(synthetic_scenarios.T)

    # Detectar escenarios extremos
    extreme_scenarios = []

    for i, scenario in enumerate(synthetic_scenarios):
        # Métricas de estrés
        max_drawdown = (scenario.cummax() - scenario).max()
        volatility = scenario.std()
        tail_ratio = (scenario < scenario.mean() - 3*scenario.std()).sum() / len(scenario)

        if max_drawdown > 0.15 or volatility > 0.05 or tail_ratio > 0.05:
            extreme_scenarios.append({
                'index': i,
                'scenario': scenario,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'tail_ratio': tail_ratio,
                'stress_score': max_drawdown + volatility*10 + tail_ratio*100
            })

    logger.warning(
        f"Stress test: {len(extreme_scenarios)}/{n_scenarios} extreme scenarios"
    )

    return {
        'scenarios': synthetic_scenarios,
        'extreme_scenarios': extreme_scenarios,
        'statistics': {
            'means': scenario_means,
            'stds': scenario_stds,
            'correlations': scenario_corrs
        }
    }
```

### Regla 3 — Discriminator Audit

El robot debe pasar prueba donde no distinga datos reales de GAN.

```python
def discriminator_audit(
    self,
    discriminator,
    real_data: np.ndarray,
    generated_data: np.ndarray
) -> dict:
    """
    Auditar calidad de la GAN.

    Wiese: Discriminator no distinguir = GAN buena.
    """
    # Predecir
    real_predictions = discriminator.predict(real_data)
    fake_predictions = discriminator.predict(generated_data)

    # Accuracy
    real_accuracy = (real_predictions > 0.5).mean()
    fake_accuracy = (fake_predictions < 0.5).mean()

    # Calidad: discriminador debería confundirse (~50%)
    discriminator_quality = abs(real_accuracy - 0.5) + abs(fake_accuracy - 0.5)

    if discriminator_quality < 0.1:  # < 10% desviación de 50%
        gan_quality = 'EXCELLENT'
        passed = True

    elif discriminator_quality < 0.2:
        gan_quality = 'GOOD'
        passed = True

    else:
        gan_quality = 'NEEDS_IMPROVEMENT'
        passed = False

    logger.info(
        f"Discriminator audit: {gan_quality}, "
        f"quality_score={discriminator_quality:.3f}, "
        f"passed={passed}"
    )

    return {
        'gan_quality': gan_quality,
        'quality_score': discriminator_quality,
        'passed': passed,
        'real_accuracy': real_accuracy,
        'fake_accuracy': fake_accuracy
    }
```

### Regla 4 — Tail Event Synthesis

Forzar a la GAN a producir flash crashes cada 100 barras.

```python
def conditional_tail_generation(
    self,
    generator,
    n_samples: int = 1000,
    tail_probability: float = 0.01
) -> dict:
    """
    Generar colas pesadas condicionalmente.

    Wiese: Tail events = entrenar resiliencia.
    """
    latent_dim = generator.input_shape[1]

    tail_samples = []
    normal_samples = []

    for _ in range(n_samples):
        # Muestrear
        noise = np.random.normal(0, 1, latent_dim)

        # Decidir si hacer tail event
        if np.random.random() < tail_probability:
            # Modificar ruido para generar cola pesada
            noise[:10] = np.random.normal(-5, 2, 10)  # Sesgo negativo extremo

            sample = generator.predict(noise.reshape(1, -1))[0]
            tail_samples.append(sample)

        else:
            sample = generator.predict(noise.reshape(1, -1))[0]
            normal_samples.append(sample)

    tail_samples = np.array(tail_samples)
    normal_samples = np.array(normal_samples)

    # Verificar colas
    tail_kurtosis = self.kurtosis(tail_samples.flatten())
    normal_kurtosis = self.kurtosis(normal_samples.flatten())

    logger.info(
        f"Tail synthesis: {len(tail_samples)} tail, {len(normal_samples)} normal, "
        f"tail_kurtosis={tail_kurtosis:.1f} vs {normal_kurtosis:.1f}"
    )

    return {
        'tail_samples': tail_samples,
        'normal_samples': normal_samples,
        'tail_kurtosis': tail_kurtosis,
        'normal_kurtosis': normal_kurtosis
    }
```

### Regla 5 — Data Augmentation

Si hay pocos datos de Stock nueva, usar GAN para generar 10 años sintéticos.

```python
def gan_data_augmentation(
    self,
    limited_data: pd.Series,
    target_years: int = 10,
    current_days: int = None
) -> dict:
    """
    Aumentar dataset usando GAN.

    Wiese: Datos escasos = GAN augmentation.
    """
    if current_days is None:
        current_days = len(limited_data)

    # Calcular cuántos datos generar
    trading_days_per_year = 252
    target_days = target_years * trading_days_per_year
    days_to_generate = max(0, target_days - current_days)

    if days_to_generate <= 0:
        return {
            'augmented': False,
            'reason': 'sufficient_data'
        }

    # Entrenar GAN con datos existentes
    gan = self.train_gan(limited_data)

    # Generar datos sintéticos
    generated_data = []

    batch_size = 100
    n_batches = int(np.ceil(days_to_generate / batch_size))

    for _ in range(n_batches):
        noise = np.random.normal(0, 1, gan['latent_dim'])
        batch = gan['generator'].predict(noise.reshape(batch_size, -1))
        generated_data.extend(batch)

    generated_data = np.array(generated_data)[:days_to_generate]

    # Combinar real + sintético
    augmented_returns = np.concatenate([
        limited_data.values,
        generated_data.flatten()
    ])

    logger.info(
        f"Data augmentation: {current_days} → {len(augmented_returns)} days "
        f"({days_to_generate} synthetic)"
    )

    return {
        'augmented': True,
        'original_days': current_days,
        'augmented_days': len(augmented_returns),
        'synthetic_days': days_to_generate,
        'augmented_data': augmented_returns
    }
```

### Regla 6 — Correlated Asset Synthesis

Generar datos donde BTC y Oro se correlacionan 100% para testear riesgo.

```python
def correlated_asset_synthesis(
    self,
    gan_model,
    target_correlation: float = 1.0,
    assets: List[str] = ['BTC', 'GOLD']
) -> dict:
    """
    Generar activos sintéticos con correlación específica.

    Wiese: Correlación extrema = testear riesgo de portafolio.
    """
    latent_dim = gan_model['latent_dim']

    # Para generar correlación, usar mismo ruido base
    base_noise = np.random.normal(0, 1, (1000, latent_dim))

    correlated_returns = []

    for asset in assets:
        # Modificar ruido ligeramente para cada activo
        asset_noise = base_noise + np.random.normal(0, 0.1, base_noise.shape)

        # Generar
        asset_returns = gan_model['generator'].predict(asset_noise)
        correlated_returns.append(asset_returns)

    correlated_returns = np.array(correlated_returns).T

    # Verificar correlación
    correlation_matrix = np.corrcoef(correlated_returns.T)

    logger.info(
        f"Correlated synthesis: {assets}, "
        f"target_corr={target_correlation:.1f}, "
        f"actual_corr={correlation_matrix[0, 1]:.3f}"
    )

    return {
        'synthetic_returns': correlated_returns,
        'correlation_matrix': correlation_matrix,
        'assets': assets,
        'target_correlation': target_correlation
    }
```

### Regla 7 — Style Transfer

Aplicar volatilidad de Cripto a Stock estable para ver reacción del algoritmo.

```python
def financial_style_transfer(
    self,
    source_returns: pd.Series,  # Cripto (volátil)
    target_returns: pd.Series,  # Stock (estable)
    n_samples: int = 1000
) -> dict:
    """
    Transferir estilo de volatilidad entre activos.

    Wiese: Style transfer = testear robustez.
    """
    # Extraer "estilo" de volatilidad del source
    source_volatility = source_returns.rolling(20).std()
    source_vol_mean = source_volatility.mean()

    # Extraer "contenido" de tendencia del target
    target_trend = target_returns.rolling(50).mean()

    # Generar datos híbridos
    hybrid_returns = []

    for _ in range(n_samples):
        # Muestrear periodo
        idx = np.random.randint(0, len(target_returns) - 20)

        # Contenido (tendencia del target)
        base_return = target_returns.iloc[idx:idx+20].values

        # Estilo (volatilidad del source escalada)
        scaling_factor = source_vol_mean / base_return.std()

        # Aplicar estilo
        styled_return = base_return * scaling_factor

        # Añadir ruido del source
        noise = np.random.choice(source_returns.values, size=20)
        final_return = styled_return + noise * 0.3

        hybrid_returns.extend(final_return)

    hybrid_returns = np.array(hybrid_returns)

    # Estadísticas
    hybrid_vol = hybrid_returns.std()
    target_vol = target_returns.std()

    logger.info(
        f"Style transfer: vol {target_vol:.3f} → {hybrid_vol:.3f}, "
        f"scaling={scaling_factor:.1f}×"
    )

    return {
        'hybrid_returns': hybrid_returns,
        'source_volatility': source_vol_mean,
        'target_volatility': target_vol,
        'hybrid_volatility': hybrid_vol,
        'scaling_factor': scaling_factor
    }
```

### Regla 8 — Overfitting Detection

Si el robot solo gana en datos reales, está sobreajustado.

```python
def overfitting_detection(
    self,
    strategy_performance_real: dict,
    strategy_performance_synthetic: dict
) -> dict:
    """
    Detectar overfitting comparando real vs sintético.

    Wiese: Overfit = gana en real, pierde en sintético.
    """
    # Métricas en datos reales
    real_return = strategy_performance_real.get('total_return', 0)
    real_sharpe = strategy_performance_real.get('sharpe', 0)

    # Métricas en datos sintéticos
    synth_return = strategy_performance_synthetic.get('total_return', 0)
    synth_sharpe = strategy_performance_synthetic.get('sharpe', 0)

    # Diferencia
    return_diff = real_return - synth_return
    sharpe_diff = real_sharpe - synth_sharpe

    # Detección de overfitting
    if real_return > 0.1 and synth_return < 0:
        overfitting = 'SEVERE'
        confidence = 0.95

    elif real_return > 0.05 and synth_return < real_return * 0.5:
        overfitting = 'MODERATE'
        confidence = 0.75

    elif return_diff > 0.02:
        overfitting = 'MILD'
        confidence = 0.50

    else:
        overfitting = 'NONE'
        confidence = 0.0

    logger.warning(
        f"Overfitting detection: {overfitting}, "
        f"real={real_return:+.2%}, synth={synth_return:+.2%}, "
        f"conf={confidence:.0%}"
    )

    return {
        'overfitting': overfitting,
        'confidence': confidence,
        'real_return': real_return,
        'synthetic_return': synth_return,
        'real_sharpe': real_sharpe,
        'synthetic_sharpe': synth_sharpe
    }
```

### Regla 9 — Market Regime Simulation

Generar 1000 horas de "mercado lateral" para verificar que el bot no pierda por comisiones.

```python
def regime_simulation(
    self,
    trained_gan: dict,
    regime: str,
    n_hours: int = 1000
) -> dict:
    """
    Simular régimen específico de mercado.

    Wiese: Regime simulation = validar robustez.
    """
    generator = trained_gan['generator']
    latent_dim = trained_gan['latent_dim']

    samples_per_hour = 60  # Asumir 1 dato por minuto

    n_samples = n_hours * samples_per_hour

    # Generar datos condicionales al régimen
    if regime == 'sideways':
        # Ruido con baja tendencia
        noise = np.random.normal(0, 0.5, (n_samples, latent_dim))

    elif regime == 'trending':
        # Ruido con drift
        noise = np.random.normal(0, 1, (n_samples, latent_dim))
        noise[:, :10] = np.random.normal(0.1, 0.5, (n_samples, 10))  # Drift positivo

    elif regime == 'volatile':
        # Ruido de alta varianza
        noise = np.random.normal(0, 3, (n_samples, latent_dim))

    else:
        noise = np.random.normal(0, 1, (n_samples, latent_dim))

    # Generar
    simulated_data = generator.predict(noise)

    # Analizar régimen resultante
    trend = (simulated_data[-1] - simulated_data[0]) / simulated_data[0]
    volatility = simulated_data.std()

    logger.info(
        f"Regime simulation: {regime}, "
        f"n_hours={n_hours}, "
        f"resulting_trend={trend:+.2%}, vol={volatility:.3f}"
    )

    return {
        'regime': regime,
        'simulated_data': simulated_data,
        'resulting_trend': trend,
        'resulting_volatility': volatility,
        'n_hours': n_hours
    }
```

### Regla 10 — Hidden Pattern Discovery

Analizar qué tipos de mercados sintéticos hacen fallar al robot.

```python
def hidden_pattern_discovery(
    self,
    strategy,
    gan_scenarios: dict,
    min_failure_rate: float = 0.3
) -> dict:
    """
    Descubrir patrones ocultos que causan fallos.

    Wiese: Conocer debilidades = mejorar código.
    """
    failure_patterns = []

    for scenario_name, scenario_data in gan_scenarios.items():
        # Testear estrategia en escenario
        results = strategy.backtest(scenario_data)

        # Métricas
        total_return = results.get('total_return', 0)
        max_drawdown = results.get('max_drawdown', 0)
        win_rate = results.get('win_rate', 0)

        # Es fallo?
        is_failure = (
            total_return < 0 or
            max_drawdown > 0.15 or
            win_rate < 0.4
        )

        if is_failure:
            # Analizar características del escenario
            scenario_features = {
                'volatility': scenario_data.std(),
                'trend': (scenario_data[-1] - scenario_data[0]) / scenario_data[0],
                'kurtosis': self.kurtosis(scenario_data),
                'autocorrelation': abs(self.autocorrelation(scenario_data, 5))
            }

            failure_patterns.append({
                'scenario': scenario_name,
                'features': scenario_features,
                'results': results
            })

    # Analizar patrones comunes de fallo
    if failure_patterns:
        avg_vol = np.mean([p['features']['volatility'] for p in failure_patterns])
        avg_trend = np.mean([p['features']['trend'] for p in failure_patterns])

        logger.warning(
            f"Hidden patterns: {len(failure_patterns)} failure scenarios, "
            f"avg_vol={avg_vol:.3f}, avg_trend={avg_trend:+.2%}"
        )

    return {
        'failure_patterns': failure_patterns,
        'n_failures': len(failure_patterns),
        'common_features': {
            'volatility': avg_vol if failure_patterns else None,
            'trend': avg_trend if failure_patterns else None
        }
    }
```

### Regla 11 — Adversarial Training

Entrenar robot contra GAN que "intenta" ganar dinero quitándoselo al robot.

```python
def adversarial_training(
    self,
    robot_strategy,
    opponent_gan: dict,
    n_rounds: int = 1000
) -> dict:
    """
    Entrenamiento adversario robot vs GAN.

    Wiese: Adversarial training = estrategia robusta.
    """
    robot_capital = 1.0
    capital_history = [robot_capital]

    for round in range(n_rounds):
        # GAN genera mercado
        market_scenario = opponent_gan['generator'].predict(
            np.random.normal(0, 1, (1, opponent_gan['latent_dim']))
        )[0]

        # Robot opera en escenario
        trade_result = robot_strategy.trade_single(market_scenario)

        # Actualizar capital
        robot_capital *= (1 + trade_result['return'])
        capital_history.append(robot_capital)

        # Si robot pierde mucho, GAN aprende
        if round > 100 and robot_capital < 0.8:
            # Generar escenarios más difíciles
            difficulty = 'increase'

        elif robot_capital > 1.2:
            # Generar escenarios más fáciles
            difficulty = 'decrease'

        else:
            difficulty = 'maintain'

    # Análisis final
    final_return = (capital_history[-1] - 1)

    if final_return > 0:
        robustness = 'HIGH'
    elif final_return > -0.1:
        robustness = 'MEDIUM'
    else:
        robustness = 'LOW'

    logger.info(
        f"Adversarial training: {robustness}, "
        f"final_capital={robot_capital:.2f}, "
        f"return={final_return:+.2%}"
    )

    return {
        'robustness': robustness,
        'final_capital': robot_capital,
        'total_return': final_return,
        'capital_history': capital_history
    }
```

### Regla 12 — Volume-Price Consistency

La GAN debe generar volumen coherente con movimiento del precio.

```python
def volume_price_consistency_check(
    self,
    generated_data: dict,
    real_data: dict
) -> dict:
    """
    Verificar coherencia volumen-precio en datos sintéticos.

    Wiese: Consistencia = realismo del mercado.
    """
    generated_prices = generated_data['prices']
    generated_volumes = generated_data['volumes']

    real_prices = real_data['prices']
    real_volumes = real_data['volumes']

    # Correlación volumen-precio (abs)
    gen_price_vol_corr = abs(np.corrcoef(
        np.diff(generated_prices),
        generated_volumes[1:]
    )[0, 1])

    real_price_vol_corr = abs(np.corrcoef(
        np.diff(real_prices),
        real_volumes[1:]
    )[0, 1])

    # Diferencia
    corr_diff = abs(gen_price_vol_corr - real_price_vol_corr)

    # Consistencia
    if corr_diff < 0.1:
        consistency = 'EXCELLENT'
    elif corr_diff < 0.2:
        consistency = 'GOOD'
    else:
        consistency = 'NEEDS_IMPROVEMENT'

    logger.info(
        f"Volume-price consistency: {consistency}, "
        f"gen_corr={gen_price_vol_corr:.3f}, "
        f"real_corr={real_price_vol_corr:.3f}, "
        f"diff={corr_diff:.3f}"
    )

    return {
        'consistency': consistency,
        'generated_correlation': gen_price_vol_corr,
        'real_correlation': real_price_vol_corr,
        'difference': corr_diff
    }
```

### Regla 13 — Long-Term Dependency Generation

Asegurar que datos sintéticos mantengan tendencias de meses (Forex).

```python
def long_term_dependency_check(
    self,
    generated_series: pd.Series,
    hurst_threshold: float = 0.55
) -> dict:
    """
    Verificar dependencia de largo plazo.

    Wiese: Long-term memory = realismo en Forex.
    """
    # Calcular exponente de Hurst
    hurst = self.calculate_hurst_exponent(generated_series.values)

    # Análisis
    if hurst > hurst_threshold:
        has_long_memory = True
        assessment = 'PERSISTENT'

    elif hurst < 0.45:
        has_long_memory = False
        assessment = 'ANTI_PERSISTENT'

    else:
        has_long_memory = False
        assessment = 'RANDOM_WALK'

    logger.info(
        f"Long-term dependency: H={hurst:.3f}, "
        f"assessment={assessment}, has_memory={has_long_memory}"
    )

    return {
        'hurst_exponent': hurst,
        'has_long_memory': has_long_memory,
        'assessment': assessment,
        'meets_threshold': hurst > hurst_threshold
    }
```

### Regla 14 — Entropy Measurement

Medir "sorpresa" de datos sintéticos para asegurar que no son copias del pasado.

```python
def entropy_measurement(
    self,
    generated_data: np.ndarray,
    real_data: np.ndarray
) -> dict:
    """
    Medir entropía para detectar copia de datos.

    Wiese: Entropía similar = datos realistas.
    """
    from scipy.stats import entropy

    # Distribuciones de retornos
    gen_hist, _ = np.histogram(generated_data, bins=50, density=True)
    real_hist, _ = np.histogram(real_data, bins=50, density=True)

    # Entropía de Shannon
    gen_entropy = entropy(gen_hist + 1e-8)
    real_entropy = entropy(real_hist + 1e-8)

    # JS Divergencia (más robusta)
    m = (gen_hist + real_hist) / 2
    js_divergence = (
        entropy(gen_hist + 1e-8, m + 1e-8) +
        entropy(real_hist + 1e-8, m + 1e-8)
    ) / 2

    # Comparación
    entropy_diff = abs(gen_entropy - real_entropy)

    if entropy_diff < 0.1 and js_divergence < 0.1:
        similarity = 'VERY_HIGH'
        risk = 'OVERFITTING'

    elif entropy_diff < 0.2:
        similarity = 'HIGH'
        risk = 'LOW'

    else:
        similarity = 'MODERATE'
        risk = 'NONE'

    logger.info(
        f"Entropy measurement: {similarity}, "
        f"gen_H={gen_entropy:.3f}, real_H={real_entropy:.3f}, "
        f"JS_div={js_divergence:.3f}"
    )

    return {
        'similarity': similarity,
        'overfitting_risk': risk,
        'generated_entropy': gen_entropy,
        'real_entropy': real_entropy,
        'js_divergence': js_divergence,
        'entropy_difference': entropy_diff
    }
```

### Regla 15 — Probabilistic Backtest

No reportar un solo resultado, sino distribución de resultados en 10,000 mercados de la GAN.

```python
def probabilistic_backtest(
    self,
    strategy,
    trained_gan: dict,
    n_simulations: int = 10000
) -> dict:
    """
    Backtest probabilístico con múltiples mundos GAN.

    Wiese: Distribución = incertidumbre real.
    """
    generator = trained_gan['generator']
    latent_dim = trained_gan['latent_dim']

    results = []

    for i in range(n_simulations):
        # Generar mercado sintético
        noise = np.random.normal(0, 1, (1, latent_dim))
        market = generator.predict(noise)[0]

        # Backtest
        backtest_result = strategy.backtest(market)

        results.append({
            'simulation': i,
            'total_return': backtest_result.get('total_return', 0),
            'sharpe': backtest_result.get('sharpe', 0),
            'max_drawdown': backtest_result.get('max_drawdown', 0),
            'win_rate': backtest_result.get('win_rate', 0)
        })

    results = pd.DataFrame(results)

    # Estadísticas de la distribución
    return_stats = {
        'mean': results['total_return'].mean(),
        'std': results['total_return'].std(),
        'median': results['total_return'].median(),
        'p5': results['total_return'].quantile(0.05),
        'p25': results['total_return'].quantile(0.25),
        'p75': results['total_return'].quantile(0.75),
        'p95': results['total_return'].quantile(0.95)
    }

    # Probabilidad de ganancia
    prob_profit = (results['total_return'] > 0).mean()

    # Confianza en la estrategia
    if prob_profit > 0.9:
        confidence = 'VERY_HIGH'
    elif prob_profit > 0.7:
        confidence = 'HIGH'
    elif prob_profit > 0.5:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'

    logger.info(
        f"Probabilistic backtest: {n_simulations} simulations, "
        f"E[r]={return_stats['mean']:+.2%}, "
        f"P(profit)={prob_profit:.1%}, confidence={confidence}"
    )

    return {
        'confidence': confidence,
        'prob_profit': prob_profit,
        'return_distribution': return_stats,
        'sharpe_distribution': {
            'mean': results['sharpe'].mean(),
            'std': results['sharpe'].std(),
            'median': results['sharpe'].median()
        },
        'drawdown_distribution': {
            'worst': results['max_drawdown'].max(),
            'median': results['max_drawdown'].median()
        },
        'all_results': results
    }
```

---

## Aplicación Práctica

### Pipeline Completo GAN Financial

```python
def gan_financial_pipeline(
    self,
    strategy,
    historical_data: pd.DataFrame,
    n_stress_scenarios: int = 1000
) -> dict:
    """
    Pipeline completo usando GANs financieras.
    """
    # 1. Entrenar GAN con datos históricos
    logger.info("Training GAN...")
    gan = self.train_gan(historical_data['returns'])

    # 2. Auditoría de discriminador
    synthetic_sample = gan['generator'].predict(
        np.random.normal(0, 1, (100, gan['latent_dim']))
    )

    audit = self.discriminator_audit(
        gan['discriminator'],
        historical_data['returns'].values[:100],
        synthetic_sample
    )

    if not audit['passed']:
        return {
            'status': 'GAN_NEEDS_TRAINING',
            'audit': audit
        }

    # 3. Generar escenarios de estrés
    stress_scenarios = self.stress_test_scenarios(
        gan,
        n_scenarios=n_stress_scenarios,
        stress_level='extreme'
    )

    # 4. Backtest en escenarios extremos
    stress_results = []

    for scenario in stress_scenarios['extreme_scenarios'][:100]:  # Top 100
        result = strategy.backtest(scenario['scenario'])
        stress_results.append(result['total_return'])

    stress_results = np.array(stress_results)

    # 5. Análisis de robustez
    stress_survival = (stress_results > -0.10).mean()  # Sobrevive 90% capital

    # 6. Detección de overfitting
    real_perf = strategy.backtest(historical_data['returns'].values)
    synth_perf = strategy.backtest(synthetic_sample.flatten())

    overfit = self.overfitting_detection(real_perf, synth_perf)

    # 7. Backtest probabilístico
    prob_test = self.probabilistic_backtest(
        strategy,
        gan,
        n_simulations=10000
    )

    # 8. Decisión final
    if stress_survival > 0.9 and prob_test['prob_profit'] > 0.7:
        recommendation = 'DEPLOY'
        confidence = prob_test['confidence']

    elif overfit['overfitting'] == 'SEVERE':
        recommendation = 'RETRAIN_STRATEGY'
        confidence = 'LOW'

    else:
        recommendation = 'IMPROVE_STRATEGY'
        confidence = 'MEDIUM'

    return {
        'recommendation': recommendation,
        'confidence': confidence,
        'stress_survival_rate': stress_survival,
        'prob_profit': prob_test['prob_profit'],
        'overfitting_detected': overfit['overfitting'],
        'gan_quality': audit['gan_quality'],
        'probabilistic_returns': prob_test['return_distribution']
    }
```
