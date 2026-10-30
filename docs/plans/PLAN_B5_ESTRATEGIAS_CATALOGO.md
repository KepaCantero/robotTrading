# Plan B5: catálogo de estrategias candidatas (paper "151 Trading Strategies")

> Estado: **EN COLA** (25-10-2026). Se ejecuta tras **B1+B3** de
> `PLAN_DATOS_REALES_Y_EJECUCION.md`. Puede correr en paralelo con el plan
> UI (clusters disjuntos: esto toca `app/backtesting` + registro de
> estrategias; la UI toca `app/presentation`). Arranca con el «empieza» del
> usuario. La cola canónica vive en `ORDEN_PLANES.md`.
> Owner del plan: sesión ZCode que lo implemente (empezar leyendo este
> archivo completo).

Fecha: 25 de octubre de 2026.

## 1. Qué es y qué no es

**Fuente**: "151 Trading Strategies", Kakushadze & Serur, 2018
([SSRN 3247865](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3247865),
gratuito; también libro en Palgrave Macmillan). 151 estrategias definidas
con fórmulas cerradas (550+).

**El paper define; NO valida**: no contiene backtests ni evidencia de
rendimiento. Su valor son definiciones matemáticas sin ambigüedad de
candidatas. **El trabajo de validación es exactamente lo que este motor
hace**: walk-forward obligatorio, comisiones IBKR reales, t+1, live-gates.

**Posición**: las estrategias propias (dividend core-satélite, carry) son
el núcleo y no se tocan. Este bloque aporta **candidatas a satélites** del
core-satélite, evaluadas con la misma disciplina que el resto. Nada de lo
que aquí sobrevive desplaza al núcleo.

## 2. Alcance

Seleccionar e implementar **3–5 estrategias** del paper compatibles con:

1. **Horizonte diario/semanal** — nada de intradía/HFT: el proyecto no
   tiene datos ni ejecución para ello (coherente con el rechazo de tick en
   `PLAN_ADOPCION_LIBRERIAS.md` §5).
2. **Datos disponibles tras B1+B3**: precios diarios (`data/historical/`),
   fundamentales PIT (SimFin), FX y tipos (`data/fx/`, `data/rates/`).
3. **Fórmula cerrada implementable** sin proveedores de pago.

La selección concreta se hace **al ejecutar el plan, leyendo el paper**:
aquí no se pre-asignan números de estrategia — sería inventar sin leer.
Familias previsiblemente compatibles: momentum transversal, reversión a la
media de bajo riesgo, filtros de tendencia, variantes de carry.

## 3. Reglas de honestidad del bloque

- Cada candidata se implementa con la **fórmula exacta citando el número**
  de estrategia del paper; cualquier adaptación se documenta como
  desviación y motivo.
- Evaluación con la disciplina existente del motor: walk-forward, t+1,
  costes IBKR, live-gates. **Sin reoptimizar sobre la ventana de test.**
- **Límite anti-overfitting**: máximo 5 candidatas por ronda. Las
  descartadas se archivan con el motivo y no se "recuperan" retocando
  parámetros (un 151-catálogo es una máquina de data snooping si se le
  deja).
- **Veredicto binario por candidata**: satélite (pasa a registro y paper)
  o descartada (documentada). Sin término medio.
- Cobertura de datos y supuestos en cada informe (D04/§5, como siempre).

## 4. Tareas

- **T5.1** Lectura y preselección de 3–5 candidatas con los criterios de
  §2; nota en `docs/` con la lista y el porqué de cada una.
- **T5.2** Implementación de cada candidata como estrategia del motor:
  fórmula citada, parámetros por config, registro en `_STRATEGIES` (mismo
  mecanismo que core-satélite y low_vol; sin constantes mágicas).
- **T5.3** Backtest walk-forward de cada una con el informe estándar
  (costes, cobertura de datos, supuestos).
- **T5.4** Veredicto por candidata (satélite o descartada, con evidencia).
  Las supervivientes quedan disponibles para paper y para que la UI las
  muestre con su rol core/satélite/defensivo.

## 5. Relación con otros planes

| Plan | Relación |
|---|---|
| `PLAN_DATOS_REALES_Y_EJECUCION.md` | Prerrequisito: B1 (fundamentales PIT) y B3 (FX/tipos) alimentan las candidatas; B4 lleva las supervivientes a paper |
| `PLAN_ADOPCION_LIBRERIAS.md` | Comparte el rechazo a intradía/HFT (tick); MAPIE podría calibrar la abstención de una candidata si procede — opcional, no requerido |
| `PLAN_UI_BEAT_THEM_ALL.md` | Clusters disjuntos; las supervivientes se integran en la narrativa UI vía `_STRATEGIES` y el rol core/satélite ya existente |
| `ORDEN_PLANES.md` | Cola canónica: este bloque figura registrado allí dentro del punto 3 |

## 6. Qué NO hace este plan

- No sustituye ni modifica las estrategias núcleo del core-satélite.
- No abre la puerta a intradía, HFT, datos de pago u operaciones reales.
- No implementa las 151 estrategias (ni de lejos): 3–5 candidatas por
  ronda, con veredicto documentado.
