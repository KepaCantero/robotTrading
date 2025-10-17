# Quick Start - AlgoTrading MVP

## Project Overview

**AlgoTrading MVP** - Sistema completo de trading algorítmico con stack Python 3.11, FastAPI, PostgreSQL, Redis, Celery, y Docker. Capaz de operar acciones, criptomonedas y forex mediante estrategias de liquidez y momentum. Incluye análisis técnico, backtesting, alertas, dashboard Streamlit y CI/CD completo en GitHub Actions + AWS.

## Current Status

- **Phase**: Memory Bank Setup Complete - Ready for Implementation
- **Next**: Begin T001 Implementation (FastAPI base structure)
- **Timeline**: 4 semanas para MVP completo (T001-T036)
- **Current Focus**: Foundation Phase (T001-T010)

## Key Components

- **Backend Core**: Python 3.11 + FastAPI 0.115+ + SQLAlchemy 2.0.x + PostgreSQL 15.x
- **Trading Engine**: pandas 2.x + numpy 1.24+ + ta-lib + yfinance + backtrader
- **Async Processing**: Celery 5.3+ + Redis 7.x + RabbitMQ
- **Dashboard**: Streamlit 1.37 + plotly + matplotlib + seaborn
- **Infrastructure**: Docker Compose + AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- **CI/CD**: GitHub Actions + AWS deployment
- **Testing**: pytest 8.x + HTTPX + >90% coverage

## Quick Recovery Commands

```bash
# Load AlgoTrading MVP context
@project algoTrading

# Load current active context
@memory active-context

# Load technical stack
@memory tech-context

# Load project brief
@memory project-brief

# Load system patterns
@memory system-patterns

# Load current tasks
@memory tasks

# Load progress status
@memory progress
```

## Essential Files

- `.memory/core/project_brief.md` - AlgoTrading MVP foundation
- `.memory/core/tech_context.md` - Complete technology stack
- `.memory/active_context.md` - Current work focus and context
- `.memory/core/system_patterns.md` - AlgoTrading architectural patterns
- `.memory/core/progress.md` - Project progress and status
- `.memory/projects/algoTrading/tasks/detailed_task_breakdown.md` - Complete task breakdown T001-T036

## Critical Requirements

- **Performance**: < 1.5s response time para trading decisions
- **Test Coverage**: >90% con pytest + HTTPX
- **Scalability**: Microservices architecture con async processing
- **Security**: OAuth 2.0 + JWT + RBAC + AES-256 encryption
- **Availability**: 99.95% uptime target
- **Trading**: Momentum + Liquidity strategies para stocks, crypto, forex
- **Deployment**: CI/CD completo en GitHub Actions + AWS

## Task Structure

- **Total Tasks**: 36 (T001-T036)
- **Phase 1 Foundation**: 10 tareas (T001-T010)
- **Phase 2 Trading Engine**: 10 tareas (T011-T020)
- **Phase 3 Advanced Features**: 10 tareas (T021-T030)
- **Phase 4 Production Ready**: 6 tareas (T031-T036)

## Development Workflow

1. **Memory Bank Setup** ✅ - Complete
2. **T001-T003** - FastAPI base, configuración, base de datos
3. **T004-T005** - Modelos de usuario y autenticación JWT
4. **T006-T007** - Sistema de estrategias base y Momentum
5. **T008-T009** - Ejecución de órdenes y Celery workers
6. **T010** - Endpoints REST principales
7. **T011-T036** - Advanced features, CI/CD, production ready
