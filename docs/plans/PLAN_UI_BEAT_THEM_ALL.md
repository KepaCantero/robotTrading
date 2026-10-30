# Plan UI "Beat Them All" — manejo + UI para novatos

> Estado: **EN COLA** (2026-10-25). Se implementa DESPUÉS de `PLAN_ADOPCION_LIBRERIAS.md` y `PLAN_DATOS_REALES_Y_EJECUCION.md` (orden explícito del usuario, 25-10-2026). Ver §0 y `ORDEN_PLANES.md` (cola canónica).
> Audiencia: gente que quiere un portfolio fiable **sin tener muchos conocimientos**.
> Posicionamiento del producto: robo-trading de loop completo — preferencias → portfolio → backtest → optimización → paper → rebalanceo → live → rebalanceo.
> Owner del plan: sesión ZCode que lo implemente (empezar leyendo este archivo completo).

---

## 0. Orden global (decisión del usuario, 25-10-2026)

Este plan se implementa **después** de:

1. **`PLAN_ADOPCION_LIBRERIAS.md`** — adopción de librerías (MAPIE adoptada como T2.6; OpenBB venv aparte; PySR sandbox; tick rechazado). No añade código del core salvo MAPIE con el Bloque 2 del siguiente plan.
2. **`PLAN_DATOS_REALES_Y_EJECUCION.md`** — el plan maestro de datos/ejecución: B1 fundamentales reales PIT (SimFin, rellena los stubs de `point_in_time_database.py`) → B2 Dividend Safety Score propio + MAPIE → B3 FX real (Dukascopy, mata las constantes inventadas del carry) → B4 `ib_async` paper sobre Docker (requiere cuenta TWS del usuario).

Orden resultante: **Plan Datos (B1→B2, B3/B4 en paralelo) → Plan UI (UI-0→UI-7)**.

**Por qué este orden tiene sentido** (y no es solo capricho): la UI cuenta la historia del loop validado — números honestos, score de dividendo, paper real. Sin B1–B4, la UI narraría stubs: el pie mostraría un score que no existe (B2), "paper trading" sin adaptador IBKR real (B4), y los badges de validación blindarían datos aún mock en FX (B3). Primero el motor dice verdad; luego se lo enseñamos al novato. Además varios assets de la UI dependen directamente de esos bloques:
- UI-1 (wizard) muestra el **score de seguridad de dividendo** en la ficha de cada valor → necesita B2 (y su abstención MAPIE de T2.6).
- UI-2 (pie) y el preview de rebalanceo → necesitan B1 (universo PIT real) para que lo que se ve sea lo que el motor usa.
- UI-3/4 (Mission Control, trust layer) → el paso "Paper" solo es real tras B4.
- Los badges "Fees included ✓ / Walk-forward 5/5 ✓" ganan peso con el score validado COVID de T2.4.

**Regla práctica para la sesión que ejecute**: si al llegar aquí B1–B4 siguen incompletos, NO se bloquea todo el plan UI — se hace igualmente UI-0 (design system, independiente), y el resto de fases se ajusta a lo que exista, mostrando siempre el estado real de los datos (regla D04: limitación visible, nunca datos inventados en la UI).

---

## 1. Tesis

Ninguna app de pago muestra al usuario **cómo se construye y valida su cartera**. Los robo-advisors ganan por marca y regulación; los terminales ganan por charts. Esta app gana donde nadie compite:

1. **Transparencia radical** — el novato VE al motor validar su cartera (backtest honesto con comisiones IBKR, walk-forward, 18 años).
2. **Números honestos** — "con comisiones reales habría hecho +X% en 18 años, peor caída −Y%". Ningún competidor enseña esto.
3. **Fiscalidad española** modelada (regla 2 meses, drag de distribuidores) — el ecosistema de pago es US-céntrico.
4. **0% de comisión** vs 0,25–0,9% anual de los robos.

NO competir en: charts intradía (TradingView), marca (Fidelity), profundidad de terminal (IBKR). El terreno es la **narrativa del loop validado**.

## 2. Meta medible (criterios de victoria)

Un novato completo, sin ayuda:
- **< 5 min** desde que abre la app hasta ver su portfolio propuesto y entender por qué es fiable.
- **< 10 min** desde que abre la app hasta tener ese portfolio corriendo en **paper**.
- **0 términos financieros sin explicación** (tooltip ELI5 en todo).
- **WCAG AA** verificado en todas las páginas (ninguno de los 10 referentes lo tiene).
- Todo texto de UI en **inglés**, tono sereno de app de aprendizaje (sin wording gamificado).

## 3. Matriz competitiva (referentes del artículo merge.rocks 2024 + robos)

| Referente | Su mejor jugada | Nuestra jugada ganadora |
|---|---|---|
| Robinhood | Onboarding móvil sin fricción | Wizard termina en portfolio **validado con historia y comisiones reales**, no en cuenta vacía |
| M1 Finance | "Pies" visuales + rebalanceo | Pie interactivo con fundamento: backtest honesto + fiscalidad detrás de cada porción |
| Fidelity / Schwab | Confianza de marca | Confianza por evidencia: ver el motor validar paso a paso |
| SaxoTraderGO | Mobile-first | PWA ligera, sin cuenta ni descarga para probar |
| Interactive Brokers | Profundidad profesional | Al revés: novice por defecto, profundidad opcional (progressive disclosure) |
| Composer.trade | Estrategias automáticas | Loop completo visible en 1 clic **y disponible fuera de EE.UU.** |
| Betterment / Indexa (~0,53%) | Robo regulado cero-esfuerzo | Mismo 1-clic + explicación del porqué + 0% comisión |
| TradingView / MetaTrader | Charts / terminal | No competir: 1 equity curve bonita basta; nuestro terreno es la narrativa |

Fuente de referencia: https://merge.rocks/blog/the-10-best-trading-platform-design-examples-in-2024

## 4. Fases

### UI-0 — Design system (fundación, ~1 semana)
**Entregables:** tokens de la paleta actual (cream/sage/teal/honey, sin blanco puro), escala tipográfica, espaciados, y librería de componentes NiceGUI: card, botón primario/secundario, skeleton loader, estado vacío, estado error, tooltip ELI5, badges de validación ("Fees included ✓", "Walk-forward 5/5 ✓").
**Criterio de aceptación:** toda página nueva se construye solo con estos componentes; dos páginas distintas se ven del mismo autor.
**Nota:** sin esta fase, cada página sale de un autor distinto. No saltársela.

### UI-1 — Wizard `/start` (la jugada maestra)
**Entregables:** página `/start` con 5 tarjetas-pregunta (edad, horizonte, riesgo, provincia/impuestos, objetivo) → pantalla final: **pie propuesto + tarjeta de números honestos** + 2 botones: *"Validate it"* (lanza backtest real detrás del wizard, con narración de progreso) y *"Customize"*.
**Reglas:** el optimizador corre INVISIBLE (presets, nunca sliders para novatos). Reusar los presets existentes de edad/riesgo/provincia del swarm dashboard.
**Criterio:** novato completo llega a portfolio validado en < 5 min sin ayuda.

### UI-2 — Portfolio como pie interactivo
**Entregables:** extender el donut de sectores existente: cada porción clicable → ficha del símbolo (qué hace en llano — "SCHD: the dividend engine", peso, rol core/satélite/defensivo que ya clasifica la estrategia). Botón único **"Preview rebalance"** → qué compraría/vendería + coste fiscal estimado → 1 clic para confirmar.
**Criterio:** preview de rebalanceo entendible por un novato en una pantalla, sin jerga.

### UI-3 — Mission Control (storytelling del loop)
**Entregables:** unificar OfficeScene + StepTrack rail como página central del novato: barra de progreso del loop completo (Design → Backtest → Optimize → Paper → Live), cada etapa narra en llano ("Checking 18 years of history… simulating real fees…"). Los diálogos por paso ya existen.
**Criterio:** esta pantalla es el screenshot de portada contra los 10 referentes.

### UI-4 — Capa de confianza (obligatoria antes de live)
**Entregables:** (a) escenarios "what can go wrong" en llano ("if 2008 repeats, expect roughly this"); (b) puerta a live: riesgo explicado sin jerga legal + confirmación explícita en 2 pasos; (c) vista del registro auditable de decisiones del bot (el event store T1→T10 ya existe).
**Criterio:** un novato entiende el riesgo que asume antes de conectar dinero real.

### UI-5 — Móvil y PWA
**Entregables:** pass de responsive (NiceGUI es desktop-first — hoyo contra Saxo/Robinhood): nav inferior en móvil, targets táctiles ≥44px, manifest PWA, prueba REAL en teléfono.
**Criterio:** el wizard `/start` completo usable con un pulgar.

### UI-6 — Retención y educación
**Entregables:** digest semanal ("your portfolio did X; suggested action: none — rebalancing in March"), tooltips-glosario en TODOS los términos, expandir los HELP&DOCS tiles existentes.
**Criterio:** el novato aprende usando la app, sin salir de ella.

### UI-7 — Pulido final
**Entregables:** micro-interacciones calmadas (sin gamificación), estados vacío/carga/error con personalidad en todas las páginas, ⌘K opcional. Gates finales: auditoría a11y AA + Lighthouse.
**Criterio:** 0 hallazgos críticos de a11y; Lighthouse ≥90 en las páginas del loop.

### Orden
UI-0 → UI-1 → UI-2 → UI-3 (corazón: loop del novato de cero a paper). UI-4 antes de live. UI-5 antes de enseñar a cualquier usuario real con móvil. UI-6/7 al final.

## 5. Assets existentes a REUTILIZAR (no reconstruir)

- **Motor**: BacktestEngine honesto (t+1, comisiones IBKR, walk-forward gate, live-gates a signal_time). Ya validado 18,8 años.
- **Estrategias**: dividend core-satélite (clasifica core/satélite/defensivo de cualquier universo), low_vol, etc. — registro `_STRATEGIES`.
- **Dashboards NiceGUI**: home "/" y "/swarm" UNIFICADOS, página "/optimize" (grid search + adopt + restore), "/portfolio" (robo-advisor con fiscalidad España, winner adoption).
- **Componentes**: OfficeScene animada, StepTrack rail + panel NOW, donut BY SECTOR, EQUITY CURVE (payload limit 64KB — cuidado con `results→backtest_result→backtest_result→equity_curve`).
- **Presets**: edad/riesgo/provincia+impuestos, PERIOD_PRESETS propios de /optimize, presets de objetivo que cambian universo (dividend → DEEP_DIVIDEND_ETF_UNIVERSE).
- **Executor/event store T1→T10** real (para UI-3 y el registro auditable de UI-4).
- **Docs ELI5** existentes (38 páginas) para los tooltips de UI-6.

## 6. Gotchas de implementación (aprendidos a golpes)

- **ECharts en NiceGUI 3.18**: formateadores como `"{value} €"` en template string; las arrow-functions JS se pintan como texto literal.
- **NiceGUI 3.18 select**: opciones en formato dict; lista-de-dicts renderiza "[object Object]".
- **Tests de UI**: usar `.mark()` para clicks.
- **Tras cada commit de estrategia/engine: REINICIAR el dashboard** (el usuario ya vio resultados idénticos por proceso stale 2026-10-21; port 8503, log `/tmp/robotTrading-dashboard.log`).
- `ui.element.text` no existe en NiceGUI 3; verificar API antes de asumir.
- Estilo UI: paleta cálida de app de aprendizaje (cream+sage/teal/honey, NO blanco puro), inglés, sereno, WCAG AA + mínimo-clic como requisitos duros, SIN listas de texto para pipelines (visual).

## 7. Contexto competitivo (por qué este plan gana)

Los robos (Indexa ~0,53% total, Betterment 0,25%, Interactive Advisors 0,10–0,75%) ganan hoy solo en: dinero real día uno, regulación y cero mantenimiento. En calidad de portfolio y transparencia no ganan — nuestro motor de validación es más honesto que lo que hay detrás de cualquiera. La batalla no es el motor (está casi todo): es **(1)** loop de 1 clic sin jerga, **(2)** live IBKR (pendiente cuenta TWS del usuario), **(3)** historia de confianza por transparencia.
