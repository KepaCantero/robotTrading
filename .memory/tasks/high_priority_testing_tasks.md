# 🎯 TAREAS PRIORITARIAS - TESTS Y CALIDAD

**Fecha:** 2025-01-26  
**Estado:** En progreso  
**Prioridad:** 🔴 ALTA

---

## TAREA 1 - Tests para mean_reversion.py

### Objetivo:
Crear tests completos para la estrategia MeanReversion con cobertura >= 95%.

### Archivos:
- `app/strategies/mean_reversion.py`
- `tests/strategies/test_mean_reversion.py` (crear)

### Estado Actual:
- ✅ Imports corregidos (SignalType, SignalStrength, SignalSource)
- ✅ Variables no usadas eliminadas (F841)
- ⚠️ Cobertura: 0% (0/112 líneas)

### Tests Requeridos:

#### 1. Inicialización y Configuración
```python
def test_mean_reversion_strategy_initialization():
    """Test inicialización de estrategia."""
    config = {
        "z_score_threshold": 2.0,
        "lookback_period": 20,
        "max_position_size": Decimal("0.1")
    }
    strategy = MeanReversionStrategy(config)
    assert strategy.z_score_threshold == Decimal("2.0")
    assert strategy.lookback_period == 20
```

#### 2. Generación de Señales - Uptrend
```python
def test_generate_signals_uptrend():
    """Test generación de señales en tendencia alcista."""
    # Crear datos de tendencia alcista simulando reversión
    market_data = create_market_data_uptrend()
    signals = strategy.generate_signals(market_data)
    
    assert len(signals) > 0
    assert all(s.signal_type in [SignalType.BUY, SignalType.SELL] for s in signals)
```

#### 3. Generación de Señales - Downtrend
```python
def test_generate_signals_downtrend():
    """Test generación de señales en tendencia bajista."""
    market_data = create_market_data_downtrend()
    signals = strategy.generate_signals(market_data)
    
    assert isinstance(signals, list)
    assert all(isinstance(s, Signal) for s in signals)
```

#### 4. Error Handling - Datos Insuficientes
```python
def test_generate_signals_insufficient_data():
    """Test manejo de datos insuficientes."""
    market_data = create_market_data_short(min_periods=20)
    
    with pytest.raises(InsufficientDataError):
        strategy.generate_signals(market_data)
```

#### 5. Validación de Z-Score
```python
def test_calculate_z_score():
    """Test cálculo de Z-score."""
    prices = [Decimal("100"), Decimal("102"), Decimal("99"), Decimal("101")]
    z_score = strategy._calculate_z_score(prices)
    
    assert isinstance(z_score, Decimal)
    assert -5 < float(z_score) < 5  # Rango razonable
```

### Criterios de Éxito:
- ✅ Todos los tests pasan
- ✅ Cobertura >= 95%
- ✅ No errores de sintaxis
- ✅ Código formateado (black, isort)

---

## TAREA 2 - Tests para momentum.py

### Objetivo:
Completar cobertura para estrategia Momentum >= 95%.

### Archivos:
- `app/strategies/momentum.py`
- `tests/strategies/test_momentum.py` (crear)

### Estado Actual:
- ✅ Imports corregidos
- ✅ Variables no usadas eliminadas (F841)
- ⚠️ Cobertura: 0% (0/107 líneas)

### Tests Requeridos:

#### 1. Inicialización
```python
def test_momentum_strategy_initialization():
    """Test inicialización con parámetros."""
    config = {
        "momentum_period": 14,
        "signal_threshold": Decimal("0.02")
    }
    strategy = MomentumStrategy(config)
    assert strategy.momentum_period == 14
```

#### 2. Cálculo de Momentum
```python
def test_calculate_momentum_positive():
    """Test cálculo de momentum positivo."""
    prices = [Decimal("100"), Decimal("105"), Decimal("110")]
    momentum = strategy._calculate_momentum(prices)
    
    assert momentum > 0
    assert isinstance(momentum, Decimal)
```

#### 3. Generación de Señales
```python
def test_generate_signals_strong_momentum():
    """Test señales con momentum fuerte."""
    market_data = create_market_data_strong_momentum()
    signals = strategy.generate_signals(market_data)
    
    assert len(signals) > 0
    assert all(s.signal_type == SignalType.BUY for s in signals)
```

### Criterios de Éxito: Igual que Tarea 1

---

## TAREA 3 - Tests para market_data_service.py

### Objetivo:
Incrementar cobertura de 22% → 70%+.

### Archivos:
- `app/services/market_data_service.py`
- `tests/services/test_market_data_service.py` (expandir)

### Estado Actual:
- ⚠️ Cobertura: 22% (45/203 líneas cubiertas)
- ⚠️ 158 líneas sin cubrir

### Tests a Crear:

#### 1. Fetch de Datos
```python
def test_fetch_market_data_success():
    """Test fetch exitoso de datos."""
    service = MarketDataService()
    data = await service.fetch_market_data("AAPL")
    
    assert data is not None
    assert data.symbol == "AAPL"
    assert data.bid < data.ask
```

#### 2. Error Handling - API Failure
```python
def test_fetch_market_data_api_error():
    """Test manejo de error de API."""
    with pytest.raises(MarketDataError):
        await service.fetch_market_data("INVALID")
```

#### 3. Cache y Caducidad
```python
def test_cache_expiration():
    """Test caducidad de cache."""
    # Fetch inicial
    data1 = await service.fetch_market_data("AAPL")
    
    # Esperar expiración
    await asyncio.sleep(service.cache_ttl + 1)
    
    # Segundo fetch debe refrescar cache
    data2 = await service.fetch_market_data("AAPL")
    assert data2.timestamp > data1.timestamp
```

### Criterios de Éxito:
- ✅ Cobertura >= 70%
- ✅ Tests pasan
- ✅ No errores de sintaxis

---

## TAREA 4 - Corregir F821 y F841 en strategies/

### Estado Actual:
- ✅ SignalType, SignalStrength, SignalSource: Importados
- ✅ Variables no usadas: Eliminadas (quantity)
- ✅ E203 (whitespace): Corregidos

### Archivos Corregidos:
- ✅ `app/strategies/mean_reversion.py`
- ✅ `app/strategies/momentum.py`
- ✅ `app/strategies/pairs_trading.py`

### Criterios de Éxito:
- ✅ Cero errores F821
- ✅ Cero errores F841
- ✅ Lint limpio

---

## TAREA 5 - Validación Integral

### Objetivo:
Asegurar cobertura >= 95% en TODO el proyecto.

### Estado Actual:
- ✅ 631 tests pasando (100%)
- ⚠️ Cobertura: 53% (5,503/11,680 líneas)
- ⚠️ Errores de lint: 39 (menores)

### Acciones Requeridas:

#### 1. Ejecutar Validación Completa:
```bash
pytest --cov=app --cov-report=term-missing
black app/ app/strategies/
isort app/ app/strategies/
flake8 app/ app/strategies/ --max-line-length=100
mypy app/
```

#### 2. Crear Tests para Áreas Sin Cobertura:
- `app/strategies/*`: 0% (CRÍTICO)
- `app/services/market_data_service.py`: 22%
- `app/services/paper_trading_service.py`: 16%
- `app/services/slippage_analysis_service.py`: 21%

#### 3. Mejorar Tests Existentes:
- Corregir `return True/False` → `assert`
- Remover variables no usadas
- Agregar edge cases

### Criterios de Éxito:
- ✅ Todos los tests pasando
- ✅ Cobertura >= 95%
- ✅ Código limpio, tipado correcto

---

## PLAN DE EJECUCIÓN INMEDIATO

### Fase 1 (Ahora):
1. ✅ Corrección de imports en strategies/
2. ✅ Eliminación de variables no usadas
3. ✅ Corrección de errores E203
4. ✅ Corrección de errores F821

### Fase 2 (Prioridad ALTA):
1. 🔴 Crear `tests/strategies/test_mean_reversion.py` (Tarea 1)
2. 🔴 Crear `tests/strategies/test_momentum.py` (Tarea 2)
3. 🔴 Expandir `tests/services/test_market_data_service.py` (Tarea 3)

### Fase 3 (Validación):
1. Ejecutar suite completa de tests
2. Verificar cobertura >= 95%
3. Corregir errores restantes

---

## PROGRESO ACTUAL

| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| Tarea 1 (MeanReversion tests) | ⚠️ Pendiente | 🔴 ALTA |
| Tarea 2 (Momentum tests) | ⚠️ Pendiente | 🔴 ALTA |
| Tarea 3 (MarketData tests) | ⚠️ Pendiente | 🔴 ALTA |
| Tarea 4 (Lint fixes) | ✅ Completado | ✅ |
| Tarea 5 (Validación) | 🟡 Parcial | 🟡 Media |

---

**Próximos Pasos:** Ejecutar Tarea 1, 2, 3 en orden.
