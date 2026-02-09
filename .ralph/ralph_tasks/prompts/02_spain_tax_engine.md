#  Spain Tax Engine - Prompt

**Tarea ID:** 02_spain_tax_engine
**Propósito:** Implementar motor de impuestos español (IRPF progresivo 19/21/23%, dividendos UE/No-UE, Modelo 720)
**Tiempo estimado:** 8 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar motor de impuestos para residente fiscal en España con:
- **IRPF-001:** Progresivo 19/21/23% (sin distinción LT/ST en España)
- **DIV-001:** Dividendos UE 0% vs No-UE 19%
- **MOD720-001:** Modelo 720 > €50k extranjeros
- **LOSS-CF-001:** Carryforward 4 años máximo

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/tax_efficiency/engines/spain_tax_engine_impl.py**
   - Implementación principal de ISpainTaxEngine
   - IRPF brackets progresivos
   - EU dividend detection
   - Modelo 720 threshold check
   - Loss carryforward tracking

2. **app/services/tax_efficiency/engines/modelo_720_generator.py**
   - Generador de reportes Modelo 720
   - Asset categorization (stocks, funds, bonds, cash)
   - ISIN → country mapping
   - Deadline tracking (31 marzo)

3. **app/services/tax_efficiency/engines/spain_dividend_tax.py**
   - Calculadora de dividend tax
   - UE country code mapping
   - Ticker → country mapping
   - Withholding calculation

4. **app/services/tax_efficiency/__init__.py**
   - Exportaciones del módulo

5. **app/services/tax_efficiency/engines/__init__.py**
   - Exportaciones de engines

---

##  REQUISITOS TÉCNICOS

### Spain Tax Engine Implementation

```python
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from app.core.protocols.i_spain_tax_engine import ISpainTaxEngine  # @skip-import si no existe


class SpainTaxEngineImpl(ISpainTaxEngine):
    """
    Motor de impuestos español para trading

    NOTA: España NO tiene distinción entre Long Term y Short Term.
    Todos los rendimientos de capital se gravan igual.
    """

    # IRPF Brackets 2026
    BRACKETS = [
        {"min": 0, "max": 6000, "rate": Decimal("0.19")},
        {"min": 6000, "max": 50000, "rate": Decimal("0.21")},
        {"min": 50000, "max": 999999999, "rate": Decimal("0.23")},
    ]

    # EU Countries for dividend tax (DIV-001)
    EU_COUNTRIES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU",
        "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    }

    MODELO_720_THRESHOLD = Decimal("50000")
```

### Restricciones:

-   Usar `Decimal` para todos los cálculos monetarios
-   NO usar `float` para dinero (solo para output JSON)
-   NO usar `abc.ABC` (usar `typing.Protocol`)
-   Si un import no existe, usar flag `@skip-import`

---

##  VALIDACIÓN

### Validación de archivos creados:

```bash
# 1. Verificar que todos los archivos existen
ls -la app/services/tax_efficiency/engines/

# 2. Validar cada archivo
for f in app/services/tax_efficiency/engines/*.py; do
  python scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar que se implementan todos los métodos del Protocol
grep "def " app/services/tax_efficiency/engines/spain_tax_engine_impl.py | wc -l
# Debe ser >= 5

# 4. Verificar IRPF brackets
grep -A 5 "BRACKETS" app/services/tax_efficiency/engines/spain_tax_engine_impl.py

# 5. Verificar países UE
grep -A 10 "EU_COUNTRIES" app/services/tax_efficiency/engines/spain_tax_engine_impl.py

# 6. Verificar threshold Modelo 720
grep "MODELO_720_THRESHOLD" app/services/tax_efficiency/engines/spain_tax_engine_impl.py
```

### Tests manuales:

```python
# Test IRPF progresivo
engine = SpainTaxEngineImpl()

assert engine.calculate_capital_gains_tax(Decimal("5000")) == Decimal("950")  # 19%
assert engine.calculate_capital_gains_tax(Decimal("10000")) == Decimal("2000")  # 21%
assert engine.calculate_capital_gains_tax(Decimal("60000")) == Decimal("13300")  # 23%

# Test dividendos UE vs No-UE
assert engine.calculate_dividend_tax("SAN", Decimal("100")) == Decimal("0")  # UE (Spain)
assert engine.calculate_dividend_tax("AAPL", Decimal("100")) == Decimal("19")  # No-UE (US)

# Test Modelo 720
assert not engine.check_modelo_720_threshold(Decimal("40000"))
assert engine.check_modelo_720_threshold(Decimal("60000"))
```

---

##  MANEJO DE @skip-import FLAGS

Si un import no existe, usar flag en el código:

```python
# @skip-import: ISpainTaxEngine not implemented yet
# TODO: Create ISpainTaxEngine in app/core/protocols/i_spain_tax_engine.py
from app.core.protocols.i_spain_tax_engine import ISpainTaxEngine  # type: ignore
```

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "02_spain_tax_engine",
  "task_name": "Spain Tax Engine Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T18:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 5,
    "created_files": 5,
    "validated_files": 5
  },
  "outputs": {
    "files_created": [
      "app/services/tax_efficiency/__init__.py",
      "app/services/tax_efficiency/engines/__init__.py",
      "app/services/tax_efficiency/engines/spain_tax_engine_impl.py",
      "app/services/tax_efficiency/engines/modelo_720_generator.py",
      "app/services/tax_efficiency/engines/spain_dividend_tax.py"
    ],
    "irpf_brackets": [19, 21, 23],
    "eu_countries_count": 31,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "03_trading_decision_logger",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T18:00:00Z"
}
```

---

##  SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] 5 archivos creados (incluyendo __init__.py)
- [ ] SpainTaxEngineImpl implementa ISpainTaxEngine
- [ ] IRPF brackets: 19/21/23% implementados
- [ ] EU countries: 31 países definidos
- [ ] Modelo 720 threshold: €50,000 definido
- [ ] Loss carryforward: 4 años máximo
- [ ] Todos los archivos validan con `python scripts/utils.py validate`
- [ ] Tests manuales pasan
- [ ] Checkpoint creado con status "COMPLETED"

---

##  REFERENCIAS

- `.ralph/docs/requirements/SERVICE_REQUIREMENTS.md` - Spain-Specific Requirements
- `.ralph/rules/rules_mapping.yml` - Spain Tax Rules
- `app/core/protocols/i_spain_tax_engine.py` - Protocol interface (debe existir de tarea 01)
