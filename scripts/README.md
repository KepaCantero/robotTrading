# 🐍 Scripts de Auditoría - Índice Maestro

**Fecha:** 2026-02-05
**Propósito:** Automatización de tareas de auditoría de requisitos

---

## 📋 Índice de Scripts

### 🔍 Scripts de Análisis

| Script | Descripción | Salida |
|--------|-------------|--------|
| `list_requirements_files.py` | Lista todos los archivos `.requirements.md` | Lista jerárquica por capas |
| `count_app_files.py` | Cuenta archivos Python en `app/` | Total: 1023 archivos en 196 dirs |
| `find_missing_requirements.py` | Encuentra archivos SIN requisitos | Lista por directorio |
| `audit_requirements_summary.py` | Resumen completo con prioridades | Cobertura %, P0/P1/P2/P3 breakdown |

### 🎯 Scripts Específicos por Prioridad

| Script | Descripción | Archivos Objetivo |
|--------|-------------|---------------------|
| `get_p1_files.py` | Lista archivos P1 sin requisitos | 21 archivos HIGH priority |
| `get_p2_files.py` | Lista archivos P2 sin requisitos | 77 archivos MEDIUM priority |

### ⚙️ Scripts de Generación

| Script | Descripción | Archivos Creados |
|--------|-------------|------------------|
| `generate_p1_requirements.py` | Genera requisitos P1 automáticamente | 34 documentos |
| `generate_p2_requirements.py` | Genera requisitos P2 automáticamente | 100 documentos |

---

## 🚀 Uso Rápido

### Ver estado actual de la auditoría

```bash
python scripts/audit_requirements_summary.py
```

### Encontrar archivos que necesitan requisitos

```bash
# Todos los archivos sin requisitos
python scripts/find_missing_requirements.py

# Solo P1 (alta prioridad)
python scripts/get_p1_files.py

# Solo P2 (media prioridad)
python scripts/get_p2_files.py
```

### Generar requisitos automáticamente

```bash
# Para archivos P1
python scripts/generate_p1_requirements.py

# Para archivos P2
python scripts/generate_p2_requirements.py
```

---

## 📊 Salidas de Scripts

### `list_requirements_files.py`

```
📋 LISTING ALL REQUIREMENTS FILES
✅ TOTAL: 504+ requirements files
```

### `count_app_files.py`

```
🐍 COUNTING PYTHON FILES IN app/
✅ TOTAL: 1023 Python files in 196 directories
```

### `audit_requirements_summary.py`

```
📊 COMPREHENSIVE REQUIREMENTS AUDIT SUMMARY
🔴 P0 - CRITICAL:    59/59  (100.0%)
🟠 P1 - HIGH:        112/112 (100.0%)
🟡 P2 - MEDIUM:      159/159 (100.0%)
🟢 P3 - LOW:         ~100/542 (18.4%)
```

### `get_p1_files.py`

```
📋 P1 (HIGH PRIORITY) FILES WITHOUT REQUIREMENTS: 21
app/backtesting/acceptance/monte_carlo_validator.py
app/backtesting/services/metrics_service.py
...
```

### `generate_p1_requirements.py`

```
📋 GENERATING REQUIREMENTS FOR P1 FILES
✅ Created: 34 requirements documents
❌ Failed:  0 files
```

### `generate_p2_requirements.py`

```
📋 GENERATING REQUIREMENTS FOR P2 FILES
✅ Created: 100 requirements documents
❌ Failed:  0 files
```

---

## 🔧 Mantenimiento de Scripts

### Agregar un nuevo script de análisis

1. Crear el script en `scripts/`
2. Seguir el patrón de los scripts existentes:
   - Usar `pathlib.Path` para operaciones de archivos
   - Retornar resultados estructurados
   - Incluir docstrings descriptivos
   - Manejar errores apropiadamente
3. Agregar entrada a este README

### Agregar un nuevo script de generación

1. Crear el script siguiendo el patrón de `generate_p1_requirements.py`
2. Actualizar este README con la nueva referencia
3. Ejecutar para generar los requisitos correspondientes

---

## 📝 Referencias

- **Template:** `.ralphex/templates/REQUIREMENTS_TEMPLATE_PYTHON.md`
- **BASE_RULES:** `.requirements/BASE_RULES.md`
- **Task Definition:** `.ralphex/tasks/audit_and_fix_codebase.md`
- **Summary:** `.ralphex/tasks/AUDIT_SUMMARY.md`

---

## 🎯 Estado Actual (2026-02-05)

- ✅ **P0 (CRITICAL):** 59/59 archivos - 100%
- ✅ **P1 (HIGH):** 112/112 archivos - 100%
- ✅ **P2 (MEDIUM):** 159/159 archivos - 100%
- ⏳ **P3 (LOW):** ~100/542 archivos - 18%

**Total crítico (P0+P1+P2): 330/330 - 100%**

---

*Última actualización: 2026-02-05*
