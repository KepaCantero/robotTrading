# TradingValidator Integration - Quick Reference

## Overview

TradingValidator is now **integrated into ALL live trading paths** to prevent catastrophic losses.

## What It Does

- ✅ Validates position size (max 25% of capital by default)
- ✅ Validates stop-loss is properly positioned
- ✅ Prevents over-leveraging
- ✅ Prevents trading without stop-loss (with warning)

## Broker Adapters

### Interactive Brokers (IBAdapter)

**File:** `/app/services/live_trading/broker_adapters/ib_adapter.py`

```python
from app.services.live_trading.broker_adapters.ib_adapter import IBAdapter

ib = IBAdapter()
await ib.connect()

# Trading happens automatically with validation:
# - Position size checked
# - Stop-loss validated
result = await ib.place_order(
    symbol="AAPL",
    side="BUY",
    quantity=100,
    order_type="MKT"
)
```

### Alpaca (AlpacaAdapter)

**File:** `/app/services/live_trading/broker_adapters/alpaca_adapter.py`

```python
from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter

alpaca = AlpacaAdapter()
await alpaca.connect(api_key="...", api_secret="...")

# Trading happens automatically with validation:
# - Position size checked
# - Stop-loss validated
order_id = await alpaca.place_order(
    symbol="AAPL",
    side=OrderSide.BUY,
    quantity=Decimal("100")
)
```

## Database Persistence

### get_sync_db() - Synchronous Database Sessions

**File:** `/app/core/database.py`

Use for non-async operations (like PositionMonitor persistence):

```python
from app.core.database import get_sync_db

with get_sync_db() as session:
    from app.database.models import PositionState

    # Query
    state = session.query(PositionState).filter_by(
        monitor_id="monitor_123"
    ).first()

    # Create
    new_state = PositionState(
        monitor_id="monitor_123",
        positions_json='{"positions": []}',
        last_sync=datetime.utcnow(),
        is_active=True
    )
    session.add(new_state)

    # Update
    state.positions_json = '{"positions": [...]}'  # Committed automatically
```

### PositionMonitor State Persistence

**File:** `/app/services/position_monitor/position_monitor.py`

```python
from app.services.position_monitor import PositionMonitor

monitor = PositionMonitor(broker)
await monitor.start()

# State automatically:
# - Loaded from DB on startup
# - Synced to DB every 10 seconds
# - Committed on shutdown

# Positions survive process restarts!
```

## Validation Rules

### Position Size Validation

```python
from app.core.trading_validators import TradingValidator
from decimal import Decimal

validator = TradingValidator()

# Max 25% of capital in single position
validator.validate_position_size(
    capital=Decimal("100000"),        # Available capital
    position_size=Decimal("20000"),    # Position value
    max_position_percent=Decimal("0.25")  # Max 25%
)
```

**Rules:**
- ✅ Position size must be ≤ 25% of capital (default)
- ✅ Position size cannot exceed available capital
- ✅ Both values must be positive

**Raises ValueError if:**
- Position exceeds max percentage
- Position exceeds available capital
- Invalid values (zero, negative)

### Stop-Loss Validation

```python
# For long positions
validator.validate_stop_loss(
    entry_price=Decimal("100"),
    stop_loss=Decimal("95"),  # Must be BELOW entry
    side="long"
)

# For short positions
validator.validate_stop_loss(
    entry_price=Decimal("100"),
    stop_loss=Decimal("105"),  # Must be ABOVE entry
    side="short"
)
```

**Rules:**
- ✅ Stop-loss is REQUIRED for validation (warns if missing)
- ✅ Long: stop-loss must be below entry price
- ✅ Short: stop-loss must be above entry price
- ⚠️  Warns if stop-loss is > 50% away from entry

**Raises ValueError if:**
- Stop-loss is None
- Stop-loss position is wrong for the side
- Invalid prices (zero, negative)

## Creating New Broker Adapters

Always integrate TradingValidator:

```python
from app.core.trading_validators import TradingValidator
from decimal import Decimal

class MyBrokerAdapter:
    def __init__(self):
        # CRITICAL: Initialize validator
        self.validator = TradingValidator()

    async def place_order(self, symbol, side, quantity, **kwargs):
        # CRITICAL STEP 1: Get available capital
        account = await self.get_account()
        available_capital = account.cash_available

        # CRITICAL STEP 2: Calculate position value
        price = kwargs.get('price') or await self.get_current_price(symbol)
        position_value = Decimal(str(quantity)) * Decimal(str(price))

        # CRITICAL STEP 3: Validate position size
        self.validator.validate_position_size(
            capital=available_capital,
            position_size=position_value,
            max_position_percent=Decimal("0.25")
        )

        # CRITICAL STEP 4: Validate stop-loss if provided
        stop_loss = kwargs.get('stop_price')
        if stop_loss:
            self.validator.validate_stop_loss(
                entry_price=Decimal(str(price)),
                stop_loss=Decimal(str(stop_loss)),
                side='long' if side == 'BUY' else 'short'
            )
        else:
            logger.warning("Order without stop-loss - ensure risk is managed")

        # CRITICAL STEP 5: Execute order
        return await self._execute_order(symbol, side, quantity, **kwargs)
```

## Database Migration

### Applying the Migration

```bash
# Check current version
alembic current

# Apply migration
alembic upgrade head

# Verify
alembic history
```

### Manual Table Creation (if not using Alembic)

```python
import asyncio
from app.core.database import init_database

async def create_tables():
    await init_database()
    print("Tables created successfully")

asyncio.run(create_tables())
```

## Troubleshooting

### "get_sync_db not found"

**Error:** `ImportError: cannot import name 'get_sync_db'`

**Solution:**
```python
# Correct import
from app.core.database import get_sync_db

# Also available from
from app.database import get_sync_db
```

### "Position size validation failed"

**Error:** `ValueError: Position size $50000.00 exceeds maximum allowed $25000.00`

**Solution:**
- Reduce position size
- Increase max_position_percent (if appropriate)
- Check available capital is correct

### "Stop-loss validation failed"

**Error:** `ValueError: Long position stop-loss ($105.00) must be BELOW entry price ($100.00)`

**Solution:**
- For long positions: stop_loss < entry_price
- For short positions: stop_loss > entry_price

### PositionMonitor not persisting

**Symptom:** Positions lost on restart

**Solution:**
1. Ensure database is initialized:
   ```python
   await init_database()
   ```

2. Check position_states table exists:
   ```sql
   SELECT * FROM position_states;
   ```

3. Enable persistence in config:
   ```python
   config = PositionMonitorConfig(persist_state=True)
   monitor = PositionMonitor(broker, config=config)
   ```

## Testing

### Unit Tests

```python
def test_trading_validator():
    from app.core.trading_validators import TradingValidator
    from decimal import Decimal

    validator = TradingValidator()

    # Should pass
    validator.validate_position_size(
        capital=Decimal("100000"),
        position_size=Decimal("20000")
    )

    # Should fail
    try:
        validator.validate_position_size(
            capital=Decimal("100000"),
            position_size=Decimal("30000")  # Too large
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
```

### Integration Tests

```python
async def test_broker_validation():
    from app.services.live_trading.broker_adapters.ib_adapter import IBAdapter

    ib = IBAdapter()
    await ib.connect()

    # Should validate before placing
    result = await ib.place_order(
        symbol="AAPL",
        side="BUY",
        quantity=1000000  # Too large - should fail validation
    )

    assert 'error' in result
    assert 'exceeds maximum' in result['error']
```

## Safety Checklist

Before deploying to production:

- [ ] TradingValidator integrated into ALL broker adapters
- [ ] get_sync_db() working correctly
- [ ] PositionMonitor persisting state
- [ ] Database migration applied
- [ ] Stop-loss validation tested
- [ ] Position size limits tested
- [ ] Logs monitored for validation failures
- [ ] Paper trading tested first

## Configuration

### Adjusting Position Limits

```python
# In your adapter, change max_position_percent
self.validator.validate_position_size(
    capital=available_capital,
    position_size=position_value,
    max_position_percent=Decimal("0.10")  # 10% instead of 25%
)
```

### Adjusting Sync Interval

```python
# PositionMonitor state sync interval
config = PositionMonitorConfig(
    persist_state=True,
    state_sync_interval_seconds=5.0  # Sync every 5 seconds (default: 10)
)
monitor = PositionMonitor(broker, config=config)
```

---

## Important Notes

1. **Validation happens BEFORE order placement** - rejects invalid orders
2. **Stop-loss is warned but not enforced** - some strategies don't use SL
3. **State persistence is automatic** - survives restarts
4. **All broker adapters must integrate TradingValidator** - safety first

---

For detailed implementation, see: `CRITICAL_FIXES_IMPLEMENTATION_SUMMARY.md`
