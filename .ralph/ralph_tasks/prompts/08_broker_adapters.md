#  Broker Adapters (IBKR Spain) - Prompt

**Tarea ID:** 08_broker_adapters
**Propósito:** Implementar adaptador IBKR funcional para España (EUR, IBEX35)
**Tiempo estimado:** 16 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar adaptador Interactive Brokers funcional para trading en España:
- Conexión API IBKR
- Conversión EUR/USD
- Soporte IBEX35
- Ejecución de órdenes
- Consulta de posiciones

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/live_trading/broker_adapters/ibkr_adapter_spain.py**
   - IBKRAdapterSpain
   - connect() / disconnect()
   - place_order() / cancel_order()
   - get_positions() / get_account()

2. **app/services/live_trading/broker_adapters/currency_converter.py**
   - CurrencyConverter
   - convert_to_eur() - USD → EUR
   - get_exchange_rate() - Tipo de cambio actual

3. **app/services/live_trading/broker_adapters/__init__.py**

### Archivos a modificar:

4. **app/services/live_trading/broker_adapters/ib_adapter.py**
   - Completar TODOs existentes
   - Integrar con IBKRAdapterSpain

---

##  REQUISITOS TÉCNICOS

### IBKR Adapter Spain

```python
from decimal import Decimal
from typing import list, dict, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# @skip-import: IB API not installed yet
# TODO: Install ibapi package
from ibapi.client import EClient  # type: ignore
from ibapi.wrapper import EWrapper  # type: ignore
from ibapi.contract import Contract  # type: ignore
from ibapi.order import Order  # type: ignore
from app.core.protocols.i_broker_adapter import IBrokerAdapter  # type: ignore


class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Tipo de orden"""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"


@dataclass
class IBKROrder:
    """Orden para IBKR"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK


@dataclass
class IBKRPosition:
    """Posición en IBKR"""
    symbol: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    currency: str


class IBKRAdapterSpain(EClient, EWrapper, IBrokerAdapter):
    """
    Adaptador IBKR para España

    Características:
    - Conexión a IBKR TWS o IB Gateway
    - Conversión automática USD → EUR
    - Soporte para IBEX35 (acciones españolas)
    - Manejo de errores específicos de España
    """

    # IBKR Connection settings
    TWS_PORT = 7497
    GATEWAY_PORT = 4001
    HOST = "127.0.0.1"

    # IBEX35 symbols (principales)
    IBEX35_SYMBOLS = {
        "SAN", "REE", "TEF", "ITX", "AMS", "ACS", "FER", "IAG",
        "BME", "ENG", "MAP", "SAB", "CLNX", "VIS", "COL", "MRL"
    }

    def __init__(self, client_id: int = 1):
        """
        Args:
            client_id: ID único para conexión IBKR (0-999)
        """
        EClient.__init__(self, self)
        self._client_id = client_id
        self._connected = False
        self._account_id: Optional[str] = None
        self._currency_converter = CurrencyConverter()

    def connect(self, host: str = None, port: int = None, client_id: int = None) -> bool:
        """
        Conecta a IBKR TWS o Gateway

        Args:
            host: Host IP (default: 127.0.0.1)
            port: Puerto (default: 7497 para TWS, 4001 para Gateway)
            client_id: ID cliente (default: self._client_id)

        Returns:
            True si conexión exitosa
        """
        host = host or self.HOST
        port = port or self.TWS_PORT
        client_id = client_id or self._client_id

        try:
            self.connect(host, port, client_id)
            return True
        except Exception as e:
            # @todo: Implementar logging de errores
            print(f"Error connecting to IBKR: {e}")
            return False

    def disconnect(self) -> None:
        """Desconecta de IBKR"""
        if self._connected:
            self.disconnect()
            self._connected = False

    def place_order(self, order: IBKROrder) -> dict:
        """
        Envía orden a IBKR

        Args:
            order: Orden a ejecutar

        Returns:
            Dict con resultado de orden
        """
        if not self._connected:
            raise ConnectionError("Not connected to IBKR")

        # Crear contract
        contract = self._create_contract(order.symbol)

        # Crear order IBKR
        ib_order = self._create_ibkr_order(order)

        # Enviar orden
        # @todo: Implementar order tracking
        order_id = self._get_next_order_id()

        self.placeOrder(
            orderId=order_id,
            contract=contract,
            order=ib_order
        )

        return {
            "order_id": order_id,
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity
        }

    def get_positions(self) -> list[IBKRPosition]:
        """
        Obtiene posiciones desde IBKR

        Returns:
            Lista de posiciones en IBKR
        """
        if not self._connected:
            raise ConnectionError("Not connected to IBKR")

        # Solicitar posiciones
        self.reqPositions()

        # @todo: Implementar await de respuesta
        # Por ahora, retornar lista vacía
        return []

    def get_account(self) -> dict:
        """
        Obtiene información de cuenta

        Returns:
            Dict con balance, equity, margin, etc.
        """
        if not self._connected:
            raise ConnectionError("Not connected to IBKR")

        # Solicitar summary de cuenta
        if self._account_id:
            self.reqAccountSummary(
                reqId=1,
                groupName="All",
                tags: "$LEDGER:$LEDGER:CURRENCY"
            )

        # @todo: Implementar await de respuesta
        return {
            "account_id": self._account_id,
            "currency": "EUR",
            "balance": Decimal("0"),
            "equity": Decimal("0"),
            "margin_available": Decimal("0")
        }

    def _create_contract(self, symbol: str) -> Contract:
        """
        Crea contract IBKR para symbol

        Args:
            symbol: Símbolo a crear contract

        Returns:
            Contract object de IBKR
        """
        contract = Contract()

        # Si es IBEX35, usar SMART routing en España
        if symbol in self.IBEX35_SYMBOLS:
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "MIBER"  # Madrid (BME)
            contract.currency = "EUR"

        # Si es US stock
        else:
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"

        return contract

    def _create_ibkr_order(self, order: IBKROrder) -> Order:
        """
        Crea Order object de IBKR

        Args:
            order: Nuestra orden

        Returns:
            Order object de IBKR
        """
        ib_order = Order()

        ib_order.action = order.side.value
        ib_order.totalQuantity = order.quantity
        ib_order.orderType = order.order_type.value
        ib_order.tif = order.time_in_force

        if order.limit_price:
            ib_order.lmtPrice = float(order.limit_price)

        if order.stop_price:
            ib_order.auxPrice = float(order.stop_price)

        return ib_order

    def _get_next_order_id(self) -> int:
        """
        Obtiene próximo ID de orden

        @todo: Implementar usando reqIds() de IBKR
        """
        return 1  # Placeholder
```

### Currency Converter

```python
from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta
import requests  # @skip-import if not available


class CurrencyConverter:
    """
    Convertidor de divisas USD ↔ EUR

    Obtiene tipos de cambio desde fuentes públicas
    y mantiene cache para evitar llamadas excesivas.
    """

    # Cache de tasas: (currency_pair, date) -> rate
    _rate_cache: dict[tuple[str, str], Decimal] = {}

    # Cache expiry: 1 hora
    _cache_expiry = timedelta(hours=1)

    # ECB API endpoint
    ECB_API_URL = "https://api.exchangerate.host/latest"

    def get_exchange_rate(
        self,
        from_currency: str = "USD",
        to_currency: str = "EUR"
    ) -> Decimal:
        """
        Obtiene tipo de cambio actual

        Args:
            from_currency: Moneda origen (default: USD)
            to_currency: Moneda destino (default: EUR)

        Returns:
            Tipo de cambio (ej: 0.92 para USD→EUR)
        """
        cache_key = (from_currency, to_currency)
        today = datetime.now().date()

        # Verificar cache
        if cache_key in self._rate_cache:
            return self._rate_cache[cache_key]

        # Obtener desde API
        try:
            response = requests.get(
                f"{self.ECB_API_URL}",
                params={"base": from_currency, "symbols": to_currency},
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            rate = Decimal(str(data["rates"][to_currency]))

            # Guardar en cache
            self._rate_cache[cache_key] = rate

            return rate

        except Exception as e:
            # @todo: Implementar logging
            # Fallback a tasa hardcoded
            if from_currency == "USD" and to_currency == "EUR":
                return Decimal("0.92")  # Tasa aproximada
            raise

    def convert_to_eur(
        self,
        amount: Decimal,
        from_currency: str = "USD"
    ) -> Decimal:
        """
        Convierte monto a EUR

        Args:
            amount: Monto a convertir
            from_currency: Moneda origen

        Returns:
            Monto en EUR
        """
        if from_currency == "EUR":
            return amount

        rate = self.get_exchange_rate(from_currency, "EUR")
        return amount * rate

    def convert_from_eur(
        self,
        amount_eur: Decimal,
        to_currency: str = "USD"
    ) -> Decimal:
        """
        Convierte desde EUR

        Args:
            amount_eur: Monto en EUR
            to_currency: Moneda destino

        Returns:
            Monto en moneda destino
        """
        if to_currency == "EUR":
            return amount_eur

        rate = self.get_exchange_rate("EUR", to_currency)
        return amount_eur * rate
```

### Restricciones:

-   IBEX35 symbols deben usar exchange "MIBER"
-   US stocks usan exchange "SMART" con currency "USD"
-   Conversión automática USD → EUR para valores
-   Tasa de cambio cacheada por 1 hora
-   Manejo de errores de conexión IBKR

---

##  VALIDACIÓN

### Validación de archivos:

```bash
# 1. Verificar archivos creados
ls -la app/services/live_trading/broker_adapters/

# 2. Validar cada archivo
for f in app/services/live_trading/broker_adapters/*.py; do
  python .ralph/scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar IBEX35 symbols
grep "IBEX35" app/services/live_trading/broker_adapters/ibkr_adapter_spain.py
grep "MIBER\|MADRID" app/services/live_trading/broker_adapters/ibkr_adapter_spain.py

# 4. Verificar conversión EUR
grep "convert_to_eur\|get_exchange_rate" app/services/live_trading/broker_adapters/currency_converter.py
```

### Tests manuales (requiere conexión IBKR):

```python
# Test Currency Converter
converter = CurrencyConverter()
rate = converter.get_exchange_rate("USD", "EUR")
print(f"USD → EUR rate: {rate}")

eur_amount = converter.convert_to_eur(Decimal("100"), "USD")
print(f"$100 = €{eur_amount}")

# Test IBKR Contract Creation
adapter = IBKRAdapterSpain()
contract = adapter._create_contract("SAN")
assert contract.exchange == "MIBER"
assert contract.currency == "EUR"

contract = adapter._create_contract("AAPL")
assert contract.exchange == "SMART"
assert contract.currency == "USD"
```

---

##  CHECKPOINT

```json
{
  "task_id": "08_broker_adapters",
  "task_name": "Broker Adapters (IBKR Spain) Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-09T02:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 4,
    "created_files": 3,
    "modified_files": 1,
    "validated_files": 4
  },
  "outputs": {
    "files_created": [
      "app/services/live_trading/broker_adapters/__init__.py",
      "app/services/live_trading/broker_adapters/ibkr_adapter_spain.py",
      "app/services/live_trading/broker_adapters/currency_converter.py"
    ],
    "files_modified": [
      "app/services/live_trading/broker_adapters/ib_adapter.py"
    ],
    "ibex35_support": true,
    "eur_usd_conversion": true,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "09_compliance_engine_refactor",
  "errors": [],
  "warnings": ["IBAPI package installation required", "IBKR TWS/Gateway required for testing"],
  "timestamp": "2026-02-09T02:00:00Z"
}
```

---

##  SUCCESS CRITERIA

- [ ] 3 archivos creados (+ 1 modificado)
- [ ] IBKRAdapterSpain implementa IBrokerAdapter
- [ ] IBEX35 symbols definidos (17 tickers)
- [ ] CurrencyConverter con cache de 1 hora
- [ ] Conversión USD → EUR implementada
- [ ] Todos los archivos validan
- [ ] Tests manuales pasan (sin conexión IBKR)
- [ ] Checkpoint creado

---

##  DEPENDENCIAS EXTERNAS

```bash
# Instalar IB API
pip install ibapi

# Instalar requests para API de divisas
pip install requests
```

---

##  REFERENCIAS

- IBKR API Documentation: https://interactivebrokers.github.io/tws-api/
- `.ralph/docs/realistic_trading_rules.md` - Live Trading rules
- `.ralph/rules/rules_mapping.yml` - Broker adapter rules
