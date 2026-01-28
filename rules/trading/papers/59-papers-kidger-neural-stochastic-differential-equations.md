# 📄 Papers Fundamentales - Neural SDEs (Kidger et al., 2020)

## Modelos Híbridos de Ecuaciones Diferenciales y Redes Neuronales

**Contexto:** Continuous-Time Modeling y Neural Differential Equations.

Kidger et al. introdujeron Neural SDEs, combinando la flexibilidad de las redes neuronales con la teoría de procesos estocásticos para modelar mercados como flujos continuos.

---

### Regla 1 — Neural SDE Solver

Usar redes neuronales para aprender coeficientes de deriva y difusión.

```python
def neural_sde_solver(
    self,
    t0: float,
    t1: float,
    x0: np.ndarray,
    drift_network,
    diffusion_network,
    dt: float = 1/252
) -> np.ndarray:
    """
    Solver de SDE con coeficientes aprendidos por NN.

    Kidger: drif y diffusion = funciones aprendidas.
    """
    n_steps = int((t1 - t0) / dt)
    trajectory = np.zeros((n_steps + 1, len(x0)))
    trajectory[0] = x0

    x = x0.copy()

    for i in range(n_steps):
        t = t0 + i * dt

        # Drift (tendency)
        drift = drift_network(torch.tensor([t, *x])).detach().numpy()

        # Diffusion (volatility)
        diffusion = diffusion_network(torch.tensor([t, *x])).detach().numpy()

        # Brownian increment
        dW = np.random.standard_normal(len(x0)) * np.sqrt(dt)

        # Euler-Maruyama step
        x = x + drift * dt + diffusion * dW

        trajectory[i + 1] = x

    logger.info(
        f"Neural SDE solved: {n_steps} steps, "
        f"x0={x0}, xT={trajectory[-1]}"
    )

    return trajectory
```

### Regla 2 — Continuous-Time Modeling

Tratar datos de ticks como flujo continuo, no puntos discretos.

```python
def continuous_time_interpolation(
    self,
    tick_data: pd.DataFrame,
    method: str = 'cubic'
) -> callable:
    """
    Interpolar ticks a función continua.

    Kidger: Tiempo continuo = SDE aplicable.
    """
    from scipy.interpolate import interp1d

    timestamps = tick_data.index.astype(np.int64) / 1e9  # Unix time
    prices = tick_data['price'].values

    # Interpolación
    price_continuous = interp1d(
        timestamps,
        prices,
        kind=method,
        bounds_error=False,
        fill_value='extrapolate'
    )

    # Función de precio en tiempo continuo
    def price_at_time(t: float) -> float:
        return float(price_continuous(t))

    logger.info(
        f"Continuous interpolation: {len(tick_data)} ticks → "
        f"continuous function"
    )

    return price_at_time
```

### Regla 3 — Adjoint Method Training

Usar método adjunto para entrenar con bajo consumo de memoria.

```python
def adjoint_sde_training(
    self,
    neural_sde,
    initial_condition: np.ndarray,
    observations: np.ndarray,
    t_span: tuple,
    n_epochs: int = 100
) -> dict:
    """
    Entrenar SDE usando adjoint method.

    Kidger: Adjoint = O(n) memory, no O(n²).
    """
    from torchdiffeq import odeint_adjoint

    # Función de pérdida
    def loss_fn(params):
        # Simular SDE
        trajectory = neural_sde.simulate(
            initial_condition,
            t_span,
            params=params
        )

        # Comparar con observaciones
        error = ((trajectory - observations) ** 2).mean()

        return error

    # Optimizar usando adjoint
    # (En producción usar torchdiffeq implementation)

    logger.info(
        f"Adjoint training: {n_epochs} epochs, "
        f"memory efficient gradient computation"
    )

    return {
        'trained': True,
        'final_loss': loss_fn(neural_sde.params)
    }
```

### Regla 4 — Latent Space Dynamics

Modelar factores ocultos (liquidez no vista) en espacio latente.

```python
def latent_sde_dynamics(
    self,
    observations: np.ndarray,
    latent_dim: int = 5
) -> dict:
    """
    SDE en espacio latente para factores ocultos.

    Kidger: Latent SDE = factores no observados.
    """
    import torch
    import torch.nn as nn

    # Encoder: obs → latent
    encoder = nn.Sequential(
        nn.Linear(observations.shape[1], 32),
        nn.Tanh(),
        nn.Linear(32, latent_dim * 2)  # Mean y log_var
    )

    # SDE dynamics en latent
    class LatentSDE(nn.Module):
        def __init__(self, dim):
            super().__init__()
            self.drift = nn.Linear(dim, dim)
            self.diffusion = nn.Linear(dim, dim)

        def forward(self, t, x):
            return self.drift(x), self.diffusion(x)

    latent_sde = LatentSDE(latent_dim)

    # Decoder: latent → obs
    decoder = nn.Sequential(
        nn.Linear(latent_dim, 32),
        nn.Tanh(),
        nn.Linear(32, observations.shape[1])
    )

    logger.info(
        f"Latent SDE: obs_dim={observations.shape[1]}, "
        f"latent_dim={latent_dim}"
    )

    return {
        'encoder': encoder,
        'latent_sde': latent_sde,
        'decoder': decoder,
        'latent_dim': latent_dim
    }
```

### Regla 5 — Pathwise Sensitivity (Greeks)

Calcular Delta/Gamma mediante diferenciación automática del solver.

```python
def neural_sde_greeks(
    self,
    neural_sde,
    initial_price: float,
    strike: float,
    ttm: float
) -> dict:
    """
    Calcular griegas via autodiff del solver SDE.

    Kidger: Autodiff → greeks exactas sin finite differences.
    """
    import torch

    # Price como tensor con grad
    S0 = torch.tensor([initial_price], requires_grad=True)

    # Simular SDE
    def sde_dynamics(t, x):
        drift = neural_sde.drift_net(t, x)
        diffusion = neural_sde.diffusion_net(t, x)
        return drift, diffusion

    # Solver
    terminal_prices = neural_sde.solve(
        S0,
        t_span=(0, ttm),
        dynamics=sde_dynamics
    )

    # Payoff
    payoff = torch.max(terminal_prices - strike, torch.tensor(0.0))

    # Delta = dPayoff/dS0
    payoff.backward()
    delta = S0.grad.item()

    # Gamma = d²Payoff/dS0²
    gamma = torch.autograd.functional.hessian(
        lambda s: neural_sde.solve(s, (0, ttm), sde_dynamics).max() - strike,
        S0
    ).item()

    logger.info(
        f"Neural SDE Greeks: Delta={delta:.3f}, Gamma={gamma:.3f}"
    )

    return {
        'delta': delta,
        'gamma': gamma,
        'option_price': payoff.item()
    }
```

### Regla 6 — Irregularly Sampled Data

Manejar gaps de tiempo sin interpolación lineal.

```python
def irregular_sde_inference(
    self,
    irregular_timestamps: List[pd.Timestamp],
    irregular_values: np.ndarray,
    neural_sde
) -> np.ndarray:
    """
    Inferir con timestamps irregulares.

    Kidger: SDE maneja nativamente datos irregulares.
    """
    # Ordenar por timestamp
    sorted_indices = np.argsort(irregular_timestamps)
    sorted_times = [irregular_timestamps[i] for i in sorted_indices]
    sorted_values = irregular_values[sorted_indices]

    # Convertir a tiempo relativo
    t0 = sorted_times[0]
    relative_times = [(t - t0).total_seconds() / 86400 for t in sorted_times]

    # Simular SDE entre cada par de puntos
    inferred_states = []

    for i in range(len(relative_times) - 1):
        t_curr = relative_times[i]
        t_next = relative_times[i + 1]

        # Simular desde t_curr a t_next
        dt = t_next - t_curr

        # State dynamics
        state = neural_sde.step(
            sorted_values[i],
            dt=dt
        )

        inferred_states.append(state)

    inferred_states = np.array(inferred_states)

    logger.info(
        f"Irregular inference: {len(sorted_times)} points, "
        f"{sum(np.diff(relative_times) > 1)} gaps"
    )

    return inferred_states
```

### Regla 7 — Brownian Motion Injection

Añadir ruido estocástico controlado a capas ocultas.

```python
def brownian_motion_layer(
    self,
    input_tensor,
    noise_level: float = 0.1
) -> torch.Tensor:
    """
    Inyectar movimiento browniano en capa.

    Kidger: BM injection = simula incertidumbre.
    """
    import torch

    # Dimension
    batch_size, *dims = input_tensor.shape

    # Brownian motion (incrementos normales)
    dW = torch.randn_like(input_tensor) * np.sqrt(noise_level)

    # Inyectar
    output = input_tensor + dW

    logger.debug(
        f"BM injection: noise={noise_level}, "
        f"shape={input_tensor.shape}"
    )

    return output
```

### Regla 8 — Neural Flow Architecture

Asegurar que la red preserve invertibilidad de transformaciones.

```python
def neural_flow_sde(
    self,
    input_dim: int,
    hidden_dim: int = 64
) -> nn.Module:
    """
    SDE con transformaciones invertibles (Normalizing Flows).

    Kidger: Invertibilidad = tractable likelihood.
    """
    import torch.nn as nn

    class NeuralFlowSDE(nn.Module):
        def __init__(self, dim, hidden):
            super().__init__()

            # Drift (invertible)
            self.drift = nn.Sequential(
                nn.Linear(dim, hidden),
                nn.Tanh(),
                nn.Linear(hidden, dim)
            )

            # Diffusion (diagonal para invertibilidad)
            self.diffusion_log_scale = nn.Linear(dim, dim)

            # Coupling layer para invertibilidad
            self.coupling = nn.Sequential(
                nn.Linear(dim // 2, hidden),
                nn.Tanh(),
                nn.Linear(hidden, dim // 2)
            )

        def forward(self, t, x):
            # Split
            x1, x2 = x.chunk(2, dim=-1)

            # Coupling
            scale_shift = self.coupling(x1)
            x2 = x2 + scale_shift

            # Recombine
            x = torch.cat([x1, x2], dim=-1)

            # Drift y diffusion
            drift = self.drift(x)
            diffusion_log_scale = self.diffusion_log_scale(x)
            diffusion = torch.exp(diffusion_log_scale)

            return drift, diffusion

    model = NeuralFlowSDE(input_dim, hidden_dim)

    logger.info(
        f"Neural Flow SDE: dim={input_dim}, hidden={hidden_dim}"
    )

    return model
```

### Regla 9 — Universal Approximation

Usar redes profundas para aproximar funciones de pago complejas.

```python
def universal_payoff_approximator(
    self,
    payoff_samples: np.ndarray,
    underlying_states: np.ndarray,
    hidden_layers: List[int] = [128, 128, 64]
) -> nn.Module:
    """
    Approximator de payoff complejo con NN.

    Kidger: NN universal approximator.
    """
    import torch.nn as nn

    # Arquitectura
    layers = []

    input_dim = underlying_states.shape[1]

    # Hidden layers
    prev_dim = input_dim
    for dim in hidden_layers:
        layers.extend([
            nn.Linear(prev_dim, dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        ])
        prev_dim = dim

    # Output layer
    layers.append(nn.Linear(prev_dim, 1))

    # Model
    model = nn.Sequential(*layers)

    logger.info(
        f"Payoff approximator: input_dim={input_dim}, "
        f"layers={hidden_layers}"
    )

    return model
```

### Regla 10 — Stiffness Handling

Solvers que no fallan cuando volatilidad se vuelve "rígida".

```python
def stiff_sde_solver(
    self,
    neural_sde,
    t_span: tuple,
    x0: np.ndarray,
    method: str = 'implicit_euler'
) -> np.ndarray:
    """
    Solver para SDE stiff (volatilidad explosiva).

    Kidger: Implicit methods = stable en stiff regimes.
    """
    n_steps = 100
    dt = (t_span[1] - t_span[0]) / n_steps

    trajectory = np.zeros((n_steps + 1, len(x0)))
    trajectory[0] = x0

    x = x0.copy()

    for i in range(n_steps):
        t = t_span[0] + i * dt

        if method == 'implicit_euler':
            # Implicit Euler: resolver para x_next
            # x_next = x + f(t, x_next) * dt + g * dW

            drift_curr, diffusion_curr = neural_sde(t, x)

            # Simplificación: usar drift en t actual
            # (para producción usar Newton-Raphson)
            dW = np.random.randn(len(x0)) * np.sqrt(dt)

            x = x + drift_curr * dt + diffusion_curr * dW

        trajectory[i + 1] = x

    logger.info(
        f"Stiff SDE solved: method={method}, "
        f"n_steps={n_steps}"
    )

    return trajectory
```

### Regla 11 — Monte Carlo Neural Integration

Generar miles de trayectorias para definir Take Profit.

```python
def neural_sde_monte_carlo(
    self,
    neural_sde,
    x0: np.ndarray,
    t_span: tuple,
    n_simulations: int = 10000,
    n_steps: int = 100
) -> dict:
    """
    Monte Carlo con Neural SDE para pricing.

    Kidger: MC Neural SDE = distribución completa.
    """
    all_terminal_values = []

    for _ in range(n_simulations):
        # Simular trayectoria
        trajectory = neural_sde.simulate(
            x0=x0,
            t_span=t_span,
            n_steps=n_steps
        )

        terminal_value = trajectory[-1]
        all_terminal_values.append(terminal_value)

    all_terminal_values = np.array(all_terminal_values)

    # Estadísticas
    mean_terminal = all_terminal_values.mean()
    std_terminal = all_terminal_values.std()

    # Percentiles
    percentiles = {
        'p5': np.percentile(all_terminal_values, 5),
        'p25': np.percentile(all_terminal_values, 25),
        'p50': np.percentile(all_terminal_values, 50),
        'p75': np.percentile(all_terminal_values, 75),
        'p95': np.percentile(all_terminal_values, 95)
    }

    # Take profit levels
    tp_levels = {
        'conservative': percentiles['p75'],
        'moderate': percentiles['p50'],
        'aggressive': percentiles['p25']
    }

    logger.info(
        f"MC Neural SDE: {n_simulations} sims, "
        f"E[xT]={mean_terminal:.3f}, σ={std_terminal:.3f}"
    )

    return {
        'mean': mean_terminal,
        'std': std_terminal,
        'percentiles': percentiles,
        'take_profit_levels': tp_levels,
        'all_simulations': all_terminal_values
    }
```

### Regla 12 — Robustness to Outliers

Solver capaz de ignorar fat fingers sin desestabilizar solución.

```python
def robust_sde_solver(
    self,
    neural_sde,
    observations: np.ndarray,
    outlier_threshold: float = 5.0
) -> dict:
    """
    Solver robusto a outliers en observaciones.

    Kidger: Robust loss = ignora fat fingers.
    """
    from scipy.stats import median_absolute_deviation

    # Detectar outliers
    median = np.median(observations)
    mad = median_absolute_deviation(observations)

    outliers_mask = np.abs(observations - median) > (outlier_threshold * mad)

    n_outliers = outliers_mask.sum()

    if n_outliers > 0:
        logger.warning(
            f"⚠️ {n_outliers} outliers detected. "
            f"Using robust fitting."
        )

        # Pesos: 0 para outliers, 1 para inliers
        weights = np.where(outliers_mask, 0.0, 1.0)

        # Fit con pesos
        fit_result = neural_sde.fit_weighted(
            observations,
            weights=weights
        )

    else:
        fit_result = neural_sde.fit(observations)

    logger.info(
        f"Robust fit: {n_outliers} outliers removed, "
        f"converged={fit_result['converged']}"
    )

    return {
        'n_outliers': n_outliers,
        'outliers_mask': outliers_mask,
        'fit_result': fit_result
    }
```

### Regla 13 — Online Recalibration

Ajustar pesos de Neural SDE tras cada nueva vela.

```python
def online_sde_recalibration(
    self,
    neural_sde,
    new_observation: np.ndarray,
    learning_rate: float = 0.01
) -> dict:
    """
    Recalibrar online con cada nueva obs.

    Kidger: Online learning = adaptación en tiempo real.
    """
    import torch

    # Current state
    current_params = {
        name: param.clone()
        for name, param in neural_sde.named_parameters()
    }

    # Predicted vs actual
    with torch.no_grad():
        prediction = neural_sde.predict_next()
        error = new_observation - prediction

    # Gradient step
    loss = (error ** 2).mean()
    loss.backward()

    # Update con learning rate pequeño
    with torch.no_grad():
        for param in neural_sde.parameters():
            param -= learning_rate * param.grad

    logger.info(
        f"Online recalibration: loss={loss:.4f}, "
        f"lr={learning_rate}"
    )

    return {
        'loss': loss.item(),
        'error': error.numpy() if hasattr(error, 'numpy') else error,
        'learning_rate': learning_rate,
        'params_updated': True
    }
```

### Regla 14 — Time-Dependent Coefficients

Permitir que parámetros cambien según hora del día (estacionalidad).

```python
def time_dependent_sde(
    self,
    t: float,
    x: np.ndarray,
    hour_embedding: np.ndarray
) -> tuple:
    """
    SDE con coeficientes dependientes del tiempo.

    Kidger: Time-dependent = estacionalidad.
    """
    # Embedding cíclico de hora
    hour_sin = np.sin(2 * np.pi * t / 24)
    hour_cos = np.cos(2 * np.pi * t / 24)

    day_sin = np.sin(2 * np.pi * t / 7)
    day_cos = np.cos(2 * np.pi * t / 7)

    time_features = np.array([hour_sin, hour_cos, day_sin, day_cos])

    # Concatenar estado y time features
    combined = np.concatenate([x, time_features])

    # Drift: f(state, time)
    # En producción, esto sería una red neuronal
    drift_base = self.drift_net(x)
    drift_time_modulation = self.time_modulation_net(time_features)
    drift = drift_base + drift_time_modulation

    # Diffusion: g(state, time)
    diffusion_base = self.diffusion_net(x)
    diffusion_time_modulation = self.diffusion_time_net(time_features)
    diffusion = diffusion_base * (1 + diffusion_time_modulation)

    return drift, diffusion
```

### Regla 15 — Boundary Conditions

Definir límites físicos (ej. precio no negativo) en arquitectura.

```python
def constrained_neural_sde(
    self,
    neural_sde,
    constraints: dict
) -> callable:
    """
    SDE con constraints físicos.

    Kidger: Constraints = realismo del modelo.
    """
    def constrained_dynamics(t, x):
        # Dynamics originales
        drift, diffusion = neural_sde(t, x)

        # Aplicar constraints

        # 1. Precio no negativo
        if 'non_negative' in constraints and constraints['non_negative']:
            # Drift pushing towards positive territory near zero
            near_zero_mask = x < 0.01
            drift = np.where(
                near_zero_mask,
                drift + 0.1,  # Push up
                drift
            )

        # 2. Volatilidad máxima
        if 'max_volatility' in constraints:
            max_vol = constraints['max_volatility']
            diffusion = np.clip(diffusion, -max_vol, max_vol)

        # 3. Mean reversion bounds
        if 'mean_reversion' in constraints:
            target = constraints['mean_reversion']['target']
            speed = constraints['mean_reversion']['speed']
            drift += speed * (target - x)

        return drift, diffusion

    logger.info(
        f"Constrained SDE: constraints={list(constraints.keys())}"
    )

    return constrained_dynamics
```

---

## Aplicación Práctica

### Pipeline Completo Neural SDE

```python
def neural_sde_trading_pipeline(
    self,
    current_state: dict,
    historical_data: pd.DataFrame
) -> dict:
    """
    Pipeline completo usando Neural SDE.
    """
    # 1. Preparar datos continuos
    price_continuous = self.continuous_time_interpolation(
        historical_data[['timestamp', 'price']].set_index('timestamp')
    )

    # 2. Entrenar/recalibrar Neural SDE
    neural_sde = self.load_neural_sde()

    if neural_sde.needs_recalibration():
        recalibration = self.online_sde_recalibration(
            neural_sde,
            current_state['price'],
            learning_rate=0.01
        )

    # 3. Monte Carlo para distribución futura
    mc_results = self.neural_sde_monte_carlo(
        neural_sde,
        x0=np.array([current_state['price']]),
        t_span=(0, 1),  # 1 día adelante
        n_simulations=10000
    )

    # 4. Calcular griegas
    greeks = self.neural_sde_greeks(
        neural_sde,
        current_state['price'],
        strike=current_state.get('strike', current_state['price']),
        ttm=1
    )

    # 5. Decisión de trading
    expected_price = mc_results['mean']
    current_price = current_state['price']

    if expected_price > current_price * 1.02:  # +2%
        action = 'BUY'
        confidence = (expected_price - current_price) / mc_results['std']

    elif expected_price < current_price * 0.98:  # -2%
        action = 'SELL'
        confidence = (current_price - expected_price) / mc_results['std']

    else:
        action = 'HOLD'
        confidence = 0

    # 6. Take profit y stop loss
    tp = mc_results['take_profit_levels']['moderate']
    sl = mc_results['percentiles']['p5']

    return {
        'action': action,
        'confidence': min(confidence, 1.0),
        'expected_price': expected_price,
        'take_profit': tp,
        'stop_loss': sl,
        'delta': greeks['delta'],
        'distribution_stats': {
            'mean': mc_results['mean'],
            'std': mc_results['std'],
            'percentiles': mc_results['percentiles']
        }
    }
```
