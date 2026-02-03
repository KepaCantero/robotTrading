# Template: Common GAP Fix Patterns

Reference guide for fixing common GAP violations in Python code.

---

## LOG-001: Structured Logging

### ❌ BAD (f-string)
```python
logger.info(f"Processing trade: {symbol} quantity={quantity}")
logger.debug(f"Order {order_id} status: {status}")
```

### ✅ GOOD (structured with keyword args)
```python
logger.info("Processing trade", symbol=symbol, quantity=quantity)
logger.debug("Order status", order_id=order_id, status=status)
```

**Why:** Structured logging is parseable by log aggregators and easier to query.

---

## LOG-004: Exception Logging with Stack Traces

### ❌ BAD (no stack trace)
```python
except Exception as e:
    logger.error("Operation failed", error=str(e))
    raise
```

### ✅ GOOD (with exc_info=True)
```python
except Exception as e:
    logger.error("Operation failed", error=str(e), exc_info=True)
    raise
```

**Why:** `exc_info=True` captures the full stack trace for debugging.

---

## CC-006: Explicit Error Handling

### ❌ BAD (generic Exception)
```python
try:
    process_trade(trade)
except Exception as e:
    logger.error("Trade processing failed", error=str(e), exc_info=True)
```

### ✅ GOOD (specific exceptions)
```python
try:
    process_trade(trade)
except ValueError as e:
    logger.error("Invalid trade data", error=str(e), exc_info=True)
except ValidationError as e:
    logger.error("Trade validation failed", error=str(e), exc_info=True)
except DatabaseError as e:
    logger.error("Database error during trade", error=str(e), exc_info=True)
```

**Why:** Specific exceptions allow targeted error handling and recovery.

---

## TYP-001: Missing Return Type Annotations

### ❌ BAD (no return type)
```python
def calculate_profit(entry_price, exit_price, quantity):
    return (exit_price - entry_price) * quantity
```

### ✅ GOOD (with return type)
```python
def calculate_profit(entry_price: Decimal, exit_price: Decimal, quantity: int) -> Decimal:
    return (exit_price - entry_price) * quantity
```

**Why:** Return types improve IDE support, documentation, and type checking.

---

## TYP-003: Using Any Without Justification

### ❌ BAD (unjustified Any)
```python
def process_data(data: Any) -> Any:
    return data
```

### ✅ GOOD (specific types)
```python
from typing import Union

def process_data(data: Union[dict, list]) -> dict:
    if isinstance(data, list):
        return {"items": data}
    return data
```

### ✅ ACCEPTABLE (Any with justification)
```python
# Any is acceptable here because this is a generic proxy handler
# that must accept arbitrary payload types from external API
def handle_proxy_request(request: Any) -> Any:
    # Justification: External API with dynamic schema
    pass
```

**Why:** Specific types enable better type checking and catch errors early.

---

## TRD-001: Validate Mathematical Relationships

### ❌ BAD (no validation)
```python
def calculate_sharpe_ratio(returns, risk_free_rate):
    return (returns.mean() - risk_free_rate) / returns.std()
```

### ✅ GOOD (with validation)
```python
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    if len(returns) == 0:
        raise ValueError("returns cannot be empty")
    if returns.std() == 0:
        raise ValueError("returns.std() cannot be zero (division by zero)")
    return (returns.mean() - risk_free_rate) / returns.std()
```

**Why:** Input validation prevents crashes and incorrect calculations.

---

## TRD-005: Price Validation

### ❌ BAD (no price validation)
```python
def execute_order(symbol: str, price: float, quantity: int) -> Order:
    return Order(symbol=symbol, price=price, quantity=quantity)
```

### ✅ GOOD (with price validation)
```python
def execute_order(symbol: str, price: Decimal, quantity: int) -> Order:
    if price <= 0:
        raise ValueError(f"price must be positive, got {price}")
    if quantity <= 0:
        raise ValueError(f"quantity must be positive, got {quantity}")
    return Order(symbol=symbol, price=price, quantity=quantity)
```

**Why:** Invalid prices/quantities can cause significant financial losses.

---

## SEC-001: No Hardcoded Secrets

### ❌ BAD (hardcoded secret)
```python
API_KEY = "sk-1234567890abcdef"
database_url = "postgres://user:password@localhost/db"
```

### ✅ GOOD (from environment/config)
```python
from app.core.config import get_settings

settings = get_settings()
API_KEY = settings.api_key
database_url = settings.database_url
```

**Why:** Hardcoded secrets in code are a security vulnerability.

---

## ARCH-004: Function Length Limits

### ❌ BAD (function too long)
```python
def process_order_batch(orders: List[Order]) -> List[Result]:
    # 85 lines of code...
```

### ✅ GOOD (broken into smaller functions)
```python
def process_order_batch(orders: List[Order]) -> List[Result]:
    validated = validate_orders(orders)
    enriched = enrich_orders(validated)
    return execute_orders(enriched)

def validate_orders(orders: List[Order]) -> List[Order]:
    # 15 lines...
```

**Why:** Functions under 20 lines are easier to test, understand, and maintain.

---

## Summary of Priority

| Rule | Priority | Impact |
|------|----------|--------|
| SEC-001, SEC-002, SEC-003 | P0 | Security vulnerabilities |
| CC-006, TRD-001, TRD-005 | P0 | Crashes, data corruption |
| LOG-001, LOG-004 | P1 | Production debugging |
| TYP-001, TYP-003 | P2 | Code quality |
| ARCH-004 | P2 | Maintainability |

---

**Template Version:** 1.0
**Reference:** `.requirements/BASE_RULES.md`
