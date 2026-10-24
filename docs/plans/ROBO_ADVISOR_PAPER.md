# Producción: Construcción de cartera + Rebalanceo (modo robo-advisor) sobre PaperAdapter

> Transcrito verbatim el 24-10-2026 desde el plan del usuario. Posición en la cola: tras la
> campaña paper (F1–F6 de `PLAN_PRODUCCION_PAPER_IBKR.md`) y tras
> `GATE_CALIDAD_DATOS_Y_OPTIMIZE.md`. Trabajo directo en develop (decisión del usuario:
> «haz los cambios en development no necesitas ramas»).

## Decisiones tomadas (usuario)

- **Secuencia:** empezar YA contra PaperAdapter (simulador determinista = primer escalón del
  ladder §5 de PLAN_PRODUCCION_PAPER_IBKR.md). Sin esperar Fases 1–3. El servicio consume el
  contrato BrokerConnector, así que cuando Fase 3 aterrice el adaptador IBKR se conecta sin
  cambios.
- **Cartera por defecto:** adoptada del último run ganador del enjambre (regla determinista:
  último run con deploy_decision APPROVE/CONDITIONAL + gates T5 verdes; a igualdad, mayor
  score), versionada con procedencia (run_id, params, decisión). Fallback semilla curada cuando
  la DB no tiene ganadores (DB vacía): cartera core/satellite estilo SCHD/VYM/VYMI/VIG/BND +
  low-vol, documentada como semilla sustituible por el primer run ganador.
- **Consolidación:** un solo motor de rebalanceo canónico. Los ~9 motores muertos se borran
  tras lograr paridad funcional (política no-debt + precedente purge 8de44cc8), en commits
  separados por clúster (repo multi-agente).

## Diagnóstico (por qué este diseño)

- **Perfilado:** 3 capas disconexas (InputProfileRouter, ProfileGenerator+investment_profiles.yaml,
  ProfileStrategyMapper); solo ProfileGenerator vive en el swarm y sus caps
  (max_position_size_pct, max_sector_allocation) nunca llegan al motor. El cuestionario de
  swarm.py no pregunta tolerancia a caídas.
- **Carteras:** NO existe artefacto persistente de cartera objetivo (ETF→%). El "portfolio" del
  UI es una reconstrucción time-weighted del backtest (allocation_from_backtest).
- **Rebalanceo:** ~9 implementaciones muertas (portfolio_rebalancer.py,
  portfolio_construction/rebalancing_engine.py+allocation_manager.py,
  domain/services/rebalancer.py, domain/engines/rebalance_engine.py,
  engines/portfolio_engine/rebalancers/rebalancers.py, domain/portfolio/multi_asset/rebalancer.py,
  rebalance_portfolio_use_case.py, analytics mock). Lo único vivo: rebalanceo calendario por
  estrategia (rebalance_days). Sin drift-band, sin cooldown en vivo, sin reactivo con caja, sin
  fraccionado, sin lotes, sin preview fiscal, sin historial explicado.
- **Fiscal:** SpainTaxEngine correcto (19/21/23%, sin LT/ST, compensación de pérdidas, 4 años)
  pero solo wired a la validación T5 del swarm. applies_wash_sale()→False: la regla española de
  loss-deferral por recompra en 2 meses NO está modelada. CapitalGainTracker/WashSaleDetector/
  TaxOptimizer usan reglas US (30 días, 15/35%) — muertos.
- **Selección de instrumentos:** auto_universe() (universe_selector.py) criba 715 CSVs por
  liquidez≥$1M/historia≥500 barras/frescura≤120d — real pero invisible (solo log). Sin
  metadatos de TER/tracking error.
- **Ejecución:** camino único OrderManager.place_order → RiskGates → BrokerConnector.adapter
  (IBKR fail-closed; PaperAdapter disponible). El plan ya prescribe diff-orders (línea 66) y
  reinvertir dividendo en el siguiente rebalanceo (línea 93). No hay scheduler (Fase 6 pendiente).
- **Persistencia:** modelos Position/Trade con precio medio, sin lotes ni fecha de compra;
  timestamps de rebalanceo solo en memoria.

## Arquitectura: nuevo paquete `app/services/portfolio_management/`

- **target_store.py** — TargetPortfolio versionado (ETF→peso, banda, caps por activo/clase,
  modo, cooldown, procedencia run_id). Nuevas tablas `target_portfolios`, `portfolio_lots`,
  `rebalance_events` + migración alembic (en app/infrastructure/persistence/database/migrations).
  Patrón repositorio existente.
- **winner_adoption.py** — lee swarm_runs.db (payloads portfolio/risk_scaling ya persistidos),
  aplica la regla de ganador, produce pesos objetivo + explicación de una frase por ETF.
  Fallback semilla curada.
- **drift.py** — DriftMonitor: banda absoluta (2.5% default, configurable por perfil) + relativa
  opcional. Cooldown primero en la cadena (7 días default, único vivo: min_rebalance_interval
  del muerto ThresholdRebalancer).
- **planner.py** — RebalancePlanner canónico, fusionando lo mejor de los muertos: plan con
  prioridades y costes (multi_asset/rebalancer.py), sells-before-buys + resumen legible
  (domain/services/rebalancer.py), coste-vs-beneficio (TransactionCostAwareRebalancer), reasons
  (rebalancing_engine.py). Cadencia de decisión: cooldown → ¿caja disponible
  (depósitos/dividendos)? → reactivo (comprar infraponderados, nunca vender) → ¿drift > banda y
  sin caja suficiente? → proactivo (vender sobreponderados con ordenación fiscal) → plan →
  preview → confirmar → diff-orders (nunca close/reopen). Flags: reactive-only, auto-rebalance
  tras cambio de perfil (con aviso + preview antes de ejecutar).
- **tax.py** — TaxImpactPreview y ordenación fiscal de sells: lotes FIFO/optimizado +
  SpainTaxEngine (tramos, compensación) + regla española 2 meses (nueva; sustituye
  applies_wash_sale()→False). Veto de ventas cuyo coste fiscal supere el beneficio del
  rebalanceo.
- **executor.py** — órdenes de diferencia vía OrderManager existente sobre PaperAdapter;
  intent persistido antes de enviar (semántica Fase 2); kill-switch respetado.
- **history.py** — RebalanceEvent persistido: reason en lenguaje llano (patrón
  build_trade_reason del backtest), pesos antes/después, impuesto estimado, trigger
  (cash/drift/profile_change), estado.
- **Fraccionado:** PaperAdapter acepta qty fraccional (interno); AlpacaAdapter vía notional
  cuando aplique; sweep de residual a efectivo si el broker es de enteros.
- **Caps:** por activo perfil-driven (5–20%, wire por fin los RiskConfig de InputProfileRouter)
  y por clase (sector/country validators existentes — su primer caller real).
- **UI:** nueva página `pages/portfolio.py` + ruta `/portfolio` en layout.py
  - Cuestionario (objetivo, tolerancia a caídas NUEVA, riesgo, edad, horizonte=período — se
    mantiene "period IS the horizon") → cartera propuesta con "por qué cada ETF" (render de
    auto_universe_summary + criterios liquidez/historia/frescura + notas curadas de coste).
  - Vista cartera: objetivo vs actual, drift, banda, countdown de cooldown, toggle
    reactive-only, botón "hazlo por mí" (adopta ganador o semilla), Tax Impact Preview antes de
    confirmar, historial de rebalanceos explicado.
  - Estilo: serene light English, WCAG AA, 1 clic para acciones núcleo.

## Fases

- **P0 Esqueleto + persistencia:** paquete, 3 tablas + migración + repos. Tests unitarios.
- **P1 Adopción ganador + cuestionario + página /portfolio** con cartera explicada y criterios
  de selección visibles.
- **P2 Motor canónico:** drift + cooldown + reactivo/proactivo + reactive-only + cambio de
  perfil + historial. Tests: matriz de escenarios (drift pequeño no actúa; caja compra
  infraponderados; banda superada sin caja vende; cooldown bloquea; reactive-only nunca vende;
  cambio de perfil dispara con aviso).
- **P3 Fiscal:** lotes + tramos + regla 2 meses + preview en € + veto fiscal. Tests de
  tramos/compensación.
- **P4 Ejecución:** diff-orders sobre PaperAdapter + fraccionado + reconciliación de posiciones.
- **P5 Runner diario paper:** entrypoint `python -m app.services.portfolio_management.run_daily`
  (posiciones→drift→plan→preview persistido→ejecutar/confirmar). Verificación por replay de
  calendarios largos (línea 163 del plan).
- **P6 Limpieza:** borrar motores muertos sustituidos + stack fiscal US
  (CapitalGainTracker/WashSaleDetector/TaxOptimizer US) tras paridad, commits por clúster.

## Cobertura de los 14 requisitos

1 Perfilado→cartera: P1 · 2 Criterios visibles: P1 · 3 Concentración: P2 · 4 Cartera defecto: P1
(ganador+semilla) · 5 Drift band: P2 · 6 Reactivo con flujos: P2 (dividendos reales al llegar
Fase 4) · 7 Proactivo gated: P2 · 8 Fiscal España: P3 · 9 Fraccionado: P4 · 10 Cooldown: P2 ·
11 Preview fiscal: P3 · 12 Historial explicado: P2 · 13 Reactive-only: P2 · 14 Rebalanceo tras
cambio perfil: P2.

## Dependencias y riesgos

- P0–P5 sin dependencia de Fases 1–3 (NiceGUI llama al servicio directamente, sin HTTP).
  Endpoints FastAPI nuevos (preview/confirm) detrás de Fase 1 auth.
- Dividendos como caja real llegan con Fase 4; hasta entonces se modelan depósitos manuales.
- IBKR real requiere Fase 3 (TWS no instalado — acción futura del usuario).
- Reiniciar el dashboard tras cada commit (lección 2026-10-21).
- Verificación: tests por módulo + E2E paper (adopción→drift→preview→orden→historial), replay
  de paridad de semántica drift vs backtest 18.8y, suite existente sin regresión en los
  clústeres tocados.
