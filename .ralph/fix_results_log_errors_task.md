# TAREA: Fix Errors from results.log

## OBJETIVO

Arreglar **todos los errores** encontrados en `results.log` generados por las herramientas de análisis estático (Flake8, Ruff, Pylint, Mypy).

---

## CATEGORÍAS DE ERRORES ENCONTRADOS

### 🔴 Categoría 1: Imports Faltantes (F821/E0602) - 5 archivos

#### 1.1 `app/main.py` - Línea 145
**Error:** `Undefined name 'IntegrityError', 'OperationalError', 'DatabaseError', 'DataError', 'ProgrammingError'`

**Fix:**
```python
# AÑADIR al inicio del archivo (imports section):
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    DatabaseError,
    DataError,
    ProgrammingError,
)
```

#### 1.2 `app/backtesting/execution/market_impact.py` - Línea 390
**Error:** `Undefined name 'List'`

**Fix:**
```python
# AÑADIR en imports:
from typing import List
```

#### 1.3 `app/backtesting/feature_engineering/fracdiff_visualizations.py` - Línea 631
**Error:** `Undefined name 'logger'`

**Fix:**
```python
# AÑADIR en imports:
import logging

logger = logging.getLogger(__name__)
```

#### 1.4 `app/backtesting/labeling/bet_sizing.py` - Línea 1033
**Error:** `Undefined name 'Any'`

**Fix:**
```python
# AÑADIR en imports:
from typing import Any
```

#### 1.5 `app/backtesting/metrics.py` - Línea 79
**Error:** `Undefined name 'SharpeRatioCombiner'`

**Fix:**
```python
# INVESTIGAR: Buscar dónde se define SharpeRatioCombiner
# Si no existe, crearlo o importar desde el módulo correcto
```

---

### 🟡 Categoría 2: Bare Except (B001) - 1 archivo

#### 2.1 `tests/backtesting/feature_engineering/test_fractional_differentiation.py` - Líneas 413, 421
**Error:** `Do not use bare except:`

**Fix:**
```python
# ANTES:
except:
    pass

# DESPUÉS:
except Exception:
    pass
```

---

### 🟡 Categoría 3: Abstract Base Class sin métodos abstractos (B024) - 1 archivo

#### 3.1 `app/application/services/__init__.py` - Línea 176
**Error:** `ApplicationService is an abstract base class, but none of the methods it defines are abstract`

**Fix:**
```python
# OPCIÓN A: Añadir @abstractmethod a los métodos que deben ser abstractos
from abc import abstractmethod

class ApplicationService:
    @abstractmethod
    def some_method_that_should_be_abstract(self):
        ...

# OPCIÓN B: Si NO es abstracta, quitar el ABC y heredar de object
class ApplicationService:  # Sin ABC
    def some_method(self):
        ...

# OPCIÓN C: Si está vacía, hacerla Protocol
from typing import Protocol

class ApplicationService(Protocol):
    """Protocol for application services."""
    ...
```

---

### 🟡 Categoría 4: Try-Except-Raise (W0706) - 1 archivo

#### 4.1 `app/backtesting/core/error_handling.py` - Línea 383
**Error:** `The except handler raises immediately`

**Fix:**
```python
# ANTES:
try:
    ...
except Exception:
    raise  # ❌ No añade valor

# DESPUÉS:
try:
    ...
except Exception as e:
    logger.error(f"Error in operation: {e}")
    raise  # ✅ Logging antes de re-raise
```

---

### 🔵 Categoría 5: Errores de Tipos Mypy - ~40 errores

#### 5.1 Enum Values Faltantes - `app/application/services/input_profile_router.py`

**Errores:**
- `InvestmentObjective.MAXIMIZAR_CAPITAL` no existe
- `InvestmentObjective.MAXIMIZAR_DIVIDENDOS` no existe
- `RiskTolerance.BAJO` no existe
- `RiskTolerance.MEDIO` no existe
- `RiskTolerance.ALTO` no existe
- `TaxResidence.country` no existe

**Fix:**
```python
# 1. Verificar los valores correctos del Enum:
# Leer el archivo de definición del Enum
# Posiblemente: InvestmentObjective.MAXIMIZE_CAPITAL (inglés)
# Posiblemente: RiskTolerance.LOW, MEDIUM, HIGH (inglés)

# 2. Actualizar los usos con los valores correctos:
# ANTES:
if objective == InvestmentObjective.MAXIMIZAR_CAPITAL:

# DESPUÉS:
if objective == InvestmentObjective.MAXIMIZE_CAPITAL:  # ✅ Valor correcto
```

#### 5.2 AbstractUnitOfWork Attributes Missing

**Errores en** `app/application/services/__init__.py`:
- `AbstractUnitOfWork` has no attribute `orders`
- `AbstractUnitOfWork` has no attribute `portfolios`
- `AbstractUnitOfWork` has no attribute `positions`
- `type[Order]` has no attribute `OrderType`
- `type[Order]` has no attribute `OrderSide`

**Fix:**
```python
# 1. Leer la definición de AbstractUnitOfWork
# 2. Añadir los atributos faltantes al Protocol/ABC:

from app.domain.models import Order, Portfolio, Position

class AbstractUnitOfWork(ABC):
    @abstractmethod
    def __init__(self):
        self.orders: AbstractRepository[Order]  # ✅ Añadir
        self.portfolios: AbstractRepository[Portfolio]  # ✅ Añadir
        self.positions: AbstractRepository[Position]  # ✅ Añadir

# 3. O verificar que Order.OrderType y Order.OrderSide existen en el modelo
```

#### 5.3 Missing Arguments in Constructor Calls

**Errores:**
- `Capital()` missing argument `tier`
- `RiskParameters()` missing arguments `stop_loss_pct`, `take_profit_pct`
- `Signal()` missing arguments `liquidity_score`, `price`, `priority_score`, `strength`, `volume`

**Fix:**
```python
# Añadir los argumentos requeridos:

# ANTES:
capital = Capital(amount=Decimal("10000"))

# DESPUÉS:
from app.domain.models import CapitalTier
capital = Capital(
    amount=Decimal("10000"),
    tier=CapitalTier.STANDARD  # ✅ Añadir tier
)

# ANTES:
risk_params = RiskParameters(max_position_size=Decimal("5000"))

# DESPUÉS:
risk_params = RiskParameters(
    max_position_size=Decimal("5000"),
    stop_loss_pct=Decimal("0.02"),  # ✅ Añadir
    take_profit_pct=Decimal("0.05")  # ✅ Añadir
)

# ANTES:
signal = Signal(symbol="AAPL", signal_type=SignalType.BUY)

# DESPUÉS:
from app.models.signal import Signal, SignalStrength
signal = Signal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    strength=SignalStrength.MODERATE,  # ✅ Añadir
    price=Decimal("150.0"),  # ✅ Añadir
    volume=Decimal("1000"),  # ✅ Añadir
    liquidity_score=80.0,  # ✅ Añadir
    priority_score=70.0,  # ✅ Añadir
    confidence=75.0  # ✅ Añadir si es requerido
)
```

#### 5.4 Type Incompatibilities

**Errores:**
- `Dict entry 0 has incompatible type "str": "dict[str, float]"`
- `Incompatible types in assignment (expression has type "ndarray", variable has type "list")`
- `Argument "max_drawdown_duration" to "PerformanceMetrics" has incompatible type`

**Fix:**
```python
# Convertir ndarray a list cuando se requiera:
import numpy as np

# ANTES:
weights_list: list[float] = np.array([0.5, 0.5])  # ❌ Error

# DESPUÉS:
weights_list: list[float] = np.array([0.5, 0.5]).tolist()  # ✅ Convertir

# Para Dict entries:
# ANTES:
my_dict: dict[str, Union[float, int, str]] = {"key": {"nested": 1.0}}  # ❌ Error

# DESPUÉS:
my_dict: dict[str, Union[float, int, str]] = {"key": 1.0}  # ✅ Valor simple
# O cambiar el tipo del dict:
my_dict: dict[str, dict[str, float]] = {"key": {"nested": 1.0}}  # ✅ Tipo correcto
```

---

## ESTRATEGIA DE EJECUCIÓN

### Orden de prioridad:

1. **Fase 1: Imports Faltantes (F821/E0602)** - Crítico, bloquea todo
2. **Fase 2: Bare Except (B001)** - Seguridad
3. **Fase 3: Abstract Base Class (B024)** - Diseño
4. **Fase 4: Try-Except-Raise (W0706)** - Logging
5. **Fase 5: Errores de Tipos Mypy** - Validación de tipos

### Por cada error:

1. **Leer el archivo actual**:
   ```bash
   cat <archivo>
   ```

2. **Identificar la línea exacta del error**:
   ```bash
   grep -n "patrón del error" <archivo>
   ```

3. **Aplicar el fix según la categoría**:
   - Seguir el código de ejemplo arriba
   - Mantener el estilo existente del archivo

4. **Validar después del fix**:
   ```bash
   # Validar el archivo individual
   scripts/validate_file_complete.sh <archivo>

   # O validar solo las herramientas que fallaron
   ruff check <archivo> --fix
   mypy <archivo>
   flake8 <archivo>
   ```

5. **Solo cuando success: true**:
   - Marcar como FIXED
   - Continuar con el siguiente error

---

## VALIDACIÓN FINAL

```bash
# 1. Ejecutar todas las herramientas
scripts/validate_file_complete.sh app/

# 2. Verificar que no hay errores F821, E0602, B001, B024, W0706
grep -E "F821|E0602|B001|B024|W0706" results.log
# Debe retornar vacío (sin errores)

# 3. Ejecutar tests para verificar que nada se rompió
.venv/bin/pytest tests/ -v --tb=short
```

---

## MÉTRICAS DE ÉXITO

### Por Categoría:
| Categoría | Errores | Fixeados | Status |
|-----------|---------|----------|--------|
| Imports Faltantes | 5 | 0 | ⬜ |
| Bare Except | 2 | 0 | ⬜ |
| Abstract Base Class | 1 | 0 | ⬜ |
| Try-Except-Raise | 1 | 0 | ⬜ |
| Type Errors (Mypy) | ~40 | 0 | ⬜ |

### General:
- [ ] **F821/E0602**: 0/5 errores de undefined names
- [ ] **B001**: 0/2 bare except
- [ ] **B024**: 0/1 abstract base class issues
- [ ] **W0706**: 0/1 try-except-raise issues
- [ ] **Mypy**: 0/~40 type errors

---

## OUTPUT FINAL: **RESULTS_LOG_ERRORS_COMPLETE**

Cuando:
- ✅ Todos los imports faltantes están añadidos
- ✅ Todos los bare except son específicos
- ✅ Abstract base class tiene métodos abstractos o es Protocol
- ✅ Try-except-raise tiene logging
- ✅ Todos los type errors de Mypy están resueltos
- ✅ `validate_file_complete.sh` devuelve success: true para todos los archivos

---

## NOTAS IMPORTANTES

1. **NO adivinar**: Si un valor de Enum no existe, buscar la definición correcta antes de cambiar
2. **NO cambiar tipos arbitrariamente**: Si Mypy dice que el tipo está mal, investigar por qué
3. **Validar después de CADA fix**: Un fix puede romper otra cosa
4. **Tests obligatorios**: Después de todos los fixes, ejecutar pytest para verificar

---

*Auto-generated on 2026-02-07*
*Task: Fix all errors from results.log*
