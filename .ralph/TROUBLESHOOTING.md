#  Ralph System - Troubleshooting Guide

**Fecha:** 2026-02-08
**Propósito:** Guía de resolución de problemas comunes del sistema Ralph

---

##  Tabla de Contenidos

1. [Problemas de Instalación/Configuración](#problemas-de-instalaciónconfiguración)
2. [Problemas de Ejecución de Tasks](#problemas-de-ejecución-de-tasks)
3. [Problemas de Checkpoints](#problemas-de-checkpoints)
4. [Problemas de Validación](#problemas-de-validación)
5. [Problemas de Integración](#problemas-de-integración)
6. [Errores Comunes](#errores-comunes)

---

##  Problemas de Instalación/Configuración

### C1. Error: "Directory not found: .ralph/specs/"

**Síntoma:**
```
Error: Directory not found: .ralph/specs/
```

**Causa:**
- El directorio `specs/` no existe o está mal configurado

**Solución:**
```bash
# Crear directorio
mkdir -p .ralph/specs/

# O usar .ralph/docs/ en su lugar
# Editar ralph_base.yml:
# specs_dir: ".ralph/docs/"
```

**Prevención:**
- Verificar que todos los directorios necesarios existen antes de ejecutar
- Usar `ls -la .ralph/` para verificar estructura

---

### C2. Error: "scripts/utils.py not found"

**Síntoma:**
```
Error: python scripts/utils.py validate <file>
python: can't open file 'scripts/utils.py': [Errno 2] No such file or directory
```

**Causa:**
- El script `utils.py` no está en la ruta esperada
- Working directory incorrecto

**Solución:**
```bash
# Verificar ubicación del script
ls -la /Users/kepa.cantero/Projects/algoTrading/scripts/utils.py

# Copiar a .ralph/scripts/
cp /Users/kepa.cantero/Projects/algoTrading/scripts/utils.py .ralph/scripts/

# Usar ruta completa
python /Users/kepa.cantero/Projects/algoTrading/scripts/utils.py validate <file>
```

**Prevención:**
- Usar siempre rutas absolutas o relativas desde `.ralph/`
- Copiar scripts necesarios a `.ralph/scripts/`

---

### C3. Error: "app/ directory does not exist"

**Síntoma:**
```
Error: Cannot create file 'app/core/protocols/xxx.py'
Directory 'app/' does not exist
```

**Causa:**
- El directorio `app/` no existe en el proyecto
- Task intenta crear archivos sin directorio base

**Solución:**
```bash
# Crear estructura completa de app/
mkdir -p app/core/protocols
mkdir -p app/services/tax_efficiency/engines
mkdir -p app/services/logging
mkdir -p app/services/risk/validators
mkdir -p app/services/compliance
mkdir -p app/services/position_management
mkdir -p app/services/reconciliation
mkdir -p app/services/capital
mkdir -p app/services/live_trading/broker_adapters

# Crear __init__.py files
find app -type d -exec touch {}/__init__.py \;
```

**Prevención:**
- Crear estructura `app/` antes de ejecutar tasks
- Verificar con `ls -la app/` antes de empezar

---

##  Problemas de Ejecución de Tasks

### T1. Error: "Prompt file not found"

**Síntoma:**
```
Error: Prompt file not found: .ralph/ralph_tasks/prompts/01_protocol_interfaces.md
```

**Causa:**
- El archivo prompt no existe
- Ruta incorrecta en el YAML

**Solución:**
```bash
# Verificar que el prompt existe
ls -la .ralph/ralph_tasks/prompts/

# Si no existe, crearlo
# Copiar de template o crear manualmente

# Verificar ruta en YAML
grep "prompt_file" .ralph/ralph_tasks/01_protocol_interfaces.yml
```

**Prevención:**
- Crear prompts para todos los tasks antes de ejecutar
- Verificar rutas en YAMLs

---

### T2. Error: "Checkpoint file already exists"

**Síntoma:**
```
Error: Checkpoint file already exists: .ralph/checkpoints/01_protocol_interfaces_checkpoint.json
Task may have already been completed
```

**Causa:**
- El task ya se ejecutó anteriormente
- Checkpoint de ejecución previa existe

**Solución:**
```bash
# Opción 1: Reanudar desde checkpoint
python .ralph/scripts/resume.py "01_protocol_interfaces"

# Opción 2: Eliminar checkpoint y reiniciar
rm .ralph/checkpoints/01_protocol_interfaces_checkpoint.json

# Opción 3: Verificar estado del task
cat .ralph/checkpoints/01_protocol_interfaces_checkpoint.json | jq '.status'
```

**Prevención:**
- Usar `resume.py` para reanudar tasks
- Verificar estado antes de re-ejecutar

---

### T3. Error: "Dependencies not satisfied"

**Síntoma:**
```
Error: Task dependencies not satisfied
Required tasks: ["01_protocol_interfaces"]
Status: PENDING
```

**Causa:**
- Task depende de otro que no está completado
- Orden de ejecución incorrecto

**Solución:**
```bash
# Verificar estado de dependencias
cat .ralph/checkpoints/01_protocol_interfaces_checkpoint.json | jq '.status'

# Si está COMPLETED, continuar
# Si está FAILED o PENDING, completarlo primero

# Ejecutar en orden correcto:
# 01 → 02 → 03 → 04 → (otros) → 09
```

**Prevención:**
- Ejecutar tasks en orden según dependencias
- Verificar checkpoints antes de continuar

---

##  Problemas de Checkpoints

### CP1. Error: "Invalid checkpoint format"

**Síntoma:**
```
Error: Invalid checkpoint format
Missing required field: "task_id"
```

**Causa:**
- Checkpoint no sigue el formato estandarizado
- Campos faltantes o incorrectos

**Solución:**
```bash
# Verificar formato
cat .ralph/checkpoints/xxx_checkpoint.json | jq

# Campos requeridos:
# - task_id
# - task_name
# - started_at
# - status
# - timestamp

# Si está corrupto, recrear desde cero
rm .ralph/checkpoints/xxx_checkpoint.json
```

**Prevención:**
- Usar template de ralph_base.yml para checkpoints
- Validar JSON antes de guardar

---

### CP2. Error: "Checkpoint directory does not exist"

**Síntoma:**
```
Error: Cannot save checkpoint
Directory: .ralph/checkpoints/
```

**Causa:**
- Directorio de checkpoints no existe

**Solución:**
```bash
# Crear directorio
mkdir -p .ralph/checkpoints/

# Verificar permisos
ls -la .ralph/
```

**Prevención:**
- Crear directorio `checkpoints/` durante setup inicial

---

##  Problemas de Validación

### V1. Error: "Validation failed: black formatting"

**Síntoma:**
```
{
  "success": false,
  "checks": {
    "black": "failed"
  }
}
```

**Causa:**
- Archivo no está formateado correctamente con black

**Solución:**
```bash
# Auto-fix con black
black <file_path>

# Re-validar
python .ralph/scripts/utils.py validate <file_path>

# Verificar que success sea true
python .ralph/scripts/utils.py validate <file_path> | jq '.success'
```

**Prevención:**
- Ejecutar black antes de validar
- Configurar editor para usar black automáticamente

---

### V2. Error: "Validation failed: import error"

**Síntoma:**
```
{
  "success": false,
  "checks": {
    "mypy": "failed",
    "errors": ["ImportError: No module named 'xxx'"]
  }
}
```

**Causa:**
- Dependencia no instalada
- Import incorrecto

**Solución:**
```bash
# Opción 1: Instalar dependencia
pip install <missing_package>

# Opción 2: Usar flag @skip-import
# En el código:
# @skip-import: Package not implemented yet
from missing_package import xxx  # type: ignore

# Opción 3: Crear stub mínimo
# Crear archivo con la clase/interface mínima
```

**Prevención:**
- Instalar todas las dependencias antes de validar
- Usar flags @skip-import para código incompleto

---

##  Problemas de Integración

### I1. Error: "Protocol interface not found"

**Síntoma:**
```
Error: ImportError: cannot import name 'ISpainTaxEngine' from 'app.core.protocols'
```

**Causa:**
- Task 01 (Protocol interfaces) no se ejecutó primero
- Protocol no existe

**Solución:**
```bash
# Verificar que Protocol existe
ls -la app/core/protocols/i_spain_tax_engine.py

# Si no existe, ejecutar task 01 primero
ralph run .ralph/ralph_tasks/01_protocol_interfaces.yml

# Luego continuar con task dependiente
```

**Prevención:**
- Ejecutar SIEMPRE task 01 primero
- Verificar dependencias antes de ejecutar

---

### I2. Error: "ralph emit command not found"

**Síntoma:**
```
Error: command not found: ralph
```

**Causa:**
- Comando `ralph` no está en PATH
- No existe script `ralph`

**Solución:**
```bash
# Usar script emit.py directamente
python .ralph/scripts/emit.py "<event>" '{"data": "value"}'

# O crear alias
alias ralph='python .ralph/scripts/emit.py'

# O añadir a PATH
export PATH="$PATH:.ralph/scripts"
```

**Prevención:**
- Usar siempre `python .ralph/scripts/emit.py` directamente
- Crear alias en `.bashrc` o `.zshrc`

---

##  Errores Comunes

### E1. Error: "Permission denied"

**Síntoma:**
```
Error: Permission denied: .ralph/scripts/emit.py
```

**Causa:**
- Script no tiene permisos de ejecución

**Solución:**
```bash
# Dar permisos de ejecución
chmod +x .ralph/scripts/emit.py
chmod +x .ralph/scripts/resume.py
chmod +x .ralph/scripts/utils.py

# Verificar permisos
ls -la .ralph/scripts/
```

**Prevención:**
- Dar permisos de ejecución a todos los scripts

---

### E2. Error: "JSON decode error"

**Síntoma:**
```
Error: JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Causa:**
- Archivo JSON vacío o corrupto
- Error de sintaxis JSON

**Solución:**
```bash
# Validar JSON
cat <file> | python -m json.tool

# Si hay error, corregir sintaxis
# Asegurar comillas, comas, llaves balanceadas

# Validar antes de usar
jq '.' <file> 2>&1
```

**Prevención:**
- Validar JSON después de editar
- usar jq o python -m json.tool

---

### E3. Error: "Working directory issue"

**Síntoma:**
```
Error: Cannot find file relative to current directory
```

**Causa:**
- Working directory incorrecto
- Rutas relativas no funcionan

**Solución:**
```bash
# Verificar working directory
pwd
# Debe ser: /Users/kepa.cantero/Projects/algoTrading

# Cambiar a directorio correcto
cd /Users/kepa.cantero/Projects/algoTrading

# O usar rutas absolutas
python /Users/kepa.cantero/Projects/algoTrading/.ralph/scripts/utils.py validate <file>
```

**Prevención:**
- Usar rutas absolutas desde proyecto
- Verificar pwd antes de ejecutar

---

##  Diagnostic Commands

### Verificar estado del sistema

```bash
# 1. Verificar estructura de directorios
ls -la .ralph/
ls -la .ralph/ralph_tasks/
ls -la .ralph/ralph_tasks/prompts/
ls -la .ralph/checkpoints/
ls -la .ralph/scripts/
ls -la app/

# 2. Verificar YAMLs creados
ls -la .ralph/ralph_tasks/*.yml | wc -l  # Debe ser >= 6

# 3. Verificar prompts creados
ls -la .ralph/ralph_tasks/prompts/*.md | wc -l  # Debe ser >= 6

# 4. Verificar checkpoints
for f in .ralph/checkpoints/*.json; do
  echo "=== $f ==="
  cat "$f" | jq '.status'
done

# 5. Verificar scripts
ls -la .ralph/scripts/
ls -la scripts/

# 6. Verificar app/ structure
find app -type f -name "*.py" | head -20
```

### Verificar integración

```bash
# 1. Test emit command
python .ralph/scripts/emit.py "test" '{"message": "test"}'
ls -la .ralph/events/test.log

# 2. Test resume command
python .ralph/scripts/resume.py "01_protocol_interfaces"

# 3. Test validation
python .ralph/scripts/utils.py validate app/core/protocols/__init__.py
```

---

##  Contact/Support

Si el problema persiste después de intentar las soluciones:

1. Revisar logs en `.ralph/logs/`
2. Verificar checkpoints para errores recientes
3. Consultar `ANALISIS_EXHAUSTIVO_V2.md` para problemas conocidos
4. Crear issue con:
   - Comando ejecutado
   - Error completo
   - Output de diagnostic commands

---

**Última actualización:** 2026-02-08
**Versión:** 1.0
