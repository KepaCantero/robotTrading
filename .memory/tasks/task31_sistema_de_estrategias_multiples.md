# 🎯 TASK-31: Sistema de Estrategias Múltiples - MVP Crítico

## 📋 **RESUMEN EJECUTIVO**

### **OBJETIVO**

Implementar un sistema modular de estrategias múltiples que permita ejecutar diferentes estrategias en backtesting y paper trading sin modificar código, basado en el principio rector: **"Don't build a strategy. Build a machine that can build, test, and run any strategy."**

### **PRIORIDAD**

🔴 **CRÍTICA MVP** - Necesaria para TASK-V2 (Backtesting Exhaustivo) y TASK-V3 (Métricas de Paper Trading)

### **IMPACTO**

- Permite probar múltiples estrategias en backtesting
- Facilita cambio de estrategias en paper trading sin reiniciar
- Habilita configuración dinámica de estrategias desde YAML
- Mantiene arquitectura modular y extensible

---

## 🏗️ **ARQUITECTURA PROPUESTA**

### **1. Strategy Protocol - Interfaz Universal**

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.models.market_data import MarketData
from app.models.signal import Signal
from app.models.portfolio import Portfolio

class BaseStrategy(ABC):
    """Clase base abstracta para todas las estrategias de trading."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.description = config.get("description", "")
        self.version = config.get("version", "1.0.0")
        self.is_active = False

    @abstractmethod
    def generate_signals(self, market_data: MarketData) -> List[Signal]:
        """Genera señales de trading basadas en datos del mercado."""
        pass

    @abstractmethod
    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """Verifica si la señal cumple criterios de riesgo."""
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Obtener parámetros actuales."""
        return self.config.copy()

    def update_parameters(self, params: Dict[str, Any]) -> None:
        """Actualizar parámetros dinámicamente."""
        self.config.update(params)

    def validate_config(self) -> bool:
        """Validar configuración de la estrategia."""
        required_params = self.get_required_parameters()
        return all(param in self.config for param in required_params)

    @abstractmethod
    def get_required_parameters(self) -> List[str]:
        """Obtener parámetros requeridos para la estrategia."""
        pass
```

### **2. Strategy Factory - Creación Dinámica**

```python
from typing import Type, Dict, Any, List
from app.strategies.base import BaseStrategy

class StrategyFactory:
    """Factory para crear estrategias dinámicamente."""

    def __init__(self):
        self.strategy_registry: Dict[str, Type[BaseStrategy]] = {}
        self._register_default_strategies()

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Registrar nueva estrategia."""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"Strategy class must inherit from BaseStrategy")
        self.strategy_registry[name] = strategy_class

    def create_strategy(self, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """Crear instancia de estrategia."""
        if name not in self.strategy_registry:
            raise ValueError(f"Strategy '{name}' not found. Available: {list(self.strategy_registry.keys())}")

        strategy_class = self.strategy_registry[name]
        strategy = strategy_class(config)

        # Validar configuración
        if not strategy.validate_config():
            raise ValueError(f"Invalid configuration for strategy '{name}'")

        return strategy

    def list_available_strategies(self) -> List[str]:
        """Listar estrategias disponibles."""
        return list(self.strategy_registry.keys())

    def _register_default_strategies(self) -> None:
        """Registrar estrategias por defecto."""
        from app.strategies.momentum import MomentumStrategy
        from app.strategies.mean_reversion import MeanReversionStrategy
        from app.strategies.pairs_trading import PairsTradingStrategy

        self.register_strategy("momentum", MomentumStrategy)
        self.register_strategy("mean_reversion", MeanReversionStrategy)
        self.register_strategy("pairs_trading", PairsTradingStrategy)
```

### **3. Strategy Registry - Registro de Estrategias**

```python
from typing import Optional, Dict, List
from app.strategies.base import BaseStrategy
from app.strategies.factory import StrategyFactory

class StrategyRegistry:
    """Registro centralizado de estrategias disponibles."""

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.factory = StrategyFactory()
        self.active_strategy: Optional[str] = None

    def load_strategy(self, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """Cargar estrategia desde configuración."""
        strategy = self.factory.create_strategy(name, config)
        self.strategies[name] = strategy
        return strategy

    def unload_strategy(self, name: str) -> None:
        """Descargar estrategia."""
        if name in self.strategies:
            strategy = self.strategies[name]
            strategy.is_active = False
            del self.strategies[name]

            # Si era la estrategia activa, limpiar
            if self.active_strategy == name:
                self.active_strategy = None

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Obtener estrategia cargada."""
        return self.strategies.get(name)

    def set_active_strategy(self, name: str) -> None:
        """Establecer estrategia activa."""
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not loaded")

        # Desactivar estrategia anterior
        if self.active_strategy and self.active_strategy in self.strategies:
            self.strategies[self.active_strategy].is_active = False

        # Activar nueva estrategia
        self.strategies[name].is_active = True
        self.active_strategy = name

    def get_active_strategy(self) -> Optional[BaseStrategy]:
        """Obtener estrategia activa."""
        if self.active_strategy:
            return self.strategies.get(self.active_strategy)
        return None

    def list_loaded_strategies(self) -> List[str]:
        """Listar estrategias cargadas."""
        return list(self.strategies.keys())

    def list_available_strategies(self) -> List[str]:
        """Listar estrategias disponibles para cargar."""
        return self.factory.list_available_strategies()
```

### **4. Strategy Config Loader**

```python
import yaml
import json
from typing import Dict, Any, List
from pathlib import Path

class StrategyConfigLoader:
    """Cargador de configuración de estrategias."""

    def __init__(self, config_path: str = "config/trading_strategies.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}

    def load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        if self.config_path.suffix == '.yaml' or self.config_path.suffix == '.yml':
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        elif self.config_path.suffix == '.json':
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")

        return self.config

    def get_active_strategies(self) -> List[str]:
        """Obtener estrategias activas."""
        return self.config.get("active_strategies", [])

    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Obtener configuración de estrategia específica."""
        strategies = self.config.get("strategies", {})
        if strategy_name not in strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found in config")
        return strategies[strategy_name]

    def get_backtesting_strategies(self) -> List[str]:
        """Obtener estrategias para backtesting."""
        return self.config.get("backtesting_strategies", [])

    def get_paper_trading_strategy(self) -> str:
        """Obtener estrategia para paper trading."""
        return self.config.get("paper_trading_strategy", "")

    def validate_config(self) -> bool:
        """Validar configuración."""
        required_keys = ["strategies", "active_strategies"]
        return all(key in self.config for key in required_keys)
```

### **5. Execution Engine Centralizado**

```python
from typing import List, Dict, Any
from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.models.market_data import MarketData
from app.models.signal import Signal
from app.models.portfolio import Portfolio
from app.services.strategy_logger import StrategyLogger

class ExecutionEngine:
    """Motor de ejecución centralizado."""

    def __init__(self, registry: StrategyRegistry, logger: StrategyLogger):
        self.registry = registry
        self.logger = logger
        self.is_running = False

    def run_cycle(self, market_data: MarketData, portfolio: Portfolio) -> List[Signal]:
        """Ejecutar ciclo de trading."""
        signals = []

        # Obtener estrategia activa
        active_strategy = self.registry.get_active_strategy()
        if not active_strategy:
            return signals

        try:
            # Generar señales
            strategy_signals = active_strategy.generate_signals(market_data)

            # Validar señales con risk check
            for signal in strategy_signals:
                if active_strategy.risk_check(signal, portfolio):
                    signals.append(signal)
                    self.logger.log_signal_generated(active_strategy.name, signal)
                else:
                    self.logger.log_signal_rejected(active_strategy.name, signal, "Risk check failed")

        except Exception as e:
            self.logger.log_strategy_error(active_strategy.name, str(e))

        return signals

    def execute_signal(self, signal: Signal) -> bool:
        """Ejecutar señal de trading."""
        try:
            # Aquí se integraría con el broker o paper trading
            self.logger.log_signal_executed(signal)
            return True
        except Exception as e:
            self.logger.log_execution_error(signal, str(e))
            return False
```

### **6. Strategy Logger / Metrics**

```python
from typing import Dict, Any, List
from datetime import datetime
from app.models.signal import Signal
import json

class StrategyLogger:
    """Logger centralizado para estrategias."""

    def __init__(self, log_path: str = "logs/strategy_logs.json"):
        self.log_path = log_path
        self.logs: List[Dict[str, Any]] = []

    def log_signal_generated(self, strategy_name: str, signal: Signal) -> None:
        """Log de señal generada."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "signal_generated",
            "strategy": strategy_name,
            "signal": signal.dict(),
            "level": "INFO"
        }
        self.logs.append(log_entry)
        self._save_logs()

    def log_signal_rejected(self, strategy_name: str, signal: Signal, reason: str) -> None:
        """Log de señal rechazada."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "signal_rejected",
            "strategy": strategy_name,
            "signal": signal.dict(),
            "reason": reason,
            "level": "WARNING"
        }
        self.logs.append(log_entry)
        self._save_logs()

    def log_signal_executed(self, signal: Signal) -> None:
        """Log de señal ejecutada."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "signal_executed",
            "signal": signal.dict(),
            "level": "INFO"
        }
        self.logs.append(log_entry)
        self._save_logs()

    def log_strategy_error(self, strategy_name: str, error: str) -> None:
        """Log de error de estrategia."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "strategy_error",
            "strategy": strategy_name,
            "error": error,
            "level": "ERROR"
        }
        self.logs.append(log_entry)
        self._save_logs()

    def log_execution_error(self, signal: Signal, error: str) -> None:
        """Log de error de ejecución."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "execution_error",
            "signal": signal.dict(),
            "error": error,
            "level": "ERROR"
        }
        self.logs.append(log_entry)
        self._save_logs()

    def _save_logs(self) -> None:
        """Guardar logs en archivo."""
        with open(self.log_path, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def get_strategy_metrics(self, strategy_name: str) -> Dict[str, Any]:
        """Obtener métricas de estrategia."""
        strategy_logs = [log for log in self.logs if log.get("strategy") == strategy_name]

        signals_generated = len([log for log in strategy_logs if log["event"] == "signal_generated"])
        signals_executed = len([log for log in strategy_logs if log["event"] == "signal_executed"])
        signals_rejected = len([log for log in strategy_logs if log["event"] == "signal_rejected"])
        errors = len([log for log in strategy_logs if log["event"] == "strategy_error"])

        return {
            "strategy": strategy_name,
            "signals_generated": signals_generated,
            "signals_executed": signals_executed,
            "signals_rejected": signals_rejected,
            "execution_rate": signals_executed / signals_generated if signals_generated > 0 else 0,
            "error_count": errors,
            "total_logs": len(strategy_logs)
        }
```

### **7. Config-driven Strategy Selection**

```yaml
# trading_strategies.yaml
strategies:
  momentum:
    class: "MomentumStrategy"
    config:
      name: "momentum"
      description: "Estrategia de momentum basada en RSI y EMA"
      version: "1.0.0"
      rsi_threshold: 40
      momentum_threshold: 0.02
      stop_loss: 0.05
      take_profit: 0.10
      max_position_size: 0.1

  mean_reversion:
    class: "MeanReversionStrategy"
    config:
      name: "mean_reversion"
      description: "Estrategia de reversión a la media basada en Z-score"
      version: "1.0.0"
      z_score_threshold: 2.0
      lookback_period: 20
      stop_loss: 0.03
      take_profit: 0.06
      max_position_size: 0.08

  pairs_trading:
    class: "PairsTradingStrategy"
    config:
      name: "pairs_trading"
      description: "Estrategia de trading de pares basada en cointegración"
      version: "1.0.0"
      cointegration_threshold: 0.05
      spread_threshold: 2.0
      stop_loss: 0.04
      take_profit: 0.08
      max_position_size: 0.06

# Configuración activa
active_strategies: ["momentum"]
backtesting_strategies: ["momentum", "mean_reversion"]
paper_trading_strategy: "momentum"

# Configuración de logging
logging:
  level: "INFO"
  log_path: "logs/strategy_logs.json"
  max_log_size: "10MB"
  backup_count: 5
```

### **8. Integración con Backtesting y Paper Trading**

#### **Backtesting Adapter**

```python
from typing import List, Dict, Any
from app.strategies.registry import StrategyRegistry
from app.strategies.config_loader import StrategyConfigLoader
from app.models.market_data import MarketData
from app.models.signal import Signal

class BacktestingAdapter:
    """Adapter para ejecutar estrategias en backtesting."""

    def __init__(self, registry: StrategyRegistry, config_loader: StrategyConfigLoader):
        self.registry = registry
        self.config_loader = config_loader

    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Ejecutar backtesting con estrategias configuradas."""
        results = {}

        # Obtener estrategias para backtesting
        backtesting_strategies = self.config_loader.get_backtesting_strategies()

        for strategy_name in backtesting_strategies:
            try:
                # Cargar estrategia
                strategy_config = self.config_loader.get_strategy_config(strategy_name)
                strategy = self.registry.load_strategy(strategy_name, strategy_config["config"])

                # Ejecutar backtesting
                strategy_results = self._run_strategy_backtest(strategy, start_date, end_date)
                results[strategy_name] = strategy_results

            except Exception as e:
                results[strategy_name] = {"error": str(e)}

        return results

    def _run_strategy_backtest(self, strategy, start_date: str, end_date: str) -> Dict[str, Any]:
        """Ejecutar backtesting para una estrategia específica."""
        # Aquí se integraría con el sistema de backtesting existente
        # Por ahora, estructura básica
        return {
            "strategy": strategy.name,
            "start_date": start_date,
            "end_date": end_date,
            "total_signals": 0,
            "profitable_signals": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
```

#### **Paper Trading Adapter**

```python
from typing import List, Dict, Any
from app.strategies.registry import StrategyRegistry
from app.strategies.config_loader import StrategyConfigLoader
from app.models.market_data import MarketData
from app.models.signal import Signal

class PaperTradingAdapter:
    """Adapter para ejecutar estrategias en paper trading."""

    def __init__(self, registry: StrategyRegistry, config_loader: StrategyConfigLoader):
        self.registry = registry
        self.config_loader = config_loader
        self.is_running = False

    def start_paper_trading(self) -> None:
        """Iniciar paper trading con estrategia configurada."""
        paper_trading_strategy = self.config_loader.get_paper_trading_strategy()

        if not paper_trading_strategy:
            raise ValueError("No paper trading strategy configured")

        # Cargar estrategia
        strategy_config = self.config_loader.get_strategy_config(paper_trading_strategy)
        strategy = self.registry.load_strategy(paper_trading_strategy, strategy_config["config"])

        # Establecer como estrategia activa
        self.registry.set_active_strategy(paper_trading_strategy)

        self.is_running = True

    def stop_paper_trading(self) -> None:
        """Detener paper trading."""
        self.is_running = False

        # Desactivar estrategia activa
        active_strategy = self.registry.get_active_strategy()
        if active_strategy:
            active_strategy.is_active = False

    def switch_strategy(self, new_strategy_name: str) -> None:
        """Cambiar estrategia en paper trading."""
        if not self.is_running:
            raise ValueError("Paper trading not running")

        # Cargar nueva estrategia
        strategy_config = self.config_loader.get_strategy_config(new_strategy_name)
        strategy = self.registry.load_strategy(new_strategy_name, strategy_config["config"])

        # Cambiar estrategia activa
        self.registry.set_active_strategy(new_strategy_name)
```

---

## 🔧 **IMPLEMENTACIÓN DETALLADA**

### **Fase 1: Strategy Protocol y Factory**

1. **Crear Strategy Protocol**

   - Definir interfaz común para todas las estrategias
   - Implementar métodos estándar (on_data, on_signal, on_exit)
   - Añadir gestión de parámetros dinámicos

2. **Implementar Strategy Factory**

   - Factory pattern para creación dinámica
   - Registro de estrategias disponibles
   - Validación de configuración

3. **Crear Strategy Registry**
   - Registro centralizado de estrategias
   - Gestión del ciclo de vida de estrategias
   - Hot-swapping de estrategias

### **Fase 2: Config-driven Selection**

1. **Configuración YAML**

   - Definir estructura de configuración de estrategias
   - Parámetros específicos por estrategia
   - Selección de estrategia activa

2. **Config Loader**

   - Cargar configuración desde YAML
   - Validar configuración de estrategias
   - Aplicar configuración a estrategias

3. **Dynamic Strategy Switching**
   - Cambiar estrategia sin reiniciar
   - Preservar estado de estrategias
   - Validar transiciones

### **Fase 3: Integration con Backtesting y Paper Trading**

1. **Backtesting Integration**

   - Ejecutar múltiples estrategias en backtesting
   - Comparar resultados entre estrategias
   - Métricas estandarizadas

2. **Paper Trading Integration**

   - Cambiar estrategia en paper trading
   - Preservar posiciones existentes
   - Transición suave entre estrategias

3. **API Endpoints**
   - Endpoints para gestión de estrategias
   - Cambio dinámico de estrategia
   - Monitoreo de estrategias activas

---

## 📊 **ESTRATEGIAS A IMPLEMENTAR**

### **1. Momentum Strategy (Existente)**

```python
class MomentumStrategy:
    """Estrategia de momentum basada en RSI, EMA y volumen."""

    def __init__(self, config: Dict[str, Any]):
        self.rsi_threshold = config.get("rsi_threshold", 40)
        self.momentum_threshold = config.get("momentum_threshold", 0.02)
        self.stop_loss = config.get("stop_loss", 0.05)
        self.take_profit = config.get("take_profit", 0.10)
```

### **2. Mean Reversion Strategy (Nueva)**

```python
class MeanReversionStrategy:
    """Estrategia de reversión a la media basada en Z-score."""

    def __init__(self, config: Dict[str, Any]):
        self.z_score_threshold = config.get("z_score_threshold", 2.0)
        self.lookback_period = config.get("lookback_period", 20)
        self.stop_loss = config.get("stop_loss", 0.03)
        self.take_profit = config.get("take_profit", 0.06)
```

### **3. Pairs Trading Strategy (Nueva)**

```python
class PairsTradingStrategy:
    """Estrategia de trading de pares basada en cointegración."""

    def __init__(self, config: Dict[str, Any]):
        self.cointegration_threshold = config.get("cointegration_threshold", 0.05)
        self.spread_threshold = config.get("spread_threshold", 2.0)
        self.stop_loss = config.get("stop_loss", 0.04)
        self.take_profit = config.get("take_profit", 0.08)
```

---

## 🧪 **TESTING STRATEGY**

### **Unit Tests**

- Strategy Protocol compliance
- Factory creation and registration
- Registry management
- Config loading and validation

### **Integration Tests**

- Strategy switching in backtesting
- Strategy switching in paper trading
- Parameter updates
- Error handling

### **End-to-End Tests**

- Complete strategy lifecycle
- Multi-strategy backtesting
- Paper trading with different strategies
- Configuration changes

---

## 📈 **MÉTRICAS DE ÉXITO**

### **Funcionalidad**

- ✅ Múltiples estrategias ejecutándose en backtesting
- ✅ Cambio dinámico de estrategia en paper trading
- ✅ Configuración YAML funcional
- ✅ Hot-swapping de estrategias

### **Performance**

- ✅ Carga de estrategia < 100ms
- ✅ Cambio de estrategia < 200ms
- ✅ Sin memory leaks en hot-swapping
- ✅ Preservación de estado

### **Robustez**

- ✅ Manejo de errores en carga de estrategia
- ✅ Validación de configuración
- ✅ Rollback en caso de error
- ✅ Logging completo

---

## 🚀 **IMPLEMENTACIÓN RECOMENDADA**

### **Sprint 1 (Semana 1)**

- Strategy Protocol y Factory
- Strategy Registry básico
- Config YAML básico

### **Sprint 2 (Semana 2)**

- Integration con Backtesting
- Integration con Paper Trading
- API Endpoints básicos

### **Sprint 3 (Semana 3)**

- Testing completo
- Documentación
- Optimización

---

## 🎯 **BENEFICIOS PARA EL MVP**

### **Para Backtesting (TASK-V2)**

- Probar múltiples estrategias simultáneamente
- Comparar rendimiento entre estrategias
- Optimización de parámetros por estrategia

### **Para Paper Trading (TASK-V3)**

- Cambiar estrategia sin reiniciar sistema
- Probar estrategias en tiempo real
- Transición suave entre estrategias

### **Para Configuración (TASK 10)**

- Configuración centralizada de estrategias
- Parámetros específicos por estrategia
- Cambios dinámicos sin código

---

## 📋 **DEPENDENCIAS**

### **Tareas Previas**

- ✅ TASK 1-5: Base del sistema
- ✅ TASK 8: Análisis de costos
- ✅ TASK 9: Optimización de parámetros

### **Tareas Relacionadas**

- 🔄 TASK-V2: Backtesting Exhaustivo
- 🔄 TASK-V3: Métricas de Paper Trading
- 🔄 TASK 10: Centralización de Configuración

---

## 🎉 **CONCLUSIÓN**

Esta tarea implementa exactamente lo que el usuario necesita: **un sistema que puede ejecutar diferentes estrategias en backtesting y paper trading sin modificar código**.

Se alinea perfectamente con:

- El principio rector del texto: "Build a machine that can build, test, and run any strategy"
- Los objetivos del MVP: Backtesting exhaustivo y paper trading funcional
- La arquitectura actual: Modular y extensible

**¿Proceder a implementar TASK-31: Sistema de Estrategias Múltiples?**
