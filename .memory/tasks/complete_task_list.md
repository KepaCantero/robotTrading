# 📋 LISTA COMPLETA DE TODAS LAS TAREAS - ESTADO ACTUAL MVP

## 🎯 **RESUMEN EJECUTIVO**

### **TOTAL DE TAREAS: 94** (40 previas + 54 nuevas críticas MVP)

- **Tareas Completadas**: 44 (TASK-1-15, 31, TASK-57, TASK-TS, TASK-HT-01-03, TASK-DV-1-4, TASK-IND-1-5, TASK-IND-ROC-1-2, TASK-IND-OBV-1-2, TASK-IND-STOCH-1-2, TASK-IND-VWAP-1, TASK-IND-EXP-1, TASK-MET-RUNTIME-1, TASK-MET-FILL-1, TASK-MET-MULTI-1, TASK-SC-1-5, TASK-RM-1-5, BACKTEST-SUMMARY-1, ATR-FILTER-1, TRAILING-STOP-1, CVaR-METRIC-1, BENCHMARK-1, MONTE-CARLO-1, Linting)
- **Tareas Pendientes**: 56 (incluye tareas de Backtesting, Portfolio, etc.)
- **Estado General**: MVP READY + **Data Validation operativo** + **Advanced Technical Indicators** (ADX, ATR, MACD) + Linting corregido
- **Prioridad Actual**: Completar Signal Scoring + Risk Management + Backtesting + Portfolio Multi-Strategy + Nuevos Indicadores Momentum
- **Nuevas Tareas Críticas**:
  - Portfolio Allocation & Risk Management (10 tareas)
  - Estrategias Complementarias (8 tareas)
  - Backtesting & Validation (5 tareas)
  - Costos Realistas (2 tareas)
  - Indicadores Técnicos Avanzados & Sizing (16 tareas - 5 completadas, 11 pendientes: ROC, OBV, Stochastic RSI, VWAP, Expectancy, Runtime tracking, Fill ratio, Multi-timeframe)
  - Validación de Datos & Outliers (4 tareas)
  - Signal Scoring & Cooldown (5 tareas)
  - Simulación Realista de Ejecución (4 tareas)
  - Logging Estructurado & Reproducibilidad (5 tareas)
  - Dashboard & Monitoring (4 tareas)
  - Automated Tests & CI (3 tareas)
  - Documentación Automática (3 tareas)
  - Parameter Optimization & Presets (4 tareas)

---

---

## 📊 **LISTA COMPLETA DE TAREAS REORGANIZADA POR EFICIENCIA DE DESARROLLO**

### 🎯 **PRINCIPIO DE REORGANIZACIÓN**

**"Cuanto más se avance, menos archivos haya que tocar"**

Las tareas están organizadas por el número de archivos que requieren modificar, respetando las dependencias entre tareas. Esto optimiza el desarrollo porque:

- **Fase 1**: Cambios grandes que requieren muchos archivos (15+ archivos)
- **Fase 2**: Cambios medianos que requieren archivos medios (5-14 archivos)
- **Fase 3**: Cambios pequeños que requieren pocos archivos (1-4 archivos)
- **Fase 4**: Tareas opcionales/avanzadas

---

### 🔴 **FASE 1: TAREAS CON MÁS ARCHIVOS (15+ archivos) - Cambios Estructurales**

| ID          | Tarea                            | Estado        | Archivos | Descripción                                                                                                                                                                                                                                           |
| ----------- | -------------------------------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TASK-31** | Sistema de Estrategias Múltiples | ✅ Completada | 20+      | Implementar Strategy Protocol, Factory, Registry y Config-driven selection para ejecutar diferentes estrategias en backtesting y paper trading sin modificar código, basado en principio "Build a machine that can build, test, and run any strategy" |
| **TASK 10** | Centralización de Configuración  | ✅ Completada | 15+      | Extraer todos los valores mágicos y thresholds hardcodeados a configuración externa para facilitar optimización                                                                                                                                       |
| **TASK-15** | Refactorización de Servicios     | ✅ Completada | 15+      | Dividir SignalScorerService y PortfolioService en componentes menores para mejorar mantenibilidad                                                                                                                                                     |

### 🟠 **FASE 2: TAREAS CON ARCHIVOS MEDIOS (5-14 archivos) - Funcionalidades Core**

| ID          | Tarea                                     | Estado       | Archivos | Descripción                                                                                                                                                                                                                                |
| ----------- | ----------------------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **TASK-V2** | Ejecutar Backtesting Exhaustivo           | ⏳ Pendiente | 8-10     | Correr backtesting usando todos los parámetros configurables: thresholds, stop loss, take profit, tamaño de posición, correlación. Guardar resultados completos con métricas detalladas y artefactos versionados para análisis posterior   |
| **TASK-V3** | Registrar Métricas de Paper Trading       | ⏳ Pendiente | 6-8      | Medir P&L, drawdown, slippage, latencia y throughput por sesión. Crear logs detallados y artefactos versionados para análisis de rendimiento y validación de estrategias antes de capital real                                             |
| **TASK 14** | Unificación de Error Handling             | ⏳ Pendiente | 6-8      | Implementar TradingErrorHandler unificado para manejo consistente de errores en todo el sistema                                                                                                                                            |
| **TASK-R1** | Implementar Límite de Pérdida Diaria      | ⏳ Pendiente | 5-7      | Implementar daily_loss_limit = 0.05. Detener trading automático si se pierden >€2,500 en un día y notificar vía Telegram/Discord. Incluir lógica de circuit breaker y recuperación automática                                              |
| **TASK-R2** | Configurar Límite de Drawdown Máximo      | ⏳ Pendiente | 5-7      | Implementar max_drawdown_limit = 0.15. Pausar operaciones si capital cae >€7,500 desde máximo histórico. Incluir alertas automáticas y proceso de recuperación gradual                                                                     |
| **TASK-R3** | Stop Loss por Posición                    | ⏳ Pendiente | 5-7      | Implementar stop loss individual stop_loss_pct = 0.05. Cada orden no puede perder más del 5% de su valor. Incluir trailing stop loss y gestión automática de posiciones                                                                    |
| **TASK-R4** | Tamaño Máximo de Posición                 | ⏳ Pendiente | 5-7      | Limitar cada posición a 10% del capital (max_position_size = 0.1) para diversificar riesgos. Implementar validación automática antes de ejecutar órdenes y ajuste dinámico según volatilidad                                               |
| **TASK-R5** | Exposición y Correlación                  | ⏳ Pendiente | 5-7      | Evitar >70% correlación entre posiciones y >30% exposición por sector. Implementar análisis de correlación en tiempo real y validación automática de nuevas posiciones                                                                     |
| **TASK-R6** | Circuit Breakers Automáticos              | ⏳ Pendiente | 5-7      | Activar paradas si pérdida diaria > límite, drawdown > límite, volatilidad >5% o error rate >5%. Implementar sistema de circuit breakers con recuperación automática y notificaciones en tiempo real                                       |
| **TASK-R7** | Monitoreo y Alertas de Riesgo             | ⏳ Pendiente | 5-7      | Configurar notificaciones en tiempo real ante cualquier evento crítico: drawdown, stop loss activado, error del sistema, circuit breaker. Integrar con Telegram/Discord para alertas inmediatas                                            |
| **TASK-35** | Arquitectura de Modos Operativos          | ⏳ Pendiente | 5-6      | Implementar arquitectura de modos operativos que permita que el bot funcione con el mismo código base en distintos entornos: LIVE (datos en tiempo real), RECORDING (captura de datos), y BACKTEST (reproducción de datos históricos)      |
| **TASK-36** | Ciclo Autónomo de Ejecución               | ⏳ Pendiente | 3-4      | Implementar ciclo autónomo de ejecución que reproduzca el comportamiento del mercado sin depender del reloj real ni forzar diferencias entre código de live y backtest, simulando latencias y condiciones reales                           |
| **TASK-37** | Testing Environment para IBKR             | ⏳ Pendiente | 3-4      | Implementar testing environment para IBKR que permita depurar, testear y validar la lógica del bot durante horas cerradas del mercado, simulando respuestas del broker sin acceso real                                                     |
| **TASK-38** | Sincronización y Validación de Resultados | ⏳ Pendiente | 3-4      | Implementar sistema de sincronización y validación de resultados para garantizar que el mismo código de estrategia produzca resultados coherentes entre LIVE y BACKTEST, detectando divergencias y validando consistencia                  |
| **TASK-39** | Gestión Rigurosa del Riesgo (RMT)         | ⏳ Pendiente | 4-5      | Implementar sistema de gestión rigurosa del riesgo (RMT) que incluya circuit breakers, kill switches, límites de pérdida diaria/consecutiva, y protocolos de emergencia para proteger el capital y garantizar la supervivencia del sistema |
| **TASK-40** | Validación de Calidad de Datos            | ⏳ Pendiente | 3-4      | Implementar sistema de validación de calidad de datos para detectar inconsistencias, gaps inesperados de precios, datos incompletos, y asegurar la integridad de los datos de mercado utilizados en el sistema                             |

### 🟡 **FASE 3: TAREAS CON POCOS ARCHIVOS (1-4 archivos) - Optimización y Testing**

| ID          | Tarea                                           | Estado        | Archivos | Descripción                                                                                                                                                                                                                                                |
| ----------- | ----------------------------------------------- | ------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TASK-32** | Validación de Disciplina y Adherencia           | ⏳ Pendiente  | 2-3      | Implementar sistema de validación de disciplina y adherencia a la estrategia para evitar overfitting dinámico y asegurar que el algoritmo no ajuste parámetros automáticamente por resultados recientes                                                    |
| **TASK-33** | Evaluación de Resiliencia ante Eventos Extremos | ⏳ Pendiente  | 3-4      | Implementar sistema de evaluación de resiliencia ante eventos extremos para verificar que el sistema puede manejar escenarios de alta volatilidad, crisis de mercado y condiciones adversas sin exceder límites de riesgo                                  |
| **TASK-34** | Registro Completo de Decisiones y Trazabilidad  | ⏳ Pendiente  | 2-3      | Implementar sistema de registro completo de decisiones y trazabilidad para garantizar que cada entrada, salida, cambio de parámetros y decisión del sistema esté completamente registrada con fecha, hora, tamaño de posición y razón de operación         |
| **TASK-V5** | Revisión y Ajuste de Parámetros                 | ⏳ Pendiente  | 3-4      | Ajustar thresholds y stop loss según resultados de backtesting y paper trading, evitando sobreajuste y respetando límites de riesgo. Implementar proceso automatizado de revisión y ajuste basado en métricas de rendimiento                               |
| **TASK-13** | Tests de Concurrencia                           | ✅ Completada | 2-3      | Implementar tests de concurrencia para órdenes y señales para prevenir race conditions en producción                                                                                                                                                       |
| **TASK-17** | Seguridad y Compliance Básica                   | ⏳ Pendiente  | 3-4      | Implementar encriptación básica, rate limiting y manejo seguro de API keys, incluir auditoría de logs sensibles (asegurar que no se registren claves o credenciales), documentar en README los mecanismos de rotación de API keys y limitación de requests |
| **TASK-11** | Análisis Dinámico de Slippage                   | ⏳ Pendiente  | 2-3      | Implementar cálculo dinámico de slippage basado en volatilidad del mercado y liquidez, no solo 0.1% fijo                                                                                                                                                   |
| **TASK-12** | Validación de Rentabilidad                      | ✅ Completada | 2-3      | Crear tests que validen que las estrategias generan rentabilidad neta positiva después de todos los costos                                                                                                                                                 |
| **TASK-16** | Tests de Performance                            | ⏳ Pendiente  | 2-3      | Implementar tests de latencia y throughput (<100ms) para validar rendimiento en alta frecuencia                                                                                                                                                            |
| **TASK-18** | Cobertura de Tests                              | ⏳ Pendiente  | 2-3      | Aumentar cobertura global a 90%+ priorizando servicios críticos                                                                                                                                                                                            |
| **TASK-19** | Documentación Avanzada                          | ⏳ Pendiente  | 1-2      | Añadir documentación de patrones y métricas de rendimiento                                                                                                                                                                                                 |
| **TASK-20** | Monitoring y Observabilidad                     | ⏳ Pendiente  | 3-4      | Implementar métricas de trading y observabilidad avanzada, agregar alertas automáticas por Telegram o Discord cuando haya errores críticos en runtime o fallos de órdenes (coherente con arquitectura actual)                                              |

---

## 📊 **ESTADO POR CATEGORÍAS REORGANIZADO**

### **🔴 Críticas MVP (Fase 1-2)**

- **TASK-31**: ✅ COMPLETADA - Sistema de Estrategias Múltiples (20+ archivos)
- **TASK-10**: ✅ COMPLETADA - Centralización de Configuración (15+ archivos)
- **TASK-15**: Refactorización de Servicios (15+ archivos)
- **TASK-V2**: Backtesting Exhaustivo (8-10 archivos)
- **TASK-V3**: Métricas de Paper Trading (6-8 archivos)
- **TASK-14**: ✅ COMPLETADA - Unificación de Error Handling (6-8 archivos)
- **TASK-R1-R7**: Control de Riesgos (5-7 archivos cada una)
- **TASK-35-TASK-40**: Funcionalidades Core (3-6 archivos cada una)

### **🟡 Optimización MVP (Fase 3)**

- **TASK-32-TASK-34**: Validación y Trazabilidad (2-4 archivos cada una)
- **TASK-V5**: Revisión y Ajuste de Parámetros (3-4 archivos)
- **TASK-11-TASK-20**: Optimización y Testing (1-4 archivos cada una)

### **🟢 Post-MVP (Opcional)**

- **TASK-41-TASK-50**: Tareas adicionales identificadas (ver `additional_tasks_41_50.md`)

---

## 🚀 **ESTRATEGIA DE IMPLEMENTACIÓN OPTIMIZADA**

### **FASE 1: MVP OPERATIVO AWS/DOCKER (Tareas Críticas)**

1. **TASK-31**: ✅ COMPLETADA - Sistema de Estrategias Múltiples
2. **TASK-10**: ✅ COMPLETADA - Centralización de Configuración
3. **TASK-15**: Refactorización de Servicios
4. **TASK-V2**: Backtesting Exhaustivo
5. **TASK-V3**: Métricas de Paper Trading

### **FASE 2: CONTROL DE RIESGOS Y FUNCIONALIDADES CORE**

1. **TASK-R1-R7**: Control de Riesgos (7 tareas)
2. **TASK-35-TASK-40**: Funcionalidades Core (6 tareas)
3. **TASK-14**: ✅ COMPLETADA - Unificación de Error Handling

### **FASE 3: OPTIMIZACIÓN Y TESTING**

1. **TASK-32-TASK-34**: Validación y Trazabilidad
2. **TASK-V5**: Revisión y Ajuste de Parámetros
3. **TASK-11-TASK-20**: Optimización y Testing

---

## 📈 **MÉTRICAS DE PROGRESO OPTIMIZADO**

### **Progreso Actual**

- **Tareas Completadas**: 13/40 (32.5%)
- **Tareas Pendientes**: 29/40 (72.5%)
- **MVP Ready**: ✅ Base del sistema + Infraestructura completa + Sistema de base de datos + CI/CD automatizado + Análisis de costos + Optimización de parámetros + Sistema de estrategias múltiples

### **Objetivos por Fase**

- **Fase 1**: 5 tareas críticas (MVP operativo)
- **Fase 2**: 14 tareas (Control de riesgos + Funcionalidades core)
- **Fase 3**: 13 tareas (Optimización y testing)

---

## 🎯 **PRÓXIMOS PASOS RECOMENDADOS OPTIMIZADO**

### **1. Completar Fase 1 MVP (Fundamentos Críticos)**

- Implementar **TASK-31** (Sistema de Estrategias Múltiples)
- Implementar **TASK-10** (Centralización de Configuración)
- Implementar **TASK-15** (Refactorización de Servicios)

### **2. Implementar Fase 2 (Control de Riesgos)**

- Implementar **TASK-R1-R7** (Control de Riesgos)
- Implementar **TASK-35-TASK-40** (Funcionalidades Core)

### **3. Optimizar Fase 3 (Testing y Optimización)**

- Implementar **TASK-32-TASK-34** (Validación y Trazabilidad)
- Implementar **TASK-V5** (Revisión y Ajuste de Parámetros)

---

## 🎉 **CONCLUSIÓN OPTIMIZADA**

### **Sistema MVP**

- **40 tareas identificadas** (TASK-1 a TASK-40)
- **8 tareas completadas** (20% del MVP)
- **32 tareas pendientes** (80% del MVP)
- **Arquitectura sólida** con microservicios, FastAPI, PostgreSQL, Redis
- **Estrategias implementadas** (Momentum, Liquidity)
- **APIs completas** con 31 archivos de test
- **TASK 8 y TASK 9 completadas** (Análisis de costos + Optimización de parámetros)

### **Próximo Paso**

Implementar **TASK-31: Sistema de Estrategias Múltiples** para continuar con el MVP operativo.

### **Objetivo Final MVP**

Sistema estable 1 mes en AWS + Docker con:

- **Paper Trading activo** con métricas detalladas
- **Backtesting profesional** validado y funcional
- **Control de riesgos** implementado y operativo
- **Sistema de Estrategias Múltiples** con Strategy Protocol, Factory y Config-driven selection
- **Arquitectura de Modos Operativos** (LIVE/RECORDING/BACKTEST)
- **Ciclo Autónomo de Ejecución** con simulación realista
- **Testing Environment para IBKR** para desarrollo sin mercado
- **Sincronización y Validación de Resultados** entre modos
- **Gestión Rigurosa del Riesgo (RMT)** con circuit breakers y kill switches
- **Validación de Calidad de Datos** para integridad garantizada

**¿Quieres que proceda a implementar TASK-31 (Sistema de Estrategias Múltiples) para continuar con el MVP operativo?**

### ✅ **COMPLETADAS (8 tareas)**

| ID          | Tarea                            | Estado        | Descripción                                                                                                                                                          |
| ----------- | -------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TASK 1**  | FastAPI Base Structure           | ✅ Completada | Estructura base de FastAPI implementada                                                                                                                              |
| **TASK 2**  | Config Base                      | ✅ Completada | Configuración base implementada                                                                                                                                      |
| **TASK 3**  | Database Integration             | ✅ Completada | Integración con base de datos implementada                                                                                                                           |
| **TASK 4**  | API Endpoints                    | ✅ Completada | Endpoints de API implementados                                                                                                                                       |
| **TASK 5**  | Testing Framework                | ✅ Completada | Framework de testing implementado                                                                                                                                    |
| **TASK 8**  | Análisis de Costos Operativos    | ✅ Completada | Análisis detallado de costos de trading implementado                                                                                                                 |
| **TASK 9**  | Optimización de Parámetros       | ✅ Completada | Walk-forward analysis y prevención de overfitting implementados                                                                                                      |
| **TASK-V4** | Validación de Costos vs Ingresos | ✅ Completada | Incluir comisiones reales y estimaciones de slippage en P&L, calcular ROI simulado, verificar si estrategia genera al menos 5% mensual neto (TASK 8 ya implementado) |

---

## 📊 **ESTADO POR CATEGORÍAS REORGANIZADO**

### **✅ COMPLETADAS (8 tareas)**

- **TASK 1**: FastAPI Base Structure
- **TASK 2**: Config Base
- **TASK 3**: Database Integration
- **TASK 4**: API Endpoints
- **TASK 5**: Testing Framework
- **TASK 8**: Análisis de Costos Operativos vs Rendimiento
- **TASK 9**: Optimización de Parámetros y Prevención de Overfitting
- **TASK-V4**: Validación de Costos vs Ingresos

### **⏳ PENDIENTES MVP (45 tareas)**

- **🔴 Fase 1**: 3 tareas (TASK-31, TASK 10, TASK 15) - Cambios estructurales (15+ archivos)
- **🟠 Fase 2**: 10 tareas (TASK-V2, V3, V5, TASK 14, TASK-R1-R7) - Funcionalidades core (5-14 archivos)
- **🟡 Fase 3**: 9 tareas (TASK-V5, TASK 13, 17, 11, 12, 16, 18, 19, 20) - Optimización y testing (1-4 archivos)
- **🟢 Fase 4**: 4 tareas (TASK-L1-L4) - Live trading (3-4 archivos cada una)
- **🔵 Fase 5**: 10 tareas (TASK 21-30) - Estrategias avanzadas (2-3 archivos cada una)
- **🚀 Optimización**: 2 tareas (TASK-O2, O3) - Solo si ROI ≥5% mensual (2-3 archivos cada una)

---

## 🚀 **ESTRATEGIA DE IMPLEMENTACIÓN OPTIMIZADA**

### **FASE 1: CAMBIOS ESTRUCTURALES (Semanas 1-3) - 15+ archivos por tarea**

- **TASK-31**: Sistema de Estrategias Múltiples (20+ archivos)
- **TASK 10**: Centralización de Configuración (15+ archivos)
- **TASK 15**: Refactorización de Servicios (15+ archivos)

**Objetivo**: Estructura base sólida y modular para el resto del desarrollo

### **FASE 2: FUNCIONALIDADES CORE (Semanas 4-7) - 5-14 archivos por tarea**

- **TASK-V2**: Ejecutar Backtesting Exhaustivo (8-10 archivos)
- **TASK-V3**: Registrar Métricas de Paper Trading (6-8 archivos)
- **TASK 14**: Unificación de Error Handling (6-8 archivos)
- **TASK-R1-R7**: Control de Riesgos (5-7 archivos cada una)

**Objetivo**: Funcionalidades principales del sistema operativas

### **FASE 3: OPTIMIZACIÓN Y TESTING (Semanas 8-10) - 1-4 archivos por tarea**

- **TASK-V5**: Revisión y Ajuste de Parámetros (3-4 archivos)
- **TASK 13**: Tests de Concurrencia (2-3 archivos)
- **TASK 17**: Seguridad y Compliance Básica (3-4 archivos)
- **TASK 11**: Análisis Dinámico de Slippage (2-3 archivos)
- **TASK 12**: Validación de Rentabilidad (2-3 archivos)
- **TASK 16**: Tests de Performance (2-3 archivos)
- **TASK 18**: Cobertura de Tests (2-3 archivos)
- **TASK 19**: Documentación Avanzada (1-2 archivos)
- **TASK 20**: Monitoring y Observabilidad (3-4 archivos)

**Objetivo**: Sistema optimizado y robusto

### **FASE 4: LIVE TRADING (Semanas 11-12) - 3-4 archivos por tarea**

- **TASK-L1**: Configuración de Capital Real (3-4 archivos)
- **TASK-L2**: Monitoreo Manual y Alertas (3-4 archivos)
- **TASK-L3**: Ajuste Dinámico de Parámetros (3-4 archivos)
- **TASK-L4**: Validación de Rendimiento Real (3-4 archivos)

**Objetivo**: Live trading operativo con €50,000

### **FASE 5: ESTRATEGIAS AVANZADAS (Solo si ROI ≥5% mensual) - 2-3 archivos por tarea**

- **TASK 21-30**: Estrategias complejas, seguridad institucional, testing avanzado
- **TASK-O2**: Optimización Técnica Gradual
- **TASK-O3**: Escalado de Estrategias

**Objetivo**: Sistema institucional completo para capital real

---

## 📈 **MÉTRICAS DE PROGRESO OPTIMIZADO**

### **Progreso General**

- **Tareas Completadas**: 10/51 (20%)
- **Tareas Pendientes**: 43/51 (84%)
- **Tiempo Estimado Restante**: 12 semanas (MVP operativo + Live trading)

### **Progreso por Fase de Desarrollo**

- **🔴 Fase 1**: 0/3 completadas (0%) - Cambios estructurales
- **🟠 Fase 2**: 0/10 completadas (0%) - Funcionalidades core
- **🟡 Fase 3**: 0/9 completadas (0%) - Optimización y testing
- **🟢 Fase 4**: 0/4 completadas (0%) - Live trading
- **🔵 Fase 5**: 0/10 completadas (0%) - Estrategias avanzadas
- **🚀 Optimización**: 1/3 completadas (33%) - TASK-O1 completada
- **✅ Completadas**: 8/8 completadas (100%)

---

## 🎯 **PRÓXIMOS PASOS RECOMENDADOS OPTIMIZADO**

### **1. Completar Fase 1 (Cambios Estructurales)**

- **TASK-31**: Sistema de Estrategias Múltiples (Strategy Protocol, Factory, Config-driven)
- **TASK 10**: Centralización de Configuración (eliminar valores mágicos)
- **TASK 15**: Refactorización de Servicios (dividir servicios grandes)

### **2. Implementar Fase 2 (Funcionalidades Core)**

- **TASK-V2**: Ejecutar Backtesting Exhaustivo (todos los parámetros)
- **TASK-V3**: Registrar Métricas de Paper Trading (P&L, drawdown, slippage)
- **TASK 14**: Unificación de Error Handling (TradingErrorHandler unificado)
- **TASK-R1-R7**: Control de Riesgos (7 tareas críticas)

### **3. Optimizar Fase 3 (Testing y Optimización)**

- **TASK-V5**: Revisión y Ajuste de Parámetros (según resultados)
- **TASK 13**: Tests de Concurrencia (prevenir race conditions)
- **TASK 17**: Seguridad y Compliance Básica (encriptación, rate limiting)
- **TASK 11-12**: Análisis Dinámico de Slippage y Validación de Rentabilidad
- **TASK 16-20**: Tests de Performance, Cobertura, Documentación, Monitoring

### **4. Activar Live Trading (Fase 4)**

- **TASK-L1**: Configuración de Capital Real (€50,000)
- **TASK-L2**: Monitoreo Manual y Alertas (Telegram/Discord)
- **TASK-L3**: Ajuste Dinámico de Parámetros
- **TASK-L4**: Validación de Rendimiento Real

### **5. Escalar a Estrategias Avanzadas (Fase 5 - Solo si ROI ≥5% mensual)**

- **TASK 21-30**: Estrategias complejas, seguridad institucional, testing avanzado
- **TASK-O2**: Optimización Técnica Gradual
- **TASK-O3**: Escalado de Estrategias

---

## 🎉 **CONCLUSIÓN OPTIMIZADA**

### **✅ ESTADO ACTUAL**

- **Sistema Base**: Completamente implementado (TASK 1-5)
- **Análisis de Costos**: Completamente implementado (TASK 8)
- **Optimización de Parámetros**: Completamente implementado (TASK 9)
- **Sistema MVP**: Completamente implementado (TASK-31, TASK 10, TASK 15)
- **Funcionalidades Core**: Pendiente de implementación (TASK-V2, V3, V5, TASK 14, TASK-R1-R7)
- **Portfolio Multi-Strategy**: Pendiente de implementación (TASK-PA, TASK-RM, TASK-MR, TASK-PT, TASK-BV, TASK-MET, TASK-CST - 20 tareas críticas)
- **Optimización y Testing**: Pendiente de implementación (TASK-V5, TASK 13, 17, 11, 12, 16, 18, 19, 20)
- **Live Trading**: Pendiente de implementación (TASK-L1-L4)
- **Total**: 47 tareas pendientes de 60 totales

### **🚀 OBJETIVO FINAL MVP OPTIMIZADO**

- **Sistema Operativo AWS/Docker** para paper trading activo
- **Sistema de Estrategias Múltiples** con Strategy Protocol, Factory y Config-driven selection
- **Backtesting Profesional** validado y funcional con múltiples estrategias
- **Control de Riesgos** implementado con circuit breakers automáticos
- **Paper Trading** con métricas detalladas por sesión y cambio dinámico de estrategias
- **Live Trading** operativo con €50,000 y monitoreo completo
- **Configuración Centralizada** y optimizada
- **Concurrencia Robusta** probada y estable
- **Seguridad Básica** garantizada

### **🎯 VENTAJA DE LA REORGANIZACIÓN**

**"Cuanto más se avance, menos archivos haya que tocar"**

Esta reorganización optimiza el desarrollo porque:

1. **Fase 1**: Se hacen todos los cambios grandes que requieren muchos archivos al principio
2. **Fase 2**: Se hacen cambios medianos que dependen de la Fase 1
3. **Fase 3**: Se hacen cambios pequeños que requieren pocos archivos
4. **Fase 4**: Se hacen tareas de live trading que requieren pocos archivos
5. **Fase 5**: Se hacen tareas opcionales/avanzadas al final

Esto hace el desarrollo más eficiente y menos propenso a conflictos.

**¿Quieres que proceda a implementar TASK-31 (Sistema de Estrategias Múltiples) para continuar con el MVP operativo?**

---

## 🟢 **FASE 5: TAREAS CRÍTICAS MVP - Portfolio Multi-Strategy**

### 📊 **Portfolio Allocation & Risk Management (10 tareas críticas)**

| ID                  | Tarea                            | Estado       | Archivos | Descripción                                                                                                                                                         |
| ------------------- | -------------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TASK-PA-1**       | Asignación Multi-Estrategia      | ⏳ Pendiente | 5-7      | Implementar asignación de capital: 50% Momentum, 25% Mean Reversion, 25% Pairs Trading                                                                              |
| **TASK-PA-2**       | Portfolio Manager                | ⏳ Pendiente | 4-6      | Crear módulo que distribuya capital entre estrategias según asignaciones configuradas                                                                               |
| **TASK-PORT-SEL-1** | Selector de Portfolio Dinámico   | ⏳ Pendiente | 4-6      | Módulo que selecciona y pondera Momentum, Mean Reversion y Pairs Trading según performance rolling de 30 días. Ajusta peso Momentum entre 40–70% según consistencia |
| **TASK-RM-1**       | Riesgo por Operación <2%         | ⏳ Pendiente | 3-5      | Limitar riesgo individual por trade a <2% del capital total (target 1-1.5%)                                                                                         |
| **TASK-RM-2**       | Ratio Riesgo/Recompensa ≥1:3     | ⏳ Pendiente | 3-5      | Implementar ratio objetivo de riesgo/recompensa ≥1:3 (arriesgar 1 para ganar 3)                                                                                     |
| **TASK-RM-3**       | Exposición Máxima por Estrategia | ⏳ Pendiente | 4-6      | Limitar exposición: 50% Momentum, 25-30% Mean Reversion, 20-30% Pairs Trading                                                                                       |
| **TASK-RM-4**       | Límite Drawdown Máximo 15%       | ⏳ Pendiente | 3-5      | Implementar stop general si portafolio cae >15% desde máximo reciente                                                                                               |
| **TASK-RM-5**       | Circuit Breakers 3-5 Stops       | ⏳ Pendiente | 3-5      | Pausar estrategia tras 3-5 stops consecutivos                                                                                                                       |
| **TASK-REB-1**      | Rebalanceo Mensual               | ⏳ Pendiente | 2-4      | Implementar rebalanceo mensual para mantener asignaciones objetivo de capital                                                                                       |
| **TASK-REB-2**      | Ajustes Dinámicos Capital        | ⏳ Pendiente | 3-5      | Reducir temporalmente capital de estrategias con rachas negativas                                                                                                   |

### 🎯 **Estrategias Complementarias (8 tareas críticas)**

| ID            | Tarea                             | Estado       | Archivos | Descripción                                                                               |
| ------------- | --------------------------------- | ------------ | -------- | ----------------------------------------------------------------------------------------- |
| **TASK-MR-1** | Mean Reversion Señal Compra       | ⏳ Pendiente | 2-3      | Implementar señal de compra cuando RSI < 30 y precio cerca de banda inferior Bollinger    |
| **TASK-MR-2** | Mean Reversion Señal Venta        | ⏳ Pendiente | 2-3      | Implementar señal de venta cuando RSI > 70 y precio cerca de banda superior Bollinger     |
| **TASK-PT-1** | Pairs Trading Correlación         | ⏳ Pendiente | 3-4      | Implementar detección de correlación entre pares de activos (coeficiente > 0.7)           |
| **TASK-PT-2** | Pairs Trading Spread              | ⏳ Pendiente | 3-4      | Implementar cálculo de spread entre pares correlacionados y señal de divergencia temporal |
| **TASK-PT-3** | Pairs Trading Apertura Simultánea | ⏳ Pendiente | 4-5      | Implementar apertura simultánea: short en activo sobrevalorado y long en subvalorado      |
| **TASK-PT-4** | Pairs Trading Cierre              | ⏳ Pendiente | 3-4      | Implementar cierre de par cuando spread vuelve a niveles normales o take-profit alcanzado |

### 📊 **Backtesting & Validation (5 tareas críticas)**

| ID             | Tarea                     | Estado       | Archivos | Descripción                                                                                       |
| -------------- | ------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------- |
| **TASK-BV-1**  | Walk-Forward Validation   | ⏳ Pendiente | 4-6      | Implementar backtesting walk-forward: entrenar en ventana histórica y probar en período siguiente |
| **TASK-BV-2**  | Cross-Validation Temporal | ⏳ Pendiente | 3-5      | Implementar validación cruzada temporal para evaluar consistencia de estrategias                  |
| **TASK-MET-1** | Sharpe y Sortino Ratio    | ⏳ Pendiente | 2-3      | Implementar cálculo de Sharpe Ratio y Sortino Ratio en métricas de backtesting                    |
| **TASK-MET-2** | Risk/Reward Ratio         | ⏳ Pendiente | 2-3      | Implementar cálculo de Risk/Reward ratio promedio por operación (target ≥1:3)                     |

### 💰 **Costos Realistas (2 tareas críticas)**

| ID             | Tarea                      | Estado       | Archivos | Descripción                                                                                  |
| -------------- | -------------------------- | ------------ | -------- | -------------------------------------------------------------------------------------------- |
| **TASK-CST-1** | Ajustar Costos Backtesting | ⏳ Pendiente | 2-3      | Incorporar spreads (0.01-0.03%), comisiones (0.01-0.05%) y slippage realistas en backtesting |
| **TASK-CST-2** | Cálculo Costos Totales     | ⏳ Pendiente | 2-3      | Implementar cálculo de costos totales por trade (0.02-0.1% adicional por transacción)        |

### 🔬 **Indicadores Técnicos Avanzados & Sizing (16 tareas - 5 completadas, 11 pendientes)**

| ID                     | Tarea                        | Estado        | Archivos | Descripción                                                                                 |
| ---------------------- | ---------------------------- | ------------- | -------- | ------------------------------------------------------------------------------------------- |
| **TASK-IND-1**         | ADX para Detectar Tendencia  | ✅ Completada | 3-4      | Implementar ADX para distinguir tendencia fuerte (>25) vs. rango                            |
| **TASK-IND-2**         | ATR para Stop Loss Dinámico  | ✅ Completada | 4-5      | Usar ATR (2x valor) para calcular stop loss dinámico que se ajusta a volatilidad del activo |
| **TASK-IND-3**         | MACD para Confirmación       | ✅ Completada | 3-4      | Integrar MACD histogram divergence como confirmador de señales (bullish/bearish crossover)  |
| **TASK-IND-4**         | ATR-Based Position Sizing    | ✅ Completada | 4-6      | Calcular tamaño de posición basado en ATR: riesgo por trade = 2% capital / (ATR \* 2)       |
| **TASK-IND-5**         | Filtros Volumen Dinámico     | ✅ Completada | 3-4      | Implementar filtro dinámico de volumen: volume_ratio > 1.2 para confirmar liquidez          |
| **TASK-IND-ROC-1**     | Implementar ROC              | ✅ Completada | 2-3      | Implementar ROC (Rate of Change) para detectar aceleración de precio                        |
| **TASK-IND-ROC-2**     | Integrar ROC en Momentum     | ✅ Completada | 2-3      | Integrar ROC en MomentumStrategy para reforzar detección de momentum real                   |
| **TASK-IND-OBV-1**     | Implementar OBV              | ✅ Completada | 2-3      | Implementar OBV (On Balance Volume) para confirmación de volumen en momentum                |
| **TASK-IND-OBV-2**     | Integrar OBV en Momentum     | ✅ Completada | 2-3      | Integrar OBV en MomentumStrategy para confirmar flujo de volumen                            |
| **TASK-IND-STOCH-1**   | Implementar Stochastic RSI   | ✅ Completada | 2-3      | Implementar Stochastic RSI para detectar pérdida de momentum y reversiones                  |
| **TASK-IND-STOCH-2**   | Usar Stochastic RSI          | ✅ Completada | 2-3      | Usar Stochastic RSI en MomentumStrategy para filtrar falsas señales                         |
| **TASK-IND-VWAP-1**    | Implementar VWAP             | ✅ Completada | 3-4      | Implementar VWAP para referencia de precio ponderado por volumen intradía                   |
| **TASK-IND-EXP-1**     | Métrica Expectancy           | ✅ Completada | 2-3      | Añadir cálculo de Expectancy como métrica de consistencia del sistema                       |
| **TASK-MET-RUNTIME-1** | Runtime Performance          | ✅ Completada | 2-3      | Añadir tracking de performance runtime (tiempo ejecución por ciclo data→signal→order)       |
| **TASK-MET-FILL-1**    | Order Fill Ratio             | ✅ Completada | 3-4      | Implementar tracking de order fill ratio para medir calidad de ejecución                    |
| **TASK-MET-MULTI-1**   | Multi-Timeframe Confirmation | ✅ Completada | 4-5      | Implementar confirmación multi-timeframe (15m, 1h, 4h, diario) para MomentumStrategy        |

### ✅ **Validación de Datos & Outliers (4 tareas críticas)**

| ID            | Tarea                         | Estado       | Archivos | Descripción                                                                                 |
| ------------- | ----------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------- |
| **TASK-DV-1** | Detección de Gaps de Precios  | ⏳ Pendiente | 3-4      | Detectar gaps inesperados >5% que puedan generar señales falsas y ajustar cálculo           |
| **TASK-DV-2** | Identificación de Outliers    | ⏳ Pendiente | 3-4      | Identificar outliers usando z-score >3 y filtrar datos anómalos antes del análisis          |
| **TASK-DV-3** | Validación de Consistencia    | ⏳ Pendiente | 2-3      | Verificar que OHLC sea consistente (high >= low, high >= close/open, low <= close/open)     |
| **TASK-DV-4** | Calidad de Datos Pre-Backtest | ⏳ Pendiente | 3-5      | Ejecutar data quality checks completos antes de cada backtest (gaps, outliers, completitud) |

### 🎯 **Signal Scoring & Cooldown (5 tareas críticas)**

| ID            | Tarea                      | Estado       | Archivos | Descripción                                                                                                              |
| ------------- | -------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| **TASK-SC-1** | Sistema de Cooldown        | ⏳ Pendiente | 3-4      | Implementar cooldown period por símbolo (5-15 min) para evitar sobre-trading y señales duplicadas                        |
| **TASK-SC-2** | Signal Compound Score      | ⏳ Pendiente | 4-5      | Crear score compuesto que combine: confidence (30%), volume_ratio (25%), volatility (20%), liquidity (15%), timing (10%) |
| **TASK-SC-3** | Signal Priority Ranking    | ⏳ Pendiente | 3-4      | Priorizar señales por compound score: >80=high, 50-80=medium, <50=low                                                    |
| **TASK-SC-4** | Portfolio Signal Filtering | ⏳ Pendiente | 4-6      | PortfolioManager debe filtrar y priorizar señales para evitar posiciones cruzadas conflictivas por estrategia/símbolo    |
| **TASK-SC-5** | Signal Scoring Integration | ⏳ Pendiente | 3-4      | Integrar scoring engine en estrategias para que todas las señales tengan compound score coherente                        |

### ⚡ **Simulación Realista de Ejecución (4 tareas críticas)**

| ID            | Tarea                    | Estado       | Archivos | Descripción                                                                                               |
| ------------- | ------------------------ | ------------ | -------- | --------------------------------------------------------------------------------------------------------- |
| **TASK-EX-1** | Slippage por Símbolo     | ⏳ Pendiente | 3-4      | Implementar slippage dinámico por símbolo (0.05-0.15% crypto, 0.1-0.3% stocks, 0.2-0.5% low-volume)       |
| **TASK-EX-2** | Latencia de Ejecución    | ⏳ Pendiente | 3-4      | Simular latencia realista: 50-200ms para orden limit, 100-500ms para market                               |
| **TASK-EX-3** | Verificación de Fills    | ⏳ Pendiente | 4-5      | Implementar fill validation: verificar que precio de ejecución sea realista (dentro de spread de mercado) |
| **TASK-EX-4** | Partial Fills Simulation | ⏳ Pendiente | 3-4      | Simular partial fills para órdenes grandes que no pueden ejecutarse completamente en un solo momento      |

### 📊 **Logging Estructurado & Reproducibilidad (5 tareas críticas)**

| ID             | Tarea                         | Estado       | Archivos | Descripción                                                                                         |
| -------------- | ----------------------------- | ------------ | -------- | --------------------------------------------------------------------------------------------------- |
| **TASK-LOG-1** | Structured Logging con Hashes | ⏳ Pendiente | 3-4      | Implementar logging estructurado con hash único por señal/trade para trazabilidad completa          |
| **TASK-LOG-2** | Commit SHA & Run Metadata     | ⏳ Pendiente | 2-3      | Incluir commit SHA, timestamp, git branch y seed en metadata de cada backtest para reproducibilidad |
| **TASK-LOG-3** | Seed-Based Reproducibilidad   | ⏳ Pendiente | 3-4      | Usar seeds determinísticos para todos los procesos aleatorios (simulación, sampleo, etc.)           |
| **TASK-LOG-4** | Audit Trail Completo          | ⏳ Pendiente | 4-5      | Generar audit trail con: decisión, razones, parámetros, resultados, timestamp para auditoría        |
| **TASK-LOG-5** | Export Resultados Versionados | ⏳ Pendiente | 3-4      | Exportar resultados de backtest con versionado automático a /docs/BACKTEST_RESULTS con timestamp    |

### 🔔 **Dashboard & Monitoring (4 tareas críticas)**

| ID              | Tarea                     | Estado       | Archivos | Descripción                                                                                                  |
| --------------- | ------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------ |
| **TASK-DASH-1** | Integración Dashboard     | ⏳ Pendiente | 4-5      | Integrar dashboard existente con PortfolioManager para visualizar asignaciones por estrategia en tiempo real |
| **TASK-DASH-2** | Kill-Switch por Drawdown  | ⏳ Pendiente | 3-4      | Implementar kill-switch automático que detiene trading si drawdown > 15% (TASK-RM-4)                         |
| **TASK-DASH-3** | Alertas Infraestructura   | ⏳ Pendiente | 3-4      | Integrar alertas de infraestructura (errores críticos, timeouts, API failures) con Telegram/Discord          |
| **TASK-DASH-4** | Monitoring Dashboard Live | ⏳ Pendiente | 4-6      | Crear panel de monitoring en dashboard: P&L por estrategia, exposure, drawdown, error rate, latencia         |

### 🧪 **Automated Tests & CI (3 tareas críticas)**

| ID              | Tarea                          | Estado       | Archivos | Descripción                                                                                              |
| --------------- | ------------------------------ | ------------ | -------- | -------------------------------------------------------------------------------------------------------- |
| **TASK-TEST-1** | Tests Automatizados Portfolio  | ⏳ Pendiente | 3-4      | Crear tests automatizados para PortfolioManager: allocation, rebalancing, risk limits, signal filtering  |
| **TASK-TEST-2** | CI Integration                 | ⏳ Pendiente | 3-4      | Integrar tests en CI pipeline: ejecutar tests antes de merge, validar calidad de código y cobertura >80% |
| **TASK-TEST-3** | Data Quality Checks Automation | ⏳ Pendiente | 4-5      | Automatizar data quality checks (TASK-DV-1 a TASK-DV-4) antes de cada backtest en CI/CD                  |

### 📚 **Documentación Automática (3 tareas críticas)**

| ID             | Tarea                             | Estado       | Archivos | Descripción                                                                                                  |
| -------------- | --------------------------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------ |
| **TASK-DOC-1** | Generación Automática de Docs     | ⏳ Pendiente | 3-4      | Generar automáticamente documentación de estrategias, parámetros y métricas en /docs                         |
| **TASK-DOC-2** | Reportes Auditables Post-Backtest | ⏳ Pendiente | 4-5      | Generar reportes auditables post-backtest: configuración usada, resultados, métricas, artefactos versionados |
| **TASK-DOC-3** | Strategy Cards Documentation      | ⏳ Pendiente | 2-3      | Crear "strategy cards" con descripción, parámetros, risk profile y performance esperada para cada estrategia |

### 🔧 **Parameter Optimization & Presets (4 tareas críticas)**

| ID                 | Tarea                             | Estado       | Archivos | Descripción                                                                                                                         |
| ------------------ | --------------------------------- | ------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **TASK-PARAM-1**   | Definir Presets de Parámetros     | ⏳ Pendiente | 2-3      | Definir presets de parámetros conservadores/agresivos/balanceados para cada estrategia como punto de partida                        |
| **TASK-PARAM-2**   | Grid Search de Parámetros         | ⏳ Pendiente | 3-4      | Implementar grid search para optimizar parámetros clave (stop_loss, take_profit, threshold) usando walk-forward                     |
| **TASK-PARAM-3**   | Sensible Ranges por Indicador     | ⏳ Pendiente | 2-3      | Definir rangos sensibles de parámetros: RSI (20-80), ATR multiplier (1.5-3.0), Volume ratio (>1.0), correlación (>0.7)              |
| **TASK-MOM-OPT-1** | Momentum Auto-Optimization Engine | ⏳ Pendiente | 3-4      | Sistema que recalibra los parámetros RSI/EMA/MACD cada mes (walk-forward), priorizando estabilidad y baja varianza del equity curve |

---

## 🔵 **FASE 6: TAREAS POST-MVP - Tests Avanzados**

| ID          | Tarea                                  | Estado       | Archivos | Descripción                                                                                                                         |
| ----------- | -------------------------------------- | ------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **TASK-TS** | Implementar Tests Avanzados Eliminados | ⏳ Pendiente | 8        | Reimplementar los siguientes tests que fueron eliminados por errores persistentes, pero que son necesarios para cobertura completa: |
|             |                                        |              |          | - test_centralized_logging.py - Tests para sistema de logging centralizado                                                          |
|             |                                        |              |          | - test_centralized_logging_simple.py - Tests simplificados para logging                                                             |
|             |                                        |              |          | - test_error_handling_simple.py - Tests para manejo de errores                                                                      |
|             |                                        |              |          | - test_cicd.py - Tests para integración continua                                                                                    |
|             |                                        |              |          | - test_docker_configuration.py - Tests para configuración Docker                                                                    |
|             |                                        |              |          | - test_concurrency_simple.py - Tests para concurrencia                                                                              |
|             |                                        |              |          | - test_test_configuration_system.py - Tests para sistema de configuración                                                           |
|             |                                        |              |          | - test_api_momentum.py - Tests para API de momentum                                                                                 |
|             |                                        |              |          | **Prioridad**: Baja. Estas tareas se implementarán después de que el MVP esté completamente operativo en producción.                |

---

## 📋 **ANÁLISIS DE TAREAS - SUBTAREAS Y PRIORIZACIÓN**

### ✅ **TAREAS MANEJABLES (2-3 horas) - 38 tareas**

#### **FASE 1: Validación de Datos (4/4 manejables)**

- TASK-DV-1, DV-2, DV-3, DV-4

#### **FASE 2: Indicadores Técnicos (3/5 manejables)**

- TASK-IND-1 (ADX)
- TASK-IND-3 (MACD)
- TASK-IND-5 (Filtro Volumen)

#### **FASE 3: Signal Scoring (3/5 manejables)**

- TASK-SC-1 (Cooldown)
- TASK-SC-3 (Priority Ranking)
- TASK-SC-5 (Scoring Integration)

#### **FASE 4: Gestión Capital y Riesgo (7/10 manejables)**

- TASK-RM-1, RM-2, RM-4, RM-5
- TASK-REB-1, REB-2
- TASK-PA-2 (Portfolio Manager)

#### **FASE 5: Backtesting (3/6 manejables)**

- TASK-MET-1 (Sharpe/Sortino)
- TASK-MET-2 (Risk/Reward)
- TASK-CST-2 (Costos Totales)

#### **FASE 6: Optimización (3/4 manejables)**

- TASK-PARAM-1 (Presets)
- TASK-PARAM-3 (Rangos Sensibles)
- TASK-MOM-OPT-1 (Recalibración - ver subtareas abajo)

#### **FASE 8: Logging (2/5 manejables)**

- TASK-LOG-2 (Commit SHA)
- TASK-LOG-5 (Export Versionados)

#### **FASE 10: Tests y CI (1/3 manejables)**

- TASK-TEST-2 (CI Integration)

#### **FASE 12: Estrategias (8/8 manejables)**

- TASK-MR-1, MR-2
- TASK-PT-1, PT-2, PT-3, PT-4

### ⚠️ **TAREAS QUE REQUIEREN SUBDIVISIÓN - 32 tareas**

#### **FASE 2: Indicadores (2 tareas)**

**TASK-IND-2 (ATR Stop Loss)**: SUBDIVIDIR

- TASK-IND-2a: Crear función calculate_stop_loss_from_atr() (2h)
- TASK-IND-2b: Integrar con PositionSizingEngine (2h)

**TASK-IND-4 (ATR-Based Position Sizing)**: SUBDIVIDIR

- TASK-IND-4a: Función calculate_position_size_from_atr() (2h)
- TASK-IND-4b: Tests de sizing con ATR (2h)
- TASK-IND-4c: Integración con PortfolioService (2h)

#### **FASE 3: Signal Scoring (2 tareas)**

**TASK-SC-2 (Signal Compound Score)**: SUBDIVIDIR

- TASK-SC-2a: Definir fórmula: confidence(30%) + volume(25%) + volatility(20%) + liquidity(15%) + timing(10%) (1h)
- TASK-SC-2b: Implementar cálculo en ScoringEngine (2h)
- TASK-SC-2c: Tests de compound score (2h)

**TASK-SC-4 (Portfolio Signal Filtering)**: SUBDIVIDIR (CRÍTICA)

- TASK-SC-4a: Filtrar señales conflictivas por símbolo (2h)
- TASK-SC-4b: Filtrar señales conflictivas por estrategia (2h)
- TASK-SC-4c: Resolver conflictos con reglas de prioridad (2h)
- TASK-SC-4d: Tests de filtering completo (2h)

#### **FASE 4: Portfolio & Risk (3 tareas)**

**TASK-PA-1 (Asignación Multi-Estrategia)**: SUBDIVIDIR

- TASK-PA-1a: Configurar asignaciones en config/trading_strategies.yaml (1h)
- TASK-PA-1b: Implementar distribución en PortfolioManager (2h)
- TASK-PA-1c: Tests de asignaciones (2h)

**TASK-PORT-SEL-1 (Selector Dinámico)**: SUBDIVIDIR

- TASK-PORT-SEL-1a: Tracking de performance 30 días por estrategia (2h)
- TASK-PORT-SEL-1b: Lógica de ajuste de pesos (40-70% Momentum) (2h)
- TASK-PORT-SEL-1c: Tests de selector dinámico (2h)

**TASK-RM-3 (Exposición por Estrategia)**: SUBDIVIDIR

- TASK-RM-3a: Calcular exposición actual por estrategia (2h)
- TASK-RM-3b: Validación de límites (50% / 25-30% / 20-30%) (2h)
- TASK-RM-3c: Alertas de sobre-exposición (1h)

#### **FASE 5: Backtesting (3 tareas)**

**TASK-BV-1 (Walk-Forward Validation)**: SUBDIVIDIR

- TASK-BV-1a: División de datos train/test temporal (2h)
- TASK-BV-1b: Lógica iterativa de walk-forward (3h)
- TASK-BV-1c: Métricas de validación cruzada (2h)

**TASK-BV-2 (Cross-Validation Temporal)**: SUBDIVIDIR

- TASK-BV-2a: Implementar splits temporales (3, 5, 10 períodos) (2h)
- TASK-BV-2b: Agregación de métricas entre períodos (2h)
- TASK-BV-2c: Reportes de consistencia (1h)

**TASK-CST-1 (Costos Backtesting)**: SUBDIVIDIR

- TASK-CST-1a: Modelo de spreads por asset class (1h)
- TASK-CST-1b: Comisiones configurables (1h)
- TASK-CST-1c: Slippage dinámico por liquidez (2h)

#### **FASE 6: Optimización (1 tarea)**

**TASK-PARAM-2 (Grid Search)**: SUBDIVIDIR

- TASK-PARAM-2a: Función grid_search() con parámetros configurables (2h)
- TASK-PARAM-2b: Evaluación de métricas por combinación (2h)
- TASK-PARAM-2c: Integración con walk-forward (2h)
- TASK-PARAM-2d: Tests de grid search (2h)

**TASK-MOM-OPT-1 (Auto-Optimization)**: SUBDIVIDIR

- TASK-MOM-OPT-1a: Recalibración mensual RSI/EMA/MACD (2h)
- TASK-MOM-OPT-1b: Integración con walk-forward (2h)
- TASK-MOM-OPT-1c: Tests de estabilidad equity curve (2h)

#### **FASE 7: Simulación Ejecución (4 tareas)**

**TASK-EX-1 (Slippage por Símbolo)**: SUBDIVIDIR

- TASK-EX-1a: Tabla de slippage por asset class (crypto/stocks/low-vol) (1h)
- TASK-EX-1b: Implementar slippage dinámico en ejecución (2h)
- TASK-EX-1c: Tests de slippage por símbolo (2h)

**TASK-EX-2 (Latencia Ejecución)**: SUBDIVIDIR

- TASK-EX-2a: Simular latencia limit orders (50-200ms) (1h)
- TASK-EX-2b: Simular latencia market orders (100-500ms) (2h)
- TASK-EX-2c: Tests de latencia (1h)

**TASK-EX-3 (Validación Fills)**: SUBDIVIDIR

- TASK-EX-3a: Validar precio dentro de spread (2h)
- TASK-EX-3b: Detectar fills imposibles/rechazarlos (2h)
- TASK-EX-3c: Tests de validación fills (1h)

**TASK-EX-4 (Partial Fills)**: SUBDIVIDIR

- TASK-EX-4a: Simular fills parciales para órdenes grandes (2h)
- TASK-EX-4b: Integración con sistema de órdenes (2h)
- TASK-EX-4c: Tests de partial fills (1h)

#### **FASE 8: Logging (3 tareas)**

**TASK-LOG-1 (Structured Logging)**: SUBDIVIDIR

- TASK-LOG-1a: Hash único por señal (SHA256) (2h)
- TASK-LOG-1b: Hash único por trade (SHA256) (2h)
- TASK-LOG-1c: Tests de trazabilidad con hashes (1h)

**TASK-LOG-3 (Seed-Based Reproducibilidad)**: SUBDIVIDIR

- TASK-LOG-3a: Seeds determinísticos en funciones aleatorias (2h)
- TASK-LOG-3b: Validación de reproducibilidad (2h)
- TASK-LOG-3c: Tests de seeds (1h)

**TASK-LOG-4 (Audit Trail)**: SUBDIVIDIR

- TASK-LOG-4a: Estructura de audit trail (decisión, razones, params, resultados, timestamp) (2h)
- TASK-LOG-4b: Poblar audit trail en cada decisión crítica (3h)
- TASK-LOG-4c: Export de audit trail a /logs/audit/ (1h)
- TASK-LOG-4d: Tests de audit trail (2h)

#### **FASE 9: Dashboard (4 tareas)**

**TASK-DASH-1 (Integración Dashboard)**: SUBDIVIDIR

- TASK-DASH-1a: Endpoint de datos de asignaciones por estrategia (2h)
- TASK-DASH-1b: Visualización en dashboard Streamlit (2h)
- TASK-DASH-1c: Tests de integración (1h)

**TASK-DASH-2 (Kill-Switch)**: SUBDIVIDIR

- TASK-DASH-2a: Lógica de kill-switch si drawdown > 15% (2h)
- TASK-DASH-2b: Integración con monitoring system (1h)
- TASK-DASH-2c: Tests de kill-switch (2h)

**TASK-DASH-3 (Alertas Infraestructura)**: SUBDIVIDIR

- TASK-DASH-3a: Detectar errores críticos, timeouts, API failures (2h)
- TASK-DASH-3b: Integrar notificaciones Telegram/Discord (2h)
- TASK-DASH-3c: Tests de alertas (1h)

**TASK-DASH-4 (Monitoring Dashboard Live)**: SUBDIVIDIR

- TASK-DASH-4a: Panel de monitoring en Streamlit (3h)
- TASK-DASH-4b: Métricas: P&L por estrategia, exposure, drawdown, error rate, latencia (3h)
- TASK-DASH-4c: Tests de panel (2h)

#### **FASE 10: Tests (2 tareas)**

**TASK-TEST-1 (Tests Portfolio)**: SUBDIVIDIR

- TASK-TEST-1a: Tests de allocation (2h)
- TASK-TEST-1b: Tests de rebalancing (2h)
- TASK-TEST-1c: Tests de risk limits (1h)
- TASK-TEST-1d: Tests de signal filtering (2h)

**TASK-TEST-3 (Data Quality Automation)**: SUBDIVIDIR

- TASK-TEST-3a: Automatizar TASK-DV-1 (gaps) en CI (1h)
- TASK-TEST-3b: Automatizar TASK-DV-2 (outliers) en CI (1h)
- TASK-TEST-3c: Automatizar TASK-DV-3 (consistencia) en CI (1h)
- TASK-TEST-3d: Automatizar TASK-DV-4 (checks completos) en CI (2h)

#### **FASE 11: Documentación (3 tareas)**

**TASK-DOC-1 (Generación Docs)**: SUBDIVIDIR

- TASK-DOC-1a: Templates de documentación estrategias (1h)
- TASK-DOC-1b: Generación automática de docs en /docs (2h)
- TASK-DOC-1c: Tests de generación (1h)

**TASK-DOC-2 (Reportes Auditables)**: SUBDIVIDIR

- TASK-DOC-2a: Reporte de configuración usada en backtest (1h)
- TASK-DOC-2b: Reporte de resultados y métricas (2h)
- TASK-DOC-2c: Artefactos versionados (1h)
- TASK-DOC-2d: Tests de reportes (1h)

**TASK-DOC-3 (Strategy Cards)**: SUBDIVIDIR

- TASK-DOC-3a: Cards para cada estrategia (descripción, params, risk profile) (2h)
- TASK-DOC-3b: Performance esperada por estrategia (1h)
- TASK-DOC-3c: Tests de cards (1h)

### 🎯 **PRIORIZACIÓN FINAL**

#### **CRÍTICO - Implementar Primero (Día 1-2)**

1. **TASK-DV-1, DV-2, DV-3, DV-4** (4 tareas, 2h c/u = 8h) ⚠️ CRÍTICO: Base de todo
2. **TASK-IND-1, IND-3, IND-5** (3 tareas, 2-3h c/u = 6-9h)
3. **TASK-SC-1, SC-3, SC-5** (3 tareas, 2h c/u = 6h)

#### **ALTA PRIORIDAD (Día 3-7)**

4. **TASK-IND-2** subdividida (4h)
5. **TASK-IND-4** subdividida (6h)
6. **TASK-SC-2** subdividida (5h)
7. **TASK-SC-4** subdividida (8h) ⚠️ CRÍTICA

#### **MEDIA PRIORIDAD (Día 8-14)**

8. **FASE 4** (RM y PA) - 12 tareas con subdivisiones (60h estimadas)
9. **FASE 5** (Backtesting) - 6 tareas con subdivisiones (30h estimadas)

#### **BAJA PRIORIDAD (Paralelo, 2 semanas)**

10. **FASE 6-12** - Resto de tareas (100h estimadas)

---

### 📊 **ACTUALIZACIÓN DE RESUMEN**

**TOTAL DE TAREAS: 83** (40 previas + 43 nuevas críticas MVP)

**TAREAS DESPUÉS DE SUBDIVISIÓN: 155** (83 originales + 85 subtareas adicionales identificadas - 13 tareas ya completadas)

- **Tareas Completadas**: 13 (TASK-1 a TASK-7, TASK-8, TASK-9, TASK-10, TASK-11, TASK-12, TASK-13, TASK-14, TASK-15, TASK-31)
- **Tareas Manejables Directas**: 38 (listo para implementar)
- **Tareas con Subtareas Identificadas**: 32 (requieren subdivisión en 85 subtareas)
- **Tareas Totales Pendientes**: 142 (70 originales + 72 subtareas pendientes)
- **Estado General**: MVP READY para AWS/Docker deployment + Sistema de base de datos + CI/CD automatizado + Backtesting Exhaustivo + Control de Riesgos + Sistema de Estrategias Múltiples + Portfolio Multi-Strategy (pendiente)

### 📋 **DESGLOSE DE FASE 5 - Portfolio Multi-Strategy (43 tareas críticas)**

- **Portfolio Allocation & Risk Management**: 10 tareas (TASK-PA-1, PA-2, PORT-SEL-1, RM-1 a RM-5, REB-1, REB-2)
- **Estrategias Complementarias**: 8 tareas (TASK-MR-1, MR-2, PT-1 a PT-4)
- **Backtesting & Validation**: 5 tareas (TASK-BV-1, BV-2, MET-1, MET-2)
- **Costos Realistas**: 2 tareas (TASK-CST-1, CST-2)
- **Indicadores Técnicos Avanzados & Sizing**: 5 tareas (TASK-IND-1 a IND-5)
- **Validación de Datos & Outliers**: 4 tareas (TASK-DV-1 a DV-4)
- **Signal Scoring & Cooldown**: 5 tareas (TASK-SC-1 a SC-5)
- **Simulación Realista de Ejecución**: 4 tareas (TASK-EX-1 a EX-4)
- **Logging Estructurado & Reproducibilidad**: 5 tareas (TASK-LOG-1 a LOG-5)
- **Dashboard & Monitoring**: 4 tareas (TASK-DASH-1 a DASH-4)
- **Automated Tests & CI**: 3 tareas (TASK-TEST-1 a TEST-3)
- **Documentación Automática**: 3 tareas (TASK-DOC-1 a DOC-3)
- **Parameter Optimization & Presets**: 4 tareas (TASK-PARAM-1 a PARAM-3, MOM-OPT-1)
