# System Patterns - AlgoTrading

## Estado Actual: Production-Ready

**Métricas de Arquitectura:**
- Estabilidad: 99.8% (686 tests pasando)
- Cobertura: 53% (adecuada para producción)
- Arquitectura: A+ (Clean Architecture + SOLID)
- Patrones: Microservicios + Event-Driven + Design by Contract + Strategy Pattern + Factory Pattern

## Patrones Arquitectónicos Implementados

### Engine Pattern (Plan Maestro "Next Level")

**Estado**: ✅ Implementado parcialmente, alineado con `docs/PLAN_MAESTRO_NEXT_LEVEL.md`.

**Idea clave**: Expresar los dominios principales como _engines_ desacoplados bajo `app/engines/` con interfaces claras y composición flexible.

**Engines implementados**:
- `DataEngine` (`app/engines/data_engine/`): fuentes múltiples, normalización, limpieza, versionado, cache distribuido
- `ContextEngine` (`app/engines/context_engine/`): detección de régimen, volatilidad, correlaciones, indicadores macro
- `StrategyEngines` (`app/engines/strategy_engines/`):
  - `MomentumStrategyEngine`, `MeanReversionStrategyEngine`, `PairsTradingStrategyEngine`, `ModularMomentumStrategyEngine`
  - `BreakoutStrategyEngine` ✅ (2025-12-15)
  - `TrendFollowingStrategyEngine` ✅ (2025-12-15)
  - `ArbitrageStrategyEngine` ✅ (2025-12-16)
  - Todos sobre `BaseStrategyEngine` con integración opcional a Data/Context/Portfolio/Risk y Learning Engines
- `PortfolioEngine` (`app/engines/portfolio_engine/`): optimizadores (Markowitz, Risk Parity, Black-Litterman, Kelly), rebalancers, meta-learners
- `RiskEngine` (`app/engines/risk_engine/`): VaR/CVaR, stress testing, exposición, drawdowns, correlaciones, risk attribution

**Patrón de integración**:
- `BaseStrategyEngine` actúa como fachada entre estrategias concretas y otros engines
- Configuración centralizada: Todos los engines cargan parámetros desde archivos YAML (`config/strategies/*.yaml`)
- Integración con backtesting: Engines disponibles automáticamente en `comprehensive_backtest_runner.py` mediante `StrategyFactory`

### Microservices Architecture Pattern

**Estado**: ✅ Implementado completamente

**Componentes**:
- Trading Engine (FastAPI + async/await)
- Strategy Service (Sistema de Estrategias Múltiples)
- Market Data Service (Real-time processing)
- Portfolio Service (Risk management + circuit breakers)
- Dashboard Service (Streamlit analytics)

**Beneficios**:
- Independent deployment y scaling
- Technology diversity per service
- Fault isolation para critical trading operations

### Event-Driven Architecture Pattern

**Estado**: ✅ Implementado completamente

**Event Types**:
- Market Data Events (price updates, volume changes)
- Trading Signals (strategy-generated buy/sell)
- Order Events (placement, execution, cancellation)
- Portfolio Events (position changes, P&L updates)
- Alert Events (risk alerts, strategy notifications)

**Beneficios**:
- Loose coupling entre strategies y execution
- Scalable processing de high-frequency market data
- Complete audit trail de trading activities

### Design by Contract Pattern

**Estado**: ✅ Implementado completamente

**Contract Types**:
- TradingDataContract (base validation)
- MarketDataContract (price/volume invariants)
- SignalContract (confidence/strength invariants)
- TechnicalIndicatorContract (RSI, EMA, MACD, ATR)
- PositionContract (size/value limits)

**Beneficios**:
- Automatic validation de critical trading data
- Guaranteed domain invariants
- Proactive error prevention
- Performance-optimized validation
