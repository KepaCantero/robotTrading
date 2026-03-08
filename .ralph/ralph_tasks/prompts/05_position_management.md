#  Position Management - Prompt

**Tarea ID:** 05_position_management
**Propósito:** Implementar gestión de posiciones avanzada (R11, R12, R13)
**Tiempo estimado:** 12 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar gestión avanzada de posiciones con:
- **R11:** Trailing Stop Dinámico
- **R12:** Take Profit Parcial
- **R13:** Pyramiding (solo ganadores)

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/position_management/trailing_stop_manager.py**
   - TrailingStopManager
   - update_stop_loss() - Ajusta SL dinámicamente
   - calculate_trailing_distance() - Distancia según volatilidad

2. **app/services/position_management/partial_take_profit.py**
   - PartialTakeProfitManager
   - execute_partial_exit() - Cierra porción en TP1, TP2, TP3
   - calculate_partial_sizes() - 25% / 25% / 50%

3. **app/services/position_management/pyramiding_manager.py**
   - PyramidingManager
   - can_add_position() - Solo si en ganancia
   - calculate_pyramid_size() - Tamaños decrecientes

4. **app/services/position_management/__init__.py**

---

##  REQUISITOS TÉCNICOS

### Trailing Stop Manager (R11)

```python
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass


@dataclass
class TrailingStopConfig:
    """Configuración de trailing stop"""
    initial_stop_pct: Decimal = Decimal("0.02")  # 2% inicial
    trail_distance_pct: Decimal = Decimal("0.015")  # 1.5% de distancia
    activation_pct: Decimal = Decimal("0.02")  # Activar tras 2% de ganancia


class TrailingStopManager:
    """
    Gestiona trailing stop dinámico (R11)

    El stop loss se ajusta automáticamente a favor del trade
    cuando el precio alcanza cierto nivel de ganancia.
    """

    def __init__(self, config: TrailingStopConfig):
        self.config = config
        self._highest_price: Optional[Decimal] = None
        self._current_stop: Optional[Decimal] = None

    def update_stop_loss(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        is_long: bool = True
    ) -> tuple[Decimal, bool]:
        """
        Actualiza stop loss basado en precio actual

        Args:
            entry_price: Precio de entrada
            current_price: Precio actual
            is_long: True para long, False para short

        Returns:
            (nuevo_stop_loss, se_activó)
        """
        if is_long:
            self._highest_price = max(self._highest_price or current_price, current_price)

            # Calcular ganancia actual
            profit_pct = (current_price - entry_price) / entry_price

            # Activar trailing solo si hay ganancia suficiente
            if profit_pct >= self.config.activation_pct:
                # Nuevo stop: precio más alto menos distancia de trail
                new_stop = self._highest_price * (Decimal("1") - self.config.trail_distance_pct)

                # Solo actualizar si es mejor que el stop actual
                if self._current_stop is None or new_stop > self._current_stop:
                    self._current_stop = new_stop
                    return new_stop, True

            # Stop inicial si no se ha activado
            if self._current_stop is None:
                initial_stop = entry_price * (Decimal("1") - self.config.initial_stop_pct)
                self._current_stop = initial_stop

        return self._current_stop, False
```

### Partial Take Profit (R12)

```python
@dataclass
class TakeProfitLevel:
    """Nivel de take profit"""
    price: Decimal
    percentage: Decimal  # Porción a cerrar (0-1)
    executed: bool = False


class PartialTakeProfitManager:
    """
    Gestiona take profit parcial (R12)

    Cierra posiciones parcialmente en múltiples niveles:
    - TP1: 25% de posición
    - TP2: 25% de posición
    - TP3: 50% de posición (restante)
    """

    def __init__(self, tp_levels: list[tuple[Decimal, Decimal]]):
        """
        Args:
            tp_levels: Lista de (precio, porcentaje) para cada TP
                      Ej: [(105, 0.25), (110, 0.25), (120, 0.50)]
        """
        self.tp_levels = [
            TakeProfitLevel(price=price, percentage=pct)
            for price, pct in tp_levels
        ]

    def get_next_tp_level(self, current_price: Decimal) -> Optional[TakeProfitLevel]:
        """Obtiene siguiente nivel de TP no ejecutado"""
        for tp in self.tp_levels:
            if not tp.executed and current_price >= tp.price:
                return tp
        return None

    def execute_partial_exit(
        self,
        current_price: Decimal,
        position_size: Decimal
    ) -> Optional[Decimal]:
        """
        Ejecuta salida parcial en TP

        Args:
            current_price: Precio actual
            position_size: Tamaño de posición actual

        Returns:
            Cantidad a cerrar o None si no hay TP alcanzado
        """
        tp_level = self.get_next_tp_level(current_price)

        if tp_level:
            tp_level.executed = True
            return position_size * tp_level.percentage

        return None
```

### Pyramiding Manager (R13)

```python
class PyramidingManager:
    """
    Gestiona pyramiding (R13)

    Añade a posición SOLO si el trade es ganador.
    Tamaños decrecientes para reducir riesgo.
    """

    MAX_PYRAMID_ENTRIES = 3  # Máximo 3 entradas adicionales
    MIN_PROFIT_TO_ADD = Decimal("0.015")  # 1.5% de ganancia mínimo

    def __init__(
        self,
        entry_price: Decimal,
        is_long: bool = True
    ):
        self.entry_price = entry_price
        self.is_long = is_long
        self._pyramid_entries: list[Decimal] = []
        self._entry_count = 0

    def can_add_position(
        self,
        current_price: Decimal,
        current_position: Decimal
    ) -> tuple[bool, str]:
        """
        Verifica si se puede añadir a posición

        Args:
            current_price: Precio actual
            current_position: Tamaño de posición actual

        Returns:
            (puede_añadir, razón)
        """
        # Verificar número máximo de entradas
        if self._entry_count >= self.MAX_PYRAMID_ENTRIES:
            return False, "Max pyramid entries reached"

        # Verificar que estamos en ganancia
        profit_pct = self._calculate_profit_pct(current_price)

        if profit_pct < self.MIN_PROFIT_TO_ADD:
            return False, f"Profit {profit_pct:.2%} below minimum {self.MIN_PROFIT_TO_ADD:.2%}"

        return True, "OK to add"

    def calculate_pyramid_size(
        self,
        original_size: Decimal,
        entry_number: int
    ) -> Decimal:
        """
        Calcula tamaño de entrada piramidal

        Tamaños decrecientes:
        - Entrada 1: 100% del tamaño original
        - Entrada 2: 75% del tamaño original
        - Entrada 3: 50% del tamaño original
        """
        size_multipliers = [Decimal("1.0"), Decimal("0.75"), Decimal("0.5")]
        multiplier = size_multipliers[min(entry_number, len(size_multipliers) - 1)]
        return original_size * multiplier

    def _calculate_profit_pct(self, current_price: Decimal) -> Decimal:
        """Calcula porcentaje de ganancia/pérdida"""
        if self.is_long:
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price
```

### Restricciones:

-   Usar `Decimal` para todos los cálculos monetarios
-   R11: Trailing stop solo activa tras 2% de ganancia
-   R12: TP levels: 25%, 25%, 50%
-   R13: Solo pyramid en trades ganadores (>1.5%)
-   Máximo 3 entradas pyramid

---

##  VALIDACIÓN

### Validación de archivos:

```bash
# 1. Verificar archivos creados
ls -la app/services/position_management/

# 2. Validar cada archivo
for f in app/services/position_management/*.py; do
  python .ralph/scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar constantes
grep "activation_pct\|trail_distance" app/services/position_management/trailing_stop_manager.py
grep "0.25\|0.50" app/services/position_management/partial_take_profit.py
grep "MIN_PROFIT_TO_ADD" app/services/position_management/pyramiding_manager.py
```

### Tests manuales:

```python
# Test Trailing Stop
config = TrailingStopConfig()
manager = TrailingStopManager(config)
stop, activated = manager.update_stop_loss(
    entry_price=Decimal("100"),
    current_price=Decimal("102"),
    is_long=True
)
assert activated  # Debe activarse tras 2% de ganancia

# Test Partial TP
tp_levels = [
    (Decimal("105"), Decimal("0.25")),  # TP1
    (Decimal("110"), Decimal("0.25")),  # TP2
    (Decimal("120"), Decimal("0.50")),  # TP3
]
manager = PartialTakeProfitManager(tp_levels)
exit_size = manager.execute_partial_exit(
    current_price=Decimal("105"),
    position_size=Decimal("100")
)
assert exit_size == Decimal("25")  # 25% de 100

# Test Pyramiding
manager = PyramidingManager(entry_price=Decimal("100"))
can_add, reason = manager.can_add_position(
    current_price=Decimal("102"),
    current_position=Decimal("100")
)
assert can_add  # 2% de ganancia > 1.5% mínimo
```

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "05_position_management",
  "task_name": "Position Management Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T22:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 4,
    "created_files": 4,
    "validated_files": 4
  },
  "outputs": {
    "files_created": [
      "app/services/position_management/__init__.py",
      "app/services/position_management/trailing_stop_manager.py",
      "app/services/position_management/partial_take_profit.py",
      "app/services/position_management/pyramiding_manager.py"
    ],
    "r11_trailing_stop": true,
    "r12_partial_tp": true,
    "r13_pyramiding": true,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "06_reconciliation_daily",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T22:00:00Z"
}
```

---

##  SUCCESS CRITERIA

- [ ] 4 archivos creados
- [ ] TrailingStopManager: activation_pct = 2%
- [ ] PartialTakeProfitManager: TP levels 25/25/50
- [ ] PyramidingManager: MIN_PROFIT_TO_ADD = 1.5%
- [ ] Todos los archivos validan
- [ ] Tests manuales pasan
- [ ] Checkpoint creado

---

##  REFERENCIAS

- `rules/trading/` - R11, R12, R13
- `rules/trading/` - Position Management rules
