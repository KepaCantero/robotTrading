# Task 24: Análisis de Problemas - 24_structural_fix.yml

**Fecha:** 2025-02-25
**Archivo:** `.ralph/ralph_tasks/24_structural_fix.yml`
**Estado:** REQUIERE CORRECCIONES

---

## PROBLEMAS IDENTIFICADOS

### CRITICOS (P0)

#### 1. Evento `srp_fixer` usa variables Python inexistentes
- **Ubicacion:** Linea 1096-1097
- **Problema:** `${len(extracted_classes)}` y `${len(files_content)}` son variables Python, no disponibles en contexto bash del evento
- **Impacto:** El evento fallara al ejecutarse
- **Solucion:** Leer valores desde archivo JSON generado

```yaml
# ACTUAL (INCORRECTO):
ralph emit "structural_fix.srp_fixed" "classes=${len(extracted_classes)}, files=${len(files_content)}"

# CORREGIDO:
ralph emit "structural_fix.srp_fixed" "status=complete"
```

#### 2. Evento `final_reporter` usa variable no definida
- **Ubicacion:** Linea 1229
- **Problema:** `${new_score}` no existe en contexto bash
- **Impacto:** El evento fallara
- **Solucion:** Leer desde STRUCTURAL_AUDIT_FINAL_REPORT.json

#### 3. Final reporter busca archivo incorrecto
- **Ubicacion:** Linea 1152
- **Problema:** Busca `SRP_REFACTOR_PLAN.json` pero srp_fixer genera `SRP_FIXED.json`
- **Impacto:** No se cargaran los resultados SRP
- **Solucion:** Cambiar a `SRP_FIXED.json`

### ALTOS (P1)

#### 4. Deteccion de duplicados por tamanho es imprecisa
- **Ubicacion:** Lineas 146-152
- **Problema:** Dos archivos con mismo tamanho NO son necesariamente identicos
- **Impacto:** Puede eliminar archivos diferentes que coinciden en tamanho
- **Solucion:** Agregar verificacion de hash MD5

#### 5. Falta clase `SectorCountryDiversificationConfig` en extraccion
- **Ubicacion:** __init__.py template (lineas 999-1013)
- **Problema:** Se importa pero no esta en lista de clases a extraer
- **Impacto:** Import error al ejecutar
- **Solucion:** Agregar a risk_config.py o quitar del __init__.py

#### 6. `CommissionModel` y subclases no se re-exportan
- **Ubicacion:** __init__.py template
- **Problema:** `CommissionModel`, `FixedCommission`, `TieredCommission`, `HybridCommission`, `TierBracket` no estan en __all__
- **Impacto:** Imports rotos para usuarios de estas clases
- **Solucion:** Agregar a __all__

#### 7. Falta codigo de extraccion para compliance_engine.py
- **Ubicacion:** Prompt menciona compliance_engine.py como prioritario
- **Problema:** No hay hat ni codigo para extraer sus clases
- **Impacto:** No se refactorizara compliance_engine.py
- **Solucion:** Agregar `compliance_extractor` hat

### MEDIOS (P2)

#### 8. Imports incompletos en new_content_lines
- **Ubicacion:** Lineas 1020-1057
- **Problema:** Faltan imports como `from pydantic import BaseModel, Field, validator`
- **Impacto:** centralized_config.py puede tener imports incompletos
- **Solucion:** Preservar imports originales o agregar los necesarios

#### 9. Falta validacion post-extraccion
- **Ubicacion:** Despues de srp_fixer
- **Problema:** No hay verificacion de que los imports siguen funcionando
- **Impacto:** Puede haber imports rotos silenciosamente
- **Solucion:** Agregar hat `import_validator`

#### 10. Import de `MarketMicrostructureThresholds` puede fallar
- **Ubicacion:** Linea 1046
- **Problema:** Importa de `signal_risk` que puede no existir
- **Impacto:** Error al generar nuevo centralized_config.py
- **Solucion:** Verificar existencia o hacer condicional

---

## PLAN DE CORRECCION

### Fase 1: Corregir eventos (P0)
1. [ ] Cambiar evento srp_fixer a usar archivo JSON
2. [ ] Cambiar evento final_reporter a usar archivo JSON
3. [ ] Corregir busqueda de SRP_FIXED.json

### Fase 2: Mejorar deteccion (P1)
4. [ ] Agregar verificacion MD5 a deteccion de duplicados
5. [ ] Agregar SectorCountryDiversificationConfig a clases a extraer
6. [ ] Agregar CommissionModel y subclases a __init__.py
7. [ ] Crear hat compliance_extractor

### Fase 3: Robustecer (P2)
8. [ ] Preservar imports originales en new_content_lines
9. [ ] Agregar hat import_validator post-extraccion
10. [ ] Hacer condicional import de signal_risk

---

## ARCHIVOS A MODIFICAR

1. `.ralph/ralph_tasks/24_structural_fix.yml` - Correcciones principales
2. `.ralph/ralph_tasks/prompts/24_structural_fix.md` - Actualizar segun cambios

---

## SIGUIENTE PASO

Entrar en **PLAN MODE** para diseñar la implementacion de estas correcciones antes de modificar el archivo.
