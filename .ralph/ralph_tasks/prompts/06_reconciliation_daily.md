#  Daily Reconciliation - Prompt

**Tarea ID:** 06_reconciliation_daily
**Propósito:** Implementar reconciliación diaria de posiciones (R16)
**Tiempo estimado:** 6 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar reconciliación diaria entre broker y sistema interno:
- **R16:** Reconciliación diaria obligatoria
- Detectar discrepancias en posiciones
- Alertar sobre errores de datos

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/reconciliation/daily_reconciler.py**
   - DailyReconciler
   - reconcile_positions() - Compara broker vs interno
   - generate_reconciliation_report() - Reporte diario

2. **app/services/reconciliation/discrepancy_detector.py**
   - DiscrepancyDetector
   - detect_position_mismatch() - Diferencias en cantidad
   - detect_price_mismatch() - Diferencias en precio
   - detect_missing_positions() - Posiciones faltantes

3. **app/services/reconciliation/__init__.py**

---

##  REQUISITOS TÉCNICOS

### Daily Reconciler (R16)

```python
from decimal import Decimal
from typing import list, dict, Optional
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Position:
    """Posición para reconciliación"""
    symbol: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    currency: str = "EUR"


@dataclass
class ReconciliationResult:
    """Resultado de reconciliación"""
    date: date
    total_positions: int
    matched_positions: int
    mismatched_positions: int
    missing_positions: int
    discrepancies: list[dict]
    is_balanced: bool


class DailyReconciler:
    """
    Reconciliador diario de posiciones (R16)

    Compara posiciones del broker con registros internos
    y detecta discrepancias.
    """

    def __init__(self):
        self._broker_positions: dict[str, Position] = {}
        self._internal_positions: dict[str, Position] = {}

    async def reconcile_positions(
        self,
        broker_positions: list[Position],
        internal_positions: list[Position]
    ) -> ReconciliationResult:
        """
        Reconcilia posiciones del broker vs internas

        Args:
            broker_positions: Posiciones desde broker API
            internal_positions: Posiciones desde base de datos interna

        Returns:
            ReconciliationResult con detalles
        """
        # Convertir a dict por symbol
        self._broker_positions = {p.symbol: p for p in broker_positions}
        self._internal_positions = {p.symbol: p for p in internal_positions}

        # Obtener todos los symbols únicos
        all_symbols = set(self._broker_positions.keys()) | set(self._internal_positions.keys())

        discrepancies = []
        matched = 0
        mismatched = 0
        missing = 0

        for symbol in all_symbols:
            broker_pos = self._broker_positions.get(symbol)
            internal_pos = self._internal_positions.get(symbol)

            # Detectar discrepancias
            result = self._compare_positions(symbol, broker_pos, internal_pos)

            if result["status"] == "MATCHED":
                matched += 1
            elif result["status"] == "MISMATCH":
                mismatched += 1
                discrepancies.append(result)
            elif result["status"] == "MISSING":
                missing += 1
                discrepancies.append(result)

        total = len(all_symbols)
        is_balanced = (mismatched == 0 and missing == 0)

        return ReconciliationResult(
            date=date.today(),
            total_positions=total,
            matched_positions=matched,
            mismatched_positions=mismatched,
            missing_positions=missing,
            discrepancies=discrepancies,
            is_balanced=is_balanced
        )

    def _compare_positions(
        self,
        symbol: str,
        broker_pos: Optional[Position],
        internal_pos: Optional[Position]
    ) -> dict:
        """Compara dos posiciones y retorna resultado"""
        # Ambos missing
        if broker_pos is None and internal_pos is None:
            return {"status": "MATCHED", "symbol": symbol}

        # Solo en broker (extraña)
        if broker_pos is not None and internal_pos is None:
            return {
                "status": "MISSING",
                "symbol": symbol,
                "type": "INTERNAL_ONLY",
                "broker_quantity": str(broker_pos.quantity),
                "detail": "Position exists in broker but not in internal records"
            }

        # Solo en interno (falta en broker)
        if broker_pos is None and internal_pos is not None:
            return {
                "status": "MISSING",
                "symbol": symbol,
                "type": "BROKER_ONLY",
                "internal_quantity": str(internal_pos.quantity),
                "detail": "Position exists in internal records but not in broker"
            }

        # Ambos existen - verificar cantidades
        qty_diff = abs(broker_pos.quantity - internal_pos.quantity)
        price_diff_pct = abs(broker_pos.current_price - internal_pos.current_price) / internal_pos.current_price

        # Tolerancia: 0.1% para precio, 1 share para cantidad
        if qty_diff <= Decimal("1") and price_diff_pct <= Decimal("0.001"):
            return {"status": "MATCHED", "symbol": symbol}

        # Hay discrepancia
        discrepancies = []
        if qty_diff > Decimal("1"):
            discrepancies.append({
                "type": "QUANTITY_MISMATCH",
                "broker": str(broker_pos.quantity),
                "internal": str(internal_pos.quantity),
                "difference": str(qty_diff)
            })

        if price_diff_pct > Decimal("0.001"):
            discrepancies.append({
                "type": "PRICE_MISMATCH",
                "broker": str(broker_pos.current_price),
                "internal": str(internal_pos.current_price),
                "difference_pct": str(price_diff_pct * Decimal("100")) + "%"
            })

        return {
            "status": "MISMATCH",
            "symbol": symbol,
            "discrepancies": discrepancies
        }

    def generate_reconciliation_report(self, result: ReconciliationResult) -> str:
        """Genera reporte de reconciliación en formato Markdown"""
        report = f"""# Daily Reconciliation Report
**Date:** {result.date}
**Status:** {'✅ BALANCED' if result.is_balanced else '⚠️ DISCREPANCIES'}

## Summary
- **Total Positions:** {result.total_positions}
- **Matched:** {result.matched_positions}
- **Mismatched:** {result.mismatched_positions}
- **Missing:** {result.missing_positions}

"""

        if result.discrepancies:
            report += "## Discrepancies\n\n"
            for disc in result.discrepancies:
                report += f"### {disc['symbol']}\n"
                report += f"- **Status:** {disc['status']}\n"
                if disc.get('discrepancies'):
                    for d in disc['discrepancies']:
                        report += f"  - {d['type']}: {d}\n"
                if disc.get('detail'):
                    report += f"- **Detail:** {disc['detail']}\n"
                report += "\n"

        return report
```

### Discrepancy Detector

```python
class DiscrepancyDetector:
    """
    Detector de discrepancias en reconciliación

    Analiza diferencias entre broker y sistema interno
    con diferentes umbrales de tolerancia.
    """

    # Umbrales de tolerancia
    QUANTITY_TOLERANCE = Decimal("1")  # 1 share
    PRICE_TOLERANCE_PCT = Decimal("0.001")  # 0.1%
    VALUE_TOLERANCE_PCT = Decimal("0.005")  # 0.5%

    def detect_position_mismatch(
        self,
        broker_qty: Decimal,
        internal_qty: Decimal
    ) -> Optional[dict]:
        """
        Detecta discrepancia en cantidad de posición

        Args:
            broker_qty: Cantidad según broker
            internal_qty: Cantidad según interno

        Returns:
            Diccionario con discrepancia o None si OK
        """
        diff = abs(broker_qty - internal_qty)

        if diff > self.QUANTITY_TOLERANCE:
            return {
                "type": "QUANTITY_MISMATCH",
                "broker_qty": str(broker_qty),
                "internal_qty": str(internal_qty),
                "difference": str(diff),
                "severity": "HIGH" if diff > Decimal("10") else "MEDIUM"
            }

        return None

    def detect_price_mismatch(
        self,
        broker_price: Decimal,
        internal_price: Decimal
    ) -> Optional[dict]:
        """
        Detecta discrepancia en precio

        Args:
            broker_price: Precio según broker
            internal_price: Precio según interno

        Returns:
            Diccionario con discrepancia o None si OK
        """
        if internal_price == 0:
            return {
                "type": "PRICE_MISMATCH",
                "broker_price": str(broker_price),
                "internal_price": str(internal_price),
                "detail": "Internal price is zero",
                "severity": "HIGH"
            }

        diff_pct = abs(broker_price - internal_price) / internal_price

        if diff_pct > self.PRICE_TOLERANCE_PCT:
            return {
                "type": "PRICE_MISMATCH",
                "broker_price": str(broker_price),
                "internal_price": str(internal_price),
                "difference_pct": f"{diff_pct * 100:.2f}%",
                "severity": "HIGH" if diff_pct > Decimal("0.01") else "MEDIUM"
            }

        return None

    def detect_missing_positions(
        self,
        broker_symbols: set[str],
        internal_symbols: set[str]
    ) -> list[dict]:
        """
        Detecta posiciones faltantes en un lado u otro

        Args:
            broker_symbols: Symbols en broker
            internal_symbols: Symbols en interno

        Returns:
            Lista de posiciones faltantes
        """
        missing = []

        # Symbols en broker pero no en interno
        for symbol in broker_symbols - internal_symbols:
            missing.append({
                "type": "MISSING_IN_INTERNAL",
                "symbol": symbol,
                "detail": "Position exists in broker but not in internal records",
                "severity": "HIGH"
            })

        # Symbols en interno pero no en broker
        for symbol in internal_symbols - broker_symbols:
            missing.append({
                "type": "MISSING_IN_BROKER",
                "symbol": symbol,
                "detail": "Position exists in internal records but not in broker",
                "severity": "CRITICAL"
            })

        return missing
```

### Restricciones:

-   R16: Reconciliación diaria obligatoria
-   Tolerancia cantidad: ±1 share
-   Tolerancia precio: ±0.1%
-   CRITICAL severity para posiciones faltantes en broker

---

##  VALIDACIÓN

### Validación de archivos:

```bash
# 1. Verificar archivos creados
ls -la app/services/reconciliation/

# 2. Validar cada archivo
for f in app/services/reconciliation/*.py; do
  python .ralph/scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar constantes
grep "QUANTITY_TOLERANCE\|PRICE_TOLERANCE" app/services/reconciliation/discrepancy_detector.py
grep "R16\|reconcile" app/services/reconciliation/daily_reconciler.py
```

### Tests manuales:

```python
# Test Position Mismatch
detector = DiscrepancyDetector()
result = detector.detect_position_mismatch(
    broker_qty=Decimal("100"),
    internal_qty=Decimal("98")
)
assert result is not None  # Diferencia de 2 > tolerancia de 1

# Test Price Mismatch
result = detector.detect_price_mismatch(
    broker_price=Decimal("100.50"),
    internal_price=Decimal("100.00")
)
assert result is not None  # 0.5% > 0.1% tolerancia

# Test Missing Positions
broker_syms = {"SAN", "REE"}
internal_syms = {"SAN", "AAPL"}
missing = detector.detect_missing_positions(broker_syms, internal_syms)
assert len(missing) == 2  # REE y AAPL
```

---

##  CHECKPOINT

```json
{
  "task_id": "06_reconciliation_daily",
  "task_name": "Daily Reconciliation Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T16:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 3,
    "created_files": 3,
    "validated_files": 3
  },
  "outputs": {
    "files_created": [
      "app/services/reconciliation/__init__.py",
      "app/services/reconciliation/daily_reconciler.py",
      "app/services/reconciliation/discrepancy_detector.py"
    ],
    "r16_daily_reconciliation": true,
    "discrepancy_detection": true,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "07_capital_phase_manager",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T16:00:00Z"
}
```

---

##  SUCCESS CRITERIA

- [ ] 3 archivos creados
- [ ] DailyReconciler implementa reconcile_positions()
- [ ] DiscrepancyDetector con 3 métodos de detección
- [ ] Tolerancias: qty=1, price=0.1%
- [ ] Todos los archivos validan
- [ ] Tests manuales pasan
- [ ] Checkpoint creado

---

##  REFERENCIAS

- `.ralph/docs/realistic_trading_rules.md` - R16
- `.ralph/rules/rules_mapping.yml` - Reconciliation rules
