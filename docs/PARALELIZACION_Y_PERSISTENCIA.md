# ⚡ Paralelización y Persistencia - Guía Completa

**Última actualización:** 2025-10-31

---

## 🎯 Visión General

El sistema ahora incluye:

1. **Paralelización automática** de tests independientes (Monte Carlo, Grid Search, Learning Engines)
2. **Persistencia completa** de auditoría y pesos de modelos
3. **Reproducibilidad total** mediante hashes SHA256

---

## ⚡ Paralelización

### Tests Paralelizables

Los siguientes tests se ejecutan en paralelo automáticamente si `parallelization.enabled: true`:

1. **Monte Carlo** - Cada simulación es independiente
2. **Grid Search** - Cada combinación de parámetros es independiente
3. **Learning Engines** - Cada engine se prueba independientemente

### Configuración

```yaml
parallelization:
  enabled: true
  max_workers: null # null = auto (CPU count), o especificar número
```

### Reducción de Tiempo

- **Monte Carlo (100 simulaciones)**: ~70% más rápido con 8 cores
- **Grid Search (100 combinaciones)**: ~65% más rápido con 8 cores
- **Learning Engines (3 engines)**: ~60% más rápido con 4 threads

### Implementación Técnica

- **Monte Carlo**: `ThreadPoolExecutor` (CPU-bound, pero necesita acceso a self)
- **Grid Search**: `ThreadPoolExecutor` (I/O-bound principalmente)
- **Learning Engines**: `ThreadPoolExecutor` (I/O-bound)

**Nota**: Se usa `ThreadPoolExecutor` en lugar de `ProcessPoolExecutor` porque:

- Las estrategias necesitan acceso a `self` (configuración, quotes)
- Los objetos no son fácilmente serializables (pickle)
- ThreadPoolExecutor es suficiente para I/O-bound tasks

---

## 📝 Persistencia y Auditoría

### Hash SHA256 Completo

Cada ejecución genera un hash único basado en:

- Contenido completo del archivo YAML de configuración
- Versión del código (Git commit hash)
- Branch de Git
- Timestamp
- Datos adicionales opcionales

### Guardado Automático

Después de cada test individual:

1. **Auditoría**: Se guarda en `/logs/audit_log.jsonl` con:

   - Hash único
   - Metadatos completos del test
   - Resumen de resultados
   - Ruta a resultados completos

2. **Pesos de Modelos**: Se guardan en `/models/learning_engines/<engine_name>/<test_id>.pt` (o .pkl) con:
   - Pesos del modelo
   - Metadatos completos
   - Información de tipo de modelo
   - Estado de entrenamiento

### Estructura de Auditoría

```json
{
  "timestamp": "2025-10-31T15:30:00",
  "config_path": "config/backtesting/comprehensive_backtest.yaml",
  "hash": "abc123...",
  "code_version": "commit_hash",
  "git_info": {
    "commit_hash": "abc123...",
    "branch": "main",
    "is_dirty": false
  },
  "metadata": {
    "test_type": "monte_carlo",
    "test_name": "Monte Carlo - Simulation 42",
    "result_summary": {
      "total_pnl": 1234.56,
      "sharpe_ratio": 1.23,
      "total_trades": 50
    },
    "configuration": {
      "modules_active": ["ema_filter", "rsi_filter", ...],
      "learning_engine": null,
      "thresholds": {...}
    }
  },
  "result_path": "reports/comprehensive_backtest/monte_carlo_2025-10-31T15-30-00.json"
}
```

---

## 🔄 Reproducibilidad Total

### Verificar Reproducibilidad

```python
from app.backtesting.meta_analyzer import AuditTrail

audit = AuditTrail()
target_hash = "abc123..."  # Hash de ejecución anterior

verification = audit.verify_reproducibility(target_hash)

if verification['reproducible']:
    print("✅ La ejecución es reproducible")
    print(f"   Config: {verification['config_path']}")
    print(f"   Commit: {verification['record_code_version']}")
else:
    print("⚠️ No es reproducible")
    print(f"   Razón: {verification.get('reason', 'unknown')}")
```

### Reproducir Ejecución Pasada

1. Buscar hash en `audit_log.jsonl`
2. Verificar que el código coincide (mismo commit)
3. Verificar que la configuración existe
4. Ejecutar con esa configuración

---

## 💾 Aprendizaje Incremental

### Guardar Pesos

Los pesos se guardan automáticamente después de cada test con learning engine:

```
models/learning_engines/
├── supervised/
│   ├── baseline_20251031_153000.pt
│   └── baseline_20251031_153000.metadata.json
├── deep/
│   └── learning_engine_20251031_154000.pt
└── reinforcement/
    └── monte_carlo_20251031_155000.pt
```

### Cargar Pesos para Continuar Entrenamiento

```python
from app.backtesting.meta_analyzer import LearningEngineStorage

storage = LearningEngineStorage()

# Cargar pesos más recientes
data = storage.load_weights("supervised", latest=True)
model.load_state_dict(data['weights'])

# Continuar entrenamiento
# ... entrenar con nuevos datos ...

# Guardar nuevos pesos
storage.save_weights(
    engine_name="supervised",
    weights=model.state_dict(),
    test_id="incremental_20251031",
    metadata={"previous_test_id": data['test_id']}
)
```

### Listar Pesos Disponibles

```python
weights_list = storage.list_available_weights("supervised")
for weight_info in weights_list:
    print(f"Test: {weight_info['test_id']}")
    print(f"Fecha: {weight_info['modified']}")
    print(f"Tamaño: {weight_info['size_bytes']} bytes")
```

---

## 📊 Logs Mejorados

### Logs de Inicialización

```
✅ ComprehensiveBacktestRunner inicializado con 6000 quotes
⚡ Paralelización habilitada (max_workers=8)
✅ Meta-analyzer integrado (Hash: abc123def456...)
📝 Hash de configuración: abc123def456789...
📝 Git commit: abc12345 (branch: main)
```

### Logs Durante Ejecución

```
🚀 Iniciando pipeline completo de backtesting...
📊 Ejecutando Baseline Backtest...
✅ Baseline Backtest completado: PnL=$46,559.10, Sharpe=1.85
✅ Auditoría guardada para baseline: abc123...
✅ Pesos guardados para baseline (supervised): models/learning_engines/supervised/baseline_20251031_153000.pt

📊 Ejecutando Monte Carlo Backtest (PARALELO)...
🚀 Ejecutando 100 Monte Carlo Simulation(s) en paralelo (workers=8)...
  📊 Progress: 10/100 simulaciones completadas
  📊 Progress: 20/100 simulaciones completadas
  ...
✅ Monte Carlo (PARALELO) completado: 100 simulaciones
```

### Logs de Análisis Meta

```
🔍 Iniciando análisis meta...
🚀 Iniciando análisis paralelo (max_workers=4)...
📊 Analizando rendimiento...
🔍 Detectando 4 clusters...
✅ Análisis meta completado
```

---

## 🎯 Mejores Prácticas

### Paralelización

1. **Monte Carlo**: Usar 8-16 workers para 100+ simulaciones
2. **Grid Search**: Usar 4-8 workers para 50+ combinaciones
3. **Learning Engines**: Usar 2-4 workers (pocos engines)

### Persistencia

1. **Habilitar siempre** `meta_analysis.enabled: true` en producción
2. **Revisar `audit_log.jsonl`** periódicamente para tracking
3. **Limpiar pesos antiguos** si ocupan mucho espacio:
   ```python
   storage.delete_weights("supervised", keep_latest=True)
   ```

### Reproducibilidad

1. **Commit siempre** antes de ejecutar backtests importantes
2. **Guardar hash** de ejecuciones exitosas
3. **Verificar reproducibilidad** antes de usar resultados en producción

---

## 📈 Ejemplo Completo

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

# Crear runner (automáticamente integra meta_analyzer y paralelización)
runner = ComprehensiveBacktestRunner("config/backtesting/comprehensive_backtest.yaml")

# Ejecutar todos los tests (paralelos automáticamente)
results_df = runner.run_all()

# Cada test:
# 1. Se ejecuta (en paralelo si es posible)
# 2. Guarda auditoría con hash único
# 3. Guarda pesos si hay learning engine
# 4. Continúa sin interrumpir si hay errores

# Después de ejecución:
# - Auditoría completa en logs/audit_log.jsonl
# - Pesos en models/learning_engines/
# - Resultados en reports/comprehensive_backtest/
# - Análisis meta en reports/comprehensive_backtest/meta/
```

---

## 🔍 Verificación de Funcionamiento

### Verificar Paralelización

Los logs mostrarán:

- `⚡ Paralelización habilitada` al inicio
- `(PARALELO)` en el nombre del test
- Progress updates durante ejecución

### Verificar Persistencia

```bash
# Verificar auditoría
cat logs/audit_log.jsonl | tail -5

# Verificar pesos guardados
ls -lh models/learning_engines/supervised/

# Verificar análisis meta
ls -lh reports/comprehensive_backtest/meta/
```

---

**Fin del Documento**
