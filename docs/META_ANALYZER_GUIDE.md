# 📊 Meta Analyzer - Guía de Uso Completa

**Última actualización:** 2025-10-31

---

## 🎯 Visión General

El módulo `meta_analyzer` proporciona capacidades avanzadas para:

1. **Análisis metacognitivo** de resultados de múltiples backtests
2. **Auditoría completa** y reproducibilidad de ejecuciones
3. **Persistencia de modelos** para aprendizaje incremental
4. **Ejecución paralela** eficiente de análisis masivos

---

## 📦 Componentes

### 1. BacktestMetaAnalyzer

Analizador principal para descubrir patrones en resultados de backtests.

### 2. AuditTrail

Sistema de auditoría para garantizar reproducibilidad.

### 3. LearningEngineStorage

Almacenamiento de pesos de modelos para aprendizaje incremental.

---

## 🚀 Uso Básico

### Análisis de Resultados

```python
import asyncio
from app.backtesting.meta_analyzer import BacktestMetaAnalyzer

async def main():
    # Crear analizador
    analyzer = BacktestMetaAnalyzer(
        data_dir="reports/comprehensive_backtest",
        output_dir="reports/meta"
    )

    # Cargar resultados
    await analyzer.load_results()

    # Análisis completo en paralelo
    results = await analyzer.run_parallel_analysis(
        max_workers=4,
        include_clustering=True,
        n_clusters=3
    )

    # Exportar reporte
    analyzer.export_report(format="json")

    # Sugerencias de combinaciones óptimas
    suggestions = analyzer.suggest_optimal_combinations(top_n=10)
    print(f"Top 10 combinaciones: {suggestions}")

asyncio.run(main())
```

### Auditoría y Reproducibilidad

```python
from app.backtesting.meta_analyzer import AuditTrail

# Crear auditoría
audit = AuditTrail(log_file="logs/audit_log.jsonl")

# Generar hash único por configuración
hash_value = audit.generate_hash("config/backtesting/comprehensive_backtest.yaml")

# Guardar registro de ejecución
await audit.save_audit_record(
    config_path="config/backtesting/comprehensive_backtest.yaml",
    hash_value=hash_value,
    metadata={"test_type": "baseline", "duration_seconds": 120},
    result_path="reports/comprehensive_backtest/baseline_results.json"
)

# Verificar reproducibilidad
verification = audit.verify_reproducibility(hash_value)
if verification['reproducible']:
    print("✅ La ejecución es reproducible")
else:
    print("⚠️ No es reproducible:", verification['reason'])

# Listar registros
records = audit.list_audit_records(limit=10)
```

### Persistencia de Modelos

```python
from app.backtesting.meta_analyzer import LearningEngineStorage
import torch

# Crear almacenamiento
storage = LearningEngineStorage(base_dir="models/learning_engines")

# Guardar pesos de un modelo
model = ...  # Tu modelo entrenado
test_id = "baseline_20231031"

storage.save_weights(
    engine_name="supervised",
    weights=model,
    test_id=test_id,
    metadata={
        "accuracy": 0.85,
        "sharpe_ratio": 1.2,
        "training_epochs": 50
    }
)

# Cargar pesos más recientes
data = storage.load_weights(engine_name="supervised", latest=True)
model.load_state_dict(data['weights'])

# Listar pesos disponibles
weights_list = storage.list_available_weights("supervised")
for weight_info in weights_list:
    print(f"Test: {weight_info['test_id']}, Fecha: {weight_info['modified']}")
```

---

## 🔗 Integración con ComprehensiveBacktestRunner

### Uso Integrado

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.meta_analyzer import integrate_meta_analyzer_with_runner
import asyncio

async def run_with_meta_analysis():
    # Crear runner
    runner = ComprehensiveBacktestRunner("config/backtesting/comprehensive_backtest.yaml")

    # Integrar meta_analyzer
    meta = integrate_meta_analyzer_with_runner(
        runner=runner,
        config_path="config/backtesting/comprehensive_backtest.yaml",
        enable_audit=True,
        enable_storage=True,
        enable_analysis=True
    )

    # Guardar hash en runner para usar después
    runner.audit_hash = meta['audit_hash']
    runner.config_path = "config/backtesting/comprehensive_backtest.yaml"

    # Ejecutar backtests
    runner.run_all()

    # Después de ejecutar, analizar resultados
    if meta['analyzer']:
        await meta['analyzer'].load_results()
        results = await meta['analyzer'].run_parallel_analysis()
        meta['analyzer'].export_report()

asyncio.run(run_with_meta_analysis())
```

---

## 📊 Análisis Avanzado

### Detección de Clusters

```python
analyzer = BacktestMetaAnalyzer("reports/comprehensive_backtest")
await analyzer.load_results()

# Detectar 5 clusters basados en Sharpe, PnL, Drawdown
clusters = analyzer.detect_clusters(
    n_clusters=5,
    features=['sharpe_ratio', 'total_pnl', 'max_drawdown', 'win_rate']
)

# Ver características de cada cluster
for cluster_name, cluster_info in clusters['clusters'].items():
    print(f"\n{cluster_name}:")
    print(f"  Tamaño: {cluster_info['size']}")
    print(f"  Sharpe medio: {cluster_info['characteristics']['sharpe_ratio']['mean']:.2f}")
```

### Sugerencias Personalizadas

```python
# Sugerencias con criterios personalizados
suggestions = analyzer.suggest_optimal_combinations(
    top_n=5,
    criteria={
        'sharpe_ratio': 0.5,      # Alto peso a Sharpe
        'total_pnl': 0.3,          # PnL importante
        'win_rate': 0.15,          # Win rate moderado
        'max_drawdown': -0.05      # Penalizar drawdown
    }
)

for i, suggestion in enumerate(suggestions, 1):
    print(f"\n{i}. Test: {suggestion.get('test_type')}")
    print(f"   Sharpe: {suggestion.get('sharpe_ratio', 0):.2f}")
    print(f"   PnL: ${suggestion.get('total_pnl', 0):,.2f}")
```

### Análisis por Régimen de Mercado

```python
# Filtrar resultados por régimen
df = analyzer.df_results

# Análisis por tipo de test
if 'test_type' in df.columns:
    regime_analysis = df.groupby('test_type').agg({
        'sharpe_ratio': ['mean', 'std'],
        'total_pnl': ['mean', 'std'],
        'max_drawdown': ['mean', 'min']
    })
    print(regime_analysis)
```

---

## 🔄 Ejecución Paralela

### Análisis Masivo de Resultados

```python
# Ejecutar análisis completo en paralelo
results = await analyzer.run_parallel_analysis(
    max_workers=8,              # 8 workers para CPU-bound tasks
    include_clustering=True,    # Incluir detección de clusters
    n_clusters=4                # 4 clusters
)

# Resultados incluyen:
# - results['performance']: Análisis de rendimiento
# - results['clustering']: Clusters detectados
# - results['suggestions']: Top 10 combinaciones
```

---

## 📝 Formato de Datos

### Estructura Esperada de Resultados JSON

```json
{
  "test_type": "baseline",
  "total_pnl": 46559.1,
  "return_pct": 46.56,
  "sharpe_ratio": 1.85,
  "sortino_ratio": 2.1,
  "max_drawdown": -0.15,
  "win_rate": 0.65,
  "total_trades": 19,
  "avg_trade_pnl": 2450.48,
  "profit_factor": 1.8,
  "calmar_ratio": 3.1,
  "strategy_name": "momentum_modular",
  "learning_engine": null
}
```

---

## 🛠️ API Completa

### BacktestMetaAnalyzer

#### Métodos Principales

- `load_results(path=None)`: Cargar resultados desde directorio
- `analyze_performance()`: Analizar rendimiento agregado
- `detect_clusters(n_clusters=3, features=None)`: Detectar clusters
- `suggest_optimal_combinations(top_n=10, criteria=None)`: Sugerir combinaciones
- `export_report(output_path=None, format="json")`: Exportar reporte
- `run_parallel_analysis(max_workers=4, include_clustering=True, n_clusters=3)`: Análisis paralelo

### AuditTrail

#### Métodos Principales

- `generate_hash(config_path, code_version=None, additional_data=None)`: Generar hash
- `save_audit_record(config_path, hash_value, metadata=None, result_path=None)`: Guardar registro (async)
- `save_audit_record_sync(...)`: Guardar registro (sync)
- `verify_reproducibility(target_hash)`: Verificar reproducibilidad
- `list_audit_records(limit=None, filter_by_config=None)`: Listar registros

### LearningEngineStorage

#### Métodos Principales

- `save_weights(engine_name, weights, test_id, metadata=None, format=None)`: Guardar pesos
- `save_weights_async(...)`: Guardar pesos (async)
- `load_weights(engine_name, test_id=None, latest=True)`: Cargar pesos
- `list_available_weights(engine_name, test_id_filter=None)`: Listar pesos
- `delete_weights(engine_name, test_id=None, keep_latest=True)`: Eliminar pesos

---

## 📁 Estructura de Directorios

```
models/
└── learning_engines/
    ├── supervised/
    │   ├── baseline_20231031_120000.pt
    │   └── baseline_20231031_120000.metadata.json
    ├── deep/
    │   └── walk_forward_20231031_130000.pt
    └── transformer/
        └── optimization_20231031_140000.pt

logs/
└── audit_log.jsonl

reports/
└── meta/
    ├── meta_analysis_20231031_150000.json
    ├── sharpe_distribution.png
    ├── sharpe_vs_pnl.png
    └── correlation_heatmap.png
```

---

## ⚙️ Configuración

### Dependencias Opcionales

- **scikit-learn**: Para clustering (KMeans)
- **matplotlib/seaborn**: Para visualizaciones
- **aiofiles**: Para I/O asíncrono (opcional, tiene fallback)
- **torch**: Para guardar modelos PyTorch

### Instalación

```bash
# Dependencias básicas (ya incluidas en requirements.txt)
pip install pandas numpy scikit-learn matplotlib seaborn

# Dependencia opcional para I/O asíncrono mejorado
pip install aiofiles
```

---

## 🔍 Ejemplos de Casos de Uso

### Caso 1: Análisis Post-Ejecución

Después de ejecutar múltiples backtests, analizar qué funcionó mejor:

```python
analyzer = BacktestMetaAnalyzer("reports/comprehensive_backtest")
await analyzer.load_results()

# Análisis completo
performance = analyzer.analyze_performance()
clusters = analyzer.detect_clusters(n_clusters=4)
suggestions = analyzer.suggest_optimal_combinations(top_n=5)

# Ver mejores resultados
print("Mejores por Sharpe:")
for result in performance['best_performers']['by_sharpe'][:5]:
    print(f"  {result['test_type']}: Sharpe={result['sharpe_ratio']:.2f}")

# Exportar
analyzer.export_report(format="json")
```

### Caso 2: Reproducir Ejecución Pasada

Usar auditoría para reproducir exactamente una ejecución anterior:

```python
audit = AuditTrail()

# Hash conocido de ejecución anterior
target_hash = "abc123..."

# Verificar reproducibilidad
verification = audit.verify_reproducibility(target_hash)

if verification['reproducible']:
    # Cargar configuración
    config_path = verification['config_path']

    # Ejecutar con esa configuración
    runner = ComprehensiveBacktestRunner(config_path)
    runner.run_all()

    print("✅ Ejecución reproducida exitosamente")
else:
    print("⚠️ No se puede reproducir:", verification['reason'])
```

### Caso 3: Aprendizaje Incremental

Continuar entrenando un modelo desde pesos guardados:

```python
storage = LearningEngineStorage()

# Cargar pesos del último entrenamiento
data = storage.load_weights("supervised", latest=True)
model.load_state_dict(data['weights'])

# Continuar entrenamiento con nuevos datos
# ... entrenamiento adicional ...

# Guardar nuevos pesos
storage.save_weights(
    engine_name="supervised",
    weights=model.state_dict(),
    test_id="incremental_20231031",
    metadata={"previous_test_id": data['test_id']}
)
```

---

## 🎯 Mejores Prácticas

1. **Auditoría**: Siempre habilita auditoría en producción para reproducibilidad
2. **Storage**: Guarda pesos después de cada entrenamiento importante
3. **Análisis**: Ejecuta análisis meta después de suites completas de backtests
4. **Paralelización**: Usa `run_parallel_analysis()` para análisis masivos
5. **Visualizaciones**: Revisa gráficos generados para insights cualitativos

---

**Fin del Documento**
