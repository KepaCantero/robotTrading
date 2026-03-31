# 📗 21. "Test-Driven Development with Python" - Harry Percival

## REGLAS DE TDD PARA SISTEMAS FINANCIEROS

**Regla 21.1 — Red-Green-Refactor**

Claude DEBE escribir tests ANTES de lógica:
- NO escribir lógica de cálculo sin test que falle primero

```python
# 1. RED - escribir test que falla
def test_kelly_criterion():
    """Test de Kelly criterion - debe fallar."""
    win_rate = 0.55
    avg_win = 100
    avg_loss = 80

    kelly = calculate_kelly(win_rate, avg_win, avg_loss)

    # Esto fallará porque calculate_kelly no existe aún
    assert kelly == pytest.approx(0.2375)

# 2. GREEN - implementar mínimo para pasar test
def calculate_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly criterion - implementación mínima."""
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    return kelly * 0.5  # Half-Kelly

# 3. REFACTOR - mejorar código manteniendo tests verdes
def calculate_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly criterion - refactorizado."""
    if avg_loss <= 0:
        raise ValueError("avg_loss must be positive")

    edge = win_rate * avg_win - (1 - win_rate) * avg_loss
    kelly = edge / avg_win

    # Half-Kelly, max 25%
    return max(0.0, min(kelly * 0.5, 0.25))
```

**Regla 21.2 — Property-Based Testing**

Claude DEBE usar Hypothesis para generar miles de casos:
- Precios negativos, volúmenes de 0, saltos gigantes

```python
from hypothesis import given, strategies as st
import pytest

@given(
    prices=st.lists(
        st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False),
        min_size=2
    )
)
def test_returns_are_non_nan(prices):
    """Property: returns nunca deben ser NaN."""
    returns = calculate_returns(prices)
    assert not any(np.isnan(returns))

@given(
    price=st.floats(min_value=0.01, max_value=1000000),
    quantity=st.integers(min_value=1, max_value=1000000)
)
def test_order_value_is_positive(price, quantity):
    """Property: valor de orden siempre positivo."""
    order_value = price * quantity
    assert order_value > 0

@given(
    returns=st.lists(
        st.floats(min_value=-0.5, max_value=0.5, allow_nan=False),
        min_size=30
    )
)
def test_sharpe_ratio_bounds(returns):
    """Property: Sharpe ratio debe estar en bounds razonables."""
    sharpe = calculate_sharpe(returns)
    # Sharpe debe ser > -10 y < 10 (valores extremos)
    assert -10 < sharpe < 10
```

**Regla 21.3 — Mocking Externo**

Claude DEBE usar unittest.mock para simular API broker:
- Tests no deben necesitar internet

```python
from unittest.mock import Mock, patch
import pytest

def test_execution_with_mocked_broker():
    """Test de ejecución con broker mock."""
    # Crear mock de broker
    mock_broker = Mock()
    mock_broker.execute_order.return_value = Execution(
        order_id="123",
        status="FILLED",
        filled_quantity=100,
        filled_price=150.0
    )

    # Inyectar mock
    executor = ExecutionService(mock_broker)

    # Ejecutar orden
    order = Order("AAPL", 100, 150.0, "BUY")
    execution = executor.execute(order)

    # Verificar llamada
    mock_broker.execute_order.assert_called_once_with(order)
    assert execution.status == "FILLED"
    assert execution.filled_price == 150.0

@patch('trading_bot.broker.BrokerAPI')
def test_strategy_with_mocked_api(mock_api_class):
    """Test de estrategia con API mock."""
    # Configurar mock
    mock_api = mock_api_class.return_value
    mock_api.get_quotes.return_value = [
        Quote("AAPL", 150.0, 149.9, 150.1),
        Quote("AAPL", 151.0, 150.9, 151.1)
    ]

    # Usar mock
    strategy = Strategy(mock_api)
    signal = strategy.generate_signal("AAPL")

    # Verificar
    mock_api.get_quotes.assert_called_once_with("AAPL", days=252)
```

**Regla 21.4 — Regression Tests**

Claude DEBE escribir test que reproduzca bug antes de arreglar:
- Así el bug nunca vuelve

```python
# Bug encontrado: estrategia devuelve señal cuando no debería
def test_regression_no_signal_on_insufficient_data():
    """Regression test: no señal con datos insuficientes."""
    # Este bug ocurrió en producción
    strategy = MomentumStrategy(lookback=252)

    # Solo 100 días de datos (insuficiente para lookback 252)
    prices = generate_test_prices(n_days=100)

    signal = strategy.generate_signal(prices)

    # Bug: antes retornaba 1 (BUY)
    # Fix: debe retornar 0 (HOLD)
    assert signal == 0, "No debe generar señal con datos insuficientes"

# Una vez arreglado bug, este test lo previene
```

**Regla 21.5 — Floating Point Assertions**

Claude DEBE usar pytest.approx para precios:
- NUNCA usar assert a == b

```python
def test_floating_point_comparisons():
    """Comparaciones de punto flotante."""
    price1 = 1.0000000001
    price2 = 1.0000000002

    # ❌ MAL - puede fallar por precisión
    assert price1 == price2

    # ✅ BIEN - pytest.approx maneja precisión
    assert price1 == pytest.approx(price2)

    # Con tolerancia específica
    assert 150.0001 == pytest.approx(150.0, abs=0.001)

    # Para cálculos financieros
    def test_calculate_position_value():
        quantity = 100
        price = 150.123456789
        expected_value = 15012.3456789

        actual_value = quantity * price

        # Usar approx con tolerancia relativa
        assert actual_value == pytest.approx(expected_value, rel=1e-6)
```

**Regla 21.6 — Deterministic Tests**

Claude DEBE fijar seed en tests con aleatoriedad:
- Tests deben ser reproducibles

```python
import random
import numpy as np

def test_with_randomness():
    """Test con aleatoriedad - fijar seed."""
    # Fijar seeds
    random.seed(42)
    np.random.seed(42)

    # Generar datos aleatorios
    returns = np.random.normal(0, 0.02, 252)

    # Calcular Sharpe
    sharpe = calculate_sharpe(returns)

    # Debido a seed fija, Sharpe siempre será el mismo
    assert sharpe == pytest.approx(0.987, abs=0.01)

# Usar fixture de pytest
@pytest.fixture
def random_data():
    """Fixture con datos aleatorios reproducibles."""
    np.random.seed(42)
    return np.random.normal(0, 0.02, 252)

def test_sharpe_with_fixture(random_data):
    """Test usando fixture reproducible."""
    sharpe = calculate_sharpe(random_data)
    assert sharpe == pytest.approx(0.987, abs=0.01)
```

**Regla 21.7 — Data Fixtures**

Claude DEBE crear set de datos "dorado":
- CSV con crash, lateral, alcista
- Pasar por estrategias en cada commit

```python
@pytest.fixture
def market_scenarios():
    """Escenarios de mercado 'dorado' para testing."""
    scenarios = {
        "crash_2008": load_csv("fixtures/crash_2008.csv"),
        "bull_2019": load_csv("fixtures/bull_2019.csv"),
        "sideways_2015": load_csv("fixtures/sideways_2015.csv")
    }
    return scenarios

def test_strategy_all_scenarios(market_scenarios):
    """Test estrategia en todos los escenarios."""
    strategy = MomentumStrategy()

    for scenario_name, prices in market_scenarios.items():
        returns = backtest(strategy, prices)

        # Criterios mínimos
        assert returns["sharpe"] > 0.5, f"Sharpe too low in {scenario_name}"
        assert returns["max_drawdown"] < 0.30, f"DD too high in {scenario_name}"

        print(f"{scenario_name}: Sharpe={returns['sharpe']:.2f}, DD={returns['max_drawdown']:.2%}")
```

**Regla 21.8 — Test Coverage**

Claude DEBE apuntar a 90% de cobertura:
- En carpetas domain/ y strategies/

```python
# pytest.ini
[pytest]
addopts =
    --cov=domain
    --cov=strategies
    --cov=execution
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90

# Ejecutar: pytest
# Output:
# name                      stmts   miss  cover
# ---------------------------------------------
# domain/__init__.py          10      0   100%
# domain/models.py            50      2    96%
# strategies/__init__.py      30      3    90%
# strategies/momentum.py      80      8    90%
# ---------------------------------------------
# TOTAL                      170     13    92%
#
# Required test coverage 90%, reached 92%
```

**Regla 21.9 — Integration Tests**

Claude DEBE dedicar tests a verificar conexión:
- Bot puede conectarse y autenticarse con broker
- Usando credenciales de Sandbox

```python
@pytest.mark.integration
def test_broker_connection():
    """Test de integración: conexión real con sandbox."""
    # Usar credenciales de sandbox (no dinero real)
    broker = AlpacaBroker(
        api_key=os.getenv("ALPACA_SANDBOX_API_KEY"),
        api_secret=os.getenv("ALPACA_SANDBOX_API_SECRET"),
        sandbox=True  # Sandbox mode
    )

    # Test conexión
    account = broker.get_account()

    assert account is not None
    assert account.status == "ACTIVE"

    # Test autenticación
    balance = broker.get_balance()
    assert balance >= 0

@pytest.mark.integration
def test_order_execution_sandbox():
    """Test de integración: ejecución real en sandbox."""
    broker = AlpacaBroker(sandbox=True)

    # Crear orden pequeña
    order = Order("AAPL", 1, 150.0, "BUY")

    # Ejecutar (sandbox, no dinero real)
    execution = broker.execute_order(order)

    assert execution.status == "FILLED"
    assert execution.filled_quantity == 1
```

**Regla 21.10 — Performance Testing**

Claude DEBE escribir tests que midan tiempo:
- Si tiempo sube de 10ms a 100ms, test debe fallar

```python
import time

def test_signal_generation_performance():
    """Test de performance: generación de señal."""
    strategy = MomentumStrategy()
    prices = generate_test_prices(n_days=252 * 10)  # 10 años

    start_time = time.time()
    signal = strategy.generate_signal(prices)
    elapsed_ms = (time.time() - start_time) * 1000

    # Debe tomar < 100ms
    assert elapsed_ms < 100, f"Too slow: {elapsed_ms}ms"

@pytest.mark.parametrize("n_prices", [100, 1000, 10000])
def test_scalability(n_prices):
    """Test de escalabilidad."""
    strategy = MomentumStrategy()
    prices = generate_test_prices(n_days=n_prices)

    start_time = time.time()
    strategy.generate_signal(prices)
    elapsed = time.time() - start_time

    # Debe escalar linealmente (O(n))
    # Si n_prices se multiplica por 10, elapsed se multiplica por ~10
    expected_max = n_prices * 0.0001  # 0.1ms por precio
    assert elapsed < expected_max
```

**Regla 21.11 — Isolation**

Claude DEBE limpiar estado antes de cada test:
- Un test no debe depender del anterior

```python
@pytest.fixture
def clean_database():
    """Fixture que limpia DB antes y después del test."""
    # Setup: limpiar DB
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM positions")
    db.commit()

    yield

    # Teardown: limpiar DB
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM positions")
    db.commit()

def test_order_creation(clean_database):
    """Test aislado - DB limpia antes y después."""
    repo = OrderRepository(db)

    repo.add(Order("AAPL", 100, 150.0, "BUY"))

    # Verificar que solo hay 1 orden (no residuos de tests anteriores)
    orders = repo.get_all()
    assert len(orders) == 1
```

**Regla 21.12 — Parametrización**

Claude DEBE usar @pytest.mark.parametrize:
- Probar misma lógica con diferentes activos
- Sin repetir código

```python
@pytest.mark.parametrize("symbol,expected_sharpe", [
    ("AAPL", 1.2),
    ("MSFT", 1.1),
    ("GOOGL", 1.3),
    ("AMZN", 0.9),
])
def test_strategy_multiple_symbols(symbol, expected_sharpe):
    """Test estrategia parametrizado con múltiples símbolos."""
    strategy = MomentumStrategy()
    prices = load_historical_prices(symbol)

    returns = backtest(strategy, prices)

    assert returns["sharpe"] == pytest.approx(expected_sharpe, abs=0.2)

@pytest.mark.parametrize("lookback,threshold", [
    (21, 0.02),
    (63, 0.03),
    (252, 0.10),
])
def test_strategy_parameters(lookback, threshold):
    """Test estrategia con diferentes parámetros."""
    strategy = MomentumStrategy(lookback=lookback, threshold=threshold)
    prices = generate_test_prices(n_days=500)

    signal = strategy.generate_signal(prices)

    # Señal debe estar en [-1, 1]
    assert -1 <= signal <= 1
```

**Regla 21.13 — Continuous Integration (CI)**

Claude DEBE configurar GitHub Actions:
- Ejecutar todos los tests en cada push
- Si tests fallan, código no se sube

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run unit tests
      run: pytest tests/unit/ --cov=domain --cov=strategies

    - name: Run integration tests
      env:
        ALPACA_SANDBOX_API_KEY: ${{ secrets.ALPACA_SANDBOX_API_KEY }}
        ALPACA_SANDBOX_API_SECRET: ${{ secrets.ALPACA_SANDBOX_API_SECRET }}
      run: pytest tests/integration/ -m integration

    - name: Check coverage
      run: |
        coverage report --fail-under=90
```

**Regla 21.14 — Snapshot Testing**

Claude DEBE guardar estado final esperado:
- Comparar con resultado actual
- Detectar desviaciones sutiles

```python
from syrupy import SnapshotAssertion

def test_backtest_snapshot(snapshot: SnapshotAssertion):
    """Test de snapshot: backtest debe producir mismo resultado."""
    strategy = MomentumStrategy()
    prices = load_test_data()

    result = backtest(strategy, prices)

    # Comparar con snapshot guardado
    assert result == snapshot

# Primer run: crea snapshot
# test_backtest_snapshot/amazing_test_name/amazing_output.txt
# {
#   "sharpe": 1.23,
#   "max_drawdown": 0.15,
#   "total_return": 0.45,
#   "n_trades": 52
# }

# Runs subsiguientes: comparan con snapshot
# Si cambias algo en strategy que afecta resultado, test falla
```

**Regla 21.15 — Side-Effect Testing**

Claude DEBE verificar no solo retorno, sino efectos:
- ¿Se llamó a función de enviar alerta?

```python
from unittest.mock import patch, call

def test_alert_on_drawdown():
    """Test: alerta se envía cuando DD > 5%."""
    with patch('trading_bot.send_telegram_alert') as mock_alert:
        strategy = MomentumStrategy()
        strategy.max_drawdown_limit = 0.05

        # Simular drawdown > 5%
        strategy.update_equity(current_drawdown=0.06)

        # Verificar que se llamó a alerta
        mock_alert.assert_called_once()
        mock_alert.assert_called_with(
            "⚠️ Max Drawdown exceeded: 6.0%"
        )

def test_no_alert_on_normal_drawdown():
    """Test: no alerta cuando DD < 5%."""
    with patch('trading_bot.send_telegram_alert') as mock_alert:
        strategy = MomentumStrategy()
        strategy.max_drawdown_limit = 0.05

        # Drawdown normal
        strategy.update_equity(current_drawdown=0.03)

        # Verificar que NO se llamó a alerta
        mock_alert.assert_not_called()
```
