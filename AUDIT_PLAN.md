# Plan de Auditoría - Sistema de Trading Algorítmico

**Fecha:** 29 de Enero de 2026
**Objetivo:** Auditoría completa del sistema para habilitar backtests robustos de 25 años y optimización multi-estrategia

---

## 1. Resumen Ejecutivo

### 1.1 Situación Actual
- **1376 archivos Python** en el proyecto
- **Múltiples componentes**: backtesting, estrategias, API, base de datos, microestructura
- **InputProfile existente** con parámetros de usuario (capital, objetivos, riesgo, tax residence)
- **Papers de investigación** analizados (63 papers en `/rules/trading/papers/`)

### 1.2 Objetivos del Sistema Final
1. **Backtests robustos de 25 años** sobre datos históricos reales
2. **Optimización automática** de parámetros para encontrar la mejor estrategia
3. **Multi-activo**: Stocks, Crypto, Forex, ETFs, Dividendos
4. **Multi-estrategia**: Combinación de estrategias optimizada según InputProfile
5. **Funcionamiento autónomo**: Selección, rebalanceo, gestión de riesgo, optimización fiscal

### 1.3 Enfoque de la Auditoría
```
FASE 1: ANÁLISIS → Entender qué existe y qué funciona
FASE 2: ARQUITECTURA → Diseñar estructura profesional y escalable
FASE 3: IMPLEMENTACIÓN → Construir por fases, validando continuamente
```

---

## 2. Análisis del Código Existente

### 2.1 Estructura Detectada

```
app/
├── api/                    # Endpoints FastAPI (20+ archivos)
├── application/            # Capa de aplicación (use cases)
├── backtesting/           # Motor de backtesting
│   ├── core/             # Núcleo (orchestrator, executor, facade)
│   ├── execution/        # Motor de ejecución
│   ├── labeling/         # Etiquetado de datos
│   ├── validation/       # Walk-forward validation
│   ├── drift_detection/  # Detección de drift
│   └── meta_analyzer/    # Análisis meta
├── core/                  # Modelos centrales
│   ├── config/           # Configuración
│   ├── interfaces/       # Interfaces del dominio
│   └── models/           # InputProfile y más
├── database/              # SQLAlchemy + Alembic
├── microstructure/        # Microestructura de mercado
├── strategies/            # Estrategias de trading
│   └── indicators/       # Indicadores técnicos
└── security/              # Seguridad
```

### 2.2 Componentes Clave a Auditar

| Componente | Archivos Principales | Estado Inicial | Prioridad |
|------------|---------------------|----------------|-----------|
| **InputProfile** | `core/models/input_profile.py` | ✅ Existe, bien estructurado | P0 |
| **Backtesting Engine** | `backtesting/core/` | ⚠️ Requiere auditoría | P0 |
| **Execution Engine** | `backtesting/execution_engine.py` | ⚠️ Requiere auditoría | P0 |
| **Data Loader** | `backtesting/data_loader.py` | ⚠️ Requiere auditoría | P0 |
| **Strategies** | `strategies/` | ⚠️ Requiere auditoría | P1 |
| **Risk Management** | `portfolio/risk_manager.py` | ⚠️ Requiere auditoría | P0 |
| **Optimization** | `backtesting/meta_analyzer/` | ⚠️ Requiere auditoría | P1 |
| **Tax Calculation** | ¿Existe? | ❓ Por verificar | P1 |

---

## 3. Plan de Auditoría Detallado

### 3.1 FASE 1: Auditoría de Arquitectura (Días 1-3)

**Objetivo:** Entender la arquitectura actual y identificar problemas de diseño

#### Tareas:
1. **Mapeo de dependencias**
   ```bash
   # Generar grafo de dependencias
   pydeps app --cluster --max-bacon=3 --no-dot > dependencies.txt
   ```

2. **Análisis de acoplamiento**
   - Identificar módulos con alto acoplamiento
   - Detectar dependencias circulares
   - Verificar violaciones de dependencia (infraestructura → dominio)

3. **Revisión de patrones de diseño**
   - ¿Se siguen SOLID principles?
   - ¿Hay God Objects?
   - ¿Existen Singletons mal implementados?
   - ¿El código es testeable?

4. **Análisis de capas**
   ```
   ¿La arquitectura sigue?: Presentation → Application → Domain ← Infrastructure
   ¿O hay?: Capas mezcladas, dependencias erróneas
   ```

#### Deliverables:
- [ ] Mapa de dependencias actual
- [ ] Lista de problemas arquitectónicos detectados
- [ ] Recomendaciones de refactorización
- [ ] Diagrama de arquitectura objetivo

---

### 3.2 FASE 2: Auditoría de Calidad de Código (Días 4-7)

**Objetivo:** Evaluar la calidad del código contra los estándares enterprise Python

#### Herramientas a Ejecutar:

```bash
# 1. Formato y estilo
black --check app/
isort --check-only app/
flake8 app/ --max-complexity=10
ruff check app/

# 2. Type hints
mypy --strict app/

# 3. Documentación
pydocstyle app/
interrogate app/ --fail-under=100

# 4. Seguridad
bandit -r app/ -ll
safety check --json
pip-audit

# 5. Calidad
radon cc app/ -a
vulture app/ --min-confidence 80
pylint app/ --fail-under=8.0

# 6. Cobertura de tests
pytest --cov=app --cov-report=html
```

#### Métricas a Recolectar:

| Métrica | Objetivo | Actual | Gap |
|---------|----------|--------|-----|
| Complejidad ciclomática | < 10 | ? | ? |
| Cobertura de tests | > 80% | ? | ? |
| Type hints | 100% | ? | ? |
| Docstrings | 100% | ? | ? |
| Duplicación | < 5% | ? | ? |
| Pylint score | > 8.0 | ? | ? |

#### Deliverables:
- [ ] Reporte completo de QA (todas las herramientas)
- [ ] Métricas de calidad actuales
- [ ] Lista de archivos que no cumplen estándares
- [ ] Plan de corrección priorizado

---

### 3.3 FASE 3: Auditoría de Backtesting (Días 8-12)

**Objetivo:** Verificar que el motor de backtesting puede ejecutar backtests de 25 años robustamente

#### Puntos a Verificar:

**3.3.1 Motor de Ejecución**
```python
# ¿El execution engine maneja correctamente?
- [ ] 25 años de datos diarios (~6,500 días por activo)
- [ ] Dividendos y corporate actions
- [ ] Splits de acciones
- [ ] Cambios de ticker (tickers que dejan de existir)
- [ ] Survivorship bias (¿se maneja?)
- [ ] Costos de transacción realistas
- [ ] Slippage
- [ ] Market impact
- [ ] Liquidity constraints
```

**3.3.2 Datos Históricos**
```python
# ¿Qué datos se necesitan para 25 años?
- [ ] Precios OHLCV diarios
- [ ] Dividendos (yield, pagos, fechas ex-div)
- [ ] Corporate actions (splits, mergers, spinoffs)
- [ ] Lista de activos sobrevivientes (para survivorship bias)
- [ ] Tasa libre de riesgo (RF) diaria
- [ ] Índices de referencia (S&P 500, etc.)
```

**3.3.3 Multi-Activo**
```python
# ¿El sistema soporta?
- [ ] Stocks (acciones individuales)
- [ ] ETFs
- [ ] Crypto (BTC, ETH, etc.)
- [ ] Forex (pares de divisas)
- [ ] Bonds/Fixed Income
- [ ] Commodities
```

**3.3.4 Escenarios de Prueba**
```python
# Casos de prueba para robustez
test_cases = [
    "backtest_25_years_single_stock",
    "backtest_25_years_portfolio_50_stocks",
    "backtest_with_dividends_reinvested",
    "backtest_with_corporate_actions",
    "backtest_crypto_2017_present",  # Si hay datos
    "backtest_forex_major_pairs",
    "stress_test_extreme_volatility",
    "stress_test_market_crash_2008",
    "stress_test_covid_crash_2020",
]
```

#### Deliverables:
- [ ] Reporte de capacidades del backtesting engine
- [ ] Lista de features faltantes
- [ ] Pruebas de rendimiento (tiempo de ejecución)
- [ ] Análisis de memoria para 25 años de datos
- [ ] Plan de optimización del engine

---

### 3.4 FASE 4: Auditoría de Estrategias (Días 13-16)

**Objetivo:** Catalogar estrategias existentes y evaluar su implementación

#### Inventario de Estrategias:

| Tipo de Estrategia | Archivos | Implementado | ¿Funciona? | Prioridad |
|-------------------|----------|--------------|-----------|-----------|
| Trend Following | ? | ? | ? | P0 |
| Mean Reversion | ? | ? | ? | P0 |
| Momentum | ? | ? | ? | P0 |
| Dividend Strategy | ? | ? | ? | P1 |
| Options Strategies | ? | ? | ? | P2 |
| Arbitrage | ? | ? | ? | P2 |
| Machine Learning | ? | ? | ? | P2 |
| Factor Investing | ? | ? | ? | P1 |

#### Por Cada Estrategia:
```python
# Checklist de auditoría
strategy_audit = {
    "name": "Nombre de estrategia",
    "file": "path/al/archivo.py",
    "parameters": {
        "count": "Número de parámetros",
        "optimized": "¿Cuáles son optimizables?",
        "ranges": "Rangos de cada parámetro",
    },
    "dependencies": [
        "¿Qué indicadores necesita?",
        "¿Qué datos necesita?",
    ],
    "risk_management": {
        "has_stop_loss": bool,
        "has_position_sizing": bool,
        "has_drawdown_control": bool,
    },
    "tax_aware": bool,  # ¿Considera implicaciones fiscales?
    "tested": bool,     # ¿Ha sido testeada?
    "robust": bool,     # ¿Es robusta a parámetros?
}
```

#### Deliverables:
- [ ] Inventario completo de estrategias
- [ ] Matriz de parámetros optimizables
- [ ] Análisis de qué estrategias son viables para optimización
- [ ] Identificación de estrategias faltantes

---

### 3.5 FASE 5: Auditoría de Optimización (Días 17-20)

**Objetivo:** Evaluar capacidad de encontrar la "mejor estrategia" automáticamente

#### Puntos a Analizar:

**5.5.1 Espacio de Parámetros**
```python
# ¿Cuántas combinaciones posibles?
param_space = {
    "strategy_1": 1000,  # combinaciones
    "strategy_2": 500,
    "strategy_3": 2000,
    ...
}

total_combinations = product(param_space.values())

# ¿Es factible computacionalmente?
# Si total_combinations > 10M, necesitas búsqueda inteligente
```

**5.5.2 Algoritmos de Optimización**
```python
# ¿Qué existe?
- [ ] Grid Search (fuerza bruta)
- [ ] Random Search
- [ ] Bayesian Optimization
- [ ] Genetic Algorithms
- [ ] Multi-objective optimization (Pareto front)
```

**5.5.3 Paralelización**
```python
# ¿Se puede paralelizar?
- [ ] Multi-procesing (múltiples CPUs)
- [ ] Distributed computing (varias máquinas)
- [ ] GPU acceleration (¿cuál código es vectorizable?)
```

**5.5.4 Métricas de Optimización**
```python
# ¿Qué se optimiza?
objectives = {
    "sharpe_ratio": "Profitabilidad ajustada por riesgo",
    "total_return": "Retorno total",
    "max_drawdown": "Máximo drawdown (minimizar)",
    "sortino_ratio": "Similar a Sharpe pero solo downside",
    "calmar_ratio": "Retorno / Max Drawdown",
    "win_rate": "Porcentaje de trades ganadores",
}

# Multi-objetivo: ¿Se puede optimizar para varios?
# Ej: Maximizar Sharpe, minimizar Drawdown
```

#### Deliverables:
- [ ] Análisis del espacio de búsqueda
- [ ] Recomendación de algoritmo de optimización
- [ ] Plan de paralelización
- [ ] Estimación de tiempo para backtest completo

---

### 3.6 FASE 6: Auditoría de Gestión de Riesgo (Días 21-23)

**Objetivo:** Verificar que el sistema gestiona el riesgo adecuadamente

#### Componentes a Auditar:

```python
risk_management_audit = {
    "position_sizing": {
        "kelly_criterion": "¿Implementado?",
        "fixed_fractional": "¿Implementado?",
        "volatility_target": "¿Implementado?",
        "atr_based": "¿Implementado?",
    },
    "portfolio_constraints": {
        "max_position_size": "¿Límite por posición?",
        "max_sector_exposure": "¿Límite por sector?",
        "max_correlation_exposure": "¿Límite de correlación?",
        "concentration_limits": "¿Límites de concentración?",
    },
    "stop_loss": {
        "trailing_stop": "¿Implementado?",
        "fixed_stop": "¿Implementado?",
        "volatility_stop": "¿Implementado?",
        "time_stop": "¿Implementado?",
    },
    "drawdown_control": {
        "max_drawdown_limit": "¿Límite de drawdown?",
        "reduction_triggers": "¿Qué reduce exposición?",
        "recovery_mode": "¿Modo de recuperación?",
    },
}
```

#### Deliverables:
- [ ] Matriz de capacidades de risk management
- [ ] Identificación de features faltantes
- [ ] Recomendaciones de implementación

---

### 3.7 FASE 7: Auditoría Fiscal (Días 24-25)

**Objetivo:** Verificar que el sistema calcula impuestos correctamente

#### Puntos Clave:

```python
tax_audit = {
    "jurisdictions": {
        "spain": "¿Calcula correctamente para España?",
        "usa": "¿Calcula correctamente para USA?",
        "other": "¿Soporta otros países?",
    },
    "tax_events": {
        "capital_gains_short": "¿Calcula correctamente?",
        "capital_gains_long": "¿Calcula correctamente?",
        "dividends": "¿Calcula withholding tax?",
        "wash_sale_rule": "¿Aplica regla wash-sale (USA)?",
        "loss_carryforward": "¿Permite carryforward de pérdidas?",
    },
    "optimization": {
        "tax_loss_harvesting": "¿Optimiza pérdidas fiscales?",
        "location_optimization": "¿Optimiza ubicación de activos?",
        "dividend_timing": "¿Optimiza timing de dividendos?",
    }
}
```

#### Deliverables:
- [ ] Análisis de capacidades fiscales actuales
- [ ] Verificación de cálculos para cada jurisdicción soportada
- [ ] Recomendaciones de optimización fiscal

---

## 4. Análisis de Brechas (Gap Analysis)

### 4.1 Brechas Críticas (P0)

| Componente | Existe | Funciona | Robusto | Para 25 años | Acción |
|------------|--------|----------|---------|--------------|--------|
| Data loader | ? | ? | ❓ | ❓ | Audit + Optimizar |
| Backtesting engine | ✅ | ? | ❓ | ❌ | Audit + Reimplementar |
| Optimization engine | ❓ | ❓ | ❌ | ❌ | Implementar nuevo |
| Multi-asset support | ❓ | ❓ | ❌ | ❌ | Implementar |
| Tax calculator | ✅ (InputProfile) | ? | ❓ | ❓ | Audit + Completar |

### 4.2 Brechas Importantes (P1)

| Componente | Existe | Funciona | Robusto | Para 25 años | Acción |
|------------|--------|----------|---------|--------------|--------|
| Strategy catalog | ? | ? | ❓ | ❓ | Catalogar + Testear |
| Risk management | ? | ? | ❓ | ❓ | Audit + Completar |
| Performance analytics | ✅ | ? | ❓ | ❓ | Audit + Extender |
| Reporting | ✅ | ? | ❓ | ❓ | Audit + Mejorar |

---

## 5. Plan de Implementación Propuesto

### 5.1 Arquitectura Objetivo

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │    API      │  │    CLI      │  │ Web Dashboard│  │ Reports │  │
│  │  (FastAPI)  │  │  (Typer)    │  │   (React)    │  │ (PDF)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Use Cases                                    ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ ││
│  │  │ Run Backtest     │  │ Optimize Strategy│  │ Auto-Trade   │ ││
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘ ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ ││
│  │  │ Analyze Results  │  │ Manage Portfolio │  │ Risk Monitor │ ││
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘ ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                       DOMAIN LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Models: InputProfile, Portfolio, Trade, Order, Position        ││
│  │  Value Objects: Money, Percentage, Date, Symbol                ││
│  │  Domain Services: RiskCalculator, TaxCalculator, Rebalancer    ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│  │  Data Sources │  │   Database    │  │  External APIs│          │
│  │  (Yahoo, DB)  │  │  (PostgreSQL) │  │  (Brokers)    │          │
│  └───────────────┘  └───────────────┘  └───────────────┘          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│  │  Backtesting  │  │  Optimization │  │  Execution    │          │
│  │  Engine       │  │  Engine       │  │  Engine       │          │
│  └───────────────┘  └───────────────┘  └───────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Fases de Implementación

#### FASE 1: Fundación (Semanas 1-4)

**Objetivo:** Establecer base sólida que respete todos los estándares QA

```
Semana 1-2: Arquitectura y Calidad
- [ ] Corregir todos los errores de QA (black, mypy, pylint, etc.)
- [ ] Establecer layered architecture correcta
- [ ] Crear interfaces del dominio (Protocols)
- [ ] Implementar dependency injection
- [ ] Tests de cobertura > 80%

Semana 3-4: Datos y Backtesting Base
- [ ] Data layer optimizado para 25 años de datos
- [ ] Backtesting engine robusto y probado
- [ ] Implementar corporate actions
- [ ] Implementar survivorship bias correction
- [ ] Stress tests del engine
```

#### FASE 2: Estrategias Core (Semanas 5-8)

```
Semana 5-6: Estrategias Básicas
- [ ] Trend Following ( múltiples timeframes)
- [ ] Mean Reversion (estadístico)
- [ ] Momentum (cross-sectional)
- [ ] Factor models (Fama-French, etc.)

Semana 7-8: Validación
- [ ] Walk-forward validation de todas
- [ ] Overfitting detection
- [ ] Regime detection
- [ ] Sensitivity analysis
```

#### FASE 3: Optimización (Semanas 9-12)

```
Semana 9-10: Engine de Optimización
- [ ] Parameter space definition
- [ ] Grid search optimizado (vectorizado)
- [ ] Bayesian optimization (Optuna)
- [ ] Multi-objective optimization
- [ ] Parallel execution

Semana 11-12: Integración
- [ ] Integración con backtesting engine
- [ ] Optimización multi-estrategia
- [ ] Portfolio optimization (Markowitz, HRP, etc.)
- [ ] Reporting de resultados
```

#### FASE 4: Multi-Activo (Semanas 13-16)

```
Semana 13-14: Datos Multi-Activo
- [ ] Stocks: 25 años de datos USA + Europa
- [ ] ETFs: principales ETFs 25 años
- [ ] Crypto: datos disponibles (~2017)
- [ ] Forex: major pairs 25 años
- [ ] Bonds: treasuries 25 años

Semana 15-16: Estrategias por Activo
- [ ] Dividendos: estrategia de ingresos
- [ ] Crypto: momentum/trend
- [ ] Forex: carry trade + momentum
- [ ] Bonds: duration management
```

#### FASE 5: Producción (Semanas 17-20)

```
Semana 17-18: Risk Management
- [ ] Position sizing completo
- [ ] Portfolio constraints
- [ ] Drawdown control
- [ ] Stress testing automático

Semana 19-20: Tax Optimization
- [ ] Tax calculator por jurisdicción
- [ ] Tax-loss harvesting
- [ ] Location optimization
- [ ] Reporting fiscal
```

---

## 6. Especificación de Módulos Clave

### 6.1 Módulo de Datos

```python
# app/infrastructure/data/historical_data_loader.py
from typing import Protocol
from datetime import date

class HistoricalDataLoader(Protocol):
    """Protocol para loaders de datos históricos."""

    async def load_prices(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.DataFrame]:
        """Cargar precios OHLCV para múltiples símbolos."""
        ...

    async def load_dividends(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.DataFrame]:
        """Cargar dividendos para múltiples símbolos."""
        ...

    async def load_corporate_actions(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Cargar corporate actions (splits, mergers)."""
        ...

    async def get_universe(
        self,
        as_of_date: date,
    ) -> list[str]:
        """Obtener universo de activos válidos en fecha."""
        ...

class YahooFinanceDataLoader:
    """Implementación para Yahoo Finance."""
    # Optimizado para 25 años de datos
    # Cache inteligente
    # Paralelización de requests

class CryptoDataLoader:
    """Implementación para Crypto (Binance, etc)."""
    # Diferentes fuentes para crypto
```

### 6.2 Módulo de Backtesting

```python
# app/infrastructure/backtesting/engine.py
from typing import Protocol

class BacktestEngine(Protocol):
    """Protocol para engine de backtesting."""

    def run_backtest(
        self,
        strategy: Strategy,
        data: MarketData,
        initial_capital: Decimal,
        config: BacktestConfig,
    ) -> BacktestResult:
        """Ejecutar backtest completo."""
        ...

class BacktestConfig(BaseModel):
    """Configuración del backtesting."""

    # Costos
    commission_per_share: Decimal = Decimal("0.01")
    commission_min: Decimal = Decimal("1.0")
    commission_max_pct: Decimal = Decimal("0.005")  # 0.5%

    # Slippage
    slippage_model: SlippageModel = SlippageModel.LINEAR
    slippage_bps: int = 5  # 5 bps

    # Market impact
    market_impact_model: MarketImpactModel = MarketImpactModel.NONE
    max_position_pct: Decimal = Decimal("0.10")  # 10%

    # Cash management
    initial_cash: Decimal
    min_cash_pct: Decimal = Decimal("0.05")  # 5% mínimo
    borrowing_rate: Decimal = Decimal("0.05")  # 5% anual

class BacktestResult(BaseModel):
    """Resultado del backtesting."""

    # Métricas principales
    total_return: Decimal
    cagr: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal

    # Estadísticas de trades
    total_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    avg_trade_return: Decimal

    # Diarios
    equity_curve: list[Decimal]
    returns: list[Decimal]
    drawdowns: list[Decimal]

    # Detalles
    positions: list[Position]
    trades: list[Trade]
```

### 6.3 Módulo de Optimización

```python
# app/infrastructure/optimization/optimizer.py
from typing import Protocol

class StrategyOptimizer(Protocol):
    """Protocol para optimizador de estrategias."""

    def optimize(
        self,
        strategy_type: type[Strategy],
        data: MarketData,
        objective: OptimizationObjective,
        constraints: OptimizationConstraints,
    ) -> OptimizationResult:
        """Optimizar parámetros de estrategia."""
        ...

class OptimizationObjective(BaseModel):
    """Objetivo de optimización."""

    primary_metric: str  # "sharpe", "total_return", etc.
    maximize: bool = True
    secondary_metrics: dict[str, float] = {}  # Pesos para multi-objetivo

class OptimizationConstraints(BaseModel):
    """Restricciones de optimización."""

    # Búsqueda
    max_iterations: int = 1000
    timeout_seconds: int = 3600

    # Estrategia
    parameter_ranges: dict[str, tuple[float, float]]
    integer_parameters: list[str] = []

    # Portfolio
    max_positions: int = 50
    min_position_size: Decimal = Decimal("0.01")  # 1%
    max_position_size: Decimal = Decimal("0.20")  # 20%

    # Riesgo
    max_drawdown: Decimal = Decimal("0.30")  # 30%
    max_volatility: Decimal | None = None

class OptimizationResult(BaseModel):
    """Resultado de optimización."""

    best_parameters: dict[str, Any]
    best_score: float
    all_scores: list[dict]  # Historial de optimización

    backtest_result: BacktestResult
    convergence_curve: list[float]
```

---

## 7. Roadmap de Ejecución

### Resumen de Fases

| Fase | Duración | Objetivo | Deliverables |
|------|----------|----------|--------------|
| **Auditoría** | 25 días | Análisis completo | Reporte de auditoría |
| **Diseño** | 5 días | Arquitectura detallada | Especificaciones técnicas |
| **Fase 1** | 4 semanas | Fundación | Código limpio + tests |
| **Fase 2** | 4 semanas | Estrategias core | 5 estrategias probadas |
| **Fase 3** | 4 semanas | Optimización | Motor de optimización |
| **Fase 4** | 4 semanas | Multi-activo | Todos los activos soportados |
| **Fase 5** | 4 semanas | Producción | Sistema autónomo listo |

**Total:** ~6 meses desde inicio hasta sistema en producción

---

## 8. Próximos Pasos Inmediatos

### Hoy (Día 1)

1. **Ejecutar herramientas QA**
   ```bash
   cd /Users/kepa.cantero/Projects/algoTrading
   black --check app/ > qa/black_report.txt 2>&1
   isort --check-only app/ > qa/isort_report.txt 2>&1
   mypy --strict app/ > qa/mypy_report.txt 2>&1
   ruff check app/ > qa/ruff_report.txt 2>&1
   ```

2. **Leer archivos clave**
   - `app/core/models/input_profile.py` ✅ (leído)
   - `app/backtesting/core/orchestrator.py`
   - `app/backtesting/execution_engine.py`
   - `app/strategies/` (listar todos)

3. **Crear directorio de auditoría**
   ```bash
   mkdir -p audit/{qa,architecture,backtesting,strategies,risk,tax}
   ```

### Esta Semana

- [ ] Completar ejecución de todas las herramientas QA
- [ ] Leer todos los archivos de backtesting core
- [ ] Catalogar todas las estrategias existentes
- [ ] Crear mapa de dependencias
- [ ] Identificar top 20 problemas a corregir

---

## 9. Matriz de Decisión

### ¿Qué hacer con código existente?

| Categoría | Criterio | Acción |
|-----------|----------|--------|
| **Mantener** | Pasa QA, bien diseñado, testeado | Refactorizar mínimamente |
| **Refactorizar** | Funciona pero no cumple QA | Corregir style, tipos, tests |
| **Reescribir** | Mal diseñado, no testeable, muy complejo | Reimplementar limpio |
| **Eliminar** | No usado, duplicado, obsoleto | Eliminar |

---

## 10. Métricas de Éxito

### Auditoría Completa Cuando:

- [ ] Todos los archivos Python han sido auditados
- [ ] Mapa de dependencias generado
- [ ] Todas las estrategias catalogadas
- [ ] Brechas identificadas y priorizadas
- [ ] Plan de implementación detallado creado
- [ ] Especificaciones técnicas escritas
- [ ] Stakeholder (tú) aprueba el plan

---

## 11. Comunicación y Aprobación

### Puntos de Decisión

1. **Al finalizar FASE 1** (Auditoría de Arquitectura)
   - ¿La arquitectura propuesta es aceptable?

2. **Al finalizar FASE 2** (Auditoría de Calidad)
   - ¿El nivel de deuda técnica es manejable?

3. **Al finalizar FASE 3** (Auditoría de Backtesting)
   - ¿El engine existente se puede salvar o se reescribe?

4. **Antes de FASE 1 de Implementación**
   - Aprobación final del plan completo

---

**Documento preparado para:** Kepa Cantero
**Sistema:** AlgoTrading - Sistema de Trading Algorítmico
**Objetivo:** Habilitar backtests de 25 años y optimización multi-estrategia
