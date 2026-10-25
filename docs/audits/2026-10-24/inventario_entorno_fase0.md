# Inventario de entorno — Fase 0 (24-10-2026)

Comprobaciones de solo lectura sobre el Mac que alojará la producción paper (plan
`docs/plans/PLAN_PRODUCCION_PAPER_IBKR.md`, Fase 0).

## Host

| Elemento | Estado |
|---|---|
| Arquitectura | Apple Silicon (arm64) |
| macOS | 26.5.1 |
| Python del proyecto | 3.11.17 (`.venv` del repo) |
| Node | v24.22.0 (`~/.local/node`) |
| Homebrew | **no instalado** |
| Origen git | `https://github.com/KepaCantero/robotTrading.git` (develop) |

## Bloqueos duros para fases posteriores

| Requisito | Estado | Fase que lo necesita | Acción |
|---|---|---|---|
| Docker | **Instalado y verificado (25-10-2026)**: Docker Desktop 29.9.2, daemon aarch64 nativo, Compose v5.6.1, contenedor alpine arm64 OK. CLI al PATH vía `~/.zshrc` (el symlink de `/usr/local/bin` requiere sudo; binario en `/Applications/Docker.app/Contents/Resources/bin`). | 6 | **DESBLOQUEADO.** |
| TWS de Interactive Brokers | **NO instalado** (sin `~/Applications/Trader Work Station`, sin `/Applications`, sin `~/Jts`) | 3 | Instalar TWS desde IBKR y abrir sesión con la cuenta paper. **Solo el usuario** puede aportar credenciales/cuenta. |
| Cuenta paper IBKR | Sin verificar (requiere TWS) | 3, 5 | Crear/verificar cuenta paper y permisos de datos de mercado. |

## Estado del repositorio (24-10-2026)

- HEAD inicial de la fase: `c4e19661` (develop). Cambios sin commit heredados de la sesión
  pausada: catálogo único de estrategias (`app/domain/strategies/catalog.py`),
  `backtest_orchestrator.py` consumiéndolo, `config/trading_strategies.yaml` con el engine real
  de pairs. Guardados en la rama `zcode/produccion-paper`.
- Infra como código: `Dockerfile` + `docker-compose{,.dev,.logging,.prod}.yml` (sin probar:
  Docker ausente). `alembic.ini` → `app/infrastructure/persistence/database/migrations`.
- Datos: 715 CSVs en `data/historical`.

## Errores de colección resueltos en esta fase

1. `get_order_manager(broker: BrokerConnector | None)` usado en `Depends()` hacía fallar el
   registro de `POST /live-trading/orders` al importar `app.main` → 7 ficheros de tests no
   colectaban y **pytest abortaba la suite entera**. Fix: proveedor sin parámetros
   `get_order_manager_for_api` + actualización de los 5 endpoints y del override del test de
   seguridad.
2. `tests/integration/metrics_database/test_metrics_pipeline.py` importaba `MetricPoint` de un
   módulo purgado en `561071a4` (QuestDB/MLflow out); solo quedaba `__pycache__` huérfano.
   Eliminados el test y el directorio fantasma (`app/services/metrics_database/`).

**Colección resultante: 11.969 tests, 0 errores.**

## Línea base de la suite

- Antes del fix: pytest abortaba en colección (0 tests ejecutados).
- **Tras el fix (24-10-2026, 20:39 min): `756 failed, 11071 passed, 75 skipped, 70 errors`**
  — 11.969 tests colectados, 0 errores de colección. Detalle completo de fallos/errores en
  `baseline_suite_2026-10-24.txt` (junto a este fichero).
- Los 756 fallos y 70 errores son la línea base de deuda conocida; su resolución se planifica
  por fases (§ Fase 0 del plan: «resolver … los fallos preexistentes antes de declarar la suite
  validada»). Nota: repo multi-agente; otros cambios sin comprometer convivían en el árbol
  durante la ejecución, así que algunos fallos pueden corresponder a trabajo en vuelo de otro
  agente.
- Dependencias: **sin lockfile** (solo `requirements-dev.txt`); `pyproject.toml` no declara
  `alpaca-trade-api`, `asyncpg` ni ningún cliente IBKR (A19 confirmado; la elección de cliente
  IBKR —`ib_insync`/`ib_async`/`ibapi`— es decisión de Fase 3).

## Entornos dev/integración/paper (pendiente de Fase 0-cont/Fase 6)

Pendiente: bases de datos y configuraciones separadas. Bloqueado parcialmente por Docker ausente
(para PostgreSQL/Redis de integración y paper). La separación de configuración (`.env.dev`,
`.env.integration`,`.env.paper`) puede avanzar sin Docker y se hará al entrar en Fase 6.
