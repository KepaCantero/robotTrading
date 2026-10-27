# ORDEN_PLANES.md — Cola canónica de implementación

> **Punto de entrada para cualquier sesión de IA.** Si tienes que decidir qué
> implementar, este archivo manda sobre los encabezados de estado internos de
> cada plan (pueden estar rancios). Última actualización: 25-10-2026, por
> orden explícito del usuario.

**Reglas fijas de gobierno** (heredadas, no se renegocian aquí):
- Ningún plan se auto-autoriza: los que dicen "borrador para aprobación"
  arrancan solo cuando el usuario dice «empieza».
- Verificar cada plan contra el código antes de construir (los planes
  caducan; la matriz y el git son la verdad).
- Repo multi-agente: clusters de archivos disjuntos entre sesiones; el
- usuario commitea.
- Dinero real y exposición pública: excluidos hasta nuevo decreto.

---

## La cola, en orden

### 1 — EN CURSO: campaña paper IBKR
**`PLAN_PRODUCCION_PAPER_IBKR.md`** (+ `MATRIZ_HALLAZGOS_A_D.md` como tablero vivo)

Documento de gobierno del proyecto (aprobado 24-10-2026: «quiero que lo implementes»).
Progreso ya en git: F0 ✅, F2 ✅ (96249c4a), F4 ✅ (030898bf, 05d3327a),
F5 ✅ (3bee2f06), F6 v1 ✅ (39281032, stack paper Docker verificado en vivo).
**Queda**: el PUSH de los commits locales (valida A22, último hallazgo),
retest de quote IBKR en horario US y los pasos §5 (3 órdenes controladas →
20 sesiones). F3 ya validada EN VIVO (26-10: cuenta paper DU9811225,
observación sin envíos). F4/F5/F6 completas; recuento oficial: 35/36.

### 2 — ✅ ATERRIZADO (26-10-2026): gate de calidad + /optimize rápido
**`GATE_CALIDAD_DATOS_Y_OPTIMIZE.md`**

Fase A (0c68d5a1): `data_quality.py` STRICT — la truncación silenciosa y
el `continue` murieron; `allow_partial_data` explícito con report adjunto
SIEMPRE; caché LRU de quotes por (path, mtime, ventana). Fase B
(5ab13e6d): trials en ProcessPool con worker picklable + re-run redundante
del mejor ELIMINADO; 1.52x medido en el grid real de dividendos.
Verificación: goldens 19/19, swarm+optimization 211/211, orquestación
50/50; dashboard reiniciado tras el commit (regla permanente).

### 3 — SIGUIENTE BLOQUE: datos reales + ejecución
**`PLAN_DATOS_REALES_Y_EJECUCION.md`** con **`PLAN_ADOPCION_LIBRERIAS.md`** de compañero
*(orden del usuario 25-10-2026: antes que la UI)*

- B1 ✅ ATERRIZADO (26-10, 310f7f7e): SimFin PIT real (key del usuario en
  env), stubs de point_in_time_database muertos, 9 tests sobre corpus real.
  B3 ✅ ATERRIZADO (457dbb85): FX ECB/FRED real, constantes fuera del camino
  de datos. B2 ✅ CERRADO COMPLETO (26-10: 83bca846 score + 538d02ac endpoint T2.3 +
  4ea954e2 MAPIE T2.6): score PIT con fórmula pública validado (LUMN
  58.3<60 cazado; T/INTC límite documentado), /dividends/safety sirve el
  MISMO informe (401 sin clave), clasificador conforme LAC al 90% con
  cobertura MEDIDA 0.8957 y 6.5% abstención en walk-forward real.
  B4 ya cubierto por la Fase 3 validada en vivo. B5 ✅ RONDA 1 CERRADA (26-10,
  ce5d9749): 5 candidatas del paper implementadas y evaluadas con la
  disciplina del motor — TODAS DESCARTADAS con evidencia (0 satélites; el
  núcleo sigue invicto). **Bloque 3 del plan de datos COMPLETO.**
- B4 (`ib_async` paper) ejecuta la Fase 3 del plan 1 y arranca cuando el
  usuario tenga la cuenta TWS.
- B5 (catálogo del paper "151 Trading Strategies",
  `PLAN_B5_ESTRATEGIAS_CATALOGO.md`, creado 25-10-2026): tras B1+B3;
  paralelizable con la UI (clusters disjuntos). 3–5 candidatas a satélite
  con veredicto binario documentado; el paper define, el motor valida.
- Del plan de librerías: MAPIE entra con B2; OpenBB = venv aparte (T-O1,
  opcional); PySR solo sandbox; tick rechazado.
- Ambos dicen internamente "borrador para aprobación": el usuario ya los
  puso en cola; arrancan con su «empieza».

### 4 — ✅ COMPLETO (27-10-2026): UI "Beat Them All"
**`PLAN_UI_BEAT_THEM_ALL.md`** — las 8 fases aterrizadas: UI-0 design
system con gate AA ejecutable (de2f51d9) · UI-1 wizard /start (a8b0b7c8) ·
UI-2 pie interactivo (47703c2d) · UI-3 Mission Control (ec29f871) · UI-4
/trust (5e96d1a2) · UI-5 móvil+PWA (63fb5966) · UI-6 digest+glosario
(e08e739d) · UI-7 auditoría a11y ejecutable + fix lang (0b2ee2ed). El loop
del novato (0→cartera validada, números honestos, cero jerga) está contado
de punta a punta. Pendiente usuario: prueba REAL en teléfono (A23 =
loopback; exponer a LAN es decisión suya) y Lighthouse manual (Chrome).

### 5 — FUTURO (sin orden interno todavía)
- Dinero real: reutilizar `archivo/ROLLOUT_PLAN.md` como referencia de escalado
  cuando se decida.
- Fase crypto (ccxt anotado), datos de pago (EODHD ~20 $/mes) si el SimFin
  gratis se queda corto, valores España/BME.

---

## Completados o históricos (NO ejecutar) — viven en `archivo/`

Movidos fuera de la cola el 25-10-2026 con banner de ARCHIVADO en su
cabecera (si un agente los encuentra por grep, el banner le para).

| Plan | Estado |
|---|---|
| `archivo/FASE5_Backtesting_Engine.md` | ✅ Completado (gate walk-forward, simulador falso fuera, etc. — 562934d1) |
| `archivo/ROBO_ADVISOR_PAPER.md` | ✅ Completado (robo-advisor + /portfolio E2E — f65f28ef..bf023bdb) |
| `archivo/FASE_6_ADVANCED_MODULES.md` | Aspiracional de otra era (XAI/GAN/Neo4j); nada adoptado, fuera de cola |
| `archivo/MULTI_MARKET_EXPANSION.md` | Histórico/referencia; su parte FX vive ahora en B3 del plan 3; crypto → futuro |
| `archivo/PLAN_SUMMARY.md`, `archivo/VISUAL_ROADMAP.md` | Trilogía de 28 semanas de la era pre-campaña; timeline sustituido por el plan 1 |
| `archivo/ROLLOUT_PLAN.md` | Histórico; se reutiliza como referencia en el punto 5 |
| `archivo/fix_gap_violations.md`, `archivo/refactor-portfolio-di.md` | One-offs resueltos de otra era |
| `MATRIZ_HALLAZGOS_A_D.md` | No es un plan: tablero vivo de seguimiento del plan 1 |

---

**Mantenimiento de este archivo**: cada vez que un plan aterrice o el usuario
cambie el orden, actualizar esta lista en el mismo commit. Es la única lista
de orden que gobierna.
