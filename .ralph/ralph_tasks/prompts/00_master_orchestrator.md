# Master Orchestrator AAA v11.0 - NO SHORTCUTS

**OBJETIVO:** Llevar el código a nivel AAA (Production Ready) - EJECUCIÓN COMPLETA OBLIGATORIA

---

## ⚠️ REGLAS ANTI-ATAJOS OBLIGATORIAS

**ESTÁ PROHIBIDO:**
1. ❌ Verificar existencia sin crear/mejorar componentes
2. ❌ Saltarse fases o sub-fases
3. ❌ Continuar a la siguiente fase sin completar la anterior al 100%
4. ❌ Marcar tareas como completas sin ejecutar los checkpoints
5. ❌ Generar outputs incompletos (ej: requirements.md parciales)
6. ❌ Ignorar fallos en tests o QA

**OBLIGATORIO:**
1. ✅ Ejecutar CADA checkpoint antes de avanzar
2. ✅ Documentar outputs específicos de cada fase
3. ✅ Corregir errores antes de continuar
4. ✅ Generar requirements.md para TODOS los archivos Python
5. ✅ Tests deben pasar al 100% antes de Phase 6

---

## FLUJO (6 Fases con Checkpoints Obligatorios)

### FASE 1: ESTRUCTURA [OBLIGATORIO]

#### 1.1 Structural Fix
**ACCIÓN:** Eliminar duplicados, corregir imports
**CHECKPOINT:**
```bash
find app -name "*.py" -exec md5sum {} \; | sort | uniq -D -w32
```
**OUTPUT:** Lista de duplicados eliminados

#### 1.2 Requirements Generator
**ACCIÓN:** Generar requirements.md para CADA archivo Python
**CHECKPOINT:**
```bash
PYTHON_FILES=$(find app -name "*.py" | wc -l)
REQ_FILES=$(find .requirements/app -name "*.md" | wc -l)
echo "Python files: $PYTHON_FILES, Requirements: $REQ_FILES"
# DEBE coincidir o documentar diferencia
```
**OUTPUT:**
- Archivos Python totales: X
- Requirements generados: Y
- Diferencia: Z (justificada)

#### 1.3 Protocol Interfaces
**ACCIÓN:** CREAR/MEJORAR interfaces SOLID usando typing.Protocol
**CHECKPOINT:**
```bash
grep -r "class.*Protocol" app/shared/protocols | wc -l
```
**OUTPUT:** Documentar interfaces creadas/mejoradas con ubicación

---

### FASE 2: COMPONENTES CORE [OBLIGATORIO IMPLEMENTAR]

#### 2.1 Compliance Engine
**ACCIÓN:** CREAR/MEJORAR validaciones R1-R29
**CHECKPOINT:**
- Leer `rules/trading/64-realistic-retail-trading-rules.md`
- Verificar implementación de cada regla R1-R29
- Tests unitarios del compliance engine pasando

**OUTPUT:** Tabla de reglas implementadas con ubicación

#### 2.2 Spain Tax Engine
**ACCIÓN:** CREAR/MEJORAR IRPF 19/21/23%
**CHECKPOINT:**
```bash
pytest tests/unit/services/tax_efficiency/ -v
```
**OUTPUT:** Verificar brackets IRPF, Modelo 720, loss carryforward

#### 2.3 Risk Validators
**ACCIÓN:** CREAR/MEJORAR Kelly, DD, R:R validators
**CHECKPOINT:**
- KellyCriterionValidator tests pasando
- DrawdownValidator tests pasando
- RiskRewardValidator tests pasando

**OUTPUT:** Tabla de validators con ubicación y estado de tests

#### 2.4 Decision Logger
**ACCIÓN:** CREAR/MEJORAR append-only logger con correlation ID
**CHECKPOINT:**
- AppendOnlyLog tests pasando
- Correlation ID tracking verificado

**OUTPUT:** Documentar implementación R15 (append-only) y R28 (retención)

---

### FASE 3: CONFIGURACIÓN [OBLIGATORIO MOVER]

#### 3.1 Central Config
**ACCIÓN:** MOVER TODOS los hardcoded values a centralized_config
**CHECKPOINT:**
```bash
grep -rn "0\.0[0-9]\|[1-9][0-9]\.[0-9]" app --include="*.py" | grep -v "test" | grep -v "__pycache__"
# Documentar valores hardcoded restantes (si los hay)
```
**OUTPUT:** Lista de valores movidos a config

---

### FASE 4: QA [OBLIGATORIO 0 ERRORES CRÍTICOS]

#### 4.1 QA Validation
**ACCIÓN:** Ejecutar y CORREGIR hasta tener 0 errores
**CHECKPOINTS:**
```bash
black --check app 2>&1 | tee /tmp/black.log
isort --check app 2>&1 | tee /tmp/isort.log
ruff check app 2>&1 | tee /tmp/ruff.log
mypy app --no-error-summary 2>&1 | head -100 | tee /tmp/mypy.log
```
**OUTPUT:**
- Black: X archivos modificados / 0 errores
- isort: X archivos modificados / 0 errores
- Ruff: X errores corregidos / 0 errores restantes
- Mypy: X errores totales (aceptable >0 para type hints)

#### 4.2 Tests Unit + Integration
**ACCIÓN:** Ejecutar tests y CORREGIR todos los fallos
**CHECKPOINTS:**
```bash
pytest tests/unit -v --tb=short 2>&1 | tee /tmp/unit_tests.log
pytest tests/integration -v --tb=short 2>&1 | tee /tmp/integration_tests.log
```
**PROHIBIDO:** Continuar a Fase 5 si hay tests fallando
**OUTPUT:**
- Unit tests: X/Y pasando (debe ser 100%)
- Integration tests: X/Y pasando (debe ser 100%)

---

### FASE 5: SECURITY [OBLIGATORIO HARDENING]

#### 5.1 Security Hardening
**ACCIÓN:** Eliminar secrets, configurar .env gitignored
**CHECKPOINTS:**
```bash
grep -r "sk-\|pk-\|xoxb-\|api_key\s*=\s*['\"]" app --include="*.py" || echo "No secrets found"
grep -q ".env" .gitignore && echo ".env in gitignore" || echo "MISSING: .env in gitignore"
grep -r "password\s*=\s*['\"]" app --include="*.py" | grep -v "test" | grep -v "example" || echo "No hardcoded passwords"
```
**OUTPUT:**
- Secrets eliminados: X
- .env en .gitignore: Sí/No
- Logs limpios de datos sensibles: Sí/No

---

### FASE 6: FINAL [OBLIGATORIO DOCUMENTACIÓN]

#### 6.1 Final Cleanup
**ACCIÓN:** Resolver TODOs, generar reporte AAA con MÉTRICAS REALES
**CHECKPOINTS:**
```bash
grep -r "TODO\|FIXME\|XXX\|HACK" app --include="*.py" | wc -l
```
**OUTPUT:** `.ralph/outputs/aaa_audit_report.md` con:

```markdown
# AAA Production Ready Audit

**Fecha:** (timestamp actual)
**Estado:** AAA_PRODUCTION_READY | INCOMPLETE
**Duración:** X horas

## Métricas Reales (OBLIGATORIO)

### Estructura
- Archivos Python: X (contar con find)
- Duplicados eliminados: Y
- Imports corregidos: Z

### Requirements
- Archivos Python: X
- Requirements generados: Y
- Coverage: Y/X = Z%

### Arquitectura SOLID
- Protocol interfaces: X
- SRP violations: X
- OCP violations: X
- LSP violations: X
- ISP violations: X
- DIP violations: X

### Reglas Trading (R1-R29)
- Reglas implementadas: X/29
- Reglas pendientes: [lista]
- Tests de compliance: X/Y pasando

### Spain Tax
- IRPF brackets: ✅ 19/21/23%
- Modelo 720: ✅/❌
- Loss carryforward: ✅/❌

### QA
- Black: X errores
- isort: X errores
- Ruff: X errores
- Mypy: X errores (aceptable >0)

### Tests
- Unit tests: X/Y pasando (debe ser 100%)
- Integration tests: X/Y pasando (debe ser 100%)
- Cobertura: X%

### Security
- Secrets en código: X
- .env gitignored: Sí/No
- Logs limpios: Sí/No

## Estado Final: [AAA_PRODUCTION_READY | INCOMPLETE]

Si INCOMPLETE, listar:
1. Faltantes específicos
2. Acciones requeridas
3. Bloqueadores identificados
```

---

## FUENTES DE VERDAD

| Fuente | Ubicación | Uso |
|--------|-----------|-----|
| **Rules** | `rules/trading/64-realistic-retail-trading-rules.md` | Reglas R1-R29 de trading |
| **Docs** | `.ralph/docs/` | Análisis, arquitectura |
| **Requirements** | `.requirements/` | Requirements por archivo |
| **Código** | `app/` | Archivos Python |

---

## NO EJECUTAR BACKTESTS

**IMPORTANTE:** Este orquestador NO ejecuta backtests.
Solo valida que el código cumple las reglas R1-R29.
La ejecución de backtests llevaría demasiado tiempo.

---

## VERIFICACIÓN FINAL

Antes de marcar como COMPLETE, verificar:

- [ ] Todos los checkpoints ejecutados
- [ ] Todos los outputs documentados
- [ ] Tests al 100% pasando
- [ ] QA al 0% errores (excepto mypy type hints)
- [ ] Security hardening completo
- [ ] Reporte AAA con métricas reales (no placeholders)

---

## EJECUTAR

```bash
cd /Users/kepa.cantero/Projects/algoTrading
ralph run -P .ralph/ralph_tasks/prompts/00_master_orchestrator.md
```

**Tiempo estimado:** 3-5 horas (ejecución completa sin atajos)
