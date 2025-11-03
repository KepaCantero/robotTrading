"""
ReinforcementLearningEngine - Aprende políticas óptimas de trading con RL.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from collections import deque

from .base_learning_engine import BaseLearningEngine

logger = logging.getLogger(__name__)

# Importaciones opcionales para RL
# Hacer imports no bloqueantes para evitar deadlocks con threading
STABLE_BASELINES3_AVAILABLE = False
GYM_AVAILABLE = False

# Intentar importar stable_baselines3 - puede bloquear, así que hacerlo opcional
# Si bloquea, simplemente no estará disponible
try:
    # Desactivar threading warnings de TensorFlow si está disponible
    import os
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
    os.environ.setdefault('OMP_NUM_THREADS', '1')  # Reducir threads para evitar bloqueos
    
    from stable_baselines3 import PPO, A2C, DDPG
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import BaseCallback
    STABLE_BASELINES3_AVAILABLE = True
    logger.debug("stable-baselines3 disponible")
except (ImportError, Exception) as e:
    STABLE_BASELINES3_AVAILABLE = False
    # Silenciar completamente - es esperado que puede no estar disponible o bloquear
    logger.debug(f"stable-baselines3 no disponible o bloqueado")

# Importar gym de forma simple
try:
    import gym
    import gym.spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    logger.debug("gym no disponible. Funcionalidad RL limitada.")


class TradingEnv:
    """
    Entorno de trading para Reinforcement Learning.
    
    Estados: Indicadores técnicos, contexto de mercado, posición actual
    Acciones: BUY, SELL, HOLD, ajustar stop-loss, ajustar exposición
    Recompensas: P&L ajustado por riesgo, Sharpe ratio, drawdown
    """
    
    def __init__(self, config: Dict):
        """Inicializar entorno de trading."""
        self.config = config
        self.reset()
        
        # Espacio de observación: indicadores + contexto + posición
        self.observation_dim = config.get("observation_dim", 20)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.observation_dim,), dtype=np.float32
        )
        
        # Espacio de acciones: 0=HOLD, 1=BUY, 2=SELL, 3=Ajustar SL, 4=Ajustar TP
        self.action_space = gym.spaces.Discrete(5)
        
        # Parámetros de recompensa
        self.reward_config = config.get("reward_config", {
            "pnl_weight": 1.0,
            "sharpe_weight": 0.3,
            "drawdown_penalty": 0.5,
            "transaction_cost": 0.001
        })
    
    def reset(self):
        """Resetear entorno al estado inicial."""
        self.position = 0  # 0=sin posición, 1=long, -1=short
        self.cash = 100000.0
        self.equity = [100000.0]
        self.trades = []
        self.current_step = 0
        self.max_drawdown = 0.0
        self.peak_equity = 100000.0
        
        return self._get_observation()
    
    def step(self, action: int, market_data: Dict) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Ejecutar acción en el entorno.
        
        Args:
            action: Acción a tomar (0-4)
            market_data: Datos de mercado actuales (precio, indicadores, etc.)
        
        Returns:
            observation, reward, done, info
        """
        price = market_data.get('price', 0)
        prev_equity = self.equity[-1]
        
        # Ejecutar acción
        if action == 1:  # BUY
            if self.position == 0:  # Solo comprar si no hay posición
                self._execute_buy(price, market_data)
        elif action == 2:  # SELL
            if self.position != 0:  # Solo vender si hay posición
                self._execute_sell(price, market_data)
        elif action == 3:  # Ajustar stop-loss
            self._adjust_stop_loss(market_data)
        elif action == 4:  # Ajustar take-profit
            self._adjust_take_profit(market_data)
        # action == 0 (HOLD) no hace nada
        
        # Actualizar equity
        if self.position != 0:
            unrealized_pnl = (price - self.trades[-1]['entry_price']) * self.position * self.trades[-1]['quantity']
            current_equity = self.cash + unrealized_pnl + (self.trades[-1]['entry_price'] * self.trades[-1]['quantity'])
        else:
            current_equity = self.cash
        
        self.equity.append(current_equity)
        
        # Calcular recompensa
        reward = self._calculate_reward(prev_equity, current_equity)
        
        # Actualizar drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        self.max_drawdown = max(self.max_drawdown, drawdown)
        
        # Done condition
        done = self.current_step >= self.config.get("max_steps", 1000) or current_equity < self.cash * 0.5
        
        self.current_step += 1
        
        info = {
            'equity': current_equity,
            'position': self.position,
            'drawdown': drawdown,
            'max_drawdown': self.max_drawdown
        }
        
        return self._get_observation(market_data), reward, done, info
    
    def _execute_buy(self, price: float, market_data: Dict):
        """Ejecutar compra."""
        # Calcular cantidad basada en capital disponible
        quantity = (self.cash * 0.1) / price  # Usar 10% del capital
        
        cost = quantity * price * (1 + self.reward_config['transaction_cost'])
        
        if cost <= self.cash:
            self.cash -= cost
            self.position = 1
            self.trades.append({
                'entry_price': price,
                'quantity': quantity,
                'type': 'BUY',
                'step': self.current_step,
                'metadata': market_data
            })
    
    def _execute_sell(self, price: float, market_data: Dict):
        """Ejecutar venta."""
        if self.trades:
            trade = self.trades[-1]
            revenue = trade['quantity'] * price * (1 - self.reward_config['transaction_cost'])
            
            pnl = (price - trade['entry_price']) * trade['quantity'] * self.position
            
            self.cash += revenue
            self.position = 0
            
            trade['exit_price'] = price
            trade['pnl'] = pnl
            trade['exit_step'] = self.current_step
    
    def _adjust_stop_loss(self, market_data: Dict):
        """Ajustar stop-loss dinámicamente."""
        # Placeholder: en producción, ajustar parámetros de stop-loss
        pass
    
    def _adjust_take_profit(self, market_data: Dict):
        """Ajustar take-profit dinámicamente."""
        # Placeholder: en producción, ajustar parámetros de take-profit
        pass
    
    def _calculate_reward(self, prev_equity: float, current_equity: float) -> float:
        """Calcular recompensa basada en performance."""
        # P&L componente
        pnl_change = (current_equity - prev_equity) / prev_equity if prev_equity > 0 else 0
        
        # Sharpe ratio aproximado (necesitaría ventana histórica completa)
        sharpe_component = 0.0  # Placeholder
        
        # Drawdown penalty
        drawdown_penalty = self.max_drawdown * self.reward_config['drawdown_penalty']
        
        # Recompensa total
        reward = (
            pnl_change * self.reward_config['pnl_weight'] +
            sharpe_component * self.reward_config['sharpe_weight'] -
            drawdown_penalty
        )
        
        return float(reward)
    
    def _get_observation(self, market_data: Optional[Dict] = None) -> np.ndarray:
        """Obtener observación del entorno."""
        obs = np.zeros(self.observation_dim, dtype=np.float32)
        
        if market_data:
            # Features de indicadores
            obs[0] = market_data.get('rsi', 50) / 100.0  # Normalizar
            obs[1] = market_data.get('ema_fast', 0) / 1000.0 if market_data.get('ema_fast', 0) > 0 else 0
            obs[2] = market_data.get('ema_slow', 0) / 1000.0 if market_data.get('ema_slow', 0) > 0 else 0
            obs[3] = market_data.get('momentum makes_roc', 0)
            obs[4] = market_data.get('volume_ratio', 1)
            obs[5] = market_data.get('atr_percentile', 50) / 100.0
            
            # Contexto de mercado
            obs[6] = market_data.get('trend_strength', 0)
            obs[7] = market_data.get('volatility_regime_encoded', 0.5)  # 0=low, 0.5=normal, 1=high
            
            # Posición actual
            obs[8] = float(self.position)
            obs[9] = self.equity[-1] / 100000.0  # Normalizar equity
            
            # P&L reciente
            if len(self.equity) > 1:
                obs[10] = (self.equity[-1] - self.equity[-2]) / self.equity[-2] if self.equity[-2] > 0 else 0
        
        return obs


class ReinforcementLearningEngine(BaseLearningEngine):
    """
    Motor de Reinforcement Learning para aprender políticas óptimas de trading.
    
    Algoritmos soportados:
    - PPO (Proximal Policy Optimization)
    - A2C (Advantage Actor-Critic)
    - DDPG (Deep Deterministic Policy Gradient)
    
    Aprende a:
    - Cuándo comprar/vender/mantener
    - Ajustar stop-loss dinámicamente
    - Controlar exposición al riesgo
    """
    
    def __init__(self, config: Dict):
        """Inicializar motor de RL."""
        super().__init__("reinforcement_learning", config)
        
        if not STABLE_BASELINES3_AVAILABLE:
            raise ImportError(
                "stable-baselines3 es requerido para ReinforcementLearningEngine. "
                "Instala con: pip install stable-baselines3>=2.0.0 gym>=0.26.0"
            )
        
        self.algorithm = config.get("algorithm", "ppo")  # ppo, a2c, ddpg
        self.env_config = config.get("env_config", {})
        self.training_steps = config.get("training_steps", 100000)
        self.learning_rate = config.get("learning_rate", 3e-4)
        
        self.env = None
        self.agent = None
    
    def train(
        self,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Entrenar agente RL.
        
        Args:
            training_data: {
                'market_sequences': List[Dict],  # Secuencias de datos de mercado
                'historical_trades': List[Dict],  # Trades históricos para evaluación
                'initial_capital': float
            }
        """
        if not STABLE_BASELINES3_AVAILABLE:
            raise ImportError("stable-baselines3 es requerido")
        
        # Crear entorno
        env_config = self.env_config.copy()
        env_config['observation_dim'] = self._get_observation_dim(training_data)
        env_config['max_steps'] = len(training_data['market_sequences'])
        env_config['initial_capital'] = training_data.get('initial_capital', 100000.0)
        
        self.env = TradingEnv(env_config)
        
        # Crear agente según algoritmo
        if self.algorithm == "ppo":
            self.agent = PPO(
                "MlpPolicy",
                self.env,
                learning_rate=self.learning_rate,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                verbose=1
            )
        elif self.algorithm == "a2c":
            self.agent = A2C(
                "MlpPolicy",
                self.env,
                learning_rate=self.learning_rate,
                n_steps=5,
                gamma=0.99,
                verbose=1
            )
        elif self.algorithm == "ddpg":
            # DDPG requiere Box action space, adaptar entorno
            self.agent = DDPG(
                "MlpPolicy",
                self.env,
                learning_rate=self.learning_rate,
                verbose=1
            )
        else:
            raise ValueError(f"Algoritmo {self.algorithm} no soportado")
        
        # Entrenar
        logger.info(f"Entrenando agente {self.algorithm} por {self.training_steps} pasos...")
        
        # Wrapper para pasar datos de mercado al entorno
        market_sequences = training_data['market_sequences']
        
        class MarketDataCallback(BaseCallback):
            def __init__(self, market_data_list):
                super().__init__()
                self.market_data_list = market_data_list
                self.current_idx = 0
            
            def _on_step(self) -> bool:
                if self.current_idx < len(self.market_data_list):
                    # Resetear entorno con nuevos datos si es necesario
                    pass
                return True
        
        callback = MarketDataCallback(market_sequences)
        
        # Entrenamiento simplificado: iterar sobre secuencias
        total_reward = 0.0
        episodes = 0
        
        for episode in range(min(self.training_steps // 1000, 100)):  # Limitar episodios para demo
            obs = self.env.reset()
            done = False
            step = 0
            
            while not done and step < len(market_sequences):
                if step < len(market_sequences):
                    market_data = market_sequences[step]
                    
                    action, _ = self.agent.predict(obs, deterministic=False)
                    obs, reward, done, info = self.env.step(action, market_data)
                    
                    total_reward += reward
                    step += 1
                    
                    # Aprender (usar learn() del agente)
                    # En producción, usar callback o método learn() directo
            
            episodes += 1
        
        # Entrenar usando método learn() del agente
        self.agent.learn(total_timesteps=self.training_steps, callback=callback)
        
        self.is_trained = True
        
        # Evaluar en datos de validación
        metrics = {'total_reward': total_reward, 'episodes': episodes}
        
        if validation_data:
            eval_metrics = self._evaluate_on_data(validation_data)
            metrics.update(eval_metrics)
        
        return metrics
    
    def _get_observation_dim(self, training_data: Dict) -> int:
        """Determinar dimensión de observación."""
        if training_data.get('market_sequences'):
            sample = training_data['market_sequences'][0]
            return len(self._extract_features(sample))
        return 20  # Default
    
    def _extract_features(self, market_data: Dict) -> List[float]:
        """Extraer features de datos de mercado."""
        features = [
            market_data.get('rsi', 50) / 100.0,
            market_data.get('price', 0) / 1000.0,
            market_data.get('volume_ratio', 1),
            market_data.get('trend_strength', 0),
            market_data.get('volatility_percentile', 50) / 100.0
        ]
        return features
    
    def _evaluate_on_data(self, validation_data: Dict) -> Dict[str, float]:
        """Evaluar agente en datos de validación."""
        # Placeholder: implementar evaluación
        return {'validation_reward': 0.0, 'validation_sharpe': 0.0}
    
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generar acción recomendada.
        
        Args:
            features: {
                'market_data': Dict,      # Datos de mercado actuales
                'current_position': int,   # Posición actual
                'current_equity': float    # Equity actual
            }
        
        Returns:
            {
                'action': int,              # 0=HOLD, 1=BUY, 2=SELL, 3=Adjust SL, 4=Adjust TP
                'action_name': str,
                'confidence': float,
                'filter_adjustments': Dict, # Ajustes sugeridos para filtros
                'risk_adjustments': Dict    # Ajustes de riesgo (SL, TP, exposición)
            }
        """
        if not self.is_ready():
            return {
                'action': 0,
                'action_name': 'HOLD',
                'confidence': 0.0,
                'filter_adjustments': {},
                'risk_adjustments': {}
            }
        
        market_data = features['market_data']
        
        # Obtener observación
        obs = self.env._get_observation(market_data)
        
        # Predecir acción
        action, _ = self.agent.predict(obs, deterministic=True)
        
        action_names = ['HOLD', 'BUY', 'SELL', 'ADJUST_STOP_LOSS', 'ADJUST_TAKE_PROFIT']
        
        # Generar ajustes basados en acción
        filter_adjustments = {}
        risk_adjustments = {}
        
        if action == 1:  # BUY
            filter_adjustments = {'rsi_buy_min': -3, 'momentum_threshold': -0.005}
            risk_adjustments = {'position_size_multiplier': 1.0}
        elif action == 2:  # SELL
            risk_adjustments = {'close_position': True}
        elif action == 3:  # Ajustar stop-loss
            risk_adjustments = {'stop_loss_multiplier': 0.9}  # Ajustar más ajustado
        elif action == 4:  # Ajustar take-profit
            risk_adjustments = {'take_profit_multiplier': 1.1}  # Objetivo más alto
        
        return {
            'action': int(action),
            'action_name': action_names[action] if action < len(action_names) else 'UNKNOWN',
            'confidence': 0.8,  # Placeholder: calcular confianza real
            'filter_adjustments': filter_adjustments,
            'risk_adjustments': risk_adjustments
        }
    
    def evaluate(self, test_data: Dict[str, Any]) -> Dict[str, float]:
        """Evaluar agente en datos de prueba."""
        # Ejecutar agente en entorno de prueba
        obs = self.env.reset()
        total_reward = 0.0
        steps = 0
        
        market_sequences = test_data.get('market_sequences', [])
        
        for market_data in market_sequences:
            action, _ = self.agent.predict(obs, deterministic=True)
            obs, reward, done, info = self.env.step(action, market_data)
            total_reward += reward
            steps += 1
            
            if done:
                break
        
        sharpe = self._calculate_sharpe(self.env.equity) if len(self.env.equity) > 1 else 0.0
        
        return {
            'total_reward': float(total_reward),
            'final_equity': float(self.env.equity[-1]),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(self.env.max_drawdown),
            'total_trades': len(self.env.trades)
        }
    
    def _calculate_sharpe(self, equity_history: List[float]) -> float:
        """Calcular Sharpe ratio aproximado."""
        if len(equity_history) < 2:
            return 0.0
        
        returns = np.diff(equity_history) / equity_history[:-1]
        
        if np.std(returns) == 0:
            return 0.0
        
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizar
        return sharpe

