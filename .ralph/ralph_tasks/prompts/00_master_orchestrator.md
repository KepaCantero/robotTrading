# Master Orchestrator AAA v13.0 - PRODUCTION CODE ONLY

**OBJETIVO:** Llevar el código a nivel AAA (Production Ready) - EJECUCIÓN COMPLETA OBLIGATORIA

---

## ⚠️ ALCANCE: SOLO CÓDIGO DE PRODUCCIÓN

**ESTE ORQUESTADOR SOLO ANALIZA:**
- ✅ `app/` - Código de producción (ÚNICO directorio analizado)
- ✅ `config/` - Archivos de configuración
- ✅ `scripts/` - Scripts de utilidad

**ESTE ORQUESTADOR NUNCA ANALIZA:**
- ❌ `tests/` - **IGNORADO COMPLETAMENTE** - No leer, no modificar, no ejecutar, no generar requirements
- ❌ `.venv/` - **IGNORADO** - Virtual environment
- ❌ `__pycache__/` - **IGNORADO** - Cache

**RAZÓN:** El análisis de calidad se centra exclusivamente en el código que se despliega a producción.
Los tests son responsabilidad del desarrollador y se ejecutan fuera de este orquestador.

---

## ⚠️ REGLAS ANTI-ATAJOS OBLIGATORIAS

**ESTÁ PROHIBIDO:**
1. ❌ Verificar existencia sin crear/mejorar componentes
2. ❌ Saltarse fases o sub-fases
3. ❌ Continuar a la siguiente fase sin completar la anterior al 100%
4. ❌ Marcar tareas como completas sin ejecutar los checkpoints
5. ❌ Generar outputs incompletos (ej: requirements.md parciales)
6. ❌ Analizar, leer, modificar o ejecutar archivos en tests/

**OBLIGATORIO:**
1. ✅ Ejecutar CADA checkpoint antes de avanzar
2. ✅ Documentar outputs específicos de cada fase
3. ✅ Corregir errores antes de continuar
4. ✅ Generar requirements.md SOLO para archivos en app/
5. ✅ Centrarse EXCLUSIVAMENTE en código de producción

---

## FLUJO (6 Fases con Checkpoints Obligatorios)

### FASE 1: ESTRUCTURA [SOLO app/]

#### 1.1 Structural Fix
**ACCIÓN:** Eliminar duplicados, corregir imports en app/
**CHECKPOINT:**
```bash
find app -name "*.py" -type f -exec md5sum {} \; 2>/dev/null | sort | uniq -D -w32
```
**OUTPUT:** Lista de duplicados eliminados en app/

#### 1.2 Requirements Generator
**ACCIÓN:** Generar requirements.md para CADA archivo Python en app/
**CHECKPOINT:**
```bash
PYTHON_FILES=$(find app -name "*.py" -type f | wc -l)
REQ_FILES=$(find .requirements/app -name "*.requirements.txt" 2>/dev/null | wc -l)
echo "Production Python files in app/: $PYTHON_FILES"
echo "Requirements generated: $REQ_FILES"
echo "Coverage: $REQ_FILES/$PYTHON_FILES"
```
**OUTPUT:**
- Archivos Python en app/: X
- Requirements generados: Y
- Coverage: Y/X = Z%

#### 1.3 Protocol Interfaces
**ACCIÓN:** CREAR/MEJORAR interfaces SOLID usando typing.Protocol en app/
**CHECKPOINT:**
```bash
grep -r "class.*Protocol" app/ --include="*.py" 2>/dev/null | wc -l
```
**OUTPUT:** Documentar interfaces creadas/mejoradas con ubicación en app/

---

### FASE 2: COMPONENTES CORE [SOLO app/]

#### 2.1 Compliance Engine
**ACCIÓN:** CREAR/MEJORAR validaciones R1-R29 en app/
**CHECKPOINT:**
- Leer `rules/trading/64-realistic-retail-trading-rules.md`
- Verificar implementación de cada regla R1-R29 en app/services/compliance/
- Verificar que los archivos de compliance existen y tienen la lógica correcta

**OUTPUT:** Tabla de reglas implementadas con ubicación en app/

#### 2.2 Spain Tax Engine
**ACCIÓN:** CREAR/MEJORAR IRPF 19/21/23% en app/
**CHECKPOINT:**
```bash
# Verificar que los archivos de tax engine existen en app/
find app -name "*tax*" -o -name "*irpf*" 2>/dev/null | head -20
grep -r "IRPF\|irpf\|19\|21\|23" app/services/tax* --include="*.py" 2>/dev/null | head -10
```
**OUTPUT:** Verificar que brackets IRPF, Modelo 720, loss carryforward están implementados en app/

#### 2.3 Risk Validators
**ACCIÓN:** CREAR/MEJORAR Kelly, DD, R:R validators en app/
**CHECKPOINT:**
```bash
# Verificar que los validators existen en app/
grep -r "KellyCriterion\|DrawdownValidator\|RiskReward" app/ --include="*.py" 2>/dev/null | head -20
```
**OUTPUT:** Tabla de validators con ubicación en app/

#### 2.4 Decision Logger
**ACCIÓN:** CREAR/MEJORAR append-only logger con correlation ID en app/
**CHECKPOINT:**
```bash
# Verificar que el logger existe en app/
grep -r "append.only\|correlation.id\|AppendOnlyLog" app/ --include="*.py" 2>/dev/null | head -10
```
**OUTPUT:** Documentar implementación R15 (append-only) y R28 (retención) en app/

---

### FASE 3: CONFIGURACIÓN [SOLO app/]

#### 3.1 Central Config
**ACCIÓN:** MOVER TODOS los hardcoded values a centralized_config en app/
**CHECKPOINT:**
```bash
# Buscar valores hardcoded en app/ (NO en tests)
grep -rn "0\.0[0-9]\|[1-9][0-9]\.[0-9]" app --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -v "\.pyc" | head -50
```
**OUTPUT:** Lista de valores movidos a config

---

### FASE 4: QA [SOLO app/]

#### 4.1 QA Validation
**ACCIÓN:** Ejecutar linting y CORREGIR errores en app/
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

---

### FASE 5: SECURITY [SOLO app/]

#### 5.1 Security Hardening
**ACCIÓN:** Eliminar secrets, configurar .env gitignored en app/
**CHECKPOINTS:**
```bash
# Buscar secrets SOLO en app/ (NO en tests)
grep -r "sk-\|pk-\|xoxb-\|api_key\s*=\s*['\"]" app --include="*.py" 2>/dev/null || echo "No secrets found"
grep -q ".env" .gitignore && echo ".env in gitignore" || echo "MISSING: .env in gitignore"
grep -r "password\s*=\s*['\"]" app --include="*.py" 2>/dev/null | grep -v "example" || echo "No hardcoded passwords"
```
**OUTPUT:**
- Secrets eliminados: X
- .env en .gitignore: Sí/No
- Logs limpios de datos sensibles: Sí/No

---

### FASE 6: FINAL [SOLO app/]

#### 6.1 Final Cleanup
**ACCIÓN:** Resolver TODOs, generar reporte AAA con MÉTRICAS REALES de app/
**CHECKPOINTS:**
```bash
grep -r "TODO\|FIXME\|XXX\|HACK" app --include="*.py" 2>/dev/null | wc -l
```
**OUTPUT:** `.ralph/outputs/aaa_audit_report.md` con:

```markdown
# AAA Production Ready Audit

**Fecha:** (timestamp actual)
**Estado:** AAA_PRODUCTION_READY | INCOMPLETE
**Duración:** X horas

## Métricas de Producción (SOLO app/)

### Estructura
- Archivos Python en app/: X (contar con find app)
- Duplicados eliminados: Y
- Imports corregidos: Z

### Requirements
- Archivos Python en app/: X
- Requirements generados: Y
- Coverage: Y/X = Z%

### Arquitectura SOLID (SOLO app/)
- Protocol interfaces: X
- SRP violations: X
- OCP violations: X
- LSP violations: X
- ISP violations: X
- DIP violations: X

### Reglas Trading (R1-R29) en app/
- Reglas implementadas: X/29
- Reglas pendientes: [lista]
- Ubicaciones: [tabla con paths en app/]

### Spain Tax en app/
- IRPF brackets: ✅ 19/21/23%
- Modelo 720: ✅/❌
- Loss carryforward: ✅/❌

### QA (SOLO app/)
- Black: X errores
- isort: X errores
- Ruff: X errores
- Mypy: X errores (aceptable >0)

### Security (SOLO app/)
- Secrets en código: X
- .env gitignored: Sí/No
- Logs limpios: Sí/No

## Estado Final: [AAA_PRODUCTION_READY | INCOMPLETE]

Si INCOMPLETE, listar:
1. Faltantes específicos en app/
2. Acciones requeridas
3. Bloqueadores identificados
```

---

## FUENTES DE VERDAD

| Fuente | Ubicación | Uso |
|--------|-----------|-----|
| **Código Producción** | `app/` | Archivos Python a analizar |
| **Rules** | `rules/trading/64-realistic-retail-trading-rules.md` | Reglas R1-R29 de trading |
| **Docs** | `.ralph/docs/` | Análisis, arquitectura |
| **Requirements** | `.requirements/app/` | Requirements por archivo |

---

## NO EJECUTAR BACKTESTS

**IMPORTANTE:** Este orquestador NO ejecuta backtests.
Solo valida que el código de producción cumple las reglas R1-R29.
La ejecución de backtests llevaría demasiado tiempo.

---

## VERIFICACIÓN FINAL

Antes de marcar como COMPLETE, verificar:

- [ ] Todos los checkpoints ejecutados en app/
- [ ] Todos los outputs documentados
- [ ] QA al 0% errores en app/ (excepto mypy type hints)
- [ ] Security hardening completo en app/
- [ ] Reporte AAA con métricas reales de app/ (no placeholders)
- [ ] NO se ha analizado ni ejecutado ningún archivo en tests/

---

## EJECUTAR

```bash
cd /Users/kepa.cantero/Projects/algoTrading
ralph run -P .ralph/ralph_tasks/prompts/00_master_orchestrator.md
```

**Tiempo estimado:** 3-5 horas (ejecución completa sin atajos)
