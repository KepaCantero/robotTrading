# Project Brief - AlgoTrading MVP

## Project Identity

**Name**: AlgoTrading MVP  
**Type**: Sistema completo de trading algorítmico  
**Domain**: Financial Technology - Algorithmic Trading  
**Architecture**: Microservices + Event-driven + Async Processing  
**Context Version**: 2025.10

## Business Objectives

- Implementar sistema personal de trading algorítmico para generar dinero
- Operar acciones, criptomonedas y forex mediante estrategias de momentum y liquidez
- Incluir análisis técnico, backtesting, alertas y dashboard Streamlit
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
