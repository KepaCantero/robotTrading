# PLAN · Perfil real en robotTrading (29-10-2026)

**Estado: IMPLEMENTADO y verificado. Sin commit (árbol compartido con otro agente).**

## El problema que resolvió

El dueño tiene DOS sistemas: su proyecto `~/portfolio` (dinero real IBKR,
mandato v2 "vivir de la cartera por RETORNO TOTAL", 45 años, Bizkaia) y
robotTrading (investigación). Al pedir a ambos "maximizar dividendos"
daban carteras incompatibles: robotTrading respondía con ETFs americanos
desde cero; el proyecto real exige UCITS, acumulación y partir de lo que
ya posee. Esta sesión acerca robotTrading al perfil real.

## D1 · Datos UCITS que faltaban

- **Descargados**: `EUNL.DE` (iShares Core MSCI World Acc, 2009-09→hoy,
  17 años) y `IBGS.AS` (Euro Govt Bond 7-10y, 2008-10→hoy) con
  `download_market_data.py --years 18`. Añadidos al `UNIVERSE` del
  descargador para que `--tickers-all` los refresque.
- **Ya existían**: VHYL (2013+), IDVY (2008+), QDIV (2018+), VWCE
  (2019+), IBTS (2016+). No se añaden sus símbolos Yahoo (.AS) al
  descargador porque escribirían CSV duplicados con sufijo — se
  refrescan por la vía de `import_yahoo_csv.py`.

## D2 · Objetivo `VIVIR_DE_LA_CARTERA` (retorno total, UCITS)

Cableado en TODOS los registros (la verificación headless cazó los que
faltaban):

| Registro | Cambio |
|---|---|
| `swarm.py` OBJECTIVES + GOAL_PRESETS | clave nueva; preset `("static_ew", ["EUNL.DE","VHYL","IDVY","IBGS.AS"])` |
| `universe_selector.py` | `UCITS_TOTAL_RETURN` + GOAL_FILTERS |
| `domain/models/input_profile.py` | enum `ObjectivoInversion` (validador pydantic) |
| `profile_generator` (models + templates por tramo) | sin apalancamiento, rebalanceo 90 días |
| `strategy_recommender` | pesos 0.40 retorno / 0.35 Sharpe / 0.25 DD |
| `profitability_engine` PROFILE_THRESHOLDS | barra min_sharpe 0.8 / min_return 0.08 |
| `portfolio_management/models.py` | OBJECTIVES + `IBGS.AS` como bond |
| `winner_adoption` SEED_PORTFOLIOS | VWCE 55 / VHYL 20 / IBTS 25 |

**Verificación (29-10, headless, 11 años, Bizkaia, 45 años, €112k):**
run COMPLETED → decisión CONDITIONAL, validación verde, score 65,
feasibility 3.44. Cartera resultante (exposición temporal real, con
partials de fill honestos en IDVY/IBGS): VHYL 28.5 / EUNL.DE 28.3 /
IDVY 26.4 / IBGS.AS 16.8.

Por qué EUNL.DE y no VWCE en el universo: VWCE solo tiene 7 años de
histórico local; EUNL.DE es el proxy acumulador global profundo (el
gate de cobertura habría RECHAZADO la ventana de 11 años con VWCE).

## D3 · Cuenta real vs target (`real_gap.py` + tarjeta en /portfolio)

Nuevo servicio `app/services/portfolio_management/real_gap.py` y tarjeta
"3 · Your live account vs this target" (secciones siguientes
renumeradas 4/5):

- **Import por pegado** del `holdings.csv` del proyecto portfolio
  (ticker, cantidad, coste medio; CASH→caja). Persiste por slug en
  `data/real_holdings_<slug>.json` (patrón paper-state).
- **Precio desde el corpus propio** (último cierre real); USD→EUR con el
  fx de referencia ECB (`data/fx/ecb_exr.csv`); sin fx y sin CSV ⇒
  "unpriced", nunca un número inventado.
- **Gap por manga** contra el target activo + bloque "fuera del target"
  (las 10 posiciones congeladas del dueño, visibles y sin tocar).
- **Plan de solo-compras** para dinero nuevo (filosofía dilución:
  proporcional a los gaps, nunca vende la cuenta real).
- **Coste fiscal estimado** de recortar excesos: FIFO sintético al
  coste medio pegado + `SpainRebalanceTax` (tramos ahorro, regla 2
  meses señalizada, nota de estimación).

**Smoke con la cartera real del dueño (29-10):** 13 posiciones parseadas,
total €107.936, todas con precio. VWCE 35,7% vs 55% (gap €20.816),
VHYL 31,5% vs 20% (exceso €12.418, impuesto estimado €0 — coste 69,09
sobre precio, venta con pérdida), IBTS 3,8% vs 25% (gap €22.870). Plan
€3.000/mes → IBTS €1.571 + VWCE €1.429.

## Tests y verificación

- `tests/unit/services/portfolio_management/test_real_gap.py` — 8/8.
- Regresión del paquete portfolio + universe selector — 91 passed.
- `py_compile` de los 12 ficheros tocados — OK. Wiring del objetivo — OK.

## Limitaciones honestas (pendientes)

1. **`latest_winner` no filtra por objetivo**: un ganador de otro
   objetivo puede ser adoptado para este perfil (los runs no guardan el
   objetivo en results_json — habría que persistirlo primero).
2. **La adopción sigue siendo manual**: /portfolio no avisa de que
   existe un ganador más reciente que el adoptado.
3. **Venta programada en retirada** (el "vender VWCE" del mandato v2):
   el motor no simula retiros; el preset optimiza la fase de
   acumulación.
4. El import por pegado no conoce fechas de compra reales ⇒ la regla de
   2 meses no puede evaluarse de verdad (el estimado lo dice).
