# Plan de Refactorizacion: God Classes Criticas

## Resumen Ejecutivo

| Archivo | Lineas Actuales | Responsabilidades | Archivos Objetivo |
|---------|----------------|-------------------|-------------------|
| `comprehensive_backtest_runner.py` | 4,687 | 8+ | 6 archivos (~400-500 c/u) |
| `centralized_config.py` | 3,816 | 12+ | 8 archivos (~400-500 c/u) |
| `compliance_engine.py` | 3,674 | 17+ | 7 archivos (~400-500 c/u) |
| `select_strategy.py` | 2,300 | 6+ | 5 archivos (~400-500 c/u) |

**Total**: 14,477 lineas -> ~26 archivos modulares

---

## 1. comprehensive_backtest_runner.py (4,687 lineas)

### Responsabilidades Identificadas

1. **Orquestacion de Backtests** - Coordinacion de ejecucion multi-estrategia
2. **Ejecucion de Trades** - Simulacion de ordenes y fills
3. **Calculo de Metricas** - Sharpe, Sortino, drawdown, returns
4. **Generacion de Reportes** - HTML, JSON, visualizaciones
5. **Validacion de Datos** - Calidad de datos, integridad
6. **Gestion de Capital** - Position sizing, capital allocation
7. **Walk-Forward Analysis** - Validacion robusta
8. **Regime Detection** - Deteccion de regimenes de mercado

### Estructura Propuesta

```
/app/backtesting/runner/
├── __init__.py                    # Exports publicos
├── orchestrator.py                # BacktestOrchestrator (350 lineas)
├── executor.py                    # BacktestExecutor (400 lineas)
├── metrics_calculator.py          # MetricsCalculator (400 lineas)
├── reporter.py                    # BacktestReporter (350 lineas)
├── validator.py                   # BacktestValidator (300 lineas)
├── capital_manager.py             # CapitalManager (350 lineas)
└── factory.py                     # RunnerFactory (150 lineas)
```

### Nuevas Clases

#### 1.1 BacktestOrchestrator (`orchestrator.py`)
**Responsabilidad**: Coordinar la ejecucion secuencial/paralela de backtests
```python
class BacktestOrchestrator:
    """Orquesta la ejecucion de backtests multi-estrategia."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.executor = BacktestExecutor(config)
        self.reporter = BacktestReporter()
        self.validator = BacktestValidator()

    def run_single(self, strategy, data) -> BacktestResult
    def run_multi(self, strategies, data) -> List[BacktestResult]
    def run_walk_forward(self, strategy, data) -> WalkForwardResult
```

**Dependencias**: BacktestExecutor, BacktestReporter, BacktestValidator

#### 1.2 BacktestExecutor (`executor.py`)
**Responsabilidad**: Ejecutar la simulacion de trades dia a dia
```python
class BacktestExecutor:
    """Ejecuta la simulacion de backtest."""

    def __init__(self, config: BacktestConfig):
        self.order_simulator = OrderFillSimulator()
        self.capital_manager = CapitalManager(config)

    def execute_bar(self, bar: Bar, portfolio: Portfolio) -> List[Trade]
    def execute_signal(self, signal: Signal, portfolio: Portfolio) -> Optional[Trade]
    def process_pending_orders(self) -> List[Order]
```

**Dependencias**: OrderFillSimulator, CapitalManager

#### 1.3 MetricsCalculator (`metrics_calculator.py`)
**Responsabilidad**: Calcular todas las metricas de rendimiento
```python
class MetricsCalculator:
    """Calcula metricas de rendimiento de backtest."""

    def calculate_returns(self, trades: List[Trade]) -> pd.DataFrame
    def calculate_risk_metrics(self, returns: pd.Series) -> RiskMetrics
    def calculate_trade_statistics(self, trades: List[Trade]) -> TradeStats
    def calculate_attribution(self, trades: List[Trade]) -> Attribution
```

**Dependencias**: Ninguna (utilitario puro)

#### 1.4 BacktestReporter (`reporter.py`)
**Responsabilidad**: Generar reportes en multiples formatos
```python
class BacktestReporter:
    """Genera reportes de backtest."""

    def generate_html(self, result: BacktestResult) -> str
    def generate_json(self, result: BacktestResult) -> dict
    def generate_summary(self, result: BacktestResult) -> str
    def generate_comparison(self, results: List[BacktestResult]) -> str
```

**Dependencias**: MetricsCalculator

#### 1.5 BacktestValidator (`validator.py`)
**Responsabilidad**: Validar integridad de datos y resultados
```python
class BacktestValidator:
    """Valida datos y resultados de backtest."""

    def validate_data(self, data: pd.DataFrame) -> ValidationResult
    def validate_signals(self, signals: List[Signal]) -> ValidationResult
    def validate_result(self, result: BacktestResult) -> ValidationResult
    def check_look_ahead_bias(self, data, signals) -> bool
```

**Dependencias**: Ninguna

#### 1.6 CapitalManager (`capital_manager.py`)
**Responsabilidad**: Gestionar capital y position sizing
```python
class CapitalManager:
    """Gestiona capital y position sizing."""

    def __init__(self, config: CapitalConfig):
        self.config = config

    def calculate_position_size(self, signal, portfolio) -> Decimal
    def update_capital(self, trade: Trade) -> None
    def check_limits(self, order: Order) -> bool
    def apply_kelly_criterion(self, trades: List[Trade]) -> float
```

**Dependencias**: CapitalConfig

#### 1.7 RunnerFactory (`factory.py`)
**Responsabilidad**: Crear instancias configuradas del runner
```python
class RunnerFactory:
    """Factory para crear instancias de backtest runner."""

    @staticmethod
    def create_default() -> BacktestOrchestrator

    @staticmethod
    def create_from_config(config: dict) -> BacktestOrchestrator

    @staticmethod
    def create_multi_strategy() -> BacktestOrchestrator
```

### Plan de Migracion

**Fase 1: Extraccion (Semana 1)**
1. Crear estructura de directorios
2. Extraer MetricsCalculator (mas independiente)
3. Extraer BacktestValidator
4. Crear tests unitarios para cada modulo

**Fase 2: Refactorizacion (Semana 2)**
1. Extraer BacktestExecutor
2. Extraer CapitalManager
3. Extraer BacktestReporter
4. Adaptar imports en codigo existente

**Fase 3: Integracion (Semana 3)**
1. Crear BacktestOrchestrator como fachada
2. Crear RunnerFactory
3. Actualizar todos los clientes
4. Marcar archivo original como deprecated

**Fase 4: Limpieza (Semana 4)**
1. Eliminar codigo duplicado
2. Actualizar documentacion
3. Verificar cobertura de tests

---

## 2. centralized_config.py (3,816 lineas)

### Responsabilidades Identificadas

1. **Trading Thresholds** - Limites de trading (RSI, position sizing, stops)
2. **Infrastructure Config** - Database, Redis, API
3. **Risk Management** - Circuit breakers, VaR, drawdown
4. **Monitoring Config** - Logging, metrics, alerting
5. **Compliance Config** - PDT, wash sale, position limits
6. **Strategy-Specific Config** - Momentum, mean reversion, pairs
7. **Execution Config** - Latency, slippage, order routing
8. **Tax Config** - FIFO, dividend rates, modelo 720
9. **Broker Config** - IBKR, Alpaca, rate limits
10. **Alerting Config** - Thresholds, notifications
11. **Position Monitor Config** - Timeouts, intervals
12. **Helper Functions** - get_config(), validators

### Estructura Propuesta

```
/app/shared/config/
├── __init__.py                    # Exports publicos
├── centralized_config.py          # Fachada principal (200 lineas)
├── thresholds/
│   ├── __init__.py
│   ├── trading_thresholds.py      # TradingThresholds (400 lineas)
│   ├── risk_thresholds.py         # RiskThresholds (350 lineas)
│   └── signal_thresholds.py       # SignalThresholds (300 lineas)
├── infrastructure/
│   ├── __init__.py
│   ├── database_config.py         # DatabaseConfig (250 lineas)
│   ├── redis_config.py            # RedisConfig (200 lineas)
│   └── api_config.py              # APIConfig (200 lineas)
├── strategies/
│   ├── __init__.py
│   ├── strategy_config.py         # StrategyConfig (250 lineas)
│   ├── stock_allocation.py        # StockAllocationSettings (400 lineas)
│   └── profile_config.py          # ProfileConfig (300 lineas)
├── monitoring/
│   ├── __init__.py
│   ├── logging_config.py          # LoggingConfig (200 lineas)
│   └── metrics_config.py          # MetricsConfig (250 lineas)
├── compliance/
│   ├── __init__.py
│   ├── trading_rules.py           # TradingRulesConfig (300 lineas)
│   └── tax_config.py              # TaxConfig (250 lineas)
├── execution/
│   ├── __init__.py
│   ├── broker_config.py           # BrokerConfig (350 lineas)
│   └── rate_limits.py             # RateLimitConfig (250 lineas)
└── helpers.py                     # get_config(), validators (200 lineas)
```

### Nuevas Clases

#### 2.1 TradingThresholds (`thresholds/trading_thresholds.py`)
```python
class TradingThresholds(BaseModel):
    """Thresholds centrales de trading."""
    # Signal thresholds
    min_signal_strength: float
    min_signal_confidence: float
    min_liquidity_score: float

    # Technical indicators
    rsi_oversold: float
    rsi_overbought: float

    # Position sizing
    max_position_size: float
    min_position_size: float

    # Risk management
    stop_loss_pct: float
    take_profit_pct: float
    daily_loss_limit: float
    max_drawdown_limit: float
```

#### 2.2 RiskThresholds (`thresholds/risk_thresholds.py`)
```python
class RiskThresholds(BaseModel):
    """Thresholds de gestion de riesgo."""
    # Circuit breakers
    circuit_breaker_daily_loss: float
    circuit_breaker_drawdown: float
    circuit_breaker_volatility: float

    # Portfolio limits
    max_total_exposure: float
    max_sector_exposure: float
    max_correlation: float

    # VaR limits
    max_daily_var_95: float
    max_portfolio_volatility: float
```

#### 2.3 BrokerConfig (`execution/broker_config.py`)
```python
class BrokerConfig(BaseModel):
    """Configuracion de brokers."""
    # IBKR
    ibkr_host: str
    ibkr_port: int
    ibkr_client_id: int

    # Alpaca
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str

    # Rate limits
    rate_limit_ibkr_requests_per_second: float
    rate_limit_alpaca_requests_per_second: float
```

#### 2.4 CentralizedConfigFacade (`centralized_config.py`)
```python
class CentralizedConfig(BaseSettings):
    """Fachada principal de configuracion."""
    # Environment
    environment: Environment
    debug: bool

    # Composed configs
    trading: TradingThresholds = Field(default_factory=TradingThresholds)
    risk: RiskThresholds = Field(default_factory=RiskThresholds)
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)
    strategies: StrategyConfig = Field(default_factory=StrategyConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    execution: BrokerConfig = Field(default_factory=BrokerConfig)

    # Helper methods
    def get_strategy_config(self, strategy_name: str) -> StrategySpecificConfig
    def validate_all(self) -> ValidationResult
```

### Plan de Migracion

**Fase 1: Crear Modulos (Semana 1)**
1. Crear estructura de directorios
2. Extraer TradingThresholds y RiskThresholds
3. Extraer BrokerConfig y RateLimitConfig
4. Crear tests de validacion

**Fase 2: Extraer Configs (Semana 2)**
1. Extraer DatabaseConfig, RedisConfig
2. Extraer LoggingConfig, MetricsConfig
3. Extraer StrategyConfig, StockAllocationSettings
4. Extraer ComplianceConfig, TaxConfig

**Fase 3: Composicion (Semana 3)**
1. Crear CentralizedConfigFacade
2. Actualizar helpers.py
3. Adaptar imports existentes
4. Verificar compatibilidad

**Fase 4: Deprecacion (Semana 4)**
1. Marcar clases antiguas como deprecated
2. Actualizar documentacion
3. Migrar clientes gradualmente

---

## 3. compliance_engine.py (3,674 lineas)

### Responsabilidades Identificadas

1. **ComplianceConfig** - Configuracion de compliance
2. **SystemAvailability** - Tracking de 17+ sistemas
3. **SystemBus** - Orquestacion de ejecucion de sistemas
4. **Pre-Trade Analysis** - Analisis pre-trade con 17 handlers
5. **Post-Trade Analysis** - Analisis post-trade
6. **Risk Validation** - Validacion de riesgo
7. **Regime Detection** - Deteccion de regimenes
8. **Reporting** - Generacion de reportes de compliance

### Estructura Propuesta

```
/app/domain/services/compliance/
├── __init__.py                    # Exports publicos
├── engine.py                      # ComplianceEngine fachada (300 lineas)
├── config.py                      # ComplianceConfig (200 lineas)
├── system_availability.py         # SystemAvailability (350 lineas)
├── system_bus/
│   ├── __init__.py
│   ├── bus.py                     # SystemBus (300 lineas)
│   └── handlers/
│       ├── __init__.py
│       ├── data_handler.py        # DataEngineHandler (200 lineas)
│       ├── risk_handler.py        # RiskEngineHandler (400 lineas)
│       ├── strategy_handler.py    # StrategyHandler (200 lineas)
│       ├── microstructure_handler.py  # Harris/OHaraHandler (300 lineas)
│       └── portfolio_handler.py   # PortfolioHandler (200 lineas)
├── analysis/
│   ├── __init__.py
│   ├── pre_trade.py               # PreTradeAnalyzer (350 lineas)
│   └── post_trade.py              # PostTradeAnalyzer (350 lineas)
├── validators/
│   ├── __init__.py
│   ├── position_validator.py      # PositionValidator (200 lineas)
│   ├── drawdown_validator.py      # DrawdownValidator (200 lineas)
│   └── leverage_validator.py      # LeverageValidator (200 lineas)
└── reporting/
    ├── __init__.py
    └── compliance_reporter.py     # ComplianceReporter (300 lineas)
```

### Nuevas Clases

#### 3.1 ComplianceEngine Fachada (`engine.py`)
```python
class ComplianceEngine:
    """Fachada principal del motor de compliance."""

    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.availability = SystemAvailability()
        self.system_bus = SystemBus(self)
        self.pre_trade = PreTradeAnalyzer(self)
        self.post_trade = PostTradeAnalyzer(self)

    def analyze_pre_trade(self, order: Order) -> PreTradeAnalysis
    def analyze_post_trade(self, trade: Trade) -> PostTradeAnalysis
    def check_compliance(self, order: Order) -> ComplianceResult
    def get_system_status(self) -> Dict[str, bool]
```

#### 3.2 SystemBus Refactorizado (`system_bus/bus.py`)
```python
class SystemBus:
    """Bus de sistemas con handlers modulares."""

    def __init__(self, engine: ComplianceEngine):
        self.engine = engine
        self.handlers = self._register_handlers()

    def _register_handlers(self) -> Dict[str, SystemHandler]
    def execute_pre_trade(self, context: AnalysisContext) -> PreTradeAnalysis
    def execute_post_trade(self, context: AnalysisContext) -> PostTradeAnalysis
```

#### 3.3 SystemHandler Base (`system_bus/handlers/base.py`)
```python
class SystemHandler(ABC):
    """Base class para handlers de sistema."""

    @abstractmethod
    def handle(self, context: AnalysisContext, result: AnalysisResult) -> bool

    @property
    @abstractmethod
    def system_name(self) -> str

    @property
    def is_critical(self) -> bool:
        return False
```

#### 3.4 RiskEngineHandler (`system_bus/handlers/risk_handler.py`)
```python
class RiskEngineHandler(SystemHandler):
    """Handler para risk engine checks."""

    system_name = "risk_engine"
    is_critical = True

    def __init__(self, validators: List[Validator]):
        self.validators = validators

    def handle(self, context: AnalysisContext, result: AnalysisResult) -> bool:
        # Position limit check
        # Drawdown limit check
        # Leverage check
        # Data quality check
        # VaR calculation
```

#### 3.5 PreTradeAnalyzer (`analysis/pre_trade.py`)
```python
class PreTradeAnalyzer:
    """Analisis pre-trade completo."""

    def __init__(self, engine: ComplianceEngine):
        self.engine = engine
        self.system_bus = engine.system_bus

    def analyze(self, order: Order, price_history: pd.DataFrame) -> PreTradeAnalysis:
        context = AnalysisContext(order=order, price_history=price_history)
        return self.system_bus.execute_pre_trade(context)
```

### Plan de Migracion

**Fase 1: Handlers (Semana 1-2)**
1. Crear estructura de directorios
2. Extraer SystemHandler base
3. Extraer RiskEngineHandler (mas complejo)
4. Extraer DataEngineHandler, StrategyHandler
5. Tests unitarios por handler

**Fase 2: SystemBus (Semana 2-3)**
1. Refactorizar SystemBus para usar handlers
2. Extraer Harris/OHara handlers
3. Extraer Portfolio handler
4. Tests de integracion

**Fase 3: Analizadores (Semana 3-4)**
1. Extraer PreTradeAnalyzer
2. Extraer PostTradeAnalyzer
3. Extraer Validators
4. Crear ComplianceEngine fachada

**Fase 4: Limpieza (Semana 4)**
1. Actualizar imports
2. Eliminar codigo duplicado
3. Documentacion

---

## 4. select_strategy.py (2,300 lineas)

### Responsabilidades Identificadas

1. **Strategy Selection** - Seleccion de estrategia basada en condiciones
2. **Regime Detection** - Deteccion de regimen de mercado
3. **Performance Scoring** - Scoring de rendimiento historico
4. **Capital Allocation** - Asignacion de capital entre estrategias
5. **Optimization** - Optimizacion de parametros
6. **Execution** - Ejecucion de estrategia seleccionada

### Estructura Propuesta

```
/app/application/use_cases/strategy_selection/
├── __init__.py                    # Exports publicos
├── selector.py                    # StrategySelector fachada (300 lineas)
├── regime_detector.py             # RegimeDetector (350 lineas)
├── performance_scorer.py          # PerformanceScorer (300 lineas)
├── capital_allocator.py           # CapitalAllocator (350 lineas)
├── optimizer.py                   # StrategyOptimizer (400 lineas)
└── models.py                      # DTOs y modelos (300 lineas)
```

### Nuevas Clases

#### 4.1 StrategySelector (`selector.py`)
```python
class StrategySelector:
    """Fachada para seleccion de estrategias."""

    def __init__(self, config: SelectionConfig):
        self.regime_detector = RegimeDetector()
        self.performance_scorer = PerformanceScorer()
        self.capital_allocator = CapitalAllocator()

    def select(self, market_data: MarketData) -> StrategySelection
    def select_multi(self, market_data: MarketData) -> List[StrategyAllocation]
    def get_recommended_allocation(self, strategies: List[str]) -> Dict[str, float]
```

#### 4.2 RegimeDetector (`regime_detector.py`)
```python
class RegimeDetector:
    """Detecta regimen de mercado."""

    def detect(self, price_history: pd.DataFrame) -> MarketRegime
    def detect_volatility_regime(self, returns: pd.Series) -> VolatilityRegime
    def detect_trend_regime(self, prices: pd.Series) -> TrendRegime
    def get_regime_probability(self, regime: str) -> float
```

#### 4.3 PerformanceScorer (`performance_scorer.py`)
```python
class PerformanceScorer:
    """Calcula scores de rendimiento de estrategias."""

    def score(self, strategy: str, history: pd.DataFrame) -> PerformanceScore
    def rank_strategies(self, strategies: List[str]) -> List[RankedStrategy]
    def calculate_risk_adjusted_return(self, returns: pd.Series) -> float
    def calculate_consistency_score(self, returns: pd.Series) -> float
```

#### 4.4 CapitalAllocator (`capital_allocator.py`)
```python
class CapitalAllocator:
    """Asigna capital entre estrategias."""

    def allocate(self, total_capital: Decimal, scores: Dict[str, float]) -> Dict[str, Decimal]
    def rebalance(self, current: Dict[str, Decimal], target: Dict[str, float]) -> List[RebalanceAction]
    def apply_constraints(self, allocation: Dict[str, float]) -> Dict[str, float]
```

#### 4.5 StrategyOptimizer (`optimizer.py`)
```python
class StrategyOptimizer:
    """Optimiza parametros de estrategias."""

    def optimize(self, strategy: str, param_space: Dict) -> OptimalParams
    def walk_forward_optimize(self, strategy: str, data: pd.DataFrame) -> WalkForwardResult
    def validate_parameters(self, params: Dict) -> ValidationResult
```

### Plan de Migracion

**Fase 1: Extraccion (Semana 1)**
1. Crear estructura de directorios
2. Extraer modelos y DTOs
3. Extraer RegimeDetector
4. Tests unitarios

**Fase 2: Scoring y Allocation (Semana 2)**
1. Extraer PerformanceScorer
2. Extraer CapitalAllocator
3. Tests de integracion

**Fase 3: Optimizer y Fachada (Semana 3)**
1. Extraer StrategyOptimizer
2. Crear StrategySelector fachada
3. Actualizar imports
4. Tests end-to-end

---

## Dependencias Entre Modulos

```
                    +-------------------+
                    |   comprehensive   |
                    |   backtest runner |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v----+ +-------v-------+ +----v------+
    | centralized  | | compliance    | |  select   |
    |   config     | |   engine      | | strategy  |
    +---------+----+ +-------+-------+ +----+------+
              |              |              |
              +------+-------+--------------+
                     |
              +------v------+
              |   shared    |
              |   utils     |
              +-------------+
```

## Principios de Refactorizacion Aplicados

1. **Single Responsibility Principle (SRP)**
   - Cada clase tiene una sola razon para cambiar
   - Maximo 400-500 lineas por archivo

2. **Open/Closed Principle (OCP)**
   - Extension mediante composicion
   - Handlers extensibles sin modificar SystemBus

3. **Dependency Inversion Principle (DIP)**
   - Depender de abstracciones (protocols)
   - Inyeccion de dependencias

4. **Interface Segregation Principle (ISP)**
   - Interfaces especificas por cliente
   - No forzar implementaciones innecesarias

5. **Composition over Inheritance**
   - Composicion de configs en lugar de herencia
   - Handlers compuestos en SystemBus

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|------------|
| Romper imports existentes | Alta | Alto | Mantener facade con mismo nombre |
| Tests fallando | Media | Alto | Tests antes/desures de cada fase |
| Performance regression | Baja | Medio | Benchmarks antes/despues |
| Merge conflicts | Alta | Medio | Branch por modulo, merge secuencial |

## Cronograma Estimado

| Fase | Duracion | Archivos Afectados |
|------|----------|-------------------|
| comprehensive_backtest_runner | 4 semanas | 6 nuevos |
| centralized_config | 4 semanas | 8 nuevos |
| compliance_engine | 4 semanas | 7 nuevos |
| select_strategy | 3 semanas | 5 nuevos |
| **Total** | **15 semanas** | **26 archivos nuevos** |

## Siguiente Paso

1. Revisar y aprobar este plan
2. Crear branch de refactorizacion
3. Comenzar con `comprehensive_backtest_runner.py`
4. Seguir orden por criticidad y dependencias
