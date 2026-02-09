#  Final Cleanup & TODO Resolution - Prompt

**Tarea ID:** 99_final_cleanup
**Propósito:** Verificar y resolver todos los TODOs/@flags pendientes usando implementer_hat flow
**Tiempo estimado:** 4 horas
**Depends on:** Todas las tareas anteriores completadas (01-20)

---

##  OBJETIVO

Verificar que no quedan TODOs/@flags sin resolver en el código y arreglarlos o documentarlos apropiadamente, usando el flujo completo del implementer_hat.

---

##  FLUJO COMPLETO

Esta tarea tiene 3 fases que se ejecutan en orden:

### FASE 1: Escanear código (cleanup_scanner hat)
- Usa `scan_flags.py` para encontrar todos los flags
- Genera reporte JSON y Markdown
- Emite `cleanup.scan_complete` o `cleanup.no_flags`

### FASE 2: Arreglar flags (cleanup_implementer hat)
- Para cada flag encontrado, aplica el fix correspondiente
- Sigue el flujo del implementer_hat (NO FALLBACKS)
- Valida después de cada cambio con `utils.py validate`
- Emite `cleanup.fix_complete` por cada flag
- Emite `cleanup.all_complete` cuando todos están resueltos

### FASE 3: Validar y reportar (cleanup_validator hat)
- Re-escanea para verificar que no quedan flags críticos
- Valida sintaxis de todo el código
- Valida imports críticos
- Genera reporte final
- Emite `cleanup.complete`

---

##  FLAG TYPES A BUSCAR

| Flag | Descripción | Acción |
|------|-------------|--------|
| `@skip-import` | Import que no existe | Verificar si existe, eliminar flag o crear stub |
| `@todo` | Tarea pendiente | Completar o documentar como "PENDING: Task XX" |
| `@clarify` | Punto a aclarar | Aclarar con documentación o eliminar |
| `@review` | Código a revisar | Revisar, arreglar o eliminar flag |
| `@fixme` | Bug conocido | Arreglar obligatoriamente |
| `@hack` | Solution temporal | Reemplazar con solución proper |
| `XXX` | Código peligroso | Arreglar obligatoriamente |
| `TODO` (case-insensitive) | Tarea pendiente | Completar o documentar |
| `FIXME` (case-insensitive) | Bug a arreglar | Arreglar obligatoriamente |

---

##  HAT 1: CLEANUP SCANNER

### Paso 1: Ejecutar script de escaneo

```bash
# Escanear app/ completo con el script Python
python .ralph/scripts/scan_flags.py \
  --dir app/ \
  --output .ralph/outputs/flags_found.json \
  --format json

# También generar reporte markdown
python .ralph/scripts/scan_flags.py \
  --dir app/ \
  --output .ralph/outputs/flags_report.md \
  --format markdown
```

### Paso 2: Verificar resultados

```bash
# Leer reporte JSON
cat .ralph/outputs/flags_found.json | jq '.total_flags'

# Si es 0 → emitir cleanup.no_flags
# Si > 0 → emitir cleanup.scan_complete con datos
```

### Paso 3: Emitir evento apropiado

**No flags found:**
```bash
ralph emit "cleanup.no_flags" "total=0, timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

**Scan complete with flags:**
```bash
ralph emit "cleanup.scan_complete" "total=<n>, flags_by_type=<json>"
```

---

##  HAT 2: CLEANUP IMPLEMENTER

### ESTRATEGIA POR TIPO DE FLAG

#### 1. @skip-import

```bash
# PASO 1: Leer archivo
cat <file_path>

# PASO 2: Extraer el import que falta
grep "@skip-import" <file_path>

# PASO 3: Verificar si el import AHORA existe
find app/ -name "<import_name>.py"

# PASO 4A: Si EXISTE → Eliminar el flag @skip-import
# Editar el archivo, quitar el comentario @skip-import
# Validar con: python .ralph/scripts/utils.py validate <file_path>

# PASO 4B: Si NO EXISTE → Crear stub mínimo
# Crear el archivo con un stub Protocol (ver template abajo)
# Validar con: python .ralph/scripts/utils.py validate <stub_file>

# PASO 4C: Si NO se puede crear stub → Documentar mejor
# Mejorar el comentario @skip-import con más contexto
```

#### 2. @todo

```bash
# PASO 1: Leer archivo y contexto del @todo
cat <file_path> | head -n <line> | tail -n 5

# PASO 2: Analizar si la tarea es trivial
# Si es trivial (< 30 min) → Implementar ahora
# Si es compleja → Documentar como "pending for task XX"

# PASO 3A: Implementar si es trivial
# Editar el archivo
# Validar con: python .ralph/scripts/utils.py validate <file_path>

# PASO 3B: Documentar si es compleja
# Cambiar @todo por: ✅ PENDING: Task XX - <description>
```

#### 3. @clarify

```bash
# PASO 1: Leer contexto
cat <file_path> | head -n <line> | tail -n 5

# PASO 2: Aclarar con documentación
# Reemplazar @clarify por comentario claro explicando el punto
# O eliminar si no es relevante

# Validar cambios
```

#### 4. @review

```bash
# PASO 1: Revisar el código marcado
cat <file_path> | head -n <line> | tail -n 10

# PASO 2: Arreglar problemas encontrados
# Editar el archivo con la corrección

# PASO 3: Eliminar flag @review si está correcto

# Validar cambios
```

#### 5. @fixme / XXX / FIXME

```bash
# MISMO flujo que @review pero MÁS CRÍTICO
# Son bugs o código peligroso

# PASO 1: Leer contexto extendido
# PASO 2: Arreglar el bug
# PASO 3: Validar extensivamente

# NUNCA dejar un @fixme o XXX sin arreglar
```

#### 6. @hack

```bash
# PASO 1: Identificar por qué es un hack
# PASO 2: Implementar solución proper
# PASO 3: Reemplazar hack con implementación correcta

# Si no se puede reemplazar ahora, documentar:
# @hack: <reason> - TODO: Replace with proper implementation in task XX
```

### VALIDACIÓN SIEMPRE OBLIGATORIA

```bash
# Para cada archivo modificado:
python .ralph/scripts/utils.py validate <file_path>

# Debe retornar: {"success": true, ...}

# Si success: false → Revisar errores y corregir
# NUNCA continuar si validation falla
```

### STUB TEMPLATE

```python
"""
Stub para <ProtocolName>

@note: Task XX no ejecutada aún
@todo: Ejecutar task XX para implementar funcionalidad completa
"""
from typing import Protocol, Any


class <ProtocolName>(Protocol):
    """
    Stub de <ProtocolName>

    Task XX no ejecutada - Solo métodos mínimos definidos.
    """

    def method1(self, param1: str) -> str:
        """
        Method 1 stub.

        @todo: Implementar en task XX
        """
        raise NotImplementedError(
            "<ProtocolName>.method1 not implemented - Task XX not executed"
        )

    def method2(self, param1: int, param2: float) -> bool:
        """
        Method 2 stub.

        @todo: Implementar en task XX
        """
        raise NotImplementedError(
            "<ProtocolName>.method2 not implemented - Task XX not executed"
        )
```

---

##  HAT 3: CLEANUP VALIDATOR

### Paso 1: Re-escanear para verificar

```bash
# Ejecutar scan_flags.py nuevamente
python .ralph/scripts/scan_flags.py \
  --dir app/ \
  --output .ralph/outputs/flags_final.json \
  --format json

# Verificar total
cat .ralph/outputs/flags_final.json | jq '.total_flags'
```

### Paso 2: Verificar flags críticos

```bash
# Contar flags críticos
cat .ralph/outputs/flags_final.json | jq '.summary | {"@skip-import", "@fixme", "XXX", "FIXME"}'

# Si hay alguno → cleanup.blocked
# Si no hay → continuar
```

### Paso 3: Validar @todos documentados

```bash
# Verificar que todos los @todo están documentados
grep -r "@todo" app/ | grep -v "PENDING\|Task XX\|pending for"

# Si la salida está vacía → OK, son @todos documentados
# Si hay @todos sin documentar → cleanup.blocked
```

### Paso 4: Validar sintaxis

```bash
# Compilar todos los archivos Python
for f in $(find app/ -name "*.py" | grep -v __pycache__); do
  python -m py_compile "$f" 2>&1 | tee -a .ralph/outputs/syntax_check.log
done
```

### Paso 5: Validar imports críticos

```bash
# Intentar importar módulos principales
python -c "
try:
    from app.core.protocols import *
    print('✅ app.core.protocols imports OK')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
" 2>&1 | tee -a .ralph/outputs/imports_check.log
```

### Paso 6: Generar reporte final

Crear `.ralph/outputs/FINAL_CLEANUP_REPORT.md` con:
- Resumen de flags encontrados
- Acciones tomadas por cada tipo
- Stubs creados
- Estado final del sistema
- Recomendaciones para producción

---

##  REGLAS CRÍTICAS DEL IMPLEMENTER_HAT

- ❌ **NO** intentar importar con fallbacks (`try/except ImportError`)
- ✅ **SÍ** verificar que el import existe ANTES de usarlo
- ✅ Si el import NO existe → **FLAG `@skip-import: <reason>`** en código
- ✅ Si una dependencia NO está lista → **FLAG `@todo: <feature>`**
- ✅ **SIEMPRE validar** después de cambios con `utils.py validate`
- ✅ **NUNCA continuar** si validation falla
- ✅ **PRESERVAR** funcionalidad existente

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "99_final_cleanup",
  "task_name": "Final Cleanup & TODO Resolution",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T14:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_flags_found": 50,
    "flags_resolved": 50,
    "flags_documented": 0,
    "stubs_created": 5
  },
  "outputs": {
    "flags_resolved": {
      "@skip-import": 10,
      "@todo": 30,
      "@clarify": 5,
      "@review": 5,
      "@fixme": 0,
      "@hack": 0,
      "XXX": 0
    },
    "stubs_created": [
      "app/core/protocols/i_feature.py",
      "app/services/optional/i_optional_service.py"
    ],
    "validation_passed": true
  },
  "validation": {
    "no_critical_flags": true,
    "all_optional_flags_documented": true,
    "syntax_check_passed": true,
    "imports_check_passed": true
  },
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T14:00:00Z"
}
```

---

##  SUCCESS CRITERIA

La tarea está **COMPLETED** cuando:

- [ ] Escaneo ejecutado con `scan_flags.py`
- [ ] Todos los flags críticos (@skip-import, @fixme, XXX, FIXME) resueltos
- [ ] Todos los @todo resueltos o documentados como "PENDING: Task XX"
- [ ] Código valida sin errores de sintaxis
- [ ] Imports críticos funcionan
- [ ] Stubs creados para imports faltantes
- [ ] Reporte final creado en `.ralph/outputs/FINAL_CLEANUP_REPORT.md`
- [ ] Checkpoint creado con status "COMPLETED"

---

##  OUTPUT ESPERADO

Archivo final: `.ralph/outputs/FINAL_CLEANUP_REPORT.md`

Con:
- Resumen de flags encontrados
- Acciones tomadas para cada tipo
- Stubs creados
- Estado final del sistema
- Recomendaciones para producción

---

##  EVENTOS

| Evento | Cuándo | Datos |
|--------|-------|-------|
| `cleanup.start` | Inicio de tarea | - |
| `cleanup.scan_complete` | Escaneo completado con flags | total, flags_by_type |
| `cleanup.no_flags` | No se encontraron flags | total=0 |
| `cleanup.next_flag` | Siguiente flag a procesar | flag_data |
| `cleanup.fix_complete` | Flag arreglado | file, flag_type, line |
| `cleanup.all_complete` | Todos los flags resueltos | total_resolved |
| `cleanup.blocked` | No se puede continuar | error, cannot_resolve |
| `cleanup.complete` | Tarea completada | status, report |

---

##  REFERENCIAS

- `.ralph/scripts/scan_flags.py` - Script de escaneo
- `.ralph/scripts/utils.py` - Script de validación
- `.ralph/ralph_templates/hats/implementer_hat.yml` - Template de implementer
- `.ralph/TROUBLESHOOTING.md` - Guía de problemas
