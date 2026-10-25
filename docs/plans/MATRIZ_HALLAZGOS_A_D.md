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
| A01 | P1 | Operaciones sensibles sin autenticar | routers con `Depends(get_current_principal)` | **validado** (F1) | 1 |
| A02 | P1 | Clave dev aceptada en producción | `AuthMiddleware` eliminada; solo `API_ACCESS_KEYS` | **validado** (F1) | 1 |
| A03 | P1 | Límites por API desconectados de ejecución (3 RiskGates) | singleton `get_risk_gates` compartido por API/órdenes/bridge| **validado** (F2) | 2 |
| A04 | P1 | STOP se salta RiskGates | validación incondicional; STOP valida al trigger| **validado** (F2) | 2 |
| A05 | P1 | Precio fijo 100 en validación | `BrokerQuote` real con niveles de caducidad; sin precio 100| **validado** (F2) | 2 |
| A06 | P1 | Sin exposición proyectada ni reservas | reservas `OrderReservation` + exposición proyectada| **validado** (F2) | 2 |
| A07 | P1 | Ganancias activan límite de pérdidas | `max(0,-pnl)` sobre base de sesión; una implementación| **validado** (F2) | 2 |
| A08 | P1 | Breaker bloquea reducir posiciones | reduce-only verificado pasa con breaker activo| **validado** (F2) | 2 |
| A09 | P1 | Idempotencia/recuperación solo en memoria | intención persistida antes del envío, clave estable| **validado** (F2) | 2 |
| A10 | P1 | Venta completa pierde el efectivo | venta completa acredita efectivo (papel)| **validado** (F2, adelantado de F3) | 3 |
| A11 | P1 | Variables ML con resultados futuros | `training_data_preparator.py:771` † | abierto | 5 |
| A12 | P1 | Fallo de CV temporal → split aleatorio | `supervised_learning_engine.py:251-256` ✔ fallback | abierto | 5 |
| A13 | P2 | Auth válida inutilizable con roles | `Principal` con roles vía `API_KEY_ROLES` | **validado** (F1) | 1 |
| A14 | P2 | Decoradores no ven `http_request` | wrapper escanea kwargs por valor | **validado** (F1) | 1 |
| A15 | P2 | Fallo auth global responde 500 | AuthMiddleware eliminada; 401 + headers | **validado** (F1) | 1 |
b2 REJECTED con motivo; estado real del broker| **validado** (F2) | 2 |
| A17 | P2 | Nueva orden cancela monitor de la anterior | monitores por order_id; stop() cancela todos| **validado** (F2) | 2 |
| A18 | P2 | Validación numérica incompleta | cantidad/precio finitos y >0 siempre| **validado** (F2) | 2 |
| A19 | P1 | Dependencias operativas fuera de manifiesto | `pyproject.toml` ✔ sin `alpaca-trade-api`/`asyncpg` | abierto | 6 |
| A20 | P1 | Tablas live sin migración | migración 0004 crea las 4 tablas live| **validado** (F2) | 6 |
| A21 | P2 | Workers/scheduler despliegan otra API | `Dockerfile:151` † | abierto | 6 |
| A22 | P2 | CI sin gate real (`|| true`) | `.github/workflows/ci-testing.yml` † | abierto | 6 |
| A23 | P2 | Servicios expuestos en compose prod | `docker-compose.prod.yml` † | abierto | 6 |
| A24 | P2 | Entornos no reproducibles, config fuera de imagen | `Dockerfile:91` † | abierto | 6 |

## Serie D — workflow «Maximizar dividendos»

| ID | Sev | Título | Ubicación (24-10-2026) | Estado | Fase |
|---|---|---|---|---|---|
| D01 | P1 | El objetivo no mide dividendo cobrado | `DividendLedger`+`DividendMetrics` en todo backtest real| **validado** (F4·p1)abierto 4 |
| D02 | P1 | Backend no deriva estrategia del objetivo | executor deriva estrategia del objetivo| **validado** (F4·p1)abierto 4 |
| D03 | P1 | Parámetros del perfil no gobiernan el backtest | `executor.py:603` ✔ `_build_strategy` sin params | abierto | 4 |
| D04 | P1 | Yields constantes sin fecha histórica | `dividend_core_satellite.py:60` ✔ `DIVIDEND_YIELDS` fijo | abierto | 4 |
| D05 | P1 | Posiciones teóricas ≠ ejecutadas | `dividend_core_satellite.py:229` ✔ `_holdings = desired` sin fills | abierto | 4 |
| D06 | P2 | Exposición declarada ≠ pesos (0.95×(0.50+0.45)) | `dividend_core_satellite.py:168-172,360` ✔ clamp sin redistribución | abierto | 4 |
| D07 | P2 | Refugio defensivo nunca en cartera objetivo | `dividend_core_satellite.py:296-340` ✔ sin defensive (peso `:356` muerto) | abierto | 4 |
| D08 | P1 | Precio de una barra para todas las señales | `dividend_core_satellite.py:362-373` ✔ `_signal(quote,…)` reutiliza | abierto | 4 |
| D09 | P2 | Rebalanceo en días naturales, no sesiones | `dividend_core_satellite.py:265` ✔ `.days >=` | abierto | 4 |
| D10 | P2 | Venta SMA perdida al coincidir con rebalance | `dividend_core_satellite.py:224` ✔ `signals = []` reinicia | abierto | 4 |
| D11 | P2 | Grid no explora la cadencia anunciada | grid estratificado `_stratified_combos`| **validado** (F4·p1)abierto 4 |
| D12 | P2 | Benchmark ≠ universo completo ni buy&hold | benchmark EW con TODOS los símbolos| **validado** (F4·p1)**parcial** 4 |

**Nota D12:** `c4e19661` añadió `_load_dividend_benchmark` (exceso vs equal-weight del propio
universo), pero sigue cortando a los 6 primeros símbolos y sin separar buy&hold de rebalance
diario. La aceptación (invariancia al orden, todos los activos declarados) sigue sin cumplirse.

## Registro de cambios de estado

| Fecha | Hallazgo | Cambio | Estado nuevo |
|---|---|---|---|
| 2026-10-24 | (colección) | `get_order_manager_for_api` sin parámetros para `Depends`; 5 endpoints de `live_trading.py` actualizados; test de seguridad re-keyed; eliminado `tests/integration/metrics_database` (módulo purgado en `561071a4`). Colección: 7 errores → **0** (11.969 tests). | — |
| 2026-10-24 | A01, A02, A13, A14, A15 | **Fase 1 auth**: `AuthMiddleware` eliminada de raíz (mataba la clave dev y respondía 500); principal único `Principal` con roles viewer/trader/admin (`API_ACCESS_KEYS` + `API_KEY_ROLES`; default viewer+trader, admin nunca automático); dependencias `get_current_principal`/`require_roles` en los 13 routers (solo `/health` público); roles por endpoint (resets/umbrales → admin; órdenes/señales → trader); `require_auth`/`rate_limit` reconocen `http_request`; el handler global preserva `WWW-Authenticate`; audit del reset con identidad y timestamp. Aceptación: `tests/api/test_auth_matrix.py` **41/41** (matriz rutas × credenciales contra la app real). Tests de integración actualizados honestamente (conftest con clave operadora admin). Regresión vs línea base en tests/api, tests/integration/api y tests/unit/core: **0 nuevos**. | **validado** |

| 2026-10-25 | A03–A09, A16–A18, A20 (+A10) | **Fase 2 completa** (d584a9f6, ddb7db8c, 41f14e54, 96249c4a, 9bb9997b): semántica de riesgo (base de sesión, reduce-only, reservas proyectadas, gates numéricos) · camino de órdenes (validación SIEMPRE, cotización real `BrokerQuote` con niveles fresco/STALE>7d/rechazo>90d sobre CSV EOD propio, MARKET ejecuta a cotización, 422 REJECTED honesto) · unificación (un RiskGates autoritativo; monitores por orden) · intención persistida antes del envío (idempotente por client_order_id) · migración 0004 tablas live (+guard SQLite en 0003 que rompía la cadena). Aceptación: 4 baterías nuevas (~50 tests) en tests/unit/live_trading/test_*_f2.py; 0 fallos nuevos vs herencia 32. | **validado** |

| 2026-10-25 | D01, D02, D11, D12 | **Fase 4 parte 1** (030898bf): libro de renta REAL (`app/backtesting/dividends.py` — eventos yfinance en data/dividends/, 16 símbolos; contado contra el libro EJECUTADO del motor; retención 15% configurable; gaps de cobertura EXPLÍCITOS, nunca yields inventados) enganchado a todo backtest — sonda SCHD 1y: retorno 8,41% + renta bruta 1.007,38 / neta 856,27 USD (4 eventos, por año). Executor deriva estrategia del objetivo (D02); grid estratificado cubre todos los ejes (D11); benchmark EW sin recorte a 6 (D12); gate de arranque dividendos = mayoría-del-core suelo 1 (universos mono-core antes mudos para siempre). 22 tests nuevos; 0 fallos nuevos vs baseline en agent_swarm/orchestration/strategies. **Pendiente F4·p2**: D03 (params perfil→motor), D04 (yields point-in-time), D05–D10 (bucle motor-estrategia), reinversión en rebalanceo, scoring T6.1 consciente de renta. | ver fila |

## Pruebas de aceptación

Cada hallazgo cierra con su prueba de aceptación tal como está definida en
`docs/audits/2026-10-24/auditoria_general_A01-A24.md` (§Verificación de cada hallazgo) y
`docs/audits/2026-10-24/auditoria_dividendos_D01-D12.md` (§Aceptación de cada hallazgo).
El cierre del proyecto exige: todos los hallazgos **validados**, suite verde sin errores de
colección y cero discrepancias de órdenes/contabilidad (§4 del plan).
