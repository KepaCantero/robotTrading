# TAREA: Auditoría GAP Automatizada con Ralph Orchestrator

## OBJETIVO

Ejecutar auditoría completa de 772 archivos Python con `Audit Status: NEEDS_AUDIT`, procesarlos en batches optimizados, y marcar como `PASSED` tras verificar cumplimiento de BASE_RULES.md.

---

## FASE 0: PREREQUISITOS ✅ COMPLETADO

- [x] Verificar templates existentes en `.claude/templates/gap/`
- [x] Verificar BASE_RULES.md (443 lines, 35 sections)
- [x] Instalar herramientas: mypy, ruff, pytest, bandit, radon, rich
- [x] Confirmar git clean state
- [x] Crear directorios: .gap_reports, .gap_backups, .ralph

---

## FASE 1: PREPARAR BATCHES ✅ COMPLETADO

### Ejecutar: `python scripts/prepare_batches_optimized.py`

**Output generado:**
- Total archivos: 772
- Total batches: 166 (sin duplicados)
- Archivo: `.ralph/batches.json` (ya creado)

**Distribución por capa:**
| Capa | Archivos |
|------|----------|
| 1_Core | 27 |
| 2_Database | 2 |
| 3_Domain_Entities | 8 |
| 4_Domain_Services | 4 |
| 5_Domain_Strategies | 9 |
| 6_Application | 10 |
| 7_Backtesting | 114 |
| 8_Strategies | 64 |
| 9_Analysis | 5 |
| 10_Microstructure | 15 |
| 11_API | 15 |
| 12_Middleware | 3 |
| 13_Presentation | 22 |
| 14_Others | 489 |

---

## FASE 2: CONFIGURAR RALPH ORCHESTRATOR ✅ COMPLETADO

### Archivo: `.ralph/config.yaml`

Configuración cargada:
- Model: glm-4.7 (200K context, 128K max output)
- Max concurrent: 3
- Timeout: 30 min por batch
- Checkpointing habilitado
- Dashboard en puerto 8080
- Tiempo estimado: 2824 minutos (~47 horas)

---

## FASE 3: SCRIPTS DE APOYO ✅ COMPLETADO

### Scripts creados:

1. **`scripts/validate_file_comprehensive.sh`**
   - Ejecuta: mypy, ruff, bandit, radon, syntax check
   - Genera reporte markdown en `.gap_reports/`

2. **`scripts/live_dashboard.py`**
   - Monitoreo en tiempo real
   - Ejecutar: `python scripts/live_dashboard.py`

3. **`scripts/handle_blocked_files.py`**
   - Analiza archivos bloqueados
   - Detecta circular dependencies
   - Intenta auto-fix cuando posible

---

## FASE 4: EJECUTAR AUDITORÍA

### Instrucciones para Ralph Orchestrator:

Para cada batch en `.ralph/batches.json` (ya creado):

```
PARA CADA ARCHIVO EN BATCH:
  1. LEER: .requirements/app/path/file.py.requirements.md
  2. LEER: app/path/file.py
  3. LEER: .requirements/BASE_RULES.md

  4. ENCONTRAR: sección "Critical Rules" en .requirements.md
  5. PARA CADA REGLA en Critical Rules:
      - Leer qué exige la regla
      - Buscar en código si se cumple
      - Si hay violación (❌ GAP):
          a. Documentar violación
          b. Fixear código (cambio mínimo)
          c. Verificar que no rompe nada

  6. CUANDO TODAS LAS REGLAS OK:
      - Actualizar: "Audit Status: NEEDS_AUDIT" → "PASSED"
      - Actualizar timestamp: 2026-02-07T{hora}Z
      - Guardar .requirements.md

  7. VALIDAR con: scripts/validate_file_comprehensive.sh

  8. SI FALLA VALIDACIÓN:
      - Revertir cambios
      - Marcar como BLOCKED
      - Documentar razón
```

### Formato Audit Status en .requirements.md:

```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T10:30:00Z |
| **Audit Status** | PASSED |
```

---

## FASE 5: POST-PROCESAMIENTO

### Al finalizar todos los batches:

1. **Generar reporte final:**
   ```bash
   python scripts/generate_final_report.py
   ```

2. **Verificar checkpoint:**
   ```bash
   python scripts/checkpoint_tracker.py status all
   ```

3. **Commitear cambios:**
   ```bash
   git add -A
   git commit -m "feat: complete GAP audit - 772 files PASSED"
   ```

---

## ORDEN DE EJECUCIÓN

Procesar batches en orden numérico (batch_0001 → batch_0166):

1. **batch_0001 - batch_0010**: 1_Core (small/medium)
2. **batch_0011 - batch_0040**: 3_Domain_Entities, 4_Domain_Services
3. **batch_0041 - batch_0080**: 7_Backtesting
4. **batch_0081 - batch_0120**: 8_Strategies
5. **batch_0121 - batch_0166**: Resto de capas

---

## MÉTRICAS DE ÉXITO

- [ ] 772 archivos procesados
- [ ] 100% Audit Status: PASSED
- [ ] 0 archivos BLOCKED
- [ ] 0 violaciones GAP pendientes
- [ ] Todos los tests pasan
- [ ] mypy clean (0 errores)
- [ ] bandit clean (0 issues HIGH)

---

## NOTAS

- Cada batch debe procesarse secuencialmente dentro del batch
- Batches pueden procesarse en paralelo (max 3 concurrentes)
- Guardar checkpoint después de cada 5 archivos
- Dashboard muestra progreso en tiempo real
- Archivos bloqueados se manejan con `handle_blocked_files.py`
