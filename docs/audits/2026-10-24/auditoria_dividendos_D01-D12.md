# Auditoría específica: workflow «Maximizar dividendos»

> Transcrita verbatim el 24-10-2026 desde la entrega del auditor externo.
> Commit auditado: `e4cb5eac8b5dfc53b92ce9c36621ecd6bf6de04a`. Las rutas
> absolutas `/Users/josu/...` son las del entorno del auditor; en este repo,
> anteponer `app/…` relativo a la raíz. Fuente de los hallazgos D01–D12 del
> plan `docs/plans/PLAN_PRODUCCION_PAPER_IBKR.md`; estado verificado contra
> código en `docs/plans/MATRIZ_HALLAZGOS_A_D.md`.

24/10/2026 · Commit `e4cb5eac8b5dfc53b92ce9c36621ecd6bf6de04a` · Sin cambios al código del repositorio.

## Conclusión

El recorrido principal del dashboard es una estrategia de asignación y selección de ETFs con sesgo de dividendo y momentum. **No demuestra maximización del dividendo neto cobrado.** El criterio optimizado, la contabilidad de resultados y la presentación no miden ese objetivo de extremo a extremo. Además hay defectos de integración que alteran pesos, señales y parámetros efectivos.

El análisis es técnico: no valida las afirmaciones académicas de los comentarios, rentabilidades prometidas ni normativa fiscal. No se recomienda comprar los activos del universo; aquí sus símbolos identifican entradas del programa.

## Recorrido localizado

1. `swarm.py`: el preset de MAXIMIZAR_DIVIDENDOS selecciona `dividend_tracking` y VIG/DGRO/DGRW/SCHD/VYM/DVY/BND; desde 180 meses usa SDY/DLN/DVY/PEY/BIV. La selección automática dispone de otro universo curado y filtros propios.
2. `executor.py`, T1–T3: entrada → perfil por capital/riesgo → parámetros de módulos.
3. T4: `BacktestOrchestrator` instancia `DividendCoreSatelliteStrategy`, carga CSV históricos, alimenta calentamiento y precalcula señales sobre un timeline global.
4. Estrategia: núcleo ponderado por yield fijo, satélites ordenados por yield × momentum, salidas por momentum en rebalance; guardia SMA opcional. Por defecto los satélites admiten momentum negativo (> -1), pese a comentarios que mencionan positivo.
5. `BacktestEngine`: procesa señales, calcula tamaños, costes y rendimiento; devuelve métricas generales de rentabilidad/riesgo.
6. T5–T6: validación de viabilidad y recomendación con esas métricas. El optimizador separado compara Sharpe de variaciones de parámetros.

**Rutas distintas:** `app/services/strategy_recommender` contiene un scoring con peso de dividend yield, pero T6.1 del workflow inspeccionado importa `app/services/strategy_recommendation/strategy_recommender`. No debe atribuirse la lógica del primero al segundo. También existen dividend_screener y otras estrategias antiguas: su presencia no significa que se ejecuten en este preset.

## Verificación

- Los **10 tests originales** de DividendCoreSatelliteStrategy pasan en el entorno temporal.
- **8 reproducciones adicionales** confirman los comportamientos descritos; importan y ejecutan la estrategia original con barras sintéticas. No usan mocks de la lógica de estrategia.
- Una de las ocho comprueba la composición del grid leyendo su AST; no ejecuta los backtests de los 12 trials.
- No se ejecutó un backtest histórico completo ni se midió rentabilidad realizable o renta real. La revisión de contabilidad de dividendos y conexión de etapas es estática.
- Los hallazgos que siguen indican cuándo existe reproducción y cuándo dependen de una ruta/configuración concreta.

## Hallazgos

### D01 · P1 · El objetivo no mide dividendo cobrado

`app/services/backtest_orchestration/models.py:126`

El resultado contiene retorno total, CAGR, Sharpe y drawdown, pero no flujo de distribuciones, renta mensual neta, retenciones o calendario de pagos. El optimizador de agent_swarm selecciona por Sharpe y crea requests con objective="maximizar_capital" incluso para dividend_tracking. El score de T6.1 emplea Sharpe, drawdown, feasibility, exceso frente a benchmark y walk-forward, sin ingreso por dividendos.

El downloader solicita auto_adjust=True; el retorno de una serie ajustada puede servir para comparar retorno total, pero no demuestra cuánto efectivo se cobra ni permite separar revalorización y distribuciones. El ajuste fiscal de T5.1 parte del incremento de capital final y tampoco sustituye un libro de pagos. El panel dividend_panel es un placeholder.

**Corrección:** definir un contrato de renta distribuida y una contabilidad de eventos por posición: fecha ex-dividendo, fecha de pago, unidades con derecho, importe/divisa, costes y retenciones parametrizadas. Separar retorno total y renta disponible, con reinversión opcional. No sumar dividendos explícitos a una curva ya ajustada sin cambiar la contabilidad, porque se contarían dos veces. **Aceptación:** dos carteras con igual Sharpe pero distinto efectivo distribuido deben distinguirse en el objetivo de renta.

### D02 · P1 · La petición de backend no deriva estrategia del objetivo

`app/services/agent_swarm/executor.py:187`

El preset de la página swarm sí transforma MAXIMIZAR_DIVIDENDOS en dividend_tracking. Sin embargo SwarmRunRequest tiene mean_reversion como estrategia predeterminada y _t41_input prioriza ctx.request.strategy sobre el módulo calculado. Un cliente que envía el objetivo pero omite strategy ejecutará mean_reversion.

**Corrección:** resolver objetivo/estrategia en el servicio compartido, mantener override explícito y validar contradicciones. **Aceptación:** una request de dividendos sin estrategia produce DividendCoreSatelliteStrategy; el frontend y backend deben dar la misma configuración efectiva.

### D03 · P1 · Parámetros del perfil no gobiernan el backtest

`app/services/agent_swarm/executor.py:603`

T3.1 produce module_parameters, pero T4.1 solo toma el nombre del primer módulo como alternativa y transmite un identificador de parámetros, no sus valores al constructor. _build_strategy(dividend_tracking, symbols) pasa nombre, enabled y symbols: se aplican los defaults de la clase. El perfil de dividendos declara, por ejemplo, max_position_size 10/8/5/3 y rebalance_days 60/60/30/30 según tier; el motor recibe suggested_max_position_size de la estrategia y esta usa rebalance_days=126 por defecto. El optimizador sí dispone de un override separado, lo que no conecta T3.1.

**Corrección:** traducir el parameter_set a configuración tipada efectiva y validar qué límites del perfil prevalecen; guardar esa configuración en el resultado. **Aceptación:** cambiar un límite de posición o cadencia en T3.1 modifica la ejecución, no solo el JSON intermedio. No se afirma que todo el risk envelope posterior esté desconectado; el defecto es esta transmisión concreta.

### D04 · P1 · Yields constantes sin fecha histórica

`app/domain/strategies/dividend_core_satellite.py:60`

La selección de satélites usa yield fijo × momentum; la ponderación del núcleo también usa ese diccionario. Por ejemplo, SCHD siempre vale 3,4 y VYMI 4,2, independientemente de la fecha simulada; un símbolo desconocido recibe 2,5. No hay fecha de observación, fuente ni control de recortes de dividendo.

**Consecuencia:** se optimiza una aproximación estática, no renta histórica o futura verificable. No se ha determinado cuándo se obtuvieron esas cifras, por lo que no se afirma fuga temporal demostrada de cada yield: sí ausencia de garantía point-in-time. **Corrección:** series de distribuciones y fundamentales conocidos en t, con política explícita para datos ausentes. **Aceptación:** un recorte entra en la decisión solo cuando se conoce y no altera retrospectivamente las señales anteriores.

### D05 · P1 · Posiciones teóricas se confunden con ejecutadas

`app/domain/strategies/dividend_core_satellite.py:213`

La estrategia actualiza _holdings al emitir señales. El orquestador precalcula todas las señales antes de llamar a BacktestEngine, sin feedback de fills, rechazos o cierres del motor. Si se rechaza una compra o se liquida por un stop, el siguiente rebalance puede no recomprar porque el símbolo sigue en _holdings. Tampoco se reajustan pesos de símbolos que continúan en el conjunto deseado.

**Reproducción:** primera llamada emite dos compras; sin ejecutar ninguna, el siguiente rebalance emite cero y considera ambas compradas. **Corrección:** distinguir cartera objetivo de posición real y generar deltas contra libro ejecutado, preferiblemente dentro de un bucle por eventos. **Aceptación:** rechazo, fill parcial y stop deben reflejarse en la siguiente decisión; verificar rebalance de cantidades además de pertenencia al conjunto.

### D06 · P2 · Exposición declarada y pesos no coinciden

`app/domain/strategies/dividend_core_satellite.py:326`

target_exposure=0,95 se multiplica por core_share=0,50 y satellite_share=0,45: las mangas ya suman solo 0,95. Además cada posición se recorta a 25% y el sobrante no se redistribuye.

**Reproducciones:** defaults de clase, un núcleo SCHD y dos satélites seleccionados suman 67,74%; preset UI de cuatro núcleos y dos satélites suma 90,24%, ambos antes de costes/restricciones de ejecución. No son exposiciones medidas de un backtest completo: son sumas de pesos objetivo. **Corrección:** definir si las mangas son fracciones del patrimonio o de la exposición, normalizar y redistribuir bajo restricciones; si el universo no permite alcanzar 95%, reportar exposición factible. **Aceptación:** suma de pesos más caja coincide con 100% y el desvío del objetivo se explica.

### D07 · P2 · El refugio defensivo no forma parte de la cartera objetivo

`app/domain/strategies/dividend_core_satellite.py:270`

BND/BIV se clasifican como defensivos y existe una rama de sizing, pero _desired_holdings solo añade núcleo y satélites: nunca añade defensive_symbol. La documentación inicial promete trasladar allí el peso cuando falla el núcleo.

**Reproducción:** todos los núcleos salen por momentum y el target solo contiene VYM/DVY, no BND. **Corrección:** escoger explícitamente entre efectivo y refugio y hacer coincidir diseño, mensajes y ejecución. Si se elige refugio, asignar únicamente el peso liberado con sus propios límites. **Aceptación:** test de salida y reentrada que compruebe cantidades de efectivo y activo defensivo, no solo señales SELL.

### D08 · P1 · Señales de varios activos reciben el precio de uno solo

`app/domain/strategies/dividend_core_satellite.py:355`

El rebalance se dispara al recibir una quote y _signal reutiliza su precio/volumen para todos los símbolos emitidos. El timeline se ordena por timestamp/símbolo, por lo que el primer activo del día puede proporcionar el precio para el resto.

**Reproducción:** una barra BND a 10 produce compras SCHD y VYM con signal.price=10, aunque sus históricos están sobre 100 y 50. El motor usa precios propios para ciertos cálculos posteriores, de modo que no afirmo que todos los fills se ejecuten al precio incorrecto; SignalProcessor sí consulta signal.price para comprobaciones de caja/valor. **Corrección:** snapshot de mercado por símbolo y decisión tras completar el corte temporal; no transferir volumen de otro activo. **Aceptación:** cada señal conserva símbolo, precio, timestamp y volumen coherentes; el orden de ingestión de barras no cambia la cartera.

### D09 · P2 · Rebalanceo medido en días naturales, indicadores en barras

`app/domain/strategies/dividend_core_satellite.py:249`

La configuración llama semiannual a 126, pero compara diferencia de fechas: 126 días naturales son unos cuatro meses, no 126 sesiones. Lookback y skip sí se indexan por número de observaciones.

**Reproducción:** vence exactamente a los 126 días naturales. **Corrección:** usar contador de sesiones/calendario de mercado o intervalos explícitos de meses; incluir unidades en los parámetros y en la UI. **Aceptación:** fechas esperadas de rebalance sobre un calendario que incluya fines de semana y festivos.

### D10 · P2 · Venta SMA desaparece cuando coincide con rebalanceo

`app/domain/strategies/dividend_core_satellite.py:207`

La guardia SMA añade SELL y quita el símbolo de _holdings. Después, si corresponde rebalance, la lista signals se reinicia; como el símbolo ya fue eliminado de _holdings, la diferencia de conjuntos no regenera SELL.

**Reproducción:** caída de SCHD de 100 a 20 con SMA habilitada en día de rebalance, sin señal de venta final. La SMA está desactivada por defecto, así que el defecto requiere habilitarla. **Corrección:** conservar y conciliar las señales de protección, sin comprometer estado antes de ejecución. **Aceptación:** la coincidencia debe emitir exactamente una venta y ninguna compra contradictoria.

### D11 · P2 · La búsqueda de parámetros no explora la cadencia anunciada

`app/services/agent_swarm/optimizer.py:166`

Se construye el producto cartesiano y se toman las primeras 12 combinaciones. rebalance_days es el primer eje con [63,126,189] y cada valor contiene 27 combinaciones: las 12 prueban únicamente 63. Incluso buena parte de skip_recent_days queda sin explorar. Se elige por Sharpe sobre la misma ventana enviada y la repetición del ganador usa esa misma ventana; no añade una evaluación externa de la selección de hiperparámetros.

**Reproducción:** los 12 trials tienen rebalance_days=63. **Corrección:** muestreo estratificado o búsqueda que cubra los ejes, objetivo de renta definido y holdout externo a la selección; conservar semillas y presupuesto. **Aceptación:** el presupuesto incluye todas las cadencias candidatas y la métrica final proviene de un periodo no usado para elegir parámetros.

### D12 · P2 · Benchmark no representa todo el universo ni buy-and-hold

`app/services/backtest_orchestration/backtest_orchestrator.py:390`

El benchmark usa como máximo los seis primeros símbolos y calcula la media de retornos diarios, equivalente a rebalanceo diario bajo los supuestos de la implementación. Se describe como equal-weight buy-and-hold. Con el preset de siete símbolos, BND es séptimo y se excluye. Cambiar el orden de entrada puede cambiar los activos del benchmark. Su exceso y Sharpe alimentan la recomendación T6.1.

**Corrección:** definir un benchmark reproducible con composición y pesos explícitos, misma ventana/divisas y política de costes; separar buy-and-hold de rebalance diario. **Aceptación:** invariancia al orden de símbolos y comprobación de todos los activos declarados. La elección de incluir BND debe responder al benchmark definido, no a su posición en la lista.

## Workflow que debería implementar el objetivo

Antes de optimizar parámetros, la salida debe distinguir dos modos: **renta para retirar** y **renta reinvertida**. Ambos requieren registrar dividendos; cambian la caja disponible y la métrica objetivo. No basta con renombrar el CAGR como ingreso mensual.

Un contrato mínimo sería:

- Objetivo: maximizar distribuciones netas esperadas/disponibles por periodo, con penalización explícita de inestabilidad y recortes, bajo límites de riesgo definidos por el usuario.
- Datos: precios aptos para ejecución, eventos corporativos y distribuciones con disponibilidad temporal; FX y costes parametrizados. Evitar información revisada que no era conocida en la fecha simulada.
- Cartera: pesos normalizados, límites y asignación a caja/refugio explícitos. Separar objetivo de cartera, órdenes pendientes y posiciones ejecutadas.
- Ejecución: decisión sobre snapshot coherente, fills/rechazos realimentados, cantidades ajustadas en cada rebalance.
- Contabilidad: efectivo cobrado, reinvertido o retirado; revalorización separada; costes, retenciones e impuestos según configuración validada.
- Validación: selección de hiperparámetros dentro de entrenamiento y evaluación posterior fuera de muestra. Comparar con un benchmark de renta y riesgo explícito, no solo Sharpe.
- Resultado: dividendo bruto/neto por mes y año, variación de renta, capital final, drawdown, costes, caja no invertida y desviaciones del perfil; explicar incertidumbre y datos ausentes.

## Orden de trabajo propuesto

1. **Contrato y conexión:** D01–D04. Resolver objetivo en backend, transmitir parámetros efectivos y definir métricas de renta antes de buscar mejoras de rendimiento.
2. **Corrección del simulador:** D05–D10. Feedback de ejecución, pesos/defensivo, precios por símbolo, unidades de tiempo y señal SMA. Convertir las reproducciones en tests que exijan el comportamiento corregido.
3. **Evaluación:** D11–D12. Grid representativo, separación temporal para seleccionar parámetros y benchmark estable; entonces repetir históricos.

No he realizado esos cambios: esta entrega continúa la auditoría solicitada y deja concreto qué corregir y cómo aceptarlo.

## Archivos

- `comprobar_dividendos.py`: reproduce ocho comportamientos actuales. Que pase confirma defectos/discordancias, no corrección del producto.
- `reproducciones.json`: resultados exactos.
- `../evidencias/pytest-dividendos.txt`: salida de los 10 tests originales.

Comando:

```bash
NUMBA_ENFORCE=0 /private/tmp/robottrading-audit-venv/bin/python /Users/josu/Documents/ChatGPT/RoboTreding/auditoria/dividendos/comprobar_dividendos.py
```
