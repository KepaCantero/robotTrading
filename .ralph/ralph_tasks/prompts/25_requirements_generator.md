# Requirements Generator - Prompt

**Tarea ID:** 25_requirements_generator
**Propósito:** Generar archivos requirements.md para todos los archivos Python del proyecto
**Tiempo estimado:** 8 horas
**Depends on:** Nada (tarea autónoma)

---

## OBJETIVO

Crear archivos `requirements.md` para cada archivo Python del proyecto siguiendo:
- **Rules Mapping:** `rules/trading/`
- **Docs Extraction:** `rules/trading/`
- **Service Requirements:** `rules/trading/`

---

## FLUJO DE EJECUCION

```
┌─────────────────┐
│  FILE SCANNER   │  Descubre archivos Python
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RULES MAPPER   │  Identifica reglas aplicables
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  REQ WRITER     │  Genera requirements.md
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VALIDATOR      │  Verifica completitud
└─────────────────┘
```

---

## HAT 1: FILE SCANNER

### Objetivo
Descubrir todos los archivos Python que necesitan requirements.md

### Pasos

#### 1.1 Listar archivos Python
```bash
find app -name "*.py" -type f | sort
```

#### 1.2 Identificar archivos sin requirements
```bash
for file in $(find app -name "*.py" -type f); do
  req_file=".requirements/${file}.requirements.md"
  if [[ ! -f "$req_file" ]]; then
    echo "$file needs requirements"
  fi
done
```

#### 1.3 Agrupar por servicio
Basado en `rules/trading/`:
- **compliance:** `app/services/compliance/*.py`
- **execution:** `app/services/live_trading/*.py`
- **backtesting:** `app/backtesting/*.py`
- **strategy:** `app/strategies/*.py`
- **data:** `app/data_feeds/*.py`, `app/engines/data_engine/*.py`
- **position_management:** `app/services/position_management/*.py`
- **reconciliation:** `app/services/reconciliation/*.py`

### Output
Lista JSON de archivos agrupados por servicio.

---

## HAT 2: RULES MAPPER

### Objetivo
Para cada archivo, determinar qué reglas aplican usando `rules/trading/`

### Pasos

#### 2.1 Leer rules/trading/
```yaml
# Estructura a usar:
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
```

#### 2.2 Algoritmo de mapeo

```python
def get_rules_for_file(file_path: str) -> dict:
    # 1. Buscar coincidencia exacta en file_pattern_mapping
    if file_path in file_pattern_mapping:
        return file_pattern_mapping[file_path]

    # 2. Buscar patrón con wildcard
    for pattern, config in file_pattern_mapping.items():
        if fnmatch.fnmatch(file_path, pattern):
            return config

    # 3. Fallback: usar service_mapping
    service = detect_service_from_path(file_path)
    return {
        "service": service,
        "priority": "P2",
        "rules": {
            "base": service_mapping[service]["base_rules"]
        }
    }
```

#### 2.3 Reglas por defecto

Todos los archivos tienen SOLID + Base Rules:
- **SOLID:** SRP-001, OCP-001, LSP-001, ISP-001, DIP-001
- **Base:** TYP-001, LOG-001, ERR-001, ASYNC-001, SEC-001

Reglas adicionales según servicio:
- **compliance:** Trading R1-R4, R15, R28 + Spain Tax
- **execution:** Trading R1-R4, R10 + EX-001, ID-001
- **backtesting:** Trading R5, R6, R7 + DATA-001
- **strategy:** Trading R19, R20, R21 + SIG-001, CONF-001
- **position_management:** Trading R11, R12, R13 + RISK-001
- **reconciliation:** Trading R16, R28 + AUD-001, SEC-002

---

## HAT 3: REQUIREMENTS WRITER

### Objetivo
Generar archivo requirements.md para cada archivo

### Template de requirements.md

```markdown
# Requirements: {{FILE_PATH}}

## Source File Analysis
- **File Path**: `{{FILE_PATH}}`
- **Component**: {{COMPONENT}}
- **Service**: {{SERVICE}}
- **Priority**: {{PRIORITY}}
- **Lines of Code**: {{LOC}}
- **Status**: Analysis Complete

## Purpose
{{DESCRIPTION_FROM_DOCSTRING}}

## Dependencies

### Internal
{{INTERNAL_IMPORTS}}

### External
{{EXTERNAL_IMPORTS}}

## Classes/Functions

### class {{CLASS_NAME}}
**Purpose:** {{CLASS_DESCRIPTION}}
**Methods:**
{{METHODS_LIST}}

## Business Logic
{{BUSINESS_LOGIC_DESCRIPTION}}

## Project Rules (DETERMINISTA)

### SOLID Principles
- SRP-001: Single Responsibility Principle → [{{STATUS}}] {{EVIDENCE}}
- OCP-001: Open/Closed Principle → [{{STATUS}}] {{EVIDENCE}}
- LSP-001: Liskov Substitution Principle → [{{STATUS}}] {{EVIDENCE}}
- ISP-001: Interface Segregation Principle → [{{STATUS}}] {{EVIDENCE}}
- DIP-001: Dependency Inversion Principle → [{{STATUS}}] {{EVIDENCE}}

### Trading Rules
{{TRADING_RULES_SECTION}}

### Spain Tax Rules
{{SPAIN_TAX_SECTION}}

### Base Rules
- TYP-001: Type Hints → [{{STATUS}}] {{EVIDENCE}}
- LOG-001: Structured Logging → [{{STATUS}}] {{EVIDENCE}}
- ERR-001: Error Handling → [{{STATUS}}] {{EVIDENCE}}
- ASYNC-001: No Blocking in Async → [{{STATUS}}] {{EVIDENCE}}
- SEC-001: Audit Logging → [{{STATUS}}] {{EVIDENCE}}

## Audit Status
| **Last Audit Date** | {{DATE}} |
| **Component** | {{COMPONENT}} |
| **Service** | {{SERVICE}} |
| **Priority** | {{PRIORITY}} |
| **Audit Status** | NEEDS_AUDIT |

## Implementation Gaps
{{GAPS_LIST}}
```

### Criterios de Status

| Status | Criterio |
|--------|----------|
| **[✅]** | Implementado correctamente |
| **[⚠️]** | Parcialmente implementado |
| **[❌]** | No implementado |
| **[❓]** | No aplica |

### Verificaciones por Regla

#### SOLID
```python
# SRP-001: Contar métodos y responsabilidades
methods = count_methods(class)
responsibilities = count_responsibilities(class)
status = "✅" if responsibilities == 1 else "❌"

# OCP-001: Verificar if/switch para tipos
has_type_checks = check_type_discrimination(file)
status = "✅" if not has_type_checks else "❌"

# LSP-001: Verificar uso de Protocol vs ABC
uses_protocol = "typing.Protocol" in file
uses_abc = "abc.ABC" in file
status = "✅" if uses_protocol else ("⚠️" if uses_abc else "❌")

# ISP-001: Contar métodos por interfaz
interface_methods = count_interface_methods(protocol)
status = "✅" if interface_methods <= 5 else "❌"

# DIP-001: Verificar dependencias inyectadas
has_hardcoded_deps = check_hardcoded_dependencies(class)
status = "✅" if not has_hardcoded_deps else "❌"
```

#### Trading Rules
```python
# R1: Kelly + 2% - Buscar validación de posición
has_kelly = "kelly" in file.lower() or "0.02" in file or "2%" in file

# R2: Drawdown 15% - Buscar validación
has_drawdown = "drawdown" in file.lower() and ("0.15" in file or "15%" in file)

# R3: Stop Loss - Buscar validación
has_stop_loss = "stop_loss" in file.lower() and ("none" in file.lower() or "required" in file.lower())

# R4: R:R 2:1 - Buscar ratio
has_rr = "rr_ratio" in file.lower() or ("2.0" in file and "risk" in file.lower())
```

#### Base Rules
```python
# TYP-001: Type hints
type_hint_coverage = calculate_type_hint_coverage(file)
status = "✅" if coverage > 0.9 else ("⚠️" if coverage > 0.5 else "❌")

# LOG-001: Structured logging
uses_logger = "logging" in file or "logger" in file
uses_json = "json" in file or "structlog" in file
status = "✅" if uses_logger and uses_json else ("⚠️" if uses_logger else "❌")

# ERR-001: Error handling
has_try_except = "try:" in file and "except" in file
has_custom_exceptions = "raise" in file and "Error" in file
status = "✅" if has_try_except else "❌"
```

---

## HAT 4: VALIDATOR

### Objetivo
Verificar que todos los requirements.md están completos

### Checklist de Validacion

#### Estructura
- [ ] Header correcto
- [ ] Source File Analysis completo
- [ ] Purpose documentado
- [ ] Dependencies listadas
- [ ] Classes/Functions documentadas
- [ ] Business Logic descrita
- [ ] Project Rules incluidas
- [ ] Audit Status presente
- [ ] Implementation Gaps identificados

#### Reglas
- [ ] SOLID rules presentes (5 reglas)
- [ ] Trading rules según servicio
- [ ] Spain Tax rules según servicio
- [ ] Base rules según servicio
- [ ] Status asignado a cada regla

#### Calidad
- [ ] Sin @todo sin resolver
- [ ] Sin @skip-import sin resolver
- [ ] Sin placeholders vacíos
- [ ] Evidence incluida para cada status

### Comandos de Validacion

```bash
# Verificar estructura
for req in .requirements/app/**/*.requirements.md; do
  echo "=== Checking $req ==="

  # Verificar secciones requeridas
  grep -q "## Source File Analysis" "$req" && echo "✅ Source File Analysis" || echo "❌ Missing Source File Analysis"
  grep -q "## Purpose" "$req" && echo "✅ Purpose" || echo "❌ Missing Purpose"
  grep -q "## Dependencies" "$req" && echo "✅ Dependencies" || echo "❌ Missing Dependencies"
  grep -q "## Project Rules" "$req" && echo "✅ Project Rules" || echo "❌ Missing Project Rules"
  grep -q "## Audit Status" "$req" && echo "✅ Audit Status" || echo "❌ Missing Audit Status"

  # Verificar SOLID
  solid_count=$(grep -c "SRP-001\|OCP-001\|LSP-001\|ISP-001\|DIP-001" "$req")
  echo "SOLID rules: $solid_count/5"

  # Verificar status asignados
  status_count=$(grep -c "\[✅\]\|\[❌\]\|\[⚠️\]\|\[❓\]" "$req")
  echo "Rules with status: $status_count"
done
```

---

## CHECKPOINT FORMAT

```json
{
  "task_id": "23_requirements_generator",
  "task_name": "Requirements Generator",
  "started_at": "{{TIMESTAMP}}",
  "completed_at": "{{TIMESTAMP}}",
  "status": "COMPLETED",
  "progress": {
    "total_files": 0,
    "processed_files": 0,
    "validated_files": 0,
    "files_with_gaps": 0
  },
  "outputs": {
    "requirements_created": [],
    "requirements_updated": [],
    "validation_passed": true
  },
  "metrics": {
    "by_service": {
      "compliance": 0,
      "execution": 0,
      "backtesting": 0,
      "strategy": 0,
      "data": 0,
      "position_management": 0,
      "reconciliation": 0,
      "other": 0
    },
    "by_priority": {
      "P0": 0,
      "P1": 0,
      "P2": 0
    },
    "rules_status": {
      "implemented": 0,
      "partial": 0,
      "missing": 0
    }
  },
  "errors": [],
  "warnings": [],
  "timestamp": "{{TIMESTAMP}}"
}
```

---

## SUCCESS CRITERIA

La tarea esta COMPLETED cuando:

- [ ] Todos los archivos Python tienen requirements.md
- [ ] Cada requirements.md tiene estructura completa
- [ ] Reglas SOLID incluidas para todos los archivos
- [ ] Reglas Trading incluidas segun servicio
- [ ] Reglas Spain Tax incluidas segun servicio
- [ ] Reglas Base incluidas segun servicio
- [ ] Status asignado a cada regla con evidence
- [ ] Implementation Gaps identificados
- [ ] Validacion pasa para todos los archivos
- [ ] Checkpoint creado con status "COMPLETED"

---

## REFERENCIAS

- `rules/trading/` - Mapeo de reglas por archivo
- `rules/trading/` - Extraccion determinista
- `rules/trading/` - Requisitos SOLID + R1-R29
- `rules/trading/` - Reglas de trading
- `.ralph/ralph_templates/agents/requirement_generator_agent.yml` - Agente generador
