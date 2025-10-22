# 🎯 TASK-35: Arquitectura de Modos Operativos (LIVE/RECORDING/BACKTEST) - MVP Crítico

## 📋 **RESUMEN EJECUTIVO**

### **OBJETIVO**

Implementar arquitectura de modos operativos que permita que el bot funcione con el mismo código base en distintos entornos: LIVE (datos en tiempo real), RECORDING (captura de datos), y BACKTEST (reproducción de datos históricos).

### **PRIORIDAD**

🟠 **FASE 2 MVP** - Necesaria para TASK-V2 (Backtesting Exhaustivo) y TASK-V3 (Métricas de Paper Trading)

### **IMPACTO**

- Mismo código base para todos los modos
- Flexibilidad de testing y desarrollo
- Reproducibilidad de resultados
- Desarrollo eficiente

---

## 🏗️ **ARQUITECTURA PROPUESTA**

### **1. Mode Manager**

```python
class ModeManager:
    """Gestiona los modos operativos del sistema."""

    def __init__(self):
        self.current_mode: TradingMode = TradingMode.BACKTEST
        self.mode_configs: Dict[TradingMode, Dict[str, Any]] = {}
        self.data_feeds: Dict[TradingMode, MarketDataFeed] = {}

    def set_mode(self, mode: TradingMode, config: Dict[str, Any]) -> None:
        """Establece el modo operativo."""
        self.current_mode = mode
        self.mode_configs[mode] = config
        self._initialize_data_feed(mode, config)

    def get_current_feed(self) -> MarketDataFeed:
        """Obtiene el feed de datos actual."""
        return self.data_feeds[self.current_mode]

    def _initialize_data_feed(self, mode: TradingMode, config: Dict[str, Any]) -> None:
        """Inicializa el feed de datos según el modo."""
        if mode == TradingMode.LIVE:
            self.data_feeds[mode] = IBKRLiveFeed(config)
        elif mode == TradingMode.RECORDING:
            self.data_feeds[mode] = RecordingDataFeed(config)
        elif mode == TradingMode.BACKTEST:
            self.data_feeds[mode] = HistoricalDataFeed(config)
```

### **2. Market Data Feed Interface**

```python
class MarketDataFeed(Protocol):
    """Interfaz común para todos los feeds de datos."""

    async def get_market_data(self, symbol: str) -> MarketData:
        """Obtiene datos de mercado."""
        ...

    async def subscribe_to_updates(self, symbol: str, callback: Callable) -> None:
        """Suscribe a actualizaciones de datos."""
        ...

    async def start(self) -> None:
        """Inicia el feed de datos."""
        ...

    async def stop(self) -> None:
        """Detiene el feed de datos."""
        ...

class IBKRLiveFeed:
    """Feed de datos en tiempo real de IBKR."""

    def __init__(self, config: Dict[str, Any]):
        self.ibkr_client = IBKRClient(config)
        self.subscriptions: Dict[str, Callable] = {}

    async def get_market_data(self, symbol: str) -> MarketData:
        """Obtiene datos de mercado en tiempo real."""
        return await self.ibkr_client.get_market_data(symbol)

    async def subscribe_to_updates(self, symbol: str, callback: Callable) -> None:
        """Suscribe a actualizaciones en tiempo real."""
        self.subscriptions[symbol] = callback
        await self.ibkr_client.subscribe(symbol, callback)

class HistoricalDataFeed:
    """Feed de datos históricos para backtesting."""

    def __init__(self, config: Dict[str, Any]):
        self.data_source = config["data_source"]
        self.current_time = config["start_date"]
        self.end_time = config["end_date"]
        self.time_step = config["time_step"]

    async def get_market_data(self, symbol: str) -> MarketData:
        """Obtiene datos históricos."""
        return await self._load_historical_data(symbol, self.current_time)

    async def advance_time(self) -> None:
        """Avanza el tiempo en el backtest."""
        self.current_time += self.time_step

class RecordingDataFeed:
    """Feed de datos para grabación."""

    def __init__(self, config: Dict[str, Any]):
        self.source_feed = IBKRLiveFeed(config["source_config"])
        self.recorder = MarketRecorder(config["recording_config"])

    async def get_market_data(self, symbol: str) -> MarketData:
        """Obtiene datos y los graba."""
        data = await self.source_feed.get_market_data(symbol)
        await self.recorder.record_data(symbol, data)
        return data
```

### **3. Trading Engine Adaptable**

```python
class TradingEngine:
    """Motor de trading adaptable a diferentes modos."""

    def __init__(self, mode_manager: ModeManager):
        self.mode_manager = mode_manager
        self.strategies: Dict[str, Strategy] = {}
        self.portfolio_manager = PortfolioManager()

    async def run_trading_cycle(self) -> None:
        """Ejecuta un ciclo de trading."""
        # Obtener datos según el modo actual
        data_feed = self.mode_manager.get_current_feed()

        # Procesar señales
        for strategy_name, strategy in self.strategies.items():
            market_data = await data_feed.get_market_data(strategy.symbol)
            signal = await strategy.generate_signal(market_data)

            if signal:
                await self._execute_signal(signal, strategy_name)

        # Avanzar tiempo si es backtest
        if self.mode_manager.current_mode == TradingMode.BACKTEST:
            await data_feed.advance_time()

    async def _execute_signal(self, signal: Signal, strategy_name: str) -> None:
        """Ejecuta una señal de trading."""
        # Lógica de ejecución independiente del modo
        order = await self.portfolio_manager.create_order(signal)
        await self.portfolio_manager.execute_order(order)
```

---

## 🔧 **IMPLEMENTACIÓN DETALLADA**

### **Fase 1: Mode Manager**

1. **Crear ModeManager**

   - Gestión de modos operativos
   - Configuración por modo
   - Inicialización de feeds

2. **Implementar TradingMode Enum**

   - LIVE: Datos en tiempo real
   - RECORDING: Captura de datos
   - BACKTEST: Datos históricos

3. **Crear Sistema de Configuración**
   - Configuración por modo
   - Parámetros específicos
   - Validación de configuración

### **Fase 2: Market Data Feed Interface**

1. **Crear MarketDataFeed Protocol**

   - Interfaz común para todos los feeds
   - Métodos estándar
   - Tipos de datos consistentes

2. **Implementar IBKRLiveFeed**

   - Conexión a IBKR en tiempo real
   - Suscripciones a datos
   - Manejo de errores de conexión

3. **Implementar HistoricalDataFeed**

   - Carga de datos históricos
   - Avance de tiempo
   - Simulación de ticks

4. **Implementar RecordingDataFeed**
   - Grabación de datos en tiempo real
   - Almacenamiento local
   - Compresión de datos

### **Fase 3: Trading Engine Adaptable**

1. **Crear TradingEngine**

   - Motor adaptable a modos
   - Lógica común de trading
   - Gestión de estrategias

2. **Implementar PortfolioManager**

   - Gestión de portfolio
   - Ejecución de órdenes
   - Cálculo de métricas

3. **Crear Sistema de Estrategias**
   - Estrategias independientes del modo
   - Generación de señales
   - Gestión de parámetros

---

## 📊 **MODOS OPERATIVOS**

### **1. LIVE Mode**

- **Fuente**: IBKR API en tiempo real
- **Uso**: Trading en vivo
- **Características**: Latencia real, datos actuales
- **Configuración**: API keys, símbolos, frecuencia

### **2. RECORDING Mode**

- **Fuente**: IBKR API + grabación local
- **Uso**: Captura de datos para testing
- **Características**: Grabación simultánea, datos reales
- **Configuración**: Destino de grabación, compresión

### **3. BACKTEST Mode**

- **Fuente**: Datos históricos o grabados
- **Uso**: Testing y validación
- **Características**: Reproducibilidad, velocidad controlada
- **Configuración**: Rango de fechas, frecuencia de datos

---

## 🧪 **TESTING STRATEGY**

### **Unit Tests**

- ModeManager functionality
- MarketDataFeed implementations
- TradingEngine adaptability

### **Integration Tests**

- Integration with TASK-V2
- Integration with TASK-V3
- Mode switching functionality

### **End-to-End Tests**

- Complete trading cycle in each mode
- Data consistency across modes
- Performance comparison

---

## 📈 **MÉTRICAS DE ÉXITO**

### **Funcionalidad**

- ✅ Mismo código base para todos los modos
- ✅ Cambio de modo sin reiniciar
- ✅ Consistencia de datos entre modos
- ✅ Reproducibilidad de resultados

### **Performance**

- ✅ Cambio de modo < 1s
- ✅ Inicialización de feed < 5s
- ✅ Sin pérdida de datos en transiciones
- ✅ Performance optimizada por modo

### **Robustez**

- ✅ Manejo de errores por modo
- ✅ Recuperación de fallos de conexión
- ✅ Validación de configuración
- ✅ Logging específico por modo

---

## 🚀 **IMPLEMENTACIÓN RECOMENDADA**

### **Sprint 1 (Semana 1)**

- ModeManager
- TradingMode enum
- Basic configuration system

### **Sprint 2 (Semana 2)**

- MarketDataFeed interface
- IBKRLiveFeed implementation
- HistoricalDataFeed implementation

### **Sprint 3 (Semana 3)**

- RecordingDataFeed implementation
- TradingEngine adaptability
- Integration with existing tasks

---

## 🎯 **BENEFICIOS PARA EL MVP**

### **Para TASK-V2 (Backtesting Exhaustivo)**

- Backtesting con datos históricos
- Reproducibilidad de resultados
- Testing de estrategias

### **Para TASK-V3 (Métricas de Paper Trading)**

- Paper trading con datos reales
- Comparación con backtesting
- Validación de estrategias

### **Para Desarrollo Eficiente**

- Mismo código para todos los modos
- Testing sin riesgo
- Desarrollo iterativo

---

## 📋 **DEPENDENCIAS**

### **Tareas Previas**

- ✅ TASK 1-5: Base del sistema
- ✅ TASK 8: Análisis de costos
- ✅ TASK 9: Optimización de parámetros

### **Tareas Relacionadas**

- 🔄 TASK-V2: Backtesting Exhaustivo
- 🔄 TASK-V3: Métricas de Paper Trading
- 🔄 TASK-31: Sistema de Estrategias Múltiples

---

## 🎉 **CONCLUSIÓN**

Esta tarea implementa las **Lecciones 22, 23, 24, 47, 80** de las 100 lecciones de trading algorítmico, enfocándose en:

- **Arquitectura de modos operativos**
- **Mismo código base para todos los modos**
- **Flexibilidad de testing y desarrollo**
- **Reproducibilidad de resultados**

Se integra perfectamente con **TASK-V2** y **TASK-V3** y proporciona la base para un sistema de trading algorítmico flexible y eficiente.

**¿Proceder a implementar TASK-35: Arquitectura de Modos Operativos?**
