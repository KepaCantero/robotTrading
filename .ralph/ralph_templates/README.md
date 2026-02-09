# 📁 Ralph Templates - Índice Completo

**Fecha:** 2026-02-08
**Objetivo:** Templates reutilizables para el sistema Ralph con mapeo determinista de reglas

---

## 🗂️ Estructura Organizada

```
ralph_templates/
├── README.md                      (ESTE ARCHIVO)
│
├── hats/                          # Comportamientos de agentes
│   ├── base_processor_hat.yml    # ⭐ BASE - Template principal
│   ├── requirement_checker_hat.yml # Genera requirements.md
│   ├── validation_hat.yml         # Valida archivos
│   ├── implementer_hat.yml        # Implementa código
│   └── final_reviewer_hat.yml     # Revisión final
│
├── data/                          # Input/Output templates
│   ├── agent_input_template.yml   # ⭐ Input para agentes
│   └── task_output_template.yml   # ⭐ Output de tareas
│
├── configs/                       # Configuraciones
│   ├── task_config_template.yml   # Para crear tareas
│   └── pipeline_coordinator_template.yml # Para crear pipelines
│
└── agents/                        # Agentes especializados
    └── requirement_generator_agent.yml # ⭐ Genera requirements.md
```

---

## 🎯 Uso de Templates

### 1. Requirement Generator Agent ⭐

**Archivo:** `agents/requirement_generator_agent.yml`

**Propósito:** Genera automáticamente `requirements.md` cuando no existe

**Características v2:**
- **Mapeo determinista** usando `.ralph/rules/rules_mapping.yml`
- **Detección automática** de servicio/componente
- **Inclusión de 4 tipos de reglas:**
  1. SOLID Principles (5 reglas - siempre aplicables)
  2. Trading Rules (R1-R29 - según servicio)
  3. Spain Tax Rules (IRPF, UE dividends, Modelo 720)
  4. Base Rules (TYP, LOG, ERR, etc. - según servicio)

**Flujo:**
```
Archivo Python → Identificar servicio
                ↓
        Buscar reglas en rules_mapping.yml (DETERMINISTA)
                ↓
        Generar requirements.md con reglas aplicables
                ↓
        Guardar en .requirements/{file}.requirements.md
```

**Trigger:** `file.requires_analysis`, `requirements.missing`, `audit.needs_requirements`

### 2. Hats (Comportamientos)

#### `base_processor_hat.yml` ⭐ BASE
**Uso:** Template base para cualquier tarea de procesamiento

**Contiene:**
- Shared instructions (reutilizable)
- Validation scripts (reutilizable)
- Checkpoint format (estandarizado)
- Event format (estandarizado)
- Golden rules (aplica a todas)

#### `requirement_checker_hat.yml`
**Uso:** Verifica y genera requirements.md

**Integra el requirement_generator_agent.yml**

#### `validation_hat.yml`
**Uso:** Valida archivos usando `validate_file_complete.sh`

**Flujo:**
1. Ejecuta `scripts/utils.py validate`
2. Si falla → auto-fix (black, isort, ruff)
3. Re-valida hasta success: true
4. Marca PASADO solo si success: true

#### `implementer_hat.yml` v2.0
**Uso:** Implementa o refactoriza código

**Características v2.0:**
- **NO FALLBACKS** - Si algo no funciona, usa FLAGS
- Verifica dependencias ANTES de implementar
- Usa flags en código: `@skip-import`, `@todo`, `@clarify`, `@review`

**Flujo:**
1. Lee especificación
2. **Verifica dependencias** (imports existen antes de usar)
3. Implementa según especificación
4. Valida después de cada cambio
5. Solo continúa si success: true

**Flags de código:**
```python
# @skip-import: INotificationService not found
# TODO: Create INotificationService in app/interfaces/notifications.py

# @todo: R1 - Kelly Criterion validation
# TODO: Implement kelly_fraction * 0.02 max validation

# @clarify: Should validate before or after order?
# TODO: Clarify with requirements

# @review: Is this correct drawdown calculation?
# TODO: Verify with R2 requirement
```

#### `final_reviewer_hat.yml`
**Uso:** Verificación final de tarea

**Flujo:**
1. Verifica todos los archivos
2. Ejecuta checks finales
3. Emite promesa de completación

### 3. Data (Input/Output)

#### `agent_input_template.yml`
**Define:** Cómo los agentes reciben datos

```yaml
input_data:
  previous_results:
    files: [...]
    metrics: {...}
  requirements:
    specification_file: "..."
  checkpoint:
    phase: "..."
```

#### `task_output_template.yml`
**Define:** Formato estandarizado de output

```yaml
output_format:
  task_id: "..."
  status:
    state: "completed|failed|blocked"
    success: true/false
  results:
    files: [...]
    metrics: {...}
  next_steps:
    next_task: "..."
```

### 4. Configs

#### `task_config_template.yml`
**Uso:** Para crear nuevas tareas Ralph

**Copiar y personalizar:**
```bash
cp ralph_templates/configs/task_config_template.yml \
   ralph_tasks/02_my_new_task.yml
```

#### `pipeline_coordinator_template.yml`
**Uso:** Para crear pipelines de tareas

**Define:** Cómo pasan datos entre tareas

```yaml
pipeline:
  tasks:
    - task_id: "01_analyze"
      output: "task_1_output.json"
    - task_id: "02_refactor"
      input_from: "01_analyze"
```

---

## 🔗 Sistema de Reglas - Mapeo Determinista

### Sistema de Extracción de Docs

El requirement generator usa **2 archivos de mapeo** para extracción determinista:

1. **`.ralph/rules/docs_extraction_mapping.yml`** - Define QUÉ archivo leer y QUÉ extraer
2. **`.ralph/rules/rules_mapping.yml`** - Define qué reglas aplican a cada servicio

### Archivo de Extracción: `.ralph/rules/docs_extraction_mapping.yml`

**Define fuentes de verdad:**
```yaml
truth_sources:
  solid:
    source_file: ".ralph/docs/requirements/SERVICE_REQUIREMENTS.md"
    section: "## SOLID Principles"

  trading:
    source_file: ".ralph/docs/realistic_trading_rules.md"
    section: "### Reglas Prioritarias (P0)"

  spain_tax:
    source_file: ".ralph/docs/requirements/SERVICE_REQUIREMENTS.md"
    section: "## Spain-Specific Requirements"
```

**Define pasos de extracción:**
```yaml
extraction_rules:
  solid:
    steps:
      - step: 1
        action: "READ_FILE"
        file: ".ralph/docs/requirements/SERVICE_REQUIREMENTS.md"
      - step: 2
        action: "PARSE"
        pattern: "### SRP-001: ..."
```

### Archivo de Mapeo: `.ralph/rules/rules_mapping.yml`

**Estructura:**
```yaml
file_pattern_mapping:
  "app/services/compliance/compliance_engine.py":
    component: "ComplianceEngine"
    service: "compliance"
    priority: "P0"
    rules:
      solid: [SRP-001, OCP-001, LSP-001, ISP-001, DIP-001]
      trading: [R1, R2, R3, R4, R15]
      spain_tax: [IRPF-001, DIV-001, MOD720-001]

service_mapping:
  compliance:
    base_rules: [TYP-001, LOG-001, ERR-001, ASYNC-001, SEC-001]
  execution:
    base_rules: [TYP-001, LOG-001, ERR-001, ASYNC-001, TIM-001]
```

### Reglas Disponibles

**SOLID (5 reglas):**
- SRP-001: Single Responsibility
- OCP-001: Open/Closed
- LSP-001: Liskov Substitution (usar Protocol)
- ISP-001: Interface Segregation (< 5 métodos)
- DIP-001: Dependency Inversion (Protocol-based DI)

**Trading (R1-R29):**
- R1: Kelly + 2% max
- R2: Drawdown 15% stop
- R3: Stop Loss SIEMPRE
- R4: R:R 2:1 mínimo
- R15: Logging append-only + correlation ID
- R28: Registro para Hacienda
- ... (y más)

**Spain Tax:**
- IRPF-001: Progresivo 19/21/23%
- DIV-001: UE 0% vs No-UE 19%
- MOD720-001: Modelo 720 > €50k extranjeros

**Base Rules:**
- TYP-001: Type hints requeridos
- LOG-001: Structured logging
- ERR-001: Error handling completo
- ASYNC-001: No blocking en async
- SEC-001: Audit logging obligatorio

---

## 📋 Formato de requirements.md Generado

```markdown
# Requirements: app/services/compliance/compliance_engine.py

## Source File Analysis
- **File Path**: `app/services/compliance/compliance_engine.py`
- **Component**: ComplianceEngine
- **Service**: compliance
- **Priority**: P0
- **Lines of Code**: 250
- **Status**: Analysis Complete

## Purpose
Coordinador del flujo completo de trading con compliance

## Dependencies
### Internal
- `from app.models import Portfolio`
### External
- `import pandas as pd`

## Classes/Functions
### class ComplianceEngine
**Purpose:** Coordinador del flujo de trading
**Methods:**
- `async def execute_trade(...)`: Ejecuta trade con compliance

## Business Logic
Coordina todo el ciclo de trading con validaciones SOLID y reglas R1-R29

## Project Rules (DETERMINISTA)

### SOLID Principles (5 rules)
- SRP-001: Single Responsibility Principle → [❌] Tiene 9 responsabilidades
- OCP-001: Open/Closed Principle → [❌] Hardcoded systems
- LSP-001: Liskov Substitution Principle → [⚠️] Usa ABC
- ISP-001: Interface Segregation Principle → [❌] Fat interface 14 métodos
- DIP-001: Dependency Inversion Principle → [❌] Crea dependencias directamente

### Trading Rules (5 rules)
- R1: Kelly Criterion + 2% Max → [❌] NO validado en execute_trade()
  - Category: risk_management
  - Priority: P0
  - Implementation: `kelly_fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win`
- R2: Drawdown 15% Stop → [⚠️] Parcial
- R4: R:R 2:1 Mínimo → [❌] NO validado
- R15: Logging Append-Only + Correlation ID → [❌] NO implementado
- R28: Registro para Hacienda → [❌] NO implementado

### Spain Tax Rules (3 rules)
- IRPF-001: IRPF Progresivo 19/21/23% → [❌] NO integrado
- DIV-001: Dividendos UE 0% vs No-UE 19% → [❌] NO discriminado
- MOD720-001: Modelo 720 > €50k Extranjeros → [❌] NO implementado

### Base Rules (5 rules)
- TYP-001: Type Hints → [⚠️] Parcial
- LOG-001: Structured Logging → [⚠️] Parcial
- ERR-001: Error Handling → [✅] Implementado
- ASYNC-001: No Blocking in Async → [⚠️] Parcial
- SEC-001: Audit Logging → [❌] NO implementado

## Audit Status
| **Last Audit Date** | 2026-02-08 |
| **Component** | ComplianceEngine |
| **Service** | compliance |
| **Priority** | P0 |
| **Audit Status** | NEEDS_AUDIT |

## Implementation Gap
### SRP-001: Single Responsibility Principle
**Status:** MISSING
**Evidence:** Clase tiene 9 responsabilidades
**Gap:** Separar en 7 clases con 1 responsabilidad cada una

### R1: Kelly Criterion + 2% Max
**Status:** MISSING
**Evidence:** No se valida en execute_trade()
**Gap:** Añadir validación de kelly_fraction * 0.02 antes de ordenar
```

---

## 🚀 Crear Nuevo Hat

### 1. Copiar Base
```bash
cp ralph_templates/hats/base_processor_hat.yml \
   ralph_templates/hats/my_custom_hat.yml
```

### 2. Personalizar
```yaml
hat_template: my_custom_hat
name: "My Custom Hat"
description: "Descripción de lo que hace"

triggers:
  - "my_task.start"
  - "my_task.next"

publishes:
  - "my_task.next"
  - "my_task.complete"

instructions: |
  ## MI CUSTOM HAT

  Importar shared_instructions del base_processor:
  {{shared_instructions}}

  Instrucciones específicas aquí...
```

### 3. Usar en Tarea
```yaml
# En ralph_tasks/01_my_task.yml
hats:
  my_custom_processor:
    name: "My Custom Processor"
    template: "ralph_templates/hats/my_custom_hat.yml"
```

---

## 🔄 Flujo Completo de Ralph con Requirements.md

```
┌─────────────────┐
│  Procesar File  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ¿Existe         │──NO──→ requirement_checker_hat
│ requirements.md │       └──> requirement_generator_agent v3.0
└────────┬────────┘             │
         │ SÍ                    ▼
         │              ┌─────────────────────┐
         │              │ 1. docs_extraction_mapping │
         ▼              │    QUÉ hacer, QUÉ extraer │
┌─────────────────┐   └──────────┬──────────┘
│  Leer y Usar    │              │
│  requirements   │              ▼
└────────┬────────┘   ┌─────────────────────┐
         │            │ 2. rules_mapping.yml │
         │            │    Qué reglas aplican │
         ▼            └──────────┬──────────┘
┌─────────────────┐             │
│  Procesar File  │             ▼
│  con Reglas     │   ┌─────────────────────┐
└─────────────────┘   │ 3. docs/             │
         ▲            │    - SERVICE_REQUIREMENTS.md
         │            │    - realistic_trading_rules.md
         │            │    - implementation_analysis_*.md
         │            └──────────┬──────────┘
         │                       │
         └───────────────────────┘
        Extracción DETERMINISTA
        - NO juicio
        - SOLO patrones
        - SIEMPRE mismos datos
```

---

## ✅ Checklist

Antes de crear nuevo template:

- [ ] Revisar si `base_processor_hat.yml` ya tiene lo necesario
- [ ] Usar `{{shared_instructions}}` para evitar duplicados
- [ ] Seguir formato de checkpoint estandarizado
- [ ] Seguir formato de eventos estandarizado
- [ ] Incluir golden rules

---

**Última actualización:** 2026-02-08
**Estado:** ✅ Sistema Ralph v3.0 - Extracción DETERMINISTA + NO FALLBACKS implementer
