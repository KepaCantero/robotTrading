# Integration Tests with Real Data

Este directorio contiene tests de integración que usan datos reales de `data/historical/` para verificar el funcionamiento completo del sistema.

## Tests Disponibles

### 1. `test_allocator_integration.py`

Test standalone que verifica:

- Carga de datos CSV reales
- Funcionamiento del `StrategyStockAllocator`
- Asignación de capital y validación
- Utilización de capital y calidad de asignaciones

**Ejecutar:**

```bash
python tests/integration/test_allocator_integration.py
```

### 2. `test_strategy_stock_allocator_integration.py`

Tests con pytest que verifican:

- Carga de datos históricos reales
- Filtrado de stocks
- Asignación de capital
- Creación de portfolio
- Utilización mínima de tickers

**Ejecutar:**

```bash
pytest tests/integration/test_strategy_stock_allocator_integration.py -v -s
```

### 3. `test_signal_generation_integration.py`

Tests de generación de señales con datos reales:
 
**TEST 1: Multi-Strategy Portfolio**

- Portfolio con las 3 estrategias (Momentum 60%, Mean Reversion 25%, Pairs Trading 15%)
- Generación de señales para cada estrategia según asignación

**TEST 2: Momentum-Only Portfolio**

- Selección de los mejores 10 assets para momentum
- Generación de señales solo para momentum

**TEST 3: Mean Reversion-Only Portfolio**

- Selección de los mejores 10 assets para mean reversion
- Generación de señales solo para mean reversion

**TEST 4: Pairs Trading-Only Portfolio**

- Selección de los mejores 5 pares cointegrados
- Generación de señales solo para pairs trading

**Ejecutar:**

```bash
pytest tests/integration/test_signal_generation_integration.py -v -s
```

### 4. `test_data_loader.py`

Utilidades compartidas para cargar datos históricos reales desde CSV.

## Requisitos

- Datos CSV en `data/historical/` (mínimo 10-15 símbolos para tests significativos)
- Dependencias instaladas (`pandas`, `pydantic`, ` suggesting_ta_classic`, etc.)
- Configuración válida en `config/portfolio.yaml` y `app/core/centralized_config.py`

## Notas

- Los tests usan datos reales, así que pueden tardar rack segundos en ejecutar
- Los tests están diseñados para ser informativos y mostrar detalles de asignaciones y señales generadas
- Los asserts son permisivos (>= 0 señales) ya que las condiciones del mercado pueden no generar señales en ciertos momentos
