# 📄 Papers Fundamentales - Deep RL for Trading (Yang et al., 2020)

## Deep Reinforcement Learning - Agentes Inteligentes para Trading

**Contexto:** Trading Autónomo y Gestión de Portafolio Dinámica.

Yang et al. demostraron que agentes de RL pueden aprender políticas de trading óptimas sin reglas explícitas, usando recompensas risk-adjusted.

---

### Regla 1 — PPO (Proximal Policy Optimization)

Usar PPO como algoritmo base para evitar actualizaciones de política demasiado agresivas.

```python
def ppo_agent(
    self,
    state_dim: int,
    action_dim: int,
    clip_ratio: float = 0.2
):
    """
    Inicializar agente PPO para trading.

    Yang: PPO es más estable que A2C/DQN para finanzas.
    """
    from stable_baselines3 import PPO

    model = PPO(
        'MlpPolicy',
        env=None,  # Environment se define después
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=clip_ratio,
        clip_range_vf=None,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=True,  # State-dependent exploration
        sde_sample_freq=-1,
        target_kl=0.01,
        tensorboard_log='./logs/ppo',
        policy_kwargs={
            'net_arch': [256, 256]  # Hidden layers
        }
    )

    logger.info(
        f"PPO Agent: State={state_dim}, Action={action_dim}, "
        f"Clip={clip_ratio}"
    )

    return model
```

### Regla 2 — Sharpe Ratio Reward

La función de recompensa NO debe ser el beneficio, sino el Sharpe Ratio incremental.

```python
def sharpe_ratio_reward(
    self,
    portfolio_returns: np.ndarray,
    risk_free_rate: float = 0.02
) -> float:
    """
    Reward = Sharpe Ratio de la estrategia.

    Yang: Maximizar Sharpe, no solo retornos.
    """
    if len(portfolio_returns) < 2:
        return 0.0

    # Retornos diarios anualizados
    returns = portfolio_returns

    # Mean y std
    mean_return = returns.mean() * 252  # Anualizado
    std_return = returns.std() * np.sqrt(252)

    # Sharpe Ratio
    excess_return = mean_return - risk_free_rate

    if std_return < 1e-8:
        sharpe = 0.0
    else:
        sharpe = excess_return / std_return

    # Reward = Sharpe (puede ser negativo)
    reward = sharpe

    logger.info(
        f"Sharpe Reward: {sharpe:.3f} "
        f"(μ={mean_return:.2%}, σ={std_return:.2%})"
    )

    return reward
```

### Regla 3 — State Space Design

El estado debe incluir balance, posiciones, precios y 10 indicadores técnicos.

```python
def get_trading_state(
    self,
    current_prices: dict,
    portfolio_positions: dict,
    account_balance: float
) -> np.ndarray:
    """
    Vector de estado para el agente RL.

    Yang: Estado rico = mejor aprendizaje.
    """
    state_features = []

    # 1. Balance actual (normalizado)
    state_features.append(account_balance / 100000)  # Normalizado

    # 2. Posiciones actuales (weights)
    total_value = sum(
        pos * current_prices[sym]
        for sym, pos in portfolio_positions.items()
    ) + account_balance

    for symbol in self.symbols:
        position_value = portfolio_positions.get(symbol, 0) * current_prices[symbol]
        weight = position_value / total_value if total_value > 0 else 0
        state_features.append(weight)

    # 3. Precios relativos (normalizados)
    for symbol in self.symbols:
        # Price como ratio vs initial price
        price = current_prices[symbol]
        initial_price = self.initial_prices[symbol]
        state_features.append(price / initial_price - 1)

    # 4. Indicadores técnicos (10 indicadores clave)
    for symbol in self.symbols:
        technicals = self.calculate_technicals(symbol)

        state_features.extend([
            technicals['rsi'],
            technicals['macd'],
            technicals['bollinger_position'],
            technicals['momentum_5'],
            technicals['momentum_10'],
            technicals['volatility_10'],
            technicals['volume_ratio'],
            technicals['atr_ratio'],
            technicals['gap'],
            technicals['strength']
        ])

    state = np.array(state_features, dtype=np.float32)

    logger.info(f"State vector: {len(state)} features")

    return state
```

### Regla 4 — Action Space Constraints

Acciones continuas de -1 a 1 representando el peso deseado en el activo.

```python
def action_to_weights(
    self,
    action: np.ndarray,
    current_weights: np.ndarray
) -> np.ndarray:
    """
    Convertir acción continua (-1 a 1) a pesos del portafolio.

    Yang: Acciones continuas = finer control.
    """
    # Action ∈ [-1, 1] → change en weight
    # -1 = liquidar todo, 0 = mantener, 1 = máximo peso

    max_change = 0.10  # Cambio máximo de 10% por paso

    weight_changes = action * max_change

    # Aplicar cambios
    new_weights = current_weights + weight_changes

    # Clip a [-0.5, 1] (allow short hasta 50%)
    new_weights = np.clip(new_weights, -0.5, 1.0)

    # Normalizar para que sumen 1 (o menos si cash)
    sum_weights = new_weights.sum()

    if sum_weights > 1.0:
        # Escalar a 1
        new_weights = new_weights / sum_weights
    elif sum_weights < -1.0:
        # Limitar short total
        new_weights = new_weights / abs(sum_weights) * 0.5

    logger.info(
        f"Action → Weights: {action} → {new_weights.round(3)} "
        f"(sum={new_weights.sum():.2f})"
    )

    return new_weights
```

### Regla 5 — Transaction Cost Penalization

Restar explícitamente comisiones y slippage de la recompensa.

```python
def calculate_transaction_costs(
    self,
    action: np.ndarray,
    current_weights: np.ndarray,
    portfolio_value: float,
    commission_rate: float = 0.001,  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
) -> float:
    """
    Costos de transacción para penalizar recompensa.

    Yang: High turnover = penalización en reward.
    """
    # Cambio en pesos
    weight_changes = np.abs(action - current_weights)

    # Valor de las transacciones
    turnover = portfolio_value * weight_changes.sum() / 2

    # Comisiones
    commission = turnover * commission_rate

    # Slippage (estimado)
    slippage = turnover * slippage_rate

    # Costo total
    total_cost = commission + slippage

    # Como porcentaje del portafolio
    cost_pct = total_cost / portfolio_value

    logger.info(
        f"Transaction costs: {cost_pct:.3%} "
        f"(Comm={commission/portfolio_value:.3%}, "
        f"Slipp={slippage/portfolio_value:.3%})"
    )

    return total_cost
```

### Regla 6 — Experience Replay

Guardar transiciones y re-entrenar periódicamente.

```python
def experience_replay_buffer(
    self,
    capacity: int = 100000
):
    """
    Buffer para replay de experiencias.

    Yang: Replay reduce variance del gradiente.
    """
    from collections import deque

    class ReplayBuffer:
        def __init__(self, capacity):
            self.buffer = deque(maxlen=capacity)

        def push(self, state, action, reward, next_state, done):
            self.buffer.append((state, action, reward, next_state, done))

        def sample(self, batch_size):
            import random
            batch = random.sample(self.buffer, batch_size)

            states = np.array([e[0] for e in batch])
            actions = np.array([e[1] for e in batch])
            rewards = np.array([e[2] for e in batch])
            next_states = np.array([e[3] for e in batch])
            dones = np.array([e[4] for e in batch])

            return states, actions, rewards, next_states, dones

        def __len__(self):
            return len(self.buffer)

    buffer = ReplayBuffer(capacity)

    logger.info(f"Replay buffer: Capacity={capacity}")

    return buffer
```

### Regla 7 — Actor-Critic Framework

Separar la red que decide (Actor) de la que evalúa (Critic).

```python
def actor_critic_network(
    self,
    state_dim: int,
    action_dim: int
):
    """
    Arquitectura Actor-Critic para PPO.

    Yang: Actor = policy, Critic = value function.
    """
    import torch.nn as nn

    # Shared layers
    shared = nn.Sequential(
        nn.Linear(state_dim, 256),
        nn.ReLU(),
        nn.Linear(256, 256),
        nn.ReLU()
    )

    # Actor (policy)
    actor = nn.Sequential(
        shared,
        nn.Linear(256, 128),
        nn.ReLU(),
        nn.Linear(128, action_dim),
        nn.Tanh()  # Output ∈ [-1, 1]
    )

    # Critic (value)
    critic = nn.Sequential(
        shared,
        nn.Linear(256, 128),
        nn.ReLU(),
        nn.Linear(128, 1)
    )

    logger.info(
        f"Actor-Critic: Shared(256×2), "
        f"Actor(128→{action_dim}), Critic(128→1)"
    )

    return actor, critic
```

### Regla 8 — Exploration vs. Exploitation

Usar decaimiento de ruido para explorar al inicio y explotar después.

```python
def exploration_schedule(
    self,
    current_step: int,
    total_steps: int,
    initial_noise: float = 0.3,
    final_noise: float = 0.01
) -> float:
    """
    Nivel de exploración (ruido) según progreso del entrenamiento.

    Yang: Explorar primero, explotar después.
    """
    # Linear decay
    progress = min(current_step / total_steps, 1.0)

    noise_level = initial_noise * (1 - progress) + final_noise * progress

    logger.info(
        f"Exploration: {noise_level:.3f} "
        f"(Step {current_step}/{total_steps}, "
        f"Progress={progress:.1%})"
    )

    return noise_level
```

### Regla 9 — Normalized Observations

Escalar todos los inputs entre 0 y 1 para facilitar convergencia.

```python
def normalize_state(
    self,
    state: np.ndarray,
    scaler=None
) -> tuple:
    """
    Normalizar estado [0, 1].

    Yang: Normalización = entrenamiento estable.
    """
    from sklearn.preprocessing import MinMaxScaler

    if scaler is None:
        scaler = MinMaxScaler()
        normalized = scaler.fit_transform(state.reshape(-1, 1)).flatten()
    else:
        normalized = scaler.transform(state.reshape(-1, 1)).flatten()

    logger.debug(
        f"Normalized state: [{normalized.min():.3f}, {normalized.max():.3f}]"
    )

    return normalized, scaler
```

### Regla 10 — Market Regime Adaptation

El agente debe recibir la señal del régimen de volatilidad actual.

```python
def add_regime_to_state(
    self,
    base_state: np.ndarray,
    volatility_regime: str  # 'LOW', 'MEDIUM', 'HIGH'
) -> np.ndarray:
    """
    Añadir régimen de volatilidad al estado.

    Yang: Régimen = contexto para la decisión.
    """
    # One-hot encoding del régimen
    regime_encoding = {
        'LOW': [1, 0, 0],
        'MEDIUM': [0, 1, 0],
        'HIGH': [0, 0, 1]
    }

    regime_vector = np.array(regime_encoding[volatility_regime])

    # Concatenar
    extended_state = np.concatenate([base_state, regime_vector])

    logger.info(
        f"Extended state: {len(base_state)} → {len(extended_state)} "
        f"(Regime: {volatility_regime})"
    )

    return extended_state
```

### Regla 11 — Multi-Agent Simulation

Entrenar agentes que compiten para encontrar estrategias robustas.

```python
def multi_agent_environment(
    self,
    n_agents: int = 3
):
    """
    Múltiples agentes compitiendo en el mismo mercado.

    Yang: Competencia = estrategias más robustas.
    """
    agents = []

    for i in range(n_agents):
        # Cada agente con semilla distinta
        agent = self.ppo_agent(
            state_dim=self.state_dim,
            action_dim=self.action_dim
        )
        agents.append(agent)

    logger.info(f"Multi-agent: {n_agents} agents initialized")

    return agents
```

### Regla 12 — Risk-Adjusted Return

Penalizar la recompensa si el drawdown supera umbral.

```python
def drawdown_penalty(
    self,
    portfolio_value: pd.Series,
    max_drawdown_limit: float = 0.15
) -> float:
    """
    Penalizar si DD > límite.

    Yang: Control de riesgo intrínseco al reward.
    """
    # Drawdown actual
    peak = portfolio_value.expanding(min_periods=1).max()
    drawdown = (portfolio_value - peak) / peak

    max_dd = abs(drawdown.min())

    # Penalización
    if max_dd > max_drawdown_limit:
        penalty = -(max_dd - max_drawdown_limit) * 10  # Penalización fuerte

        logger.warning(
            f"⚠️ Drawdown penalty: {max_dd:.1%} > {max_drawdown_limit:.1%}. "
            f"Penalty={penalty:.3f}"
        )

        return penalty

    return 0.0
```

### Regla 13 — Temporal Consistency

Asegurar que decisiones en t consideren impacto en t+1.

```python
def temporal_consistency_loss(
    self,
    actions: np.ndarray,
    next_actions: np.ndarray
) -> float:
    """
    Penalizar cambios bruscos de acción.

    Yang: Suavidad temporal = realistic trading.
    """
    # Diferencia entre acciones consecutivas
    action_changes = np.abs(actions - next_actions)

    # Mean squared change
    consistency_loss = np.mean(action_changes ** 2)

    logger.debug(f"Temporal consistency loss: {consistency_loss:.4f}")

    return consistency_loss
```

### Regla 14 — Ensemble Strategy

Promediar acciones de PPO, A2C y DDPG para ejecutar trade final.

```python
def ensemble_agents(
    self,
    state: np.ndarray
) -> np.ndarray:
    """
    Ensemble de PPO + A2C + DDPG.

    Yang: Ensemble = reducción de variance.
    """
    # Predicciones de cada agente
    ppo_action = self.ppo_agent.predict(state)[0]
    a2c_action = self.a2c_agent.predict(state)[0]
    ddpg_action = self.ddpg_agent.predict(state)[0]

    # Promedio
    ensemble_action = (
        ppo_action * 0.4 +
        a2c_action * 0.3 +
        ddpg_action * 0.3
    )

    logger.info(
        f"Ensemble: PPO={ppo_action[0]:.3f}, "
        f"A2C={a2c_action[0]:.3f}, "
        f"DDPG={ddpg_action[0]:.3f} → "
        f"Ensemble={ensemble_action[0]:.3f}"
    )

    return ensemble_action
```

### Regla 15 — DDPG para Mercados Líquidos

Para mercados muy líquidos, usar DDPG para mayor precisión en sizing.

```python
def ddpg_agent(
    self,
    state_dim: int,
    action_dim: int
):
    """
    Deep Deterministic Policy Gradient para sizing preciso.

    Yang: DDPG = acciones continuas determinísticas.
    """
    from stable_baselines3 import DDPG

    model = DDPG(
        'MlpPolicy',
        env=None,
        learning_rate=1e-4,
        buffer_size=100000,
        learning_starts=1000,
        batch_size=128,
        tau=0.005,  # Soft update coef
        gamma=0.99,
        gradient_steps=-1,
        policy_kwargs={'net_arch': [256, 256]}
    )

    logger.info(
        f"DDPG Agent: State={state_dim}, Action={action_dim}"
    )

    return model
```

---

## Aplicación Práctica

### Pipeline Completo Deep RL Trading

```python
def deep_rl_trading_pipeline(
    self,
    current_state: dict,
    trained_agents: dict
) -> dict:
    """
    Pipeline completo de Deep RL para trading.
    """
    # 1. Obtener estado
    state = self.get_trading_state(
        current_prices=current_state['prices'],
        portfolio_positions=current_state['positions'],
        account_balance=current_state['balance']
    )

    # 2. Normalizar
    state_norm, _ = self.normalize_state(state, scaler=self.scaler)

    # 3. Añadir régimen
    vol_regime = self.detect_volatility_regime()
    state_extended = self.add_regime_to_state(state_norm, vol_regime)

    # 4. Ensemble de agentes
    action = self.ensemble_agents(state_extended)

    # 5. Convertir acción a pesos
    current_weights = self.get_current_weights()
    new_weights = self.action_to_weights(action, current_weights)

    # 6. Calcular costos de transacción
    portfolio_value = current_state['balance'] + sum(
        pos * price
        for pos, price in zip(
            current_state['positions'].values(),
            current_state['prices'].values()
        )
    )

    tx_costs = self.calculate_transaction_costs(
        action, current_weights, portfolio_value
    )

    # 7. Calcular reward (Sharpe - costs - DD penalty)
    returns = self.get_recent_returns()
    sharpe_reward = self.sharpe_ratio_reward(returns)
    dd_penalty = self.drawdown_penalty(self.portfolio_value_series)

    total_reward = sharpe_reward - tx_costs/portfolio_value - dd_penalty

    # 8. Ejecutar trades
    trades = self.execute_weight_rebalance(
        current_weights=current_weights,
        target_weights=new_weights
    )

    return {
        'action': action,
        'new_weights': new_weights,
        'trades': trades,
        'transaction_costs': tx_costs,
        'reward': total_reward,
        'sharpe': sharpe_reward,
        'regime': vol_regime
    }
```
