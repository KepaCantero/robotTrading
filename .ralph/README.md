# 📋 AlgoTrading - Ralph System

**Fecha:** 2026-02-08
**Objetivo:** Sistema de automatización de tareas para refactores

---

## 🎯 ¿Qué es Ralph?

Ralph es un **wrapper** para automatizar pipelines de agentes con:

1. **Tareas definidas en templates** - Configuración YAML reutilizable
2. **Procesamiento de resultados** - Output estandarizado
3. **Paso de datos entre agentes** - Pipeline coordinado

### Flujo de Ralph

```
┌─────────────┐
│   Config    │  ralph_base.yml + task config
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Agent 1   │  Procesa tarea + requirements.md
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Output    │  Resultado estandarizado (JSON)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Agent 2   │  Recibe output como input
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Complete   │  Promesa de completación
└─────────────┘
```

---

## 📂 Estructura de Directorios

```
.ralph/
├── README.md                           # ESTE ARCHIVO
│
├── docs/                               # Documentación del proyecto
│   ├── scripts_README.md
│   ├── RALPH_USER_GUIDE.md
│   ├── RALPH_SYSTEM_DIAGRAM.md
│   ├── analysis/                       # Análisis de 53 problemas
│   │   ├── COMPLETE_ANALYSIS_ALL_PROBLEMS_SINGLE_USER.md ⭐
│   │   ├── VIABILITY_ANALYSIS_CRITICAL_PROBLEMS.md
│   │   └── EXECUTIVE_SUMMARY_ALL_PROBLEMS.md
│   ├── architecture/                   # Arquitectura + SOLID
│   │   ├── compliance_engine_architecture_analysis.md
│   │   └── compliance_engine_solid_audit.md
│   ├── refactoring/                    # Análisis de archivos críticos
│   │   └── analysis_critical_files_complete.md
│   └── requirements/                   # ⭐ SERVICE_REQUIREMENTS.md
│       └── SERVICE_REQUIREMENTS.md
│
├── rules/                              # ⭐ MAPEO DETERMINISTA
│   ├── docs_extraction_mapping.yml     # QUÉ archivo leer, QUÉ extraer
│   └── rules_mapping.yml               # Qué reglas aplican a cada servicio
│
├── ralph_base.yml                      # ⭐ Configuración base reutilizable
│
├── ralph_templates/                    # ⭐ Templates organizados
│   ├── README.md                       # Índice de templates
│   ├── hats/                           # Comportamientos de agentes
│   │   ├── base_processor_hat.yml      # ⭐ BASE - Template principal
│   │   ├── requirement_checker_hat.yml # Genera requirements.md
│   │   ├── validation_hat.yml          # Valida archivos
│   │   ├── implementer_hat.yml         # Implementa código
│   │   └── final_reviewer_hat.yml      # Revisión final
│   ├── data/                           # Input/Output
│   │   ├── agent_input_template.yml    # Input para agentes
│   │   └── task_output_template.yml    # Output de tareas
│   ├── configs/                        # Configuraciones
│   │   ├── task_config_template.yml    # Para crear tareas
│   │   └── pipeline_coordinator_template.yml
│   └── agents/                         # Agentes especializados
│       └── requirement_generator_agent.yml v3.0 ⭐ Extracción determinista
│
├── ralph_tasks/                        # Configuraciones de tareas
│   ├── 01_compliance_engine_refactor.yml ⭐ Tarea P0
│   └── prompts/                        # Prompts de tareas
│
├── outputs/                            # Outputs de tareas (generado)
├── checkpoints/                        # Checkpoints (generado)
└── logs/                               # Logs (generado)
```

---

## 🎯 Resumen Ejecutivo

### Estado Actual: 🔴 NO PRODUCCIÓN-READY

| Categoría | Críticos | Total |
|-----------|----------|-------|
| Arquitectura | 5 | 12 |
| Backtests/Strategies | 6 | 8 |
| Configuración/Seguridad | 3 | 7 |
| Live Trading | 4 | 8 |
| Datos/Feeds | 3 | 5 |
| Monitoreo/Alertas | 2 | 5 |
| Usuario Único | 3 | 5 |
| Específicos España | 2 | 3 |
| **TOTAL** | **28** | **53** |

---

## 📊 Viabilidad Económica

| Capital | ¿1000€/mes viable? | Probabilidad |
|---------|-------------------|-------------|
| €1,000 | ❌ NO | < 20% |
| €5,000 | ⚠️ Tal vez | ~40% |
| €10,000 | ⚠️ Probable | ~50% |
| **€20,000** | ✅ SÍ | **~60%** |

**Meta REALISTA:** €500-800/mes (no €1000)

---

## 🚀 Templates Ralph

### Hats (Comportamientos)

| Template | Uso |
|----------|-----|
| `base_processor_hat.yml` | ⭐ BASE - Template principal |
| `requirement_checker_hat.yml` | Genera requirements.md |
| `validation_hat.yml` | Valida archivos |
| `implementer_hat.yml` v2.0 | ⭐ Implementa código - NO FALLBACKS |
| `final_reviewer_hat.yml` | Revisión final |

### Data (Input/Output)

| Template | Uso |
|----------|-----|
| `agent_input_template.yml` | Input para agentes |
| `task_output_template.yml` | Output de tareas |

### Configs

| Template | Uso |
|----------|-----|
| `task_config_template.yml` | Para crear tareas |
| `pipeline_coordinator_template.yml` | Para crear pipelines |

### Rules (Mapeo Determinista)

| Archivo | Uso |
|---------|-----|
| `docs_extraction_mapping.yml` | ⭐ QUÉ archivo leer, QUÉ extraer de docs/ |
| `rules_mapping.yml` | Qué reglas aplican a cada servicio |

### Agents

| Template | Uso |
|----------|-----|
| `requirement_generator_agent.yml` v3.0 | ⭐ Generador con extracción DETERMINISTA de docs/ |

**Ver documentación completa:** [`ralph_templates/README.md`](./ralph_templates/README.md)

---

## 🔄 Flujo con Requirements.md

### Sistema de Extracción DETERMINISTA v3.0

```
┌─────────────────────────────────────────────────────────┐
│  Requirement Generator Agent v3.0                       │
│  Extracción DETERMINISTA de docs/ - NO juicio          │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │  PASO 0: Leer mapeos       │
        ▼                            │
┌─────────────────────┐               │
│ docs_extraction_map │               │
│ QUÉ hacer, QUÉ      │               │
│ extraer de cada doc │               │
└─────────────────────┘               │
                      │               │
        ┌─────────────┴───────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  PASO 1-11: Extracción paso a paso                     │
├─────────────────────────────────────────────────────────┤
│  1. Identificar archivo (rules_mapping.yml)            │
│  2. Extraer SOLID (SERVICE_REQUIREMENTS.md)             │
│  3. Extraer Trading (realistic_trading_rules.md)       │
│  4. Extraer Spain Tax (SERVICE_REQUIREMENTS.md)         │
│  5. Extraer Implementation Gaps (implementation_*.md)   │
│  6. Extraer Base Rules (docs_extraction_mapping.yml)    │
│  7. Leer archivo Python                                 │
│  8. Verificar cumplimiento                              │
│  9. Generar requirements.md                             │
│  10. Guardar en .requirements/                          │
│  11. Validar salida                                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Output: requirements.md con 4 categorías de reglas     │
│  - SOLID (5 rules)                                      │
│  - Trading (R1-R29, según servicio)                     │
│  - Spain Tax (3 rules)                                  │
│  - Base Rules (según servicio)                          │
└─────────────────────────────────────────────────────────┘
```

### Fuentes de Verdad (DETERMINISTA)

| Categoría | Archivo | Sección |
|-----------|---------|---------|
| **SOLID** | `docs/requirements/SERVICE_REQUIREMENTS.md` | `## SOLID Principles` |
| **Trading** | `docs/realistic_trading_rules.md` | `### Reglas Prioritarias (P0)` |
| **Spain Tax** | `docs/requirements/SERVICE_REQUIREMENTS.md` | `## Spain-Specific Requirements` |
| **Implementation Gaps** | `docs/implementation_analysis_R1-R29.md` | Tabla de estado |

### Cuando NO existe requirements.md:

```
┌─────────────────┐
│  Procesar File  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ¿Existe         │──NO──→ requirement_generator_agent v3.0
│ requirements.md │       │
└────────┬────────┘       │
         │ SÍ             ▼
         │    ┌──────────────────────────┐
         │    │ 1. docs_extraction_mapping │
         │    │    QUÉ hacer, QUÉ extraer │
         │    └──────────┬───────────────┘
         ▼               │
┌─────────────────┐     ▼
│  Leer y Usar    │  ┌───────────────────────┐
│  requirements   │  │ 2. rules_mapping.yml   │
└────────┬────────┘  │    Qué reglas aplican  │
         │          └──────────┬────────────┘
         ▼                     │
┌─────────────────┐             ▼
│  Procesar File  │  ┌──────────────────────┐
└─────────────────┘  │ 3. docs/               │
         ▲           │    - SERVICE_REQUIREMENTS
         │           │    - realistic_trading_rules
         │           │    - implementation_analysis
         │           └──────────┬────────────┘
         │                      │
         └──────────────────────┘
        Extracción DETERMINISTA
```

### requirements.md se genera automáticamente (v3.0):

```markdown
# Requirements: app/services/compliance_engine.py

## Source File Analysis
- **Lines of Code**: 250
- **Status**: Analysis Complete

## Purpose
<Descripción basada en código real>

## Dependencies
### Internal
- `from app.models import Portfolio`
### External
- `import pandas as pd`

## Classes/Functions
### class ComplianceEngine
**Purpose**: Coordinador del flujo de trading
**Methods**:
- `async def execute_trade(...)`: Ejecuta trade con compliance

## Business Logic
<Descripción de lógica>

## Project Rules (DETERMINISTA - de docs/)
### SOLID Principles (5 rules)
- SRP-001: Single Responsibility → [❌] Tiene 9 responsabilidades
- OCP-001: Open/Closed → [❌] Hardcoded systems
- LSP-001: Liskov Substitution → [⚠️] Usa ABC
- ISP-001: Interface Segregation → [❌] Fat interface 14 métodos
- DIP-001: Dependency Inversion → [❌] Crea dependencias directamente

### Trading Rules (5 rules)
- R1: Kelly Criterion + 2% Max → [❌] NO validado
  - Category: risk_management
  - Priority: P0
  - Implementation: `kelly_fraction = ...`
- R2: Drawdown 15% Stop → [⚠️] Parcial
- R3: Stop Loss SIEMPRE → [❌] NO implementado
- R4: R:R 2:1 Mínimo → [❌] NO validado
- R15: Logging Append-Only → [❌] NO implementado

### Spain Tax Rules (3 rules)
- IRPF-001: IRPF Progresivo 19/21/23% → [❌] NO integrado
- DIV-001: Dividendos UE 0% vs No-UE 19% → [❌] NO discriminado
- MOD720-001: Modelo 720 > €50k → [❌] NO implementado

### Base Rules (5 rules)
- TYP-001: Type Hints → [⚠️] Parcial
- LOG-001: Structured Logging → [⚠️] Parcial
- ERR-001: Error Handling → [✅] Implementado
- ASYNC-001: No Blocking in Async → [⚠️] Parcial
- SEC-001: Audit Logging → [❌] NO implementado

## Audit Status
| **Last Audit Date** | 2026-02-08 |
| **Audit Status** | NEEDS_AUDIT |
```

---

## 🚀 Tareas Ralph

### Orquestador Principal

**Tarea 00:** [`00_master_orchestrator.yml`](./ralph_tasks/00_master_orchestrator.yml) - Ejecuta TODAS las tareas en orden

```bash
# Ejecutar TODO el sistema
ralph run .ralph/ralph_tasks/00_master_orchestrator.yml
```

### Plan de Implementación Optimizado

**Ver documentación completa:**
- [`ralph_tasks/README.md`](./ralph_tasks/README.md) - Plan completo
- [`ralph_tasks/TASKS_INVENTORY.md`](./ralph_tasks/TASKS_INVENTORY.md) - Inventario exhaustivo

**Resumen:** 18 tareas optimizadas (~168 horas = 4-5 semanas)

#### Tareas YAML Creadas: 6/18 (33%)

| Tarea | Estado | Horas | Descripción |
|-------|--------|-------|-------------|
| 00_master_orchestrator | ✅ CREADO | - | Orquestador principal |
| 01_protocol_interfaces | ✅ CREADO | 4h | Interfaces Protocol |
| 02_spain_tax_engine | ✅ CREADO | 8h | IRPF 19/21/23% |
| 03_trading_decision_logger | ✅ CREADO | 6h | R15, R28 - Logging |
| 04_risk_validators | ✅ CREADO | 8h | R1, R2, R4 - Risk |
| 01_compliance_engine_refactor | ✅ ACTUALIZADO | 16h | Coordinator |

#### Tareas Pendientes: 12/18 (67%)

| Tarea | Estado | Horas | Descripción |
|-------|--------|-------|-------------|
| 05_position_management | ❌ Pendiente | 12h | R11, R12, R13 |
| 06_reconciliation_daily | ❌ Pendiente | 6h | R16 |
| 07_capital_phase_manager | ❌ Pendiente | 6h | R25-R27 |
| 08_broker_adapters | ❌ Pendiente | 16h | IBKR Spain |
| 09-12 | ❌ Pendiente | 12h | Integration |
| 13 | ❌ Pendiente | 8h | CLI |
| 14-16 | ❌ Pendiente | 24h | UI |
| 17 | ❌ Pendiente | 12h | Backtest fixes |
| 18 | ❌ Pendiente | 24h | Additional rules |
| 19 | ❌ Pendiente | 8h | Security |
| 20 | ❌ Pendiente | 16h | Testing |

### Ejecutar Fase 1 (Foundation)

```bash
# Ejecutar tareas 01-04 (dependencias base)
ralph run .ralph/ralph_tasks/01_protocol_interfaces.yml
ralph run .ralph/ralph_tasks/02_spain_tax_engine.yml
ralph run .ralph/ralph_tasks/03_trading_decision_logger.yml
ralph run .ralph/ralph_tasks/04_risk_validators.yml
```

---

## 🛠️ Scripts Organizados

```bash
# CLI UNIFICADO
python scripts/utils.py validate <archivo>
python scripts/utils.py list_files --category critical
python scripts/utils.py audit_files --category p1
```

**Ver documentación:** [`docs/scripts_README.md`](./docs/scripts_README.md)

---

## 🔗 Quick Links

- **Templates Docs:** [`ralph_templates/README.md`](./ralph_templates/README.md)
- **Docs Extraction Mapping:** [`.ralph/rules/docs_extraction_mapping.yml`](./rules/docs_extraction_mapping.yml)
- **Rules Mapping:** [`.ralph/rules/rules_mapping.yml`](./rules/rules_mapping.yml)
- **Análisis Completo:** [`docs/analysis/COMPLETE_ANALYSIS_ALL_PROBLEMS_SINGLE_USER.md`](./docs/analysis/COMPLETE_ANALYSIS_ALL_PROBLEMS_SINGLE_USER.md)
- **Requirements Refactor:** [`docs/requirements/SERVICE_REQUIREMENTS.md`](./docs/requirements/SERVICE_REQUIREMENTS.md)
- **Arquitectura:** [`docs/architecture/compliance_engine_architecture_analysis.md`](./docs/architecture/compliance_engine_architecture_analysis.md)

---

## ✅ Checklist de Validación

**SOLID:**
- [ ] Cada clase tiene 1 responsabilidad
- [ ] No modifica clases existentes (OCP)
- [ ] Usa Protocol (no clases concretas)
- [ ] Interfaces segregadas (< 5 métodos)
- [ ] Todas las dependencias inyectadas

**R1-R29:**
- [ ] R1: Kelly + 2% validado
- [ ] R2: Drawdown 15% validado
- [ ] R4: R:R 2:1 validado
- [ ] R15: Logging append-only implementado

**Validación:**
- [ ] `python scripts/utils.py validate <archivo>` returns success: true

**NO FALLBACKS (Implementer v2.0):**
- [ ] NO usar try/except ImportError para fallbacks
- [ ] Verificar imports ANTES de usarlos
- [ ] Usar `@skip-import` si import no existe
- [ ] Usar `@todo` si funcionalidad no implementada
- [ ] Usar `@clarify` si hay ambigüedad en requirements
- [ ] Usar `@review` si hay duda en implementación

---

## ⏱️ Tiempo Estimado: **4-8 meses**

---

**Última actualización:** 2026-02-08
**Estado:** ✅ Sistema Ralph v3.0 - Extracción DETERMINISTA + NO FALLBACKS (implementer v2.0)
