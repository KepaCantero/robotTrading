# Project Brief - AlgoTrading MVP

## Project Identity

**Name**: AlgoTrading MVP  
**Type**: Sistema completo de trading algorítmico  
**Domain**: Financial Technology - Algorithmic Trading  
**Architecture**: Microservices + Event-driven + Async Processing  
**Context Version**: 2025.10

## Business Objectives

- Implementar sistema personal de trading algorítmico para generar dinero
- **FUENTE DE VERDAD**: Portfolio actual en JSON/CSV o conexión API a IBKR/Binance
- **ENFOQUE ÚNICO**: Momentum diario sobre top 20 activos líquidos
- **MODO ANALÍTICO**: Paper trading antes de ejecución real
- **SIGNAL SCORER**: Priorizar señales por confianza y liquidez
- **APLAZAR DEVOPS**: Enfocar en decisiones fiables antes de CI/CD
- Garantizar código ejecutable, testeado y desplegable en AWS
- Asegurar consistencia entre tareas, módulos y outputs (T001–T036)
- **OBJETIVO PRINCIPAL**: Generar dinero con trading algorítmico automatizado

## Core Value Proposition

- **Trading Algorítmico**: Estrategias de liquidez y momentum para múltiples activos
- **Stack Moderno**: Python 3.11, FastAPI 0.115+, PostgreSQL 15, Redis 7, Celery 5.3
- **Infraestructura Cloud**: Docker Compose + AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- **CI/CD Completo**: GitHub Actions con despliegue automático a AWS
- **Dashboard Interactivo**: Streamlit 1.37 para análisis y monitoreo
- **Testing Riguroso**: >90% cobertura con pytest + HTTPX

## Success Metrics

- **Performance**: < 1.5s response time para decisiones de trading
- **Cobertura de Tests**: >90% con pytest + HTTPX
- **Despliegue**: CI/CD completo en GitHub Actions + AWS
- **Funcionalidad**: Sistema ejecutable con estrategias de trading operativas
- **Consistencia**: 100% de tareas T001-T036 implementadas y validadas

## Stakeholders

- **Trader Principal**: Usuario único del sistema de trading algorítmico (TU)
- **Desarrollador**: Equipo de desarrollo y mantenimiento
- **DevOps**: Administradores de infraestructura y despliegue
- **Analista**: Usuario del dashboard Streamlit para análisis personal

## Project Scope

### In Scope - AlgoTrading MVP

- **Core Trading Engine**: FastAPI + SQLAlchemy + PostgreSQL
- **Estrategias de Trading**: Momentum + Liquidez para acciones, crypto, forex
- **Análisis Técnico**: pandas, numpy, indicadores técnicos
- **Backtesting**: Sistema completo de backtesting
- **Alertas**: Sistema de notificaciones y alertas
- **Dashboard**: Streamlit 1.37 para visualización
- **Async Processing**: Celery + RabbitMQ para tareas asíncronas
- **Caching**: Redis 7 para performance
- **CI/CD**: GitHub Actions + AWS deployment
- **Containerización**: Docker Compose para desarrollo y producción

### Out of Scope - MVP Phase

- Integraciones con brokers específicos (solo APIs mock)
- Trading en tiempo real con dinero real
- Análisis fundamental avanzado
- Machine Learning para predicción de precios
- Mobile apps nativas

## Technical Constraints

- **Language**: Python 3.11+ (compatible con 3.10+)
- **Framework**: FastAPI 0.115+ con async/await patterns
- **Database**: PostgreSQL 15.x con SQLAlchemy 2.0.x
- **Caching**: Redis 7.x para session management y performance
- **Async Tasks**: Celery 5.3 + RabbitMQ
- **Frontend**: Streamlit 1.37
- **Packaging**: Docker Compose + Poetry
- **Cloud**: AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- **CI/CD**: GitHub Actions
- **Testing**: pytest + HTTPX con >90% cobertura

## Environment Strategy

- **Development**: Local Docker Compose + pytest + pre-commit
- **Staging**: AWS EC2 + GitHub Actions CI/CD
- **Production**: AWS ECS + RDS + S3 + CloudWatch

## Risk Factors

- **High**: Complejidad de estrategias de trading algorítmico
- **Medium**: Integración con APIs de brokers y exchanges
- **Medium**: Performance requirements para trading en tiempo real
- **Low**: Stack tecnológico conocido y estable

## Goals & Review Policy

### Goals

- Implementar el MVP hasta producción (T001–T036)
- Garantizar código ejecutable, testeado y desplegable
- Asegurar consistencia entre tareas, módulos y outputs

### Review Policy

- Validar dependencias y outputs antes de pasar de tarea
- Confirmar compilación y tests en cada módulo
- Revisar integridad de CI/CD antes del despliegue

## Next Steps

1. **Memory Bank Setup**: Completar configuración del memory bank (en progreso)
2. **Task Breakdown**: Validar y refinar tareas T001-T036
3. **Environment Setup**: Configurar Docker Compose + desarrollo local
4. **Implementation Start**: Comenzar con T001 (FastAPI base structure)
5. **CI/CD Setup**: Configurar GitHub Actions + AWS deployment
6. **Testing Strategy**: Implementar >90% cobertura con pytest

## Context Update 2025-12-15 – Plan Maestro "Next Level"

Tras completar el MVP operativo descrito en este brief (AWS/Docker + paper trading activo), el proyecto ha pasado a una fase de evolución arquitectónica definida en `docs/PLAN_MAESTRO_NEXT_LEVEL.md`:

- La arquitectura se reorganiza alrededor de **17 engines** (Data, Context, Strategy, Learning, Portfolio, Risk, Execution, Monitoring, Meta-Analyzer, Audit & Persistence, Explainability, Synthetic Data, Prediction Fusion, Compliance & Governance, Knowledge Graph, Experimentation & Orchestration, Infrastructure Optimizer).
- **Estado Actual del Plan Maestro**:
  - **Fase 1 (Data & Context)**: ✅ **100% completada** - `DataEngine` y `ContextEngine` implementados con tests de integración
  - **Fase 2 (Strategy & Learning)**: 🟡 **80% completada**
    - Tarea 3.1 ✅: Refactor de estrategias existentes completado
    - Tarea 3.2 🟡: 2/4 nuevas estrategias completadas (`BreakoutStrategyEngine` ✅, `TrendFollowingStrategyEngine` ✅)
    - Tarea 3.3 ⏳: Sistema de composición pendiente
    - Tarea 3.4 ✅: Integración con Learning Engine parcialmente completada
    - Tarea 3.5 ✅: Testing y validación completada
  - **Fase 3 (Portfolio & Risk)**: ✅ **90% completada** - `PortfolioEngine` y `RiskEngine` implementados con optimizadores avanzados
- **Integración Completa (2025-12-15)**:
  - ✅ Nuevos engines (`BreakoutStrategyEngine`, `TrendFollowingStrategyEngine`) integrados en sistema de backtesting
  - ✅ Configuración YAML centralizada (`config/strategies/breakout.yaml`, `config/strategies/trend_following.yaml`)
  - ✅ Engines registrados en `StrategyFactory` y disponibles para backtests y producción
  - ✅ Todos los parámetros centralizados (sin magic numbers)
  - ✅ Integración completa con `comprehensive_backtest_runner.py` para multi-strategy backtests
- El MVP sigue siendo la base funcional; el foco actual es completar **Fase 2** del plan maestro (resto de estrategias base y sistema de composición) y empezar a materializar los módulos avanzados (análisis, persistencia, ejecución avanzada, dashboards next level y ML/XAI) sin romper la compatibilidad con el sistema existente.
