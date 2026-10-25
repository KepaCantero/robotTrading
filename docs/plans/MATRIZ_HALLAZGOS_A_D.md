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
| A11 | P1 | Variables ML con resultados futuros | features solo con cierres conocidos en t (exit_time<=t)| **validado** (F5) | 5 |
| A12 | P1 | Fallo de CV temporal → split aleatorio | purged CV falla → entrenamiento FALLA, sin split aleatorio| **validado** (F5) | 5 |
| A13 | P2 | Auth válida inutilizable con roles | `Principal` con roles vía `API_KEY_ROLES` | **validado** (F1) | 1 |
| A14 | P2 | Decoradores no ven `http_request` | wrapper escanea kwargs por valor | **validado** (F1) | 1 |
| A15 | P2 | Fallo auth global responde 500 | AuthMiddleware eliminada; 401 + headers | **validado** (F1) | 1 |
b2 REJECTED con motivo; estado real del broker| **validado** (F2) | 2 |
| A17 | P2 | Nueva orden cancela monitor de la anterior | monitores por order_id; stop() cancela todos| **validado** (F2) | 2 |
| A18 | P2 | Validación numérica incompleta | cantidad/precio finitos y >0 siempre| **validado** (F2) | 2 |
| A19 | P1 | Dependencias operativas fuera de manifiesto | extra `paper`: asyncpg+greenlet+psycopg (3 boot-fails lo probaron)| **validado** (F6·v1) | 6 |
| A20 | P1 | Tablas live sin migración | migración 0004 crea las 4 tablas live| **validado** (F2) | 6 |
| A21 | P2 | Workers/scheduler despliegan otra API | targets/servicios worker+scheduler falsos ELIMINADOS| **validado** (F6·v1) | 6 |
| A22 | P2 | CI sin gate real (`|| true`) | UN workflow `ci.yml` (lint/security/tests/docker) con gates reales; camino docker verificado en vivo local | **corregido** (F6·p2) | 6 |
| A23 | P2 | Servicios expuestos en compose prod | compose paper solo loopback (127.0.0.1)| **validado** (F6·v1) | 6 |
| A24 | P2 | Entornos no reproducibles, config fuera de imagen | config/ copiada + uv.lock + requirements con hashes + Dockerfile `--require-hashes`; imagen construida y arrancada desde el lock | **validado** (F6·p2) | 6 |

## Serie D — workflow «Maximizar dividendos»

| ID | Sev | Título | Ubicación (24-10-2026) | Estado | Fase |
|---|---|---|---|---|---|
| D01 | P1 | El objetivo no mide dividendo cobrado | `DividendLedger`+`DividendMetrics` en todo backtest real| **validado** (F4·p1) | 4 |
| D02 | P1 | Backend no deriva estrategia del objetivo | executor deriva estrategia del objetivo| **validado** (F4·p1) | 4 |
| D03 | P1 | Parámetros del perfil no gobiernan el backtest | T3.1 params → `_strategy_param_overrides` + weight_cap| **validado** (F4·p2) | 4 |
| D04 | P1 | Yields constantes sin fecha histórica | yields trailing-12m point-in-time del corpus real| **validado** (F4·p2) | 4 |
| D05 | P1 | Posiciones teóricas ≠ ejecutadas | bucle motor↔estrategia: señal por barra DENTRO del run + `on_fill` (rechazo/fill parcial/stop) antes de la siguiente decisión | **validado** (F4·p3) | 4 |
| D06 | P2 | Exposición declarada ≠ pesos (0.95×(0.50+0.45)) | mangas fracciones de la exposición + redistribución| **validado** (F4·p2) | 4 |
| D07 | P2 | Refugio defensivo nunca en cartera objetivo | caja refugio por defecto; defensivo opt-in| **validado** (F4·p2) | 4 |
| D08 | P1 | Precio de una barra para todas las señales | señal con precio/volumen/ts PROPIOS del símbolo| **validado** (F4·p2) | 4 |
| D09 | P2 | Rebalanceo en días naturales, no sesiones | cadencia en SESIONES de mercado| **validado** (F4·p2) | 4 |
| D10 | P2 | Venta SMA perdida al coincidir con rebalance | SMA sobrevive al rebalance; sma_exits manda sobre catch-all| **validado** (F4·p2) | 4 |
| D11 | P2 | Grid no explora la cadencia anunciada | grid estratificado `_stratified_combos`| **validado** (F4·p1) | 4 |
| D12 | P2 | Benchmark ≠ universo completo ni buy&hold | EW del universo: TODOS los símbolos (`symbols_used`), rebalance diario y buy&hold SEPARADOS, invariante al orden | **validado** (F4·p3) | 4 |

**Nota D12 (histórica):** `c4e19661` añadió `_load_dividend_benchmark` pero recortaba a los
6 primeros símbolos y mezclaba las políticas. F4·p3 cerró la aceptación completa: todos los
activos declarados (`symbols_used` explícito), invariancia al orden de entrada (test) y
rebalance diario vs buy&hold puro como curvas separadas con matemática cerrada verificada.

## Registro de cambios de estado

| Fecha | Hallazgo | Cambio | Estado nuevo |
|---|---|---|---|
| 2026-10-24 | (colección) | `get_order_manager_for_api` sin parámetros para `Depends`; 5 endpoints de `live_trading.py` actualizados; test de seguridad re-keyed; eliminado `tests/integration/metrics_database` (módulo purgado en `561071a4`). Colección: 7 errores → **0** (11.969 tests). | — |
| 2026-10-24 | A01, A02, A13, A14, A15 | **Fase 1 auth**: `AuthMiddleware` eliminada de raíz (mataba la clave dev y respondía 500); principal único `Principal` con roles viewer/trader/admin (`API_ACCESS_KEYS` + `API_KEY_ROLES`; default viewer+trader, admin nunca automático); dependencias `get_current_principal`/`require_roles` en los 13 routers (solo `/health` público); roles por endpoint (resets/umbrales → admin; órdenes/señales → trader); `require_auth`/`rate_limit` reconocen `http_request`; el handler global preserva `WWW-Authenticate`; audit del reset con identidad y timestamp. Aceptación: `tests/api/test_auth_matrix.py` **41/41** (matriz rutas × credenciales contra la app real). Tests de integración actualizados honestamente (conftest con clave operadora admin). Regresión vs línea base en tests/api, tests/integration/api y tests/unit/core: **0 nuevos**. | **validado** |

| 2026-10-25 | A03–A09, A16–A18, A20 (+A10) | **Fase 2 completa** (d584a9f6, ddb7db8c, 41f14e54, 96249c4a, 9bb9997b): semántica de riesgo (base de sesión, reduce-only, reservas proyectadas, gates numéricos) · camino de órdenes (validación SIEMPRE, cotización real `BrokerQuote` con niveles fresco/STALE>7d/rechazo>90d sobre CSV EOD propio, MARKET ejecuta a cotización, 422 REJECTED honesto) · unificación (un RiskGates autoritativo; monitores por orden) · intención persistida antes del envío (idempotente por client_order_id) · migración 0004 tablas live (+guard SQLite en 0003 que rompía la cadena). Aceptación: 4 baterías nuevas (~50 tests) en tests/unit/live_trading/test_*_f2.py; 0 fallos nuevos vs herencia 32. | **validado** |

| 2026-10-25 | D01, D02, D11, D12 | **Fase 4 parte 1** (030898bf): libro de renta REAL (`app/backtesting/dividends.py` — eventos yfinance en data/dividends/, 16 símbolos; contado contra el libro EJECUTADO del motor; retención 15% configurable; gaps de cobertura EXPLÍCITOS, nunca yields inventados) enganchado a todo backtest — sonda SCHD 1y: retorno 8,41% + renta bruta 1.007,38 / neta 856,27 USD (4 eventos, por año). Executor deriva estrategia del objetivo (D02); grid estratificado cubre todos los ejes (D11); benchmark EW sin recorte a 6 (D12); gate de arranque dividendos = mayoría-del-core suelo 1 (universos mono-core antes mudos para siempre). 22 tests nuevos; 0 fallos nuevos vs baseline en agent_swarm/orchestration/strategies. **Pendiente F4·p2**: D03 (params perfil→motor), D04 (yields point-in-time), D05–D10 (bucle motor-estrategia), reinversión en rebalanceo, scoring T6.1 consciente de renta. | ver fila |

| 2026-10-25 | D03–D10, A11, A12 | **F4 parte 2** (05d3327a, 2c525e69): estrategia de dividendos con yields reales point-in-time (D04), pesos normalizados con redistribución y residuo explicado (D06), caja como refugio por defecto (D07), señales con datos propios (D08), cadencia en sesiones (D09), venta SMA conservada + sma_exits prioritario sobre el catch-all momentum-None que re-compraba lo recién vendido (D10 — bug real destapado por el test), T3.1 params gobiernan el backtest vía weight_cap (D03). **F5** (3bee2f06): ML sin información futura (A11) y sin escape a split aleatorio (A12). Suites: 0 fallos nuevos vs baseline. **Pendiente F4**: D05 (bucle motor↔estrategia con feedback de fills) y scoring T6.1 income-aware; reinversión documentada como territorio paper/ROBO. | ver fila |

| 2026-10-25 | A19, A21–A24 | **Fase 6 v1** (39281032): stack paper REAL verificado en Docker — docker-compose.paper.yml (PostgreSQL+API con `alembic upgrade head` al arrancar, puertos SOLO loopback, sin workers falsos ni stack de logs), imagen arm64 construida, migraciones aplicadas (order_records incl.), **/health 200 y rutas protegidas 401 sin clave** (F1 aguanta en contenedor), PAPER_SECRET_KEY exigido al operador. Dockerfile copia config/ (A24), targets falsos fuera (A21). pyproject extra paper: asyncpg+greenlet+psycopg (A19, demostrado por 3 arranques fallidos). CI: gates reales (A22). Pendiente F6·p2: lockfile completo, backups 14d+restore, panel/alertas, unificación de los 3 pipelines. | ver fila |

| 2026-10-25 | D05, D12 | **Fase 4 parte 3 — CIERRE de F4**: (D05) bucle motor↔estrategia — la estrategia cross-sectional genera las señales de cada barra DENTRO del bucle del motor (warm-up solo construye estado) y recibe `on_fill` por cada rechazo/fill parcial/cierre-por-stop ANTES de su siguiente decisión; `_holdings` deja de ser teórico (test de semántica por caso + smoke E2E real). Corregido de paso un bug de indentación del draft D05 que dejaba el análisis post-trade compliance dentro de la rama trade=None (crash `'NoneType' trade_id` al primer rechazo — lo cazó la suite swarm E2E, 13 tests). (D12) aceptación completa: TODOS los activos declarados con `symbols_used` explícito e invariante al orden (test), y rebalance diario vs buy&hold puro como curvas separadas — verificación con matemática cerrada (+12.5% vs 0% sintético) y datos reales (7 símbolos, BND incluido). Arreglados 3 tests rancios de test_benchmark.py (SPY local empieza 2006-10 tras el empalme; el fake del mapper no tenía `max_drawdown_percentage`). **T6.1 income-aware**: objetivos de renta (`maximizar_dividendos`/`income_generation`) puntúan la renta neta REAL anualizada sobre capital inicial (bandas 4/3/2/1% → 25/20/15/8 pts) comprimiendo los componentes de mercado al 75%; renta no computable = 0 pts y techo 75. Suites: agent_swarm 104/104 (97 base + 7 nuevos), backtest_orchestration 39/39 (4 nuevos D12 + E2E), dividend 32/32. E2E real: 12 trades, +21.14%, WF pass, EW reb 23.90 vs B&H 23.99, renta neta 5.410,04 USD (64 eventos). | **validado** |

| 2026-10-25 | — (Fase 3) | **Fase 3 IBKR** (6d2f29b2): `IbkrAdapter` al contrato `BrokerConnector` con todas las reglas del plan — paper verificado por la CUENTA (prefijo DU de `managedAccounts`; puerto/bandera no prueban nada), cuentas live o mixtas rechazadas y desconectadas SIN override; resolución de instrumentos a exactamente UN contrato (cero o ambiguo → error, jamás sustitución silenciosa, con caché); órdenes con `client_order_id` estable en `orderRef` y reenvío idempotente (SEC-005); `reconcile()` (posiciones/saldos/ejecuciones) al conectar y bajo demanda REPORTANDO divergencias, nunca absorbiéndolas; quotes fail-closed (A05); parche de asyncio solo en connect (nunca import). Instalado en este Mac: **TWS stable arm64** (~/Applications/Trader Workstation) + Docker Desktop corriendo; compose apunta la API al TWS del host (`IBKR_HOST=host.docker.internal:7497`, clientId 77001). Smoke real sin sesión TWS: `IBKRConnectionError` limpio, fail-closed. Fix de raíz en ib_adapter viejo (rechazaba un límite BUY bajo el ask — el caso normal — y no validaba precios negativos): 3 tests preexistentes verdes. 18 tests deterministas nuevos (FakeIB); live_trading 20→16 fallos (resto deriva preexistente). **Pendiente usuario (único paso)**: abrir TWS, login con credenciales paper, activar API (puerto 7497) — después el §5 paso 2 (TWS en observación, sin envíos). | ver §5 |

| 2026-10-25 | A22, A24 | **Fase 6 parte 2 — operación local** (b8602600, 2e5f41aa, aa801a5c, 7c50c9e8): (1) **Backups** — `backup_paper.sh` (pg_dump -Fc con puerta de integridad pg_restore --list ANTES de podar: un dump corrupto nuevo nunca borra los buenos), `restore_paper.sh` (--clean --if-exists sobre la BD EXISTENTE: un rollback de código no borra órdenes posteriores), prueba E2E scratch postgres → seed → backup → DROP → restore → 3/3 filas PASS, sidecar compose con ciclo diario y retención 14d (primer ciclo verificado en vivo, dump 68K). (2) **Lockfile (A24 → validado)** — uv.lock (239 paquetes) + requirements.lock.txt con hashes + Dockerfile `--require-hashes` (deps primero, app `--no-deps` después): solo el set bloqueado puede satisfacer imports; imagen construida (133s) y arrancada desde el lock; requires-python ≥3.11 (todas las superficies de deploy usan 3.11; nicegui 3.18 exige ≥3.10). (3) **Panel/alertas** — `GET /ops/status` (solo admin) agrega señales de fuentes REALES: BD, órdenes inciertas (PENDING/SUBMITTED/ACKNOWLEDGED >10min), divergencia contable (ejecutadas sin fills + fills≠cantidad), antigüedad del corpus (>5d = pipeline roto), tareas `not_deployed` HONESTO (sin scheduler en este stack); nada inventa números. `paper_watch.sh` local con notificación macOS al salir de healthy. Matriz auth F1 41/41; anónimo 401. (4) **CI unificada (A22 → corregido)** — `ci.yml` sustituye 5 workflows solapados (3 corrían la misma suite con gates distintos); 4 jobs reales (lint/security/tests/docker-arranque+migraciones+backup-restore); mypy NO gated a propósito (~800 errores = deriva trackeada; un gate siempre-rojo es ruido y uno suprimido es el pecado A22); **validación de A22 = primer push** (cada comando de cada job verificado local: ruff ✓, bandit -ll ✓, grep secretos ✓, docker job íntegro ✓; el job de tests mostrará el estado REAL de la suite). Fix de raíz destapado por el smoke: `extra={'message': ...}` en los exception handlers (clave RESERVADA de LogRecord) mataba el propio error de configuración con KeyError — ahora `detail_message` y el error real sale limpio. | ver fila |

## Pruebas de aceptación

Cada hallazgo cierra con su prueba de aceptación tal como está definida en
`docs/audits/2026-10-24/auditoria_general_A01-A24.md` (§Verificación de cada hallazgo) y
`docs/audits/2026-10-24/auditoria_dividendos_D01-D12.md` (§Aceptación de cada hallazgo).
El cierre del proyecto exige: todos los hallazgos **validados**, suite verde sin errores de
colección y cero discrepancias de órdenes/contabilidad (§4 del plan).
