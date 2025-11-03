# 🎯 Condiciones de Ejecución: Learning Engines Tests

## ⚙️ Configuración Actual

```yaml
backtests:
  learning_engines:
    enabled: true
    use_multi_strategy: true # ← ESTO ES CLAVE
```

---

## 📊 ¿Cómo se Ejecutan?

### Si `use_multi_strategy: true` (configuración actual):

1. **PRIMERO**: Ejecuta un baseline **Multi-Strategy** (sin learning engines)

   - Nombre del test: `"Learning Engines - Multi-Strategy (Baseline)"`
   - Tipo: `learning_engine_multi_strategy`
   - Estrategias: momentum + mean_reversion + pairs_trading simultáneamente
   - Sin learning engines

2. **DESPUÉS**: Para cada learning engine (supervised, deep, reinforcement, transformer):
   - Ejecuta baseline con **Simple Strategy** (ModularMomentumStrategy sin learning engine)
   - Entrena el learning engine
   - Ejecuta backtest con **Simple Strategy** (ModularMomentumStrategy CON learning engine)
   - Compara métricas antes/después

### Si `use_multi_strategy: false`:

- Solo ejecuta tests con **Simple Strategy** (ModularMomentumStrategy individual)
- NO ejecuta baseline Multi-Strategy

---

## ✅ Respuesta Directa

**Los tests que ves en el dashboard** (`Learning Engine - supervised`, `Learning Engine - deep`, `Learning Engine - reinforcement`) se ejecutan con:

### **Simple Strategy** (ModularMomentumStrategy individual)

**NO** se ejecutan con Multi-Strategy.

---

## 🔍 Detalles Técnicos

### Código relevante (líneas 546-619):

```python
# Probar cada learning engine con estrategia modular
for learning_engine in learning_engines_to_test:
    # ...

    # Crear estrategia SIN learning engine (baseline)
    baseline_strategy = ModularMomentumStrategy(baseline_strategy_config)

    # Usa SimpleBacktester (NO MultiStrategyBacktester)
    baseline_backtester = SimpleBacktester(
        config=backtest_config,
        strategy=baseline_strategy,
        strategy_name=baseline_strategy_name
    )

    # ... después del entrenamiento ...

    # También usa SimpleBacktester (NO MultiStrategyBacktester)
    backtester = SimpleBacktester(
        config=backtest_config,
        strategy=strategy,  # ModularMomentumStrategy CON learning engine
        strategy_name=strategy_name
    )
```

### ¿Dónde está el Multi-Strategy?

El Multi-Strategy solo se ejecuta **una vez al inicio** (si `use_multi_strategy: true`) como baseline de comparación, pero **NO se usa para los tests individuales de learning engines**.

---

## 📋 Resumen

| Test                                           | Tipo de Estrategia  | Backtester Usado          |
| ---------------------------------------------- | ------------------- | ------------------------- |
| `Learning Engine - supervised`                 | **Simple Strategy** | `SimpleBacktester`        |
| `Learning Engine - deep`                       | **Simple Strategy** | `SimpleBacktester`        |
| `Learning Engine - reinforcement`              | **Simple Strategy** | `SimpleBacktester`        |
| `Learning Engine - transformer`                | **Simple Strategy** | `SimpleBacktester`        |
| `Learning Engines - Multi-Strategy (Baseline)` | **Multi-Strategy**  | `MultiStrategyBacktester` |

---

## 💡 Nota sobre Walk-Forward

El test "Walk Forward" que mencionas en el dashboard es un test **separado** (`walk_forward`), no parte de `learning_engines`.

Walk-Forward:

- Puede usar learning engine (configurado en `walk_forward.learning_engine`)
- Se ejecuta con **Simple Strategy** (`ModularMomentumStrategy`)
- Divide datos en ventanas temporales (70% train, 30% test)

---

## 🔧 Para Cambiar Comportamiento

Si quieres que los learning engines se ejecuten con Multi-Strategy, necesitarías modificar el código en `run_learning_engines_backtest()` para usar `MultiStrategyBacktester` en lugar de `SimpleBacktester`.

Actualmente, el código usa **Simple Strategy** para todos los tests individuales de learning engines.
