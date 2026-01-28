# 🚀 AlgoTrading - Implementation Rules & Quality Standards

## Overview

Este documento especifica las reglas OBLIGATORIAS que TODA implementación debe cumplir antes de hacer commit. Estas reglas aseguran:

✅ Código limpio y consistente
✅ Sin errores críticos de linting
✅ Type safety
✅ Seguridad
✅ Tests funcionales

---

## 📋 QUICK START - Para implementar una feature

### 1️⃣ Escribir el código

```bash
# Implement your feature
vim app/strategies/my_feature.py
```

### 2️⃣ Validar la implementación

```
./scripts/check_all.sh
```

### 3️⃣ Revisar resultados

- Si `./scripts/check_all.sh` retorna **0**: ✅ LISTO PARA COMMIT
- Si retorna **>0**: ❌ Corregir errores y repetir paso 2

### 4️⃣ Hacer commit (SOLO si paso 2 tuvo éxito)

```bash
git add -A
git commit -m "feat: descripción de la feature [TASK-X.X]"
```

---

## ✅ CHECKLIST DE VALIDACIÓN

Antes de hacer **cualquier commit**, verifica:

### ✓ Formateo y Orden
- [ ] `Black` - Código formateado (88 chars)
- [ ] `Isort` - Imports ordenados
- [ ] `Autoflake` - Sin imports/variables sin usar
- [ ] `Ruff` - Fixes aplicados

### ✓ Linting
- [ ] `Flake8` - Máximo 5 errores E501 por archivo, CERO críticos
- [ ] `Pylint` - Score > 8.0 (informativo)

### ✓ Type Safety
- [ ] `Mypy` - Sin errores críticos

### ✓ Security
- [ ] `Bandit` - Sin issues HIGH severity

### ✓ Tests (si aplica)
- [ ] Tests pasan: `pytest tests/ -v`
- [ ] Cobertura > 80% (código nuevo)

---

## 🛠️ SCRIPTS DISPONIBLES

### `./scripts/validate_implementation.sh` ⭐ **RECOMENDADO**

**Uso:** Validación completa con reportes detallados

```bash
./scripts/validate_implementation.sh
```

**Qué hace:**
1. Ejecuta Black, Isort, Autoflake, Ruff (auto-fixes)
2. Valida Flake8, Pylint, Mypy, Bandit
3. Ejecuta pytest
4. Genera reporte con estado PASS/FAIL

**Salida esperada:**

```
✅ IMPLEMENTACIÓN VALIDADA - LISTO PARA COMMIT
```

---

### `./scripts/check_all.sh`

**Uso:** Fixes automáticos sin validación final

```bash
./scripts/check_all.sh
```

**Qué hace:**
- Ejecuta Black, Isort, Autoflake, Ruff
- Muestra salida de Flake8 y Pylint (informativo)

---

### Quick linting checks

```bash
# Solo Flake8 (rápido, <5s)
flake8 app/ tests/ --max-line-length=100

# Solo Mypy (medium, ~30s)
mypy app/ tests/ --ignore-missing-imports

# Solo tests (variable)
pytest tests/ -v

# Archivos modificados solo
black $(git diff --name-only)
flake8 $(git diff --name-only) --max-line-length=100
```

---

## ❌ ERRORES CRÍTICOS (CERO TOLERANCIA)

Estos errores **BLOQUEAN** el commit:

| Error | Descripción | Acción |
|-------|-------------|--------|
| **F821** | Undefined name | Importar o definir variable |
| **F811** | Redefinition of name | Renombrar duplicados |
| **F601** | Dictionary key repeated | Remover key duplicada |
| **E203** | Whitespace before ':' | Black auto-arregla |
| **W291** | Trailing whitespace | Black auto-arregla |
| **F541** | F-string missing placeholder | Corregir formato f-string |

---

## ⚠️ ERRORES PERMITIDOS (Limitados)

| Error | Límite | Acción |
|-------|--------|--------|
| **E501** | Máx 5 por archivo | Intentar reducir, aceptar si inevitable |

---

## 🔧 HERRAMIENTAS INSTALADAS

```bash
# Verificar instalación
pip list | grep -E "black|isort|autoflake|ruff|flake8|pylint|mypy|bandit|pytest"

# Instalar si faltan
pip install -r requirements.txt
```

### Versiones recomendadas
- **black**: 23.0+
- **isort**: 5.0+
- **autoflake**: 2.0+
- **ruff**: 0.1+
- **flake8**: 6.0+
- **pylint**: 3.0+
- **mypy**: 1.0+
- **bandit**: 1.7+
- **pytest**: 7.0+

---

## 📊 EJEMPLO: IMPLEMENTACIÓN EXITOSA

### Paso 1: Escribir código

```python
# app/strategies/my_feature.py
import numpy as np
from app.models import Signal

def my_feature(data: np.ndarray) -> Signal:
    """Calculate my feature."""
    result = np.mean(data)
    return Signal(value=result)
```

### Paso 2: Validar

```bash
$ ./scripts/validate_implementation.sh
```

Output:
```
✔ Black - Formateado completado
✔ Isort - Imports ordenados
✔ Autoflake - Limpieza completada
✔ Ruff - Fixes aplicados
✔ Flake8 - Sin errores críticos
✔ Pylint - Score: 9.2/10 ✓
✔ Mypy - Sin errores de tipo
✔ Bandit - Sin issues de severidad HIGH
✔ Tests - Todos los tests pasaron

✅ IMPLEMENTACIÓN VALIDADA - LISTO PARA COMMIT
```

### Paso 3: Commit

```bash
$ git add -A && git commit -m "feat: add my_feature calculation [TASK-5.1]"
```

---

## 📊 EJEMPLO: IMPLEMENTACIÓN CON ERRORES

### Paso 1: Escribir código (CON ERRORES)

```python
# app/strategies/bad_feature.py
import numpy as np
import pandas as pd  # Sin usar
from app.models import Signal
from app.models import Signal  # Duplicado

def my_feature(data):
    result = np.mean(data)
    # Sin retorno
```

### Paso 2: Validar

```bash
$ ./scripts/validate_implementation.sh
```

Output:
```
✔ Black - Formateado completado
✔ Isort - Imports ordenados
✔ Autoflake - Limpieza completada (eliminó pandas sin usar)
✔ Ruff - Fixes aplicados
✗ Flake8 - 2 errores críticos encontrados:
  - F811: redefinition of 'Signal' from line 3
  - F821: undefined name in function (return statement)
✗ Mypy - Errores de tipo encontrados

❌ VALIDACIÓN FALLIDA - CORREGIR ERRORES ANTES DE COMMIT

Próximos pasos:
  1. Revisar errores arriba
  2. Corregir errores críticos manualmente
  3. Ejecutar: ./scripts/validate_implementation.sh
```

### Paso 3: Corregir

```python
# app/strategies/bad_feature.py
import numpy as np
from app.models import Signal

def my_feature(data: np.ndarray) -> Signal:
    """Calculate feature."""
    result = np.mean(data)
    return Signal(value=result)
```

### Paso 4: Validar de nuevo

```bash
$ ./scripts/validate_implementation.sh
✅ IMPLEMENTACIÓN VALIDADA - LISTO PARA COMMIT
```

---

## 🎯 FLUJO DE TRABAJO COMPLETO

```
┌─────────────────────────────────────────────────────────┐
│ 1. CÓDIGO                                               │
│    - Escribir feature                                   │
│    - Crear tests                                        │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. VALIDACIÓN                                           │
│    ./scripts/validate_implementation.sh                 │
│    ├─ Black: Formatear                                 │
│    ├─ Isort: Ordenar imports                           │
│    ├─ Autoflake: Limpiar                               │
│    ├─ Ruff: Fixes                                      │
│    ├─ Flake8: Lint                                     │
│    ├─ Mypy: Types                                      │
│    ├─ Bandit: Security                                 │
│    └─ Pytest: Tests                                    │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
        ¿Retorna 0?
           /    \
        SI/      \NO
         /        \
        ▼          ▼
    ┌──────┐   ┌──────────┐
    │COMMIT│   │ CORREGIR │ → Volver a paso 2
    └──────┘   └──────────┘
       │
       ▼
   git add -A
   git commit -m "..."
       │
       ▼
   ✅ IMPLEMENTACIÓN EXITOSA
```

---

## 🚀 CI/CD Integration (Futuro)

Cuando se configure GitHub Actions, estos checks se ejecutarán automáticamente en cada PR:

```yaml
# .github/workflows/validate.yml
- name: Validate Implementation
  run: ./scripts/validate_implementation.sh
```

PRs que NO pasen validación serán rechazados automáticamente.

---

## 📞 FAQ

### P: ¿Puedo saltarme los checks?
**R:** No. Son obligatorios. Si hay razones legítimas para excepción, requiere approval explícito.

### P: ¿Qué si Flake8 tiene más de 5 E501?
**R:** Intenta reducir la línea. Si es inevitable (URL larga, regex, etc.), acepta después de revisión manual.

### P: ¿Y si no tengo las herramientas instaladas?
**R:** `pip install -r requirements.txt` las instala todas.

### P: ¿Cuánto tarda validate_implementation.sh?
**R:** ~30-60 segundos en ejecución típica (depende del tamaño del repo).

### P: ¿Puedo hacer commit si validate falla?
**R:** No. El script retorna código de error 1, impidiendo commit automático si lo integras con git hooks.

---

## 📌 RESUMEN

| Acción | Comando | Resultado |
|--------|---------|-----------|
| **Escribir código** | `vim app/...` | Código nuevo |
| **Auto-arreglar** | `./scripts/check_all.sh` | Código limpio |
| **Validar completo** | `./scripts/validate_implementation.sh` | ✅ o ❌ |
| **Si ✅** | `git commit` | Commit exitoso |
| **Si ❌** | Corregir + volver a paso 3 | Hasta ✅ |

---

## 🔗 Referencias

- Archivo de reglas: `.claude-rules.md`
- Script de validación: `scripts/validate_implementation.sh`
- Script de fixes: `scripts/check_all.sh`
- Configuración Black: `pyproject.toml`
- Configuración Isort: `pyproject.toml`

---

*Last Updated: 2025-12-19*
*Mandatory for all implementations on main branch*
