# 🚀 AlgoTrading - Paper Trading Guía de Inicio

## 📋 Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración Inicial](#configuración-inicial)
3. [Iniciar Paper Trading](#iniciar-paper-trading)
4. [Conectar Interactive Brokers](#conectar-interactive-brokers)
5. [Conectar Fuentes de Datos](#conectar-fuentes-de-datos)
6. [Próximos Pasos](#próximos-pasos)

---

## Requisitos Previos

### Software Necesario

```bash
# Python 3.9+
python3 --version

# pip (gestor de paquetes)
pip --version

# git (opcional, para control de versiones)
git --version
```

### Instalar Dependencias

```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno virtual
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración Inicial

### 1. Crear Archivo .env

```bash
# Copiar plantilla de configuración
cp .env.example .env

# Editar con tus API keys
nano .env  # o tu editor favorito
```

### 2. Configuración Mínima Requerida

Edita `.env` y configura al menos estos parámetros:

```bash
# ============================================================================
# CONFIGURACIÓN MÍNIMA PARA PAPER TRADING
# ============================================================================

# Base de datos
DATABASE_URL=sqlite:///./data/algo_trading.db

# Trading Paper
PAPER_TRADING_ENABLED=True
PAPER_TRADING_INITIAL_CAPITAL=100000
PAPER_TRADING_COMMISSION_PER_TRADE=1.0

# Gestión de Riesgo
RISK_PER_TRADE_PERCENT=2.0
RISK_REWARD_RATIO=3.0
MAX_DRAWDOWN_LIMIT_PERCENT=15.0

# Nivel de log
LOG_LEVEL=INFO
```

### 3. Crear Directorios Necesarios

```bash
mkdir -p logs data
```

---

## Iniciar Paper Trading

### Opción 1: Script Automático (Recomendado)

```bash
# Iniciar todo (API + Dashboard)
./start_paper_trading.sh

# Detener todo
./stop_paper_trading.sh
```

### Opción 2: Inicio Manual

#### Terminal 1 - API Server

```bash
source .venv/bin/activate

uvicorn app.api.paper_trading:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
```

#### Terminal 2 - Dashboard

```bash
source .venv/bin/activate

streamlit run app/dashboard/advanced_dashboard.py
```

### Opción 3: Script Python

```bash
source .venv/bin/activate

python -m app.scripts.start_paper_trading \
    --capital 100000 \
    --commission 1.0 \
    --session-name "MiSesion"
```

---

## Acceder al Sistema

Una vez iniciado, podrás acceder a:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Interfaz visual principal |
| **API** | http://localhost:8000 | API REST |
| **Documentación API** | http://localhost:8000/docs | Swagger UI |

---

## Conectar Interactive Brokers

### 1. Instalar TWS o IB Gateway

1. Descarga [TWS](https://www.interactivebrokers.com/en/trading/tws.php) o [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
2. Instala y configura con tu cuenta de paper trading

### 2. Configurar TWS/IB Gateway

1. Abre TWS/IB Gateway
2. Ve a **File → Global Configuration**
3. Configura:
   - **API → Settings**: Enable ActiveX and Socket Clients
   - **Socket Port**: 7497 (paper trading) o 7496 (live trading)
   - **Uncheck Read-Only API**
   - **Master API ID**: 0
   - **Api Clients → Allow incoming connection**: Habilitar

### 3. Configurar en .env

```bash
# ============================================================================
# INTERACTIVE BROKERS CONFIGURATION
# ============================================================================
IB_PORT=7497           # Puerto paper trading (7497) o live (7496)
IB_HOST=127.0.0.1      # Localhost
IB_CLIENT_ID=1         # ID único por conexión (auto-generado si no se especifica)
IB_ACCOUNT=DU9811225   # Tu cuenta de paper trading (opcional)
IB_PAPER_TRADING=True  # True para paper, False para real
```

### 4. Instalar Dependencias

```bash
# Instalar ib-insync
pip install ib-insync>=0.5.0
```

### 5. Verificar Conexión

```bash
# Opción 1: Script Python
python -c "
import asyncio
from app.services.live_trading.broker_adapters.ib_adapter import IBAdapter

async def test():
    adapter = IBAdapter()
    connected = await adapter.connect()
    print(f'Conectado: {connected}')

    if connected:
        # Obtener datos de cuenta
        summary = await adapter.get_account_summary()
        print(f'Cuenta: {summary}')

        # Desconectar
        await adapter.disconnect()

asyncio.run(test())
"

# Opción 2: Usar el helper get_ib_adapter()
python -c "
import asyncio
from app.services.live_trading.broker_adapters.ib_adapter import get_ib_adapter

async def test():
    ib = get_ib_adapter()
    connected = await ib.connect()
    print(f'Conectado: {connected}')

    if connected:
        # Obtener posiciones
        positions = await ib.get_positions()
        print(f'Posiciones: {positions}')

        await ib.disconnect()

asyncio.run(test())
"
```

### 6. Usar IB Adapter en Tu Estrategia

```python
from app.services.live_trading.broker_adapters.ib_adapter import get_ib_adapter

async def execute_trade():
    # Obtener adapter singleton
    ib = get_ib_adapter()

    # Conectar
    await ib.connect()

    # Obtener datos de mercado
    data = await ib.get_market_data('AAPL')
    print(f"AAPL Bid: {data['bid']}, Ask: {data['ask']}")

    # Colocar orden de mercado
    result = await ib.place_order(
        symbol='AAPL',
        side='BUY',
        quantity=100,
        order_type='MKT'
    )
    print(f"Orden colocada: {result}")

    # Suscribir a datos en tiempo real
    def on_market_data_update(data):
        print(f"Update: {data}")

    await ib.subscribe_market_data('AAPL', on_market_data_update)

    # Desconectar cuando termines
    await ib.disconnect()
```

### 7. Funciones Disponibles en IB Adapter

| Función | Descripción |
|---------|-------------|
| `await connect()` | Conectar a IB TWS/Gateway |
| `await disconnect()` | Desconectar de IB |
| `await get_market_data(symbol)` | Obtener datos de mercado |
| `await place_order(symbol, side, qty, type, price, stop_price)` | Colocar orden |
| `await cancel_order(order_id)` | Cancelar orden |
| `await get_positions()` | Obtener posiciones abiertas |
| `await get_account_summary()` | Obtener resumen de cuenta |
| `await subscribe_market_data(symbol, callback)` | Suscribir a datos en tiempo real |
| `await unsubscribe_market_data(symbol)` | Cancelar suscripción |

---

## Conectar Fuentes de Datos

### Opción 1: Polygon.io (Recomendado)

**Ventajas:** Datos en tiempo real, WebSocket, gratuito hasta cierto nivel

1. Regístrate en https://polygon.io/
2. Obtén tu API Key gratuita
3. Configura en `.env`:

```bash
POLYGON_API_KEY=tu_api_key_aqui
```

### Opción 2: Alpaca Market Data

**Ventajas:** Integración nativa con broker Alpaca

1. Regístrate en https://alpaca.markets/
2. Obtén tus API keys (paper trading)
3. Configura en `.env`:

```bash
ALPACA_API_KEY=tu_api_key_aqui
ALPACA_SECRET_KEY=tu_secret_aqui
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Opción 3: Yahoo Finance (Gratuito, 15 min delay)

**Ventajas:** Sin registro, datos históricos gratuitos

```bash
YAHOO_FINANCE_ENABLED=True
```

### Opción 4: Alpha Vantage (Gratuito)

1. Regístrate en https://www.alphavantage.co/support/#api-key
2. Configura en `.env`:

```bash
ALPHA_VANTAGE_API_KEY=tu_api_key_aqui
```

---

## Próximos Pasos

### 1. Explorar el Dashboard

- Visita http://localhost:8501
- Navega por las diferentes secciones:
  - **Portfolio**: Ver tus posiciones y P&L
  - **Trading**: Ejecutar órdenes manuales
  - **Estrategias**: Conectar estrategias automáticas
  - **Analytics**: Ver métricas de rendimiento

### 2. Probar la API

```bash
# Crear sesión de paper trading
curl -X POST "http://localhost:8000/api/paper-trading/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MiSesion",
    "initial_capital": 100000,
    "commission_per_trade": 1.0
  }'

# Obtener balance
curl "http://localhost:8000/api/paper-trading/account/{session_id}/balance"

# Ejecutar orden
curl -X POST "http://localhost:8000/api/paper-trading/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "{session_id}",
    "symbol": "AAPL",
    "side": "buy",
    "order_type": "market",
    "quantity": 100
  }'
```

### 3. Conectar una Estrategia

Las estrategias están en `app/strategies/`. Para conectar una:

```python
from app.services.paper_trading_service import PaperTradingService
from app.strategies.momentum import MomentumStrategy

# Inicializar
paper_service = PaperTradingService()
strategy = MomentumStrategy(paper_service)

# Ejecutar
await strategy.run()
```

### 4. Monitorear Logs

```bash
# Ver logs en tiempo real
tail -f logs/paper_trading.log

# Ver logs de API
tail -f logs/api_server.log
```

---

## Troubleshooting

### Error: "Port 8000 already in use"

```bash
# Encontrar proceso
lsof -i :8000

# Matar proceso
kill -9 <PID>
```

### Error: "Database locked"

```bash
# Solo un proceso puede escribir en SQLite
# Asegúrate de no tener múltiples instancias corriendo
```

### Error: "Cannot connect to Interactive Brokers"

1. Verifica que TWS/IB Gateway esté corriendo
2. Verifica que el puerto sea 7497 (paper) o 7496 (live)
3. Verifica que API esté habilitado en TWS

---

## Recursos Adicionales

- [Documentación Principal](README.md)
- [Documentación de Backtesting](BACKTESTING.md)
- [API Documentation](http://localhost:8000/docs)

---

## Soporte

Para problemas o preguntas:
- Revisa los logs en `logs/`
- Verifica la configuración en `.env`
- Consulta la documentación de la API

¡Buena suerte con tu paper trading! 🚀
