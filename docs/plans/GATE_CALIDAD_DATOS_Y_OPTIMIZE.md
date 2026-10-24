# Plan: Gate de calidad de datos en backtest + aceleración de /optimize

> Transcrito verbatim el 24-10-2026 desde el plan del usuario (cola de trabajo junto a la
> campaña `PLAN_PRODUCCION_PAPER_IBKR.md`; clusters disjuntos de ella). Primera entrega del
> texto cortada en el cambio 2 de la Fase A; esta es la versión completa.

Dos mejoras de código propio, sin dependencias nuevas y sin adoptar ningún framework (los repos de la lista quedan descartados como integración; ccxt solo se anota para la futura fase crypto).

## Fase A — Gate de calidad de datos en el path de backtest (root fix)

**Problema raíz verificado:** `DataLoader._load_from_csv` (`data_loader.py:156`) trunca ventanas en silencio cuando el CSV empieza tarde, y el orquestador (`backtest_orchestrator.py:274-287`) descarta símbolos sin datos con un `continue` silencioso. Eso es exactamente la clase de bug que produjo los números deshonestos (dividendos +114.9%, reparaciones manuales de VYM/SPY). Los validators existentes (`app/engines/data_engine/validators/`) solo están wired al DataEngine live.

1. **Nuevo `app/backtesting/data_quality.py`**: `scan_data_coverage(symbols, base_path, execution_start, execution_end, warmup_start)` → `DataQualityReport` (dataclass) con por símbolo: `csv_existe`, `primera_fecha`, `última_fecha`, `filas_en_ventana_ejecución`, `cubre_ventana` (`primera_fecha <= execution_start`). Lectura barata: solo columna de fechas (`pd.read_csv(usecols=...)`). Excepción `InsufficientDataError` con mensaje accionable (símbolo, fecha disponible vs pedida, y comando de reparación de `scripts/download_market_data.py`).
2. **Orquestador (`_run_real_backtest`)**: scan ANTES de cargar quotes. Política STRICT por defecto: si algún símbolo solicitado no cubre el inicio de la ventana de ejecución → `raise InsufficientDataError`. Solo cuenta la ventana de ejecución, nunca el warm-up (es best-effort). El benchmark sigue blando (`:464`, ya excluido de fallos). El report se adjunta SIEMPRE al resultado.
3. **Escape explícito:** `allow_partial_data: bool = False` en el request → ejecuta pero adjunta warning + report (nunca silencioso).
4. **Cero cambios de dashboard:** `orchestrate()` ya envuelve excepciones en `success=False`, `error_message` (`:132-137`, `:172-180`), así que `/optimize` y `/swarm` mostrarán el error accionable sin tocar `swarm.py` ni `optimize.py`.
5. **Models (`models.py:305/:329`):** `allow_partial_data` en `BacktestOrchestrationRequest`; `data_quality: DataQualityReport | None = None` en `BacktestOrchestrationResult`.
6. **Caché de quotes en DataLoader** (module-level, LRU acotado ~32 entradas, key = `(path, mtime, start, end)` → `list[Quote]`): elimina el re-parseo CSV + conversión Decimal (el `df.apply` por fila es lo caro) en las 13 corridas del optimizer y en cualquier backtest repetido del dashboard. Invalide por mtime (las reparaciones reescriben CSVs). Verificar en implementación que nadie muta Quote in-place (el orquestador usa `model_copy`); devolver copia de lista siempre.
7. **Tests:** nuevos unit tests (raise strict nombrando símbolos/fechas; `allow_partial_data` pasa + report; CSV ausente; warm-up sin cubrir OK; caché hit + invalide por mtime). Luego suites afectadas (backtesting, orchestration, goldens) y suite completa; los tests que dependían de la truncación silenciosa se arreglan honradamente (acortar ventana a los datos o opt-in explícito), nunca con ignore.
8. **Cambio de comportamiento esperado (intencional):** presets tipo "max" sobre símbolos con historia corta ahora fallarán con mensaje claro en vez de devolver resultados recortados engañosos.

## Fase B — Acelerar /optimize (solo tras aterrizar el cluster pairs del agente paralelo)

**Restricción:** `optimizer.py`, `factory.py`, `pairs_engine.py`, `swarm.py` tienen cambios sin commitear de otro agente. La Fase A no toca ninguno (clusters disjuntos). La Fase B empieza cuando ese cluster esté commiteado, y solo toca `optimizer.py` + tests.

1. **Paralelizar trials con `ProcessPoolExecutor` (stdlib):** función worker module-level (picklable: strategy, params, symbols, start, end, capital — tipos planos). Cada worker corre `_run_one_backtest` con su propio orquestador (los singletons ComplianceEngine/live-gates quedan aislados por proceso). `max_workers = min(4, cpu-1, len(combos))`, param `parallel=True` con fallback secuencial. Resultados reordenados por índice de combo. Mismo `OptimizationResult` de retorno → páginas `/optimize` y `/swarm` intactas.
2. **Eliminar el re-run redundante del mejor** (`optimizer.py:200-204`): conservar métricas raw (Decimal) por trial además de las stringificadas; `best_metrics = raw` del mejor trial (motor determinista). Ahorra 1 de 13 corridas.
3. La caché de quotes de A ya elimina el otro cuello (parse + Decimals ×13).
4. **vectorbt descartado deliberadamente:** segundo motor = segunda fuente de verdad (el ranking del pre-filtro puede divergir del motor real), dependencia numba nueva, y la doctrina del repo es UN solo motor. Paralelización + caché da la misma ganancia de wall-time sin coste de honestidad.
5. **Tests:** equivalencia paralelo vs secuencial en grid pequeño, orden de trials estable, un trial con error no mata el pool.

## Verificación final

- Goldens 15/15 siguen verdes; suites afectadas + suite completa; gates del repo (`check_all`) en verde.
- Medición before/after de wall-time de un `optimize()` real (se loguea la duración).
- Recordatorio operativo: reiniciar el dashboard tras commitear (regla permanente tras cambios en engine/orquestador).

## Commits

Uno por fase, por separado (protocolo de clusters del repo multi-agente).
