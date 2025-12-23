# Project Brief - AlgoTrading

## Project Identity

**Name**: AlgoTrading  
**Type**: Sistema completo de trading algorítmico  
**Domain**: Financial Technology - Algorithmic Trading  
**Architecture**: Microservices + Event-driven + Async Processing

## Business Objectives

- Implementar sistema personal de trading algorítmico **escalable por capital**
- Portfolio actual en JSON/CSV o conexión API a IBKR/Binance
- Enfoque: Momentum diario sobre top 20 activos líquidos (adaptable por tier)
- Modo analítico: Paper trading antes de ejecución real
- Signal Scorer: Priorizar señales por confianza y liquidez
- **Objetivo Principal (Dual-Mode)**:
  - **Small Capital Mode** (<€50k): Supervivencia y estabilidad
  - **Large Capital Mode** (€250k+): **Generación de €800 netos mensuales (3.9% anual neto)**

## Core Value Proposition

- Trading Algorítmico: Estrategias de liquidez y momentum para múltiples activos
- Stack Moderno: Python 3.11, FastAPI 0.115+, PostgreSQL 15, Redis 7, Celery 5.3
- Infraestructura Cloud: Docker Compose + AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- CI/CD Completo: GitHub Actions con despliegue automático a AWS
- Dashboard Interactivo: Streamlit 1.37 para análisis y monitoreo
- Testing Riguroso: >90% cobertura con pytest + HTTPX

## Success Metrics

- Performance: < 1.5s response time para decisiones de trading
- Cobertura de Tests: >90% con pytest + HTTPX
- Despliegue: CI/CD completo en GitHub Actions + AWS
- Funcionalidad: Sistema ejecutable con estrategias de trading operativas

## Context Update 2025-12-23 – Plan Maestro v3.0 "Capital-Aware Architecture"

**Evolución Estratégica**: El proyecto ha transitado desde MVP a **arquitectura dual-mode escalable por capital**:

### Fases Completadas:
- **Fase 1 (Data & Context)**: ✅ **100% completada**
- **Fase 2 (Strategy & Learning)**: ✅ **100% completada**
- **Fase 3 (Portfolio & Risk)**: ✅ **90% completada**
- **PHASE 0 (Capital Viability & Integration Audit)**: ✅ **100% completada** (23-12-2025)
  - 178 tests pasando (49 T0.1 + 60 T0.2 + 10 T0.3 + 59 T0.4)
  - Capital Viability Gates, Learning Gates, Module Gates, Deployment Validator, Account Configuration
  - **Crítico para accounts <€50k**: Fail-fast antes de pérdida de capital

### Nueva Arquitectura: Fases 1-4 para Capital Grande (€250k+)
Tras análisis de viabilidad de objetivo **€800/mes neto (3.9% anual)**, se implementan:

- **PHASE 1: Capital-Tier Aware Strategy Orchestration** (2-3 días)
  - T1.1: Capital Tier Strategy Selector (activa features por capital)
  - T1.2: Absolute Return Optimizer (optimiza hacia €800/mes específico)

- **PHASE 2: Execution Optimization for Large Capital** (2-3 días)
  - T2.1: Smart Order Routing Engine (minimiza costes en órdenes grandes)
  - T2.2: Large Position Builder (ejecución sofisticada para €50k+)

- **PHASE 3: Dynamic Risk Scaling** (1-2 días)
  - Risk limits dinámicos que escalan con capital y target
  - Leverage permisión para €250k

- **PHASE 4: Capacity Fade & Alpha Validation** (2-3 días)
  - Estima decay de alpha con escala de capital
  - Valida que 3.9% neto es realista antes de deployment

**Cronograma Total**: PHASE 0 ✅ + PHASES 1-4 (~9-11 días) + PHASES 5-17 (módulos avanzados)

**Arquitectura de 17 Engines** + integración librerías élite (QuantStats, PyPortfolioOpt, etc.)
- Mapeo Librería-Módulo por engine
- Configuración YAML escalable por tier
- Capcity fade tracking y revalidación mensual
