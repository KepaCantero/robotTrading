# 📗 20. "Site Reliability Engineering" - Google (Betsy Beyer et al.)

## REGLAS DE SRE PARA TRADING ROBUSTO

**Regla 20.1 — Error Budgets**

Claude DEBE definir presupuesto de error:
- Cuánto tiempo puede estar el bot caído antes de ser riesgo inaceptable
- Si superas presupuesto, detén desarrollo y arregla estabilidad

```python
class ErrorBudget:
    """Presupuesto de error para el bot."""

    def __init__(
        self,
        max_downtime_per_month: timedelta = timedelta(hours=4),  # 99.5% uptime
        max_failed_trades_per_day: int = 10
    ):
        self.max_downtime = max_downtime_per_month
        self.max_failed_trades = max_failed_trades_per_day
        self.current_downtime = timedelta()
        self.failed_trades_today = 0

    def check_budget(self) -> bool:
        """Verificar si estamos dentro del presupuesto."""
        if self.current_downtime >= self.max_downtime:
            logger.error("❌ Error budget agotado - downtime excedido")
            return False

        if self.failed_trades_today >= self.max_failed_trades:
            logger.error("❌ Error budget agotado - trades fallidos excedidos")
            return False

        return True

    def record_failure(self, failure_type: str):
        """Registrar fallo."""
        if failure_type == "downtime":
            self.current_downtime += timedelta(minutes=5)
        elif failure_type == "failed_trade":
            self.failed_trades_today += 1

# Uso
budget = ErrorBudget()
if not budget.check_budget():
    logger.critical("Error budget excedido - pausar desarrollo nuevo")
    sys.exit(1)
```

**Regla 20.2 — Circuit Breakers**

Claude DEBE implementar Circuit Breaker:
- Si API broker devuelve errores 5xx tres veces
- Bot debe dejar de intentar peticiones por 60 segundos

```python
from pybreaker import CircuitBreaker

# Circuit breaker para broker API
broker_breaker = CircuitBreaker(
    fail_max=3,  # 3 fallos consecutivos
    timeout_duration=60  # 60 segundos abierto
)

class BrokerClient:
    @broker_breaker
    def execute_order(self, order: Order) -> Execution:
        """Ejecutar orden con circuit breaker."""
        try:
            response = self.api.post("/orders", order.to_dict())
            return Execution.from_response(response)
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            broker_breaker.call_failed(e)  # Notificar fallo
            raise

# Si se abre el circuito, las llamadas fallan inmediatamente
try:
    execution = broker.execute_order(order)
except CircuitBreakerError:
    logger.warning("Circuit breaker abierto - esperando 60s")
    # Implementar lógica de fallback (ej. cambiar a broker backup)
```

**Regla 20.3 — Graceful Degradation**

Claude DEBE implementar degradación graceful:
- Si feed datos alta velocidad falla
- Bot debe conmutar a feed más lento (REST)

```python
class MarketDataManager:
    """Gestor de datos con fallback graceful."""

    def __init__(self):
        self.websocket_feed = WebSocketFeed()
        self.rest_feed = RESTFeed()
        self.using_websocket = True

    def get_ticks(self, symbol: str) -> List[Tick]:
        """Obtener ticks con fallback graceful."""
        if self.using_websocket:
            try:
                return self.websocket_feed.get_ticks(symbol)
            except WebSocketError as e:
                logger.warning(f"WebSocket feed failed: {e}")
                logger.info("Falling back to REST feed")
                self.using_websocket = False
                # Degradación graceful: usar REST más lento
                return self.rest_feed.get_ticks(symbol)
        else:
            # Ya en modo degradado
            return self.rest_feed.get_ticks(symbol)
```

**Regla 20.4 — Golden Signals**

Claude DEBE monitorizar solo 4 métricas críticas:
1. Latencia (tiempo de ejecución)
2. Tráfico (ticks por segundo)
3. Errores (HTTP 4xx/5xx)
4. Saturación (uso de CPU/RAM)

```python
class GoldenSignalsMonitor:
    """Monitor de golden signals."""

    def __init__(self):
        self.metrics = {
            "latency": [],
            "traffic": [],
            "errors": [],
            "saturation": {"cpu": [], "ram": []}
        }

    def record_latency(self, operation: str, duration_ms: float):
        """Latencia de operación."""
        self.metrics["latency"].append({
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.now()
        })

        if duration_ms > 1000:  # >1 segundo
            logger.warning(f"High latency: {operation} took {duration_ms}ms")

    def record_traffic(self, ticks_per_second: int):
        """Tráfico de ticks."""
        self.metrics["traffic"].append({
            "tps": ticks_per_second,
            "timestamp": datetime.now()
        })

        if ticks_per_second < 10:  # <10 ticks/seg
            logger.warning(f"Low traffic: {ticks_per_second} ticks/sec")

    def record_error(self, error_type: str, error: Exception):
        """Error en operación."""
        self.metrics["errors"].append({
            "type": error_type,
            "error": str(error),
            "timestamp": datetime.now()
        })

    def record_saturation(self, cpu_pct: float, ram_pct: float):
        """Saturación de recursos."""
        self.metrics["saturation"]["cpu"].append(cpu_pct)
        self.metrics["saturation"]["ram"].append(ram_pct)

        if cpu_pct > 80 or ram_pct > 80:
            logger.warning(f"High saturation: CPU={cpu_pct}%, RAM={ram_pct}%")
```

**Regla 20.5 — Idempotencia de Órdenes**

Claude DEBE enviar cada orden con UUID local:
- Si red cae y no sabes si llegó
- Reintentar con mismo UUID
- Broker ignora duplicado

```python
import uuid

class OrderManager:
    """Gestor de órdenes idempotentes."""

    def execute_order(self, order: Order) -> Execution:
        """Ejecutar orden con idempotencia."""
        # Generar UUID local
        client_order_id = str(uuid.uuid4())

        # Guardar orden localmente con UUID
        order.client_order_id = client_order_id
        self.save_order(order)

        try:
            # Enviar orden con client_order_id
            execution = self.broker.execute_order(order)

            # Actualizar estado
            order.status = OrderStatus.FILLED
            order.execution = execution
            self.save_order(order)

            return execution

        except ConnectionError:
            # No sabemos si la orden llegó
            logger.warning("Connection error - checking order status")

            # Consultar orden por client_order_id
            status = self.broker.get_order_status(client_order_id)

            if status == "FILLED":
                # Orden sí llegó y se ejecutó
                logger.info("Order was executed despite connection error")
                return self.broker.get_order_execution(client_order_id)
            else:
                # Orden no llegó, reintentar con mismo UUID
                logger.info("Order not received, retrying with same UUID")
                return self.execute_order(order)  # Reintento idempotente
```

**Regla 20.6 — Post-mortems sin Culpa**

Claude DEBE escribir post-mortem tras cada pérdida por error:
- Causa raíz detallada
- Cómo evitar que vuelva a ocurrir

```python
class PostMortem:
    """Documento post-mortem."""

    def __init__(self, incident_date: datetime, impact_money: float):
        self.incident_date = incident_date
        self.impact_money = impact_money
        self.timeline = []
        self.root_cause = ""
        self.action_items = []

    def add_timeline_event(self, time: datetime, description: str):
        """Añadir evento al timeline."""
        self.timeline.append({"time": time, "description": description})

    def set_root_cause(self, cause: str):
        """Establecer causa raíz."""
        self.root_cause = cause

    def add_action_item(self, action: str, owner: str, deadline: datetime):
        """Añadir acción preventiva."""
        self.action_items.append({
            "action": action,
            "owner": owner,
            "deadline": deadline
        })

    def generate_report(self) -> str:
        """Generar reporte."""
        report = f"""
# Post-Mortem: Incidente del {self.incident_date}

## Impacto
- Pérdida monetaria: ${self.impact_money:.2f}

## Timeline
"""
        for event in self.timeline:
            report += f"- {event['time']}: {event['description']}\n"

        report += f"\n## Causa Raíz\n{self.root_cause}\n\n"

        report += "## Acciones Preventivas\n"
        for item in self.action_items:
            report += f"- [{item['owner']}] {item['action']} (antes del {item['deadline']})\n"

        return report

# Usar tras incidente
post_mortem = PostMortem(datetime.now(), -5000.0)
post_mortem.add_timeline_event(datetime.now(), "Bot perdió conexión")
post_mortem.add_timeline_event(datetime.now(), "No se implementó reconexión automática")
post_mortem.set_root_cause("Falta de lógica de reconexión automática")
post_mortem.add_action_item(
    "Implementar lógica de reconexión automática con backoff exponencial",
    "DevOps Team",
    datetime.now() + timedelta(days=7)
)
```

**Regla 20.7 — Chaos Engineering Manual**

Claude DEBE probar resistencias desconectando servicios:
- Desconectar Wi-Fi mientras bot en Paper Trading
- Matar proceso de DB

```python
class ChaosEngineering:
    """Pruebas de caos manuales."""

    def simulate_network_failure(self):
        """Simular fallo de red."""
        logger.warning("CHAOS: Simulating network failure")
        # Desconectar interfaz de red (requiere permisos)
        os.system("sudo ifconfig eth0 down")

        # Esperar 30 segundos
        time.sleep(30)

        # Reconectar
        os.system("sudo ifconfig eth0 up")
        logger.info("CHAOS: Network restored")

    def simulate_database_crash(self):
        """Simular crash de base de datos."""
        logger.warning("CHAOS: Simulating database crash")
        # Matar proceso de PostgreSQL
        os.system("sudo pkill -9 postgres")

        # Esperar 30 segundos
        time.sleep(30)

        # Reiniciar PostgreSQL
        os.system("sudo service postgresql start")
        logger.info("CHAOS: Database restored")

    def simulate_broker_api_failure(self):
        """Simular fallo de API del broker."""
        logger.warning("CHAOS: Simulating broker API failure")
        # Cambiar URL a endpoint inválido
        original_url = settings.broker_api_url
        settings.broker_api_url = "http://invalid-endpoint"

        # Esperar 30 segundos
        time.sleep(30)

        # Restaurar URL
        settings.broker_api_url = original_url
        logger.info("CHAOS: Broker API restored")
```

**Regla 20.8 — Canary Deployments**

Claude DEBE lanzar nueva versión primero al 1%:
- NO al 100% del capital
- Ejecutar primero con 1% o cuenta paralela pequeña

```python
class CanaryDeployment:
    """Despliegue canary de estrategia."""

    def __init__(
        self,
        new_strategy: Strategy,
        old_strategy: Strategy,
        canary_allocation: float = 0.01  # 1% a nueva estrategia
    ):
        self.new_strategy = new_strategy
        self.old_strategy = old_strategy
        self.canary_allocation = canary_allocation

    def execute_trade(self, signal: Signal):
        """Ejecutar trade con canary allocation."""
        total_capital = self.get_account_balance()

        # 1% a nueva estrategia (canary)
        canary_capital = total_capital * self.canary_allocation
        old_capital = total_capital * (1 - self.canary_allocation)

        # Ejecutar con ambas estrategias
        canary_order = self.new_strategy.create_order(signal, canary_capital)
        old_order = self.old_strategy.create_order(signal, old_capital)

        canary_execution = self.execute(canary_order)
        old_execution = self.execute(old_order)

        # Comparar resultados
        self.compare_performance(canary_execution, old_execution)

    def compare_performance(self, canary: Execution, old: Execution):
        """Comparar rendimiento canary vs old."""
        canary_slippage = canary.slippage_pct
        old_slippage = old.slippage_pct

        if canary_slippage > old_slippage * 1.5:
            logger.error(f"Canary worse: {canary_slippage:.2%} vs {old_slippage:.2%}")
            # Revertir canary
            self.rollback_canary()
```

**Regla 20.9 — Automation of Toil**

Claude DEBE automatizar trabajo manual:
- Si reinicias bot manualmente todos los días
- Automatizar con Systemd unit o CronJob

```python
# /etc/systemd/system/trading-bot.service
[Unit]
Description=Algorithmic Trading Bot
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/trading-bot
Environment="PATH=/home/trader/.virtualenvs/trading-bot/bin"
ExecStart=/home/trader/.virtualenvs/trading-bot/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Comandos
# sudo systemctl enable trading-bot  # Auto-start en boot
# sudo systemctl start trading-bot   # Iniciar bot
# sudo systemctl stop trading-bot    # Parar bot
# sudo systemctl status trading-bot  # Ver estado
```

**Regla 20.10 — Dead Man's Switch**

Claude DEBE implementar ping a servicio externo:
- Bot envía ping cada minuto
- Si servicio no recibe ping, avisa al móvil

```python
import requests

class DeadMansSwitch:
    """Dead man's switch - detectar procesos muertos."""

    def __init__(self, healthcheck_url: str, ping_interval: int = 60):
        self.healthcheck_url = healthcheck_url
        self.ping_interval = ping_interval
        self.last_ping = None

    def start(self):
        """Iniciar thread de ping."""
        threading.Thread(target=self._ping_loop, daemon=True).start()

    def _ping_loop(self):
        """Loop de ping."""
        while True:
            try:
                response = requests.post(self.healthcheck_url, timeout=5)
                if response.status_code == 200:
                    self.last_ping = datetime.now()
                    logger.debug("Ping sent successfully")
                else:
                    logger.error(f"Ping failed: {response.status_code}")
            except Exception as e:
                logger.error(f"Ping error: {e}")

            time.sleep(self.ping_interval)

# Usar con Healthchecks.io
healthcheck = DeadMansSwitch(
    healthcheck_url="https://healthchecks.io/ping/your-uuid-here",
    ping_interval=60
)
healthcheck.start()

# Si el bot muere, Healthchecks.io te envía notificación al móvil
```

**Regla 20.11 — Alert Fatigue**

Claude DEBE enviar alertas solo si requieren acción humana:
- NO spam por "Info"
- Alertas solo para: "Conexión Perdida", "Drawdown > 5%"

```python
class AlertManager:
    """Gestor de alertas con prioridades."""

    def __init__(self):
        self.alert_counts = defaultdict(int)
        self.last_alert_time = {}

    def send_alert(self, level: str, message: str):
        """Enviar alerta solo si es crítica."""
        # Solo alertas críticas
        if level not in ["CRITICAL", "ERROR"]:
            logger.info(f"Skipping non-critical alert: {message}")
            return

        # Rate limiting: max 1 alert por hora por tipo
        alert_key = f"{level}:{message}"
        now = datetime.now()

        if alert_key in self.last_alert_time:
            time_since_last = (now - self.last_alert_time[alert_key]).seconds
            if time_since_last < 3600:  # 1 hora
                logger.debug(f"Rate limiting alert: {message}")
                return

        # Enviar alerta
        self.send_telegram_message(f"[{level}] {message}")
        self.last_alert_time[alert_key] = now
        self.alert_counts[alert_key] += 1
```

**Regla 20.12 — Infrastructure as Code**

Claude DEBE usar Terraform o Ansible:
- NUNCA configurar servidor "a mano"

```python
# playbook.yml - Ansible playbook
---
- name: Configure Trading Bot Server
  hosts: trading_servers
  become: yes

  tasks:
    - name: Install Python 3.10
      apt:
        name: python3.10
        state: present

    - name: Install PostgreSQL
      apt:
        name: postgresql
        state: present

    - name: Create trading bot user
      user:
        name: trader
        system: yes
        shell: /bin/bash

    - name: Copy trading bot code
      synchronize:
        src: ./trading-bot/
        dest: /home/trader/trading-bot/

    - name: Install Python dependencies
      pip:
        requirements: /home/trader/trading-bot/requirements.txt

    - name: Configure systemd service
      copy:
        src: ./trading-bot.service
        dest: /etc/systemd/system/trading-bot.service

    - name: Start trading bot service
      systemd:
        name: trading-bot
        state: started
        enabled: yes
```

**Regla 20.13 — Log Aggregation**

Claude DEBE centralizar logs de múltiples bots:
- Usar pila ELK o Grafana Loki

```python
import logging
from pythonjsonlogger import jsonlogger

# Configurar JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Logs estructurados en JSON
logger.info(
    "Order executed",
    extra={
        "symbol": "AAPL",
        "quantity": 100,
        "price": 150.0,
        "execution_time_ms": 45
    }
)

# Output:
# {"asctime": "2025-01-28 10:30:00", "name": "__main__", "levelname": "INFO",
#  "symbol": "AAPL", "quantity": 100, "price": 150.0, "execution_time_ms": 45}
```

**Regla 20.14 — Time-to-Recovery (TTR)**

Claude DEBE medir tiempo de recuperación:
- Objetivo: reducir TTR mediante scripts de recuperación

```python
class RecoveryTracker:
    """Track time-to-recovery."""

    def __init__(self):
        self.incident_start = None
        self.incidents = []

    def start_incident(self, description: str):
        """Registrar inicio de incidente."""
        self.incident_start = datetime.now()
        logger.critical(f"INCIDENT START: {description}")

    def resolve_incident(self):
        """Registrar resolución de incidente."""
        if self.incident_start:
            recovery_time = datetime.now() - self.incident_start
            self.incidents.append({
                "start": self.incident_start,
                "end": datetime.now(),
                "recovery_time": recovery_time
            })
            logger.info(f"INCIDENT RESOLVED: Recovery time {recovery_time}")
            self.incident_start = None

    def get_mean_recovery_time(self) -> timedelta:
        """Calcular tiempo medio de recuperación."""
        if not self.incidents:
            return timedelta()

        total = sum(inc["recovery_time"] for inc in self.incidents, timedelta())
        return total / len(self.incidents)
```

**Regla 20.15 — Health Check Endpoints**

Claude DEBE crear API interna /health:
- Retorna estado de salud del bot
- Conexión broker, balances, latencia

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Check conexión broker
    try:
        broker_status = broker.get_status()
        health_status["checks"]["broker"] = {
            "status": "ok",
            "latency_ms": broker_status["latency_ms"]
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["broker"] = {
            "status": "error",
            "error": str(e)
        }

    # Check balances
    try:
        balance = broker.get_account_balance()
        health_status["checks"]["balance"] = {
            "status": "ok",
            "balance_usd": float(balance.amount)
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["balance"] = {
            "status": "error",
            "error": str(e)
        }

    # Check latencia actual
    health_status["checks"]["latency"] = {
        "current_latency_ms": measure_current_latency()
    }

    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code

# Usar: curl http://localhost:5000/health
```
