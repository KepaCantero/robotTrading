# 📋 AlgoTrading - Ralph System v2.0

**Fecha:** 2026-03-08
**Objetivo:** Sistema de automatización de tareas para nivel AAA

---

## 🎯 ¿Qué es Ralph?

Ralph es un **orchestrator** para automatizar pipelines de agentes con:

1. **Presets de workflows** - Configuraciones pre-definidas
2. **Hats especializados** - Personas con roles específicos
3. **Memories persistentes** - Aprendizaje entre sesiones
4. **Tasks tracking** - Seguimiento de runtime
5. **Backpressure validation** - Gates de calidad automáticos

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
├── ralph-v2.yml                        # ⭐ Configuración v2.0
│
├── docs/                               # Documentación del proyecto
│   ├── analysis/                       # Análisis de problemas
│   ├── architecture/                   # Arquitectura + SOLID
│   └── refactoring/                    # Análisis de archivos críticos
│
├── .agent/                             # ⭐ Estado persistente
│   ├── memories.md                    # Aprendizaje entre sesiones
│   └── tasks.jsonl                     # Tracking de runtime
│
├── hooks/                              # ⭐ Hooks de validación
│   ├── pre_tool_use.py                 # Pre-validación de herramientas
│   ├── post_tool_use.py                # Post-validación
│   └── stop.py                         # Cleanup al finalizar
│
├── presets/                             # ⭐ WORKFLOWS PRE-DEFINIDOS
│   ├── aaa-production.yml              # Producción AAA completo
│   ├── tdd-red-green.yml               # TDD Red-Green-Refactor
│   ├── debug.yml                        # Debug workflow
│   ├── spec-driven.yml                  # Spec-driven development
│   └── refactor.yml                     # Refactor workflow
│
├── rules/                              # REGLAS DE TRADING
│   ├── python/                         # Reglas de Python
│   └── trading/                        # 64 archivos de libros/papers
│
├── ralph_templates/                    # TEMPLATES
│   ├── hats/                           # Comportamientos de agentes
│   ├── data/                           # Input/Output
│   ├── configs/                        # Configuraciones
│   └── agents/                         # Agentes especializados
│
├── ralph_tasks/                        # CONFIGURACIONES DE TAREAS
│   ├── 00_master_orchestrator.yml       # ⭐ Master Orchestrator AAA
│   └── prompts/                        # Prompts de tareas
│
├── scripts/                            # SCRIPTS DE UTILIDAD
│   ├── utils.py                        # CLI unificado
│   ├── verify_compliance_validations.py
│   └── ...
│
├── outputs/                            # Outputs (generado)
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

### Agents

| Template | Uso |
|----------|-----|
| `requirement_generator_agent.yml` v3.0 | ⭐ Generador con extracción DETERMINISTA de docs/ |

**Ver documentación completa:** [`ralph_templates/README.md`](./ralph_templates/README.md)

---

## 🔄 Flujo con Requirements.md

### Flujo de Análisis Dinámico

```
┌─────────────────────────────────────────────────────────┐
│  Tarea Ralph - Análisis por archivo                     │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │  ANALIZAR 4 FUENTES:       │
        ▼                            │
┌─────────────────────┐               │
│ 1. Archivo fuente   │  app/.../file.py
└─────────────────────┘               │
                      │               │
        ┌─────────────┴───────────────┘
        │
        ▼
┌─────────────────────┐
│ 2. Requirements     │  .requirements/app/.../file.requirements.txt
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ 3. Rules            │  rules/trading/ (64 archivos de libros/papers)
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ 4. Docs             │  .ralph/docs/ (análisis, arquitectura, etc.)
└─────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Output: Código actualizado / requirements / validación │
└─────────────────────────────────────────────────────────┘
```

### Fuentes de Verdad

| Fuente | Ubicación | Contenido |
|--------|-----------|-----------|
| **Código** | `app/` | Archivos fuente Python |
| **Requirements** | `.requirements/` | Requirements por archivo |
| **Rules** | `rules/trading/` | 64 archivos de libros/papers |
| **Docs** | `.ralph/docs/` | Análisis, arquitectura, guías |

### Flujo de Análisis por Archivo:

Para cada tarea de Ralph, el agente:

1. **Analiza el archivo** → Lee el código fuente del servicio
2. **Analiza requirements** → Busca en `.requirements/app/.../archivo.requirements.txt`
3. **Analiza rules** → Busca en `rules/trading/` las reglas relevantes
4. **Analiza docs** → Busca en `.ralph/docs/` documentación adicional

### Ejemplo de requirements.md generado:

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
- **Rules (Trading):** [`rules/trading/`](./rules/trading/)
- **Análisis Completo:** [`docs/analysis/COMPLETE_ANALYSIS_ALL_PROBLEMS_SINGLE_USER.md`](./docs/analysis/COMPLETE_ANALYSIS_ALL_PROBLEMS_SINGLE_USER.md)
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

**Última actualización:** 2026-03-08
**Estado:** ✅ Sistema Ralph v2.1 - Optimizado para GLM 5.0 + Sub-agents integrados

---

## 🤖 Sub-Agents Integrados

Los siguientes agentes de `awesome-claude-agents` están disponibles para delegación:

| Agente | Uso en AlgoTrading |
|--------|-------------------|
| `code-archaeologist` | ⭐ Análisis profundo de codebase, genera reports |
| `python-expert` | ⭐ Desarrollo Python 3.12+, async, FastAPI |
| `ml-data-expert` | ⭐ ML/Data Science, trading algorithms |
| `code-reviewer` | Reviews rigurosos con severity tagging |
| `performance-optimizer` | Optimización de rendimiento |
| `security-guardian` | Seguridad y hardening |

### Cómo usar los sub-agents

Los hats de Ralph pueden delegar tareas específicas a estos agentes:

```yaml
# En ralph_tasks/XX_task.yml
hats:
  implementer:
    delegate_to: "@agent-python-expert"  # Para código Python complejo

  trading_logic:
    delegate_to: "@agent-ml-data-expert"  # Para algoritmos de trading

  code_review:
    delegate_to: "@agent-code-reviewer"  # Para reviews
```

---

## 🧠 GLM 5.0 Optimizaciones

Ralph v2.1 está optimizado para GLM 5.0:

| Configuración | Valor | Razón |
|---------------|-------|-------|
| `max_iterations` | 300 | GLM más eficiente |
| `memories.budget` | 16000 | Contexto 128K tokens |
| `reasoning.type` | multi-step | GLM maneja bien multi-step |

### Prompts para GLM 5.0

Los prompts deben ser más directos (GLM prefiere instrucciones claras):
- Usar bullet points en lugar de párrafos largos
- Especificar formato de salida esperado
- Incluir ejemplos concretos
