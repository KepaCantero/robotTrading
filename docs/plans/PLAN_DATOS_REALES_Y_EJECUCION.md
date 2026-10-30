# Plan: datos reales, score de dividendo propio, FX real y ejecución paper con ib_async

> **Origen.** Sesión ZCode del 25-10-2026, a partir del análisis competitivo
> frente a QuantConnect, Portfolio123, Simply Safe Dividends, Snowball,
> Indexa, Composer y TradingView. Cada bloque cierra una brecha concreta de
> ese análisis. Este documento **complementa** y no sustituye a
> `PLAN_PRODUCCION_PAPER_IBKR.md` (su Fase 3 —adaptador IBKR— y su Fase 6
> —stack paper Docker— siguen siendo la referencia de gobierno); aquí se
> acota qué se añade sobre ellas.

Fecha: 25 de octubre de 2026.

**Estado: borrador para aprobación.** Este documento no autoriza
implementación hasta instrucción directa del usuario (misma regla de
gobierno que el plan de producción paper).

## 1. Objetivo y contexto

Sustituir los datos simulados y los stubs que hoy sostienen el backtest por
datos reales gratuitos, construir sobre ellos el diferencial propio (score
de seguridad de dividendo) y completar la ejecución paper con IBKR. El
principio del análisis competitivo se mantiene: no replicamos a los
proveedores de pago, cubrimos con datos libres lo que ellos venden y
modelamos lo que ellos no hacen (fiscalidad ES, core-satélite propio).

### Punto de partida verificado en código

- `app/backtesting/point_in_time_database.py` — la interfaz PIT existe
  (snapshots, look-ahead, corporate actions) pero los métodos de carga son
  stubs: `_load_universe_for_date` devuelve 10 símbolos US hardcodeados
  (AAPL…JNJ), `_load_historical_data` devuelve un DataFrame vacío,
  `_apply_filters` no filtra y `_select_top_by_market_cap` devuelve los N
  primeros. La PIT database está **sin validar contra datos reales**.
- `app/backtesting/dividends.py` — módulo real y honesto: eventos por
  símbolo desde `data/dividends/<SYMBOL>.csv` (`scripts/download_dividends.py`,
  fuente yfinance), `knowledge_date` ya previsto en `DistributionEvent`,
  huecos de cobertura declarados (D04). **No hay ningún fundamental**
  (payout, deuda, beneficios): el score del Bloque 2 parte de cero en
  factores, no en eventos.
- `app/services/forex_data_service.py` — `_fetch_rate_from_api` y
  `_fetch_correlations_from_api` devuelven `None` y el servicio cae a
  constantes hardcodeadas (EUR/USD 1.08, correlaciones fijas): **el carry
  corre hoy sobre números inventados**, contra la regla D04 aplicada al
  resto del sistema.
- `docker-compose.paper.yml` — stack paper v1 (Fase 6) operativo: PostgreSQL
  + API + dashboard, todo en loopback (A23).
- `app/services/live_trading/broker_connector.py:187` define el contrato
  `BrokerConnector`; `app/infrastructure/brokers/paper.py` es la única
  implementación.

### Reglas heredadas (no se renegocian)

- **D04**: lo que no tiene fuente real es MISSING DATA; nunca se rellena con
  constantes. El Bloque 3 elimina la última violación importante.
- **Plan §5**: la indisponibilidad de datos gratuitos se muestra como
  limitación, no se oculta.
- **A23**: todo lo paper en loopback; nada expuesto fuera de este Mac.
- **D01/D05**: renta vs. rentabilidad separadas; solo fills ejecutados.
- Los datos de pago (EODHD, Polygon…) quedan **fuera** de este plan; se
  anotan como alternativa cuando el gratis se quede corto.

## 2. Bloque 1 — Fundamentales reales (SimFin gratis) y validación de la PIT database

**Brecha que cierra**: frente a QuantConnect (fundamentales point-in-time) y
Portfolio123 (20 años de historia). SimFin ofrece su **bulk gratuito** con
estados financieros (income, balance, cashflow) y, clave, la **fecha de
publicación** (filing/publish date) de cada cifra: eso convierte el stub PIT
en una PIT database real sin coste.

### Alcance

- Registro gratuito y API key de SimFin (variable `SIMFIN_API_KEY` en
  config, nunca en el repo).
- Descarga bulk → `data/fundamentals/` (un fichero por dataset, mismo patrón
  que `scripts/download_dividends.py` → `data/dividends/`).
- Materializador PIT: query de cualquier cifra **as of** una fecha devuelve
  solo lo publicado hasta esa fecha (publish_date <= query_date).
- Rellenar los cuatro stubs de `point_in_time_database.py`:
  universo histórico real (constituyentes con fecha de entrada/salida),
  market cap real para `_select_top_by_market_cap`, filtros reales, y
  carga histórica desde `data/historical/` + fundamentales.

### Fuera de alcance

- Opciones, futuros, fundamentales de pago, datos intradía.
- Cobertura completa de España/BME: el tier gratis de SimFin está centrado
  en EE.UU. → **limitación visible** (§5): el universo core-satélite con
  valores españoles queda pendiente de EODHD (~20 $/mes) si el usuario lo
  decide más adelante.

### Tareas

- **T1.1** `scripts/download_simfin.py`: descarga bulk con caché local y
  reanudación (patrón `download_dividends.py`).
- **T1.2** `app/backtesting/fundamentals_source.py`: lector SimFin con
  semántica publish-date (PIT) y huecos de cobertura explícitos.
- **T1.3** Sustituir los stubs de `point_in_time_database.py`; eliminar el
  universo hardcodeado.
- **T1.4** Tests: (a) `validate_no_look_ahead` sobre datos reales;
  (b) test que **falla** si una cifra con publish_date posterior a la fecha
  de decisión entra en un snapshot; (c) snapshot de universo en fechas
  pasadas refleja constituyentes de entonces, no los de hoy.

### Salida

Backtest del núcleo con universos y fundamentales reales PIT; suite anti
look-ahead en verde sobre datos reales; entrada nueva en
`MATRIZ_HALLAZGOS_A_D.md` cerrando el stub PIT como hallazgo corregido.

## 3. Bloque 2 — Dividend Safety Score propio (diferencial vs. Simply Safe Dividends, 468 $/año)

**Brecha que cierra**: SSD vende un score propietario sobre 866+ acciones.
No se clona (su metodología es privada y copiarla no es el objetivo): se
publica **la fórmula propia**, reproducible y configurable, sobre factores
públicos. Decide **qué valores entran en el universo core** (selección), no
cuándo comprar (eso sigue siendo del motor).

### Diseño (ponderaciones configurables, documentadas en el propio informe)

Score 0–100 por símbolo y fecha, calculado solo con información publicada
hasta esa fecha (usa el Bloque 1):

1. **Cobertura del dividendo**: payout sobre net income (FFO/OCF cuando el
   cashflow lo permita) — peso mayor.
2. **Solvencia**: deuda/EBITDA y deuda/patrimonio, tendencia 3 años.
3. **Persistencia**: años consecutivos de pago sin recorte (desde
   `data/dividends/`, ya existe).
4. **Crecimiento**: CAGR de dividendo y de beneficio a 3 y 5 años.
5. **Estabilidad**: desviación de beneficios y drawdown del pago.

- Cuando falta un factor → `computable=False` para ese símbolo y el hueco
  aparece en el informe (patrón D04 de `DividendMetrics`).
- El score degrada o excluye; nunca inventa.

### Tareas

- **T2.1** `app/backtesting/dividend_safety.py`: dataclasses de factores
  (SimFin + eventos existentes) y motor de score con ponderaciones en config.
- **T2.2** Integración como filtro de universo del core-satélite (delante
  del ranking, no detrás).
- **T2.3** Endpoint API + sección de informe con fórmula, factores por
  símbolo y huecos.
- **T2.4** **Validación empírica PIT**: recorte COVID 2020 (símbolos US que
  suspendieron o recortaron) — el score calculado con datos hasta feb-2020
  debe situarlos sistemáticamente por debajo de los que mantuvieron el pago.
  Si no discrimina, se ajustan ponderaciones y se documenta el intento.
- **T2.5** Tests unitarios + golden file del score para reproducibilidad.
- **T2.6** (añadida 25-10-2026, detalle en `PLAN_ADOPCION_LIBRERIAS.md` §2)
  Predicción conforme con MAPIE sobre el clasificador de recortes:
  conjuntos LAC/APS con nivel de confianza configurable (90% por defecto) y
  estado de abstención "no clasificable con confianza". La cobertura se
  mide empíricamente en walk-forward y se publica junto al score;
  dependencia `mapie` se añade con este bloque, no antes.

### Salida

Score reproducible con fórmula publicada, validado contra el episodio
COVID, integrado como filtro del núcleo; informe con factores y cobertura.
Es la pieza que ningún gratuito da y SSD cobra.

## 4. Bloque 3 — FX real (Dukascopy) para el carry

**Brecha que cierra**: el análisis competitivo lo decía literalmente — "tu
FX carry aún corre sobre datos mock". Hoy `forex_data_service.py` cae a
1.08/150.0/etc. hardcodeados.

### Alcance

- `scripts/download_fx.py`: histórico Dukascopy (gratuito) de los pares del
  carry — EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CAD, NZD/USD, USD/CHF —
  a `data/fx/<PAIR>.csv` (diario; intradía solo si la estrategia lo exige).
- **Separación histórico ≠ tiempo real**: servicio de historia FX para
  backtest (lee CSV, sin red) junto al fetcher existente; en backtest los
  fallbacks constantes pasan a ser error/MISSING DATA (D04). El fallback
  queda permitido solo en paper/live y se loguea como tal.
- **Tipos de interés**: un carry con precios FX pero sin diferenciales de
  tipos sigue siendo mock. Se añaden los tipos de referencia públicos
  (BCE/Fed/BoE/BoJ/RBA/BoC/RBNZ, series gratuitas) a `data/rates/` y el
  diferencial se calcula con ellos, con su fecha de vigencia (PIT).
- Validación cruzada de una muestra de cierres con las series diarias del
  BCE (gratuitas) para detectar corrupción de descarga.

### Fuera de alcance

- Ejecución/hedging FX real, tick data, cuenta OANDA.

### Tareas

- **T3.1** `scripts/download_fx.py` (+ verificador de integridad por rango
  de fechas).
- **T3.2** `app/backtesting/fx_history.py` (historial PIT de pares y
  diferenciales de tipos) y reconexión del carry a esta fuente.
- **T3.3** Eliminar constantes de fallback del camino de backtest;
  tests de que un par sin datos aborta la ventana en vez de inventar.
- **T3.4** Re-ejecutar el backtest de carry y **documentar la diferencia**
  contra los resultados mock (qué cambió al usar datos reales).

### Salida

Carry con precios y diferenciales reales; comparativa mock vs. real en
`docs/`; cero constantes inventadas en el camino de backtest.

## 5. Bloque 4 — ib_async en paper con Docker

**Brecha que cierra**: ejecución real (tu Fase 3 pendiente) sin coste y sin
producto externo (Composer está descartado por geografía). La Fase 3 del
plan de gobierno define el adaptador y sus exigencias; este bloque la
ejecuta con `ib_async` (fork mantenido de ib_insync) y el stack paper
existente.

### Alcance

- Dependencia `ib_async` (extra `[paper]` del pyproject).
- Adaptador `app/infrastructure/brokers/ibkr.py` cumpliendo el contrato de
  `BrokerConnector` (`broker_connector.py:187`) y las exigencias de la
  Fase 3: `client_id` estable, verificación de cuenta paper **fail-closed**
  (ni puerto ni bandera local bastan; cuenta no verificada → no arranca),
  resolución de contratos por símbolo+mercado+divisa sin sustituciones
  silenciosas, reconciliación al arrancar y periódica.
- TWS (o IB Gateway) en el Mac host en modo paper, puerto 7497/4002; el
  contenedor reacha al host vía `host.docker.internal`; nada abre puertos
  fuera de loopback (A23).
- E2E paper sobre `docker-compose.paper.yml`: orden de prueba → fill →
  ledger → reconciliación tras reinicio.

### Fuera de alcance

- Dinero real (excluido por decisión de gobierno), multi-broker, mercado
  no operativo aún sin datos de suscripción.

### Tareas

- **T4.1** Dependencia + config (host/puerto/client_id/entorno en settings
  paper).
- **T4.2** Adaptador con tests de contrato (mismos que supera `paper.py`).
- **T4.3** Wiring Docker↔TWS: perfil `ibkr` en `docker-compose.paper.yml`,
  documentación del paso en el Mac.
- **T4.4** E2E paper: ciclo completo con reinicio del contenedor a mitad y
  reconciliación sin duplicados.

### Salida

Orden paper ejecutada de punta a punta desde el stack Docker contra el TWS
del Mac, con trazabilidad contable; Fase 3 del plan de gobierno marcada
validada en la matriz.

**Dependencia externa**: requiere la cuenta paper TWS del usuario (trámite
del usuario, no del código).

## 6. Orden y dependencias

1. **Bloque 1** primero: sin fundamentales PIT no hay score honesto.
2. **Bloque 2** depende del 1 (factores) y del corpus de dividendos (ya
   existe).
3. **Bloque 3** independiente: puede correr en paralelo con 1–2.
4. **Bloque 4** independiente del código de datos; arranca cuando el
   usuario tenga la cuenta TWS paper.

Cada bloque deja el sistema desplegable y testeado por sí mismo (sin
big-bang). Rama sugerida por bloque sobre `main`, siguiendo el flujo ya
usado (`zcode/…`).

**Qué viene después de este plan**: `PLAN_UI_BEAT_THEM_ALL.md`
(orden explícito del usuario, 25-10-2026: primero este plan y
`PLAN_ADOPCION_LIBRERIAS.md`, después la UI). La UI del score, del pie y
del paper real presupone los Bloques 1, 2 y 4 de aquí. La cola completa y
canónica de planes vive en `ORDEN_PLANES.md`.

## 7. Riesgos y limitaciones visibles

- **Límites del SimFin gratis** (ratio de peticiones, cobertura centrada en
  EE.UU.): el informe de cobertura lo cuantifica; escalada a EODHD solo por
  decisión del usuario.
- **Validación del score**: un score que no discrimina en COVID 2020 se
  re-pondera y se documenta; no se publica hasta discriminar o hasta
  declarar explícitamente sus límites.
- **Calidad Dukascopy**: gaps de sesiones y días festivos se muestran como
  cobertura, no se interpolan en backtest.
- **TWS pendiente**: el Bloque 4 puede quedar bloqueado por el trámite
  externo; no bloquea a los demás.
