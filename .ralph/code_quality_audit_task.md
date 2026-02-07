# TAREA: Code Quality Audit - Dead Code, Assembly & Data Flow

## OBJETIVO

Auditar y corregir tres aspectos críticos de calidad de código:
1. **Estático**: Eliminar código muerto o aislado (vulture + pydeps)
2. **Ensamblaje**: Verificar inyección de dependencias en constructores
3. **Dinámico**: Verificar flujo de datos con Correlation IDs

---

## FASE 1: Estático - Código Muerto (vulture)

### Archivo de resultados: `vulture_results.txt`

#### 1.1 Imports No Utilizados (90% confidence)

**Archivo:** `app/backtesting/awesome_quant_integrator.py:39`
```python
# ❌ ELIMINAR:
import pyfolio  # No se usa en el código
```

#### 1.2 Variables No Utilizadas (100% confidence)

**Total encontrados:** ~70 variables

**Principales archivos afectados:**
- `app/api/security.py:421` - `allow_api_key`
- `app/backtesting/bias_correctors.py:242` - `symbol_col`
- `app/backtesting/comprehensive_backtest_runner.py:1906` - `val_size`
- `app/backtesting/data_loader.py:38` - `index_as_date`
- `app/backtesting/execution_engine.py:181,184` - `bar_open`, `bar_close`
- `app/backtesting/universe_manager.py:185` - `historical_date`
- `app/core/audit.py:592` - `auto_log`
- `app/core/contracts.py:197` - `invariants`
- `app/core/logging_config.py:443` - `file_level`
- `app/main.py:117` - `fastapi_app`
- `app/services/emergency_handler/emergency_closer.py:123` - `frame`

**Fix general:**
```python
# ❌ ANTES:
def some_function():
    unused_var = calculate_something()  # Nunca se usa
    return result

# ✅ DESPUÉS (opción 1 - eliminar):
def some_function():
    return result

# ✅ DESPUÉS (opción 2 - usar la variable):
def some_function():
    unused_var = calculate_something()
    logger.debug(f"Calculated: {unused_var}")
    return result
```

#### 1.3 Código Inalcanzable (100% confidence)

**Archivos afectados:**
- `app/application/services/risk_configurator.py:179` - unreachable code after 'if'
- `app/core/tier_mapper.py:194` - unreachable code after 'try'

**Fix:**
```python
# ❌ ANTES:
if condition:
    return True
return False  # ← Esta línea NUNCA se ejecuta

# ✅ DESPUÉS:
if condition:
    return True
else:
    return False

# O mejor:
return condition
```

---

## FASE 2: Ensamblaje - Inyección de Dependencias

### Objetivo: Verificar que todos los constructores reciben sus dependencias

#### 2.1 Detectar constructores con problemas

**Patrones a buscar:**

1. **Instanciación directa (sin DI)**:
```python
# ❌ MAL - Acoplamiento fuerte
class TradingEngine:
    def __init__(self):
        self.broker = BrokerConnector()  # Crea su propia dependencia
        self.database = Database()        # No se puede mockear
```

2. **Dependencias opcionales sin valor por defecto**:
```python
# ❌ MAL - TypeError si no se pasa
class OrderManager:
    def __init__(self, broker: BrokerConnector, logger: Logger):
        self.broker = broker
        self.logger = logger
```

3. **Usar clases concretas en lugar de Protocol/ABC**:
```python
# ❌ MAL - Violación SOL-005
class ExecutionEngine:
    def __init__(self, registry: StrategyRegistry):  # Clase concreta
        self.registry = registry
```

**Fix general:**
```python
# ✅ BIEN - Dependency Injection + Protocol
from typing import Protocol

class BrokerConnectorProto(Protocol):
    async def place_order(self, ...) -> Order:
        ...

class ExecutionEngine:
    def __init__(
        self,
        broker: BrokerConnectorProto,  # Protocol, no clase concreta
        logger: Logger | None = None,   # Opcional con valor por defecto
    ):
        self.broker = broker
        self.logger = logger or logging.getLogger(__name__)
```

#### 2.2 Estrategia de auditoría

```bash
# 1. Buscar constructores con new() o instanciación directa
grep -rn "def __init__" app/ | while read file; do
    # Verificar si hay ClassName() dentro del __init__
done

# 2. Buscar clases concretas en type hints
grep -rn "def __init__.*: StrategyRegistry" app/
grep -rn "def __init__.*: BrokerConnector" app/
grep -rn "def __init__.*: Logger" app/

# 3. Verificar que todos los services usen Protocol
grep -rn "class.*Service.*:" app/application/services/
```

---

## FASE 3: Dinámico - Flujo de Datos con Correlation IDs

### Objetivo: Verificar que los datos fluyen entre módulos con trazabilidad

#### 3.1 ¿Qué es un Correlation ID?

Un `correlation_id` es un identificador único que permite:
- Trazar una operación a través de múltiples módulos
- Agrupar logs de la misma transacción
- Debuggear problemas en producción

**Ejemplo:**
```python
# ❌ SIN correlation_id - Imposible de tracear
logger.info("Placing order")
broker.place_order(...)
logger.info("Order executed")

# ✅ CON correlation_id - Todo traceable
correlation_id = str(uuid.uuid4())
logger.info("Placing order", correlation_id=correlation_id, order_id=order_id)
broker.place_order(..., correlation_id=correlation_id)
logger.info("Order executed", correlation_id=correlation_id, status="filled")
```

#### 3.2 Patrón de implementación

```python
import uuid
import logging

# Estructura de log con correlation_id
logger.info(
    "Message describing action",
    correlation_id=correlation_id,
    entity_id=entity_id,
    action="action_name",
    status="started|completed|failed",
    extra_context=value,
)
```

#### 3.3 Módulos críticos que DEBEN tener correlation_id

1. **Trading Operations**:
   - `app/services/live_trading/order_manager.py`
   - `app/services/live_trading/broker_connector.py`
   - `app/services/live_trading/trading_bridge_orchestrator.py`

2. **Risk Management**:
   - `app/services/live_trading/risk_gates.py`

3. **Execution**:
   - `app/strategies/execution_engine.py`

#### 3.4 Auditoría de correlation_id

```bash
# Verificar qué módulos tienen correlation_id
grep -rn "correlation_id" app/services/live_trading/
grep -rn "correlation_id" app/strategies/

# Buscar logger.info sin correlation_id en módulos críticos
grep -rn "logger.info.*order" app/services/live_trading/order_manager.py | grep -v correlation_id
```

---

## ESTRATEGIA DE EJECUCIÓN

### FASE 1: Código Muerto (vulture)

1. **Leer vulture_results.txt**
2. **Por cada archivo con código muerto:**
   - Leer el archivo
   - Eliminar variables no utilizadas
   - Eliminar imports no utilizados
   - Corregir código inalcanzable
3. **Validar:**
   ```bash
   scripts/validate_file_complete.sh <archivo>
   ```

### FASE 2: Inyección de Dependencias

1. **Buscar constructores con problemas:**
   ```bash
   grep -rn "def __init__" app/ > all_init_methods.txt
   ```

2. **Analizar cada constructor:**
   - ¿Tiene instanciación directa? → Convertir a DI
   - ¿Usa clases concretas? → Convertir a Protocol
   - ¿Tiene dependencias requeridas sin default? → Añadir default

3. **Crear Protocol para las dependencias:**
   ```python
   # Crear protocols.py si no existe
   from typing import Protocol

   class DependencyProto(Protocol):
       def required_method(self) -> None:
           ...
   ```

### FASE 3: Correlation IDs

1. **Identificar puntos de entrada:**
   - API endpoints
   - Command handlers
   - Event handlers

2. **Generar correlation_id en entrada:**
   ```python
   correlation_id = str(uuid.uuid4())
   ```

3. **Propagar a través de toda la cadena:**
   - Pasar como parámetro
   - Incluir en todos los logs
   - Devolver en respuesta

---

## VALIDACIÓN FINAL

```bash
# 1. Verificar que vulture no encuentra código muerto
.venv/bin/vulture app/ --min-confidence 90
# Debe retornar 0 items

# 2. Verificar pydeps
.venv/bin/pydeps app/ --max-bacon=3 -o pydeps_final.png
# Revisar el gráfico visualmente

# 3. Buscar constructores sin DI
grep -rn "def __init__.*:" app/ | grep -v "Protocol" | grep -v "ABC"

# 4. Verificar correlation_id en módulos críticos
grep -c "correlation_id" app/services/live_trading/order_manager.py
grep -c "correlation_id" app/services/live_trading/broker_connector.py
grep -c "correlation_id" app/services/live_trading/trading_bridge_orchestrator.py
# Deben ser > 0

# 5. Ejecutar tests
.venv/bin/pytest tests/ -v --tb=short
```

---

## MÉTRICAS DE ÉXITO

### Por Fase:
| Fase | Métrica | Antes | Después | Status |
|------|---------|-------|---------|--------|
| 1. Código Muerto | Items de vulture | 74 | 0 | ⬜ |
| 2. Ensamblaje | Constructores sin Protocol | ? | 0 | ⬜ |
| 3. Correlation ID | Módulos críticos con tracing | 0/4 | 4/4 | ⬜ |

### General:
- [ ] **Vulture**: 0 items de código muerto
- [ ] **Pydeps**: Gráfico limpio sin módulos aislados
- [ ] **DI**: Todos los constructores usan Protocol o ABC
- [ ] **Correlation ID**: Todos los módulos críticos tienen tracing

---

## OUTPUT FINAL: **CODE_QUALITY_AUDIT_COMPLETE**

Cuando:
- ✅ Vulture retorna 0 items
- ✅ Pydeps no muestra módulos aislados
- ✅ Todos los constructores usan inyección de dependencias
- ✅ Todos los módulos críticos tienen correlation_id
- ✅ Todos los tests pasan

---

## NOTAS IMPORTANTES

1. **Código muerto**: Eliminar con cuidado - puede ser usado en tests
2. **Inyección de dependencias**: Priorizar Protocol sobre ABC
3. **Correlation ID**: Usar uuid.uuid4() para generar únicos
4. **Validar después de CADA cambio**: Un fix puede romper otra cosa

---

*Auto-generated on 2026-02-07*
*Task: Code Quality Audit - Dead Code, Assembly & Data Flow*
