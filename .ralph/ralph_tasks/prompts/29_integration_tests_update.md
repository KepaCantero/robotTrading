# Integration Tests Update - Prompt

**Tarea ID:** 29_integration_tests_update
**Propósito:** Actualizar integration tests
**Tiempo estimado:** 8 horas
**Prioridad:** P0 (Crítica)
**Depends on:** 09, 10, 11, 12 (Integration layer)

---

## OBJETIVO

Integration tests actualizados para reflejar la nueva arquitectura.

## ESTRUCTURA

```
tests/integration/
├── compliance/
│   ├── test_compliance_engine.py
│   ├── test_pre_trade_validator.py
│   └── test_risk_validators.py
├── execution/
│   ├── test_order_manager.py
│   └── test_broker_adapter.py
└── backtesting/
    └── test_backtest_engine.py
```

## TESTS REQUERIDOS

### Compliance Engine
```python
@pytest.mark.integration
async def test_execute_trade_full_flow():
    """Test complete trade execution flow"""
    signal = create_test_signal()
    result = await compliance_engine.execute_trade(signal, portfolio)

    assert result.success
    assert result.validation.kelly_passed
    assert result.validation.rr_ratio >= 2.0
```

### Order Manager
```python
@pytest.mark.integration
async def test_order_manager_uses_compliance():
    """Test OrderManager delegates to ComplianceEngine"""
    order_manager = create_order_manager()

    result = await order_manager.place_order(signal)

    assert result.executed
    assert result.correlation_id
```

### Broker Adapter
```python
@pytest.mark.integration
async def test_alpaca_adapter_connection():
    """Test Alpaca broker connection"""
    adapter = create_alpaca_adapter()

    connected = await adapter.connect()
    assert connected
```

## SUCCESS CRITERIA

- [ ] All integration tests pass
- [ ] Coverage > 80%
- [ ] No flaky tests
