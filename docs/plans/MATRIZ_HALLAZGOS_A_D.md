# Matriz de hallazgos A01–A24 · D01–D12

Plan: `PLAN_PRODUCCION_PAPER_IBKR.md` · Auditorías fuente: `docs/audits/2026-10-24/`
(auditadas en `e4cb5eac`) · Verificación contra código: **24-10-2026**, árbol `c4e19661` + fixes Fase 0.

Estados: **abierto** (defecto presente), **parcial** (parte tratado), **corregido** (cambio aplicado,
sin validación completa), **validado** (prueba de aceptación verde). Método de verificación del
24-10-2026: lectura directa del patrón defectuoso (marcado ✔) o herencia por archivo intacto desde
`e4cb5eac` (`git diff --name-only e4cb5eac..HEAD` no toca el archivo, marcado †).

## Serie A — general

| ID | Sev | Título | Ubicación (24-10-2026) | Estado | Fase |
|---|---|---|---|---|---|
| A01 | P1 | Operaciones sensibles sin autenticar | `app/presentation/api/portfolio.py` † | abierto | 1 |
| A02 | P1 | Clave dev aceptada en producción | `middleware.py:102` ✔ `dev-api-key-12345` | abierto | 1 |
| A03 | P1 | Límites por API desconectados de ejecución (3 RiskGates) | `order_manager.py` † | abierto | 2 |
| A04 | P1 | STOP se salta RiskGates | `order_manager.py:158` ✔ `if order_price is not None` | abierto | 2 |
| A05 | P1 | Precio fijo 100 en validación | `order_manager.py:155` ✔ `Decimal("100")` | abierto | 2 |
| A06 | P1 | Sin exposición proyectada ni reservas | `risk_gates.py:188` † | abierto | 2 |
| A07 | P1 | Ganancias activan límite de pérdidas | `risk_gates.py:236` ✔ `abs(self.daily_pnl)` | abierto | 2 |
| A08 | P1 | Breaker bloquea reducir posiciones | `risk_gates.py:174` † | abierto | 2 |
| A09 | P1 | Idempotencia/recuperación solo en memoria | `trading_bridge_orchestrator.py` † | abierto | 2 |
| A10 | P1 | Venta completa pierde el efectivo | `paper_adapter.py:333-335` ✔ `return` antes del abono | abierto | 3 |
| A11 | P1 | Variables ML con resultados futuros | `training_data_preparator.py:771` † | abierto | 5 |
| A12 | P1 | Fallo de CV temporal → split aleatorio | `supervised_learning_engine.py:251-256` ✔ fallback | abierto | 5 |
| A13 | P2 | Auth válida inutilizable con roles | `security.py:555` † | abierto | 1 |
| A14 | P2 | Decoradores no ven `http_request` | `security.py:498-508` ✔ wrapper args/kwargs | abierto | 1 |
| A15 | P2 | Fallo auth global responde 500 | `middleware.py:237` † | abierto | 1 |
| A16 | P2 | SUBMITTED aunque rechazada | `live_trading.py:183-191` ✔ incondicional | abierto | 2 |
| A17 | P2 | Nueva orden cancela monitor de la anterior | `trading_bridge_orchestrator.py:428` † | abierto | 2 |
| A18 | P2 | Validación numérica incompleta | `risk_gates.py:188` † | abierto | 2 |
| A19 | P1 | Dependencias operativas fuera de manifiesto | `pyproject.toml` ✔ sin `alpaca-trade-api`/`asyncpg` | abierto | 6 |
| A20 | P1 | Tablas live sin migración | `trade_persistence.py` † | abierto | 6 |
| A21 | P2 | Workers/scheduler despliegan otra API | `Dockerfile:151` † | abierto | 6 |
| A22 | P2 | CI sin gate real (`|| true`) | `.github/workflows/ci-testing.yml` † | abierto | 6 |
| A23 | P2 | Servicios expuestos en compose prod | `docker-compose.prod.yml` † | abierto | 6 |
| A24 | P2 | Entornos no reproducibles, config fuera de imagen | `Dockerfile:91` † | abierto | 6 |

## Serie D — workflow «Maximizar dividendos»

| ID | Sev | Título | Ubicación (24-10-2026) | Estado | Fase |
|---|---|---|---|---|---|
| D01 | P1 | El objetivo no mide dividendo cobrado | `backtest_orchestration/models.py:126` † | abierto | 4 |
| D02 | P1 | Backend no deriva estrategia del objetivo | `executor.py:187` ✔ default `mean_reversion` | abierto | 4 |
| D03 | P1 | Parámetros del perfil no gobiernan el backtest | `executor.py:603` ✔ `_build_strategy` sin params | abierto | 4 |
| D04 | P1 | Yields constantes sin fecha histórica | `dividend_core_satellite.py:60` ✔ `DIVIDEND_YIELDS` fijo | abierto | 4 |
| D05 | P1 | Posiciones teóricas ≠ ejecutadas | `dividend_core_satellite.py:229` ✔ `_holdings = desired` sin fills | abierto | 4 |
| D06 | P2 | Exposición declarada ≠ pesos (0.95×(0.50+0.45)) | `dividend_core_satellite.py:168-172,360` ✔ clamp sin redistribución | abierto | 4 |
| D07 | P2 | Refugio defensivo nunca en cartera objetivo | `dividend_core_satellite.py:296-340` ✔ sin defensive (peso `:356` muerto) | abierto | 4 |
| D08 | P1 | Precio de una barra para todas las señales | `dividend_core_satellite.py:362-373` ✔ `_signal(quote,…)` reutiliza | abierto | 4 |
| D09 | P2 | Rebalanceo en días naturales, no sesiones | `dividend_core_satellite.py:265` ✔ `.days >=` | abierto | 4 |
| D10 | P2 | Venta SMA perdida al coincidir con rebalance | `dividend_core_satellite.py:224` ✔ `signals = []` reinicia | abierto | 4 |
| D11 | P2 | Grid no explora la cadencia anunciada | `optimizer.py:172` ✔ `combos[:max_trials]` | abierto | 4 |
| D12 | P2 | Benchmark ≠ universo completo ni buy&hold | `backtest_orchestrator.py:387` ✔ `symbols[:6]` persiste | **parcial** | 4 |

**Nota D12:** `c4e19661` añadió `_load_dividend_benchmark` (exceso vs equal-weight del propio
universo), pero sigue cortando a los 6 primeros símbolos y sin separar buy&hold de rebalance
diario. La aceptación (invariancia al orden, todos los activos declarados) sigue sin cumplirse.

## Registro de cambios de estado

| Fecha | Hallazgo | Cambio | Estado nuevo |
|---|---|---|---|
| 2026-10-24 | (colección) | `get_order_manager_for_api` sin parámetros para `Depends`; 5 endpoints de `live_trading.py` actualizados; test de seguridad re-keyed; eliminado `tests/integration/metrics_database` (módulo purgado en `561071a4`). Colección: 7 errores → **0** (11.969 tests). | — |

## Pruebas de aceptación

Cada hallazgo cierra con su prueba de aceptación tal como está definida en
`docs/audits/2026-10-24/auditoria_general_A01-A24.md` (§Verificación de cada hallazgo) y
`docs/audits/2026-10-24/auditoria_dividendos_D01-D12.md` (§Aceptación de cada hallazgo).
El cierre del proyecto exige: todos los hallazgos **validados**, suite verde sin errores de
colección y cero discrepancias de órdenes/contabilidad (§4 del plan).
