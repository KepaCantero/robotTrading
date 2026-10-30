# Plan de adopción de librerías: MAPIE, OpenBB, PySR, tick

> **Origen.** Sesión ZCode del 25-10-2026, evaluando cuatro librerías contra el
> análisis competitivo y el plan maestro `PLAN_DATOS_REALES_Y_EJECUCION.md`.
> Cada decisión está respaldada por verificación directa del repositorio
> upstream y del `pyproject.toml` del proyecto (estado y hechos al 25-10-2026).

Fecha: 25 de octubre de 2026.

**Estado: borrador para aprobación.** Este documento no autoriza
implementación hasta instrucción directa del usuario (misma regla de
gobierno que el resto de planes).

## 1. Resumen de decisiones

| Librería | Decisión | Papel | Toca `pyproject.toml` |
|---|---|---|---|
| **MAPIE** | ✅ Adoptar | Predicción conforme en el score de dividendo (Bloque 2) | Sí, al implementar el Bloque 2 |
| **OpenBB** | ✅ Fuera del core | Terminal de investigación personal, venv aparte | No |
| **PySR** | ⚠️ Solo sandbox | Experimento aislado en `experiments/` si hay curiosidad | No |
| **tick** | ❌ Rechazar | Ninguno (dominio HFT/microestructura) | No |

Regla que gobierna las cuatro: una librería entra solo si resuelve un
problema que el proyecto **tiene hoy**, con licencia compatible y sin
romper la trazabilidad de datos (D04/§5). Lo demás se registra para no
re-debatirlo.

## 2. MAPIE — adopción como mejora del Bloque 2

**Qué es** (verificado: `scikit-learn-contrib/MAPIE`, activo, licencia
BSD-3): predicción conforme sobre cualquier estimador sklearn-compatible,
con garantía de cobertura bajo intercambiabilidad.

**Por qué encaja**: convierte el Dividend Safety Score de "número 0–100"
en tres estados — seguro / dudoso / **no clasificable con confianza** —
con respaldo estadístico. Es la versión rigurosa del patrón
`computable=False` de `dividends.py`: la abstención deja de ser una
heurística y pasa a tener nivel de confianza elegido.

**Dónde**: tarea nueva **T2.6** del Bloque 2 de
`PLAN_DATOS_REALES_Y_EJECUCION.md`, después de que el score base (T2.1)
exista:

- Clasificación conforme (métodos LAC/APS de MAPIE) sobre el clasificador
  "recorta / no recorta en 12m" que alimenta el score.
- El informe del score publica: score, conjunto de predicción (etiquetas
  compatibles con la confianza elegida) y etiqueta de abstención cuando el
  conjunto no es un único valor.
- Nivel de confianza configurable (90% por defecto) y visible en el
  informe, como cualquier supuesto.

**Dependencia**: `mapie` se añade a `pyproject.toml` **solo cuando se
implemente el Bloque 2** — no antes (el score base no existe aún, y el
proyecto ya tiene `scikit-learn>=1.3.0`, que es su único prerrequisito).

**Honestidad exigida** (letra pequeña del método):

- La cobertura es garantía *bajo intercambiabilidad*; los mercados la
  violan en cambios de régimen. La cobertura publicada se **mide
  empíricamente en walk-forward** (hit-rate real de los intervalos) y esa
  medición es parte del informe, no un copiado del nominal.
- Los métodos de series temporales (EnbPI) para intervalos de predicción
  de rentabilidades quedan **fuera de alcance** hasta que exista un modelo
  predictivo en el sistema; hoy las estrategias son basadas en reglas.

**Criterio de aceptación**: (a) score + conjunto conforme reproducibles
(golden file); (b) cobertura empírica walk-forward dentro de una banda
predefinida del nominal (p. ej. ≥ nominal − 5 pp); (c) la abstención
declarada coincide con los símbolos con huecos de fundamentales
(covariación sensata con `coverage_gaps`).

## 3. OpenBB — terminal de investigación al lado de la app

**Qué es** (verificado: `openbq-org/OpenBB` — renombrado desde
`OpenBB-finance`; 74,7k estrellas, activo; **Apache-2.0**, confirmado en
su LICENSE): plataforma abierta de datos para analistas: paquete Python
unificado sobre decenas de proveedores + CLI/desktop para investigar.

**Rol aprobado**: herramienta personal de investigación — charts,
exploración de fundamentales, datos macro y FX — cubre gratis parte del
hueco "TradingView" (punto 5 del análisis competitivo) y ayuda a explorar
el universo de dividendos antes de codificarlo.

**Condiciones de uso**:

- Instalación en un **venv propio, fuera del proyecto** (p. ej.
  `~/venvs/openbb`); nunca en el entorno de `robotTrading`.
- **Prohibido** como dependencia del core. Motivos verificados:
  1. **No resuelve el PIT**: SimFin **no** es proveedor de OpenBB
     (verificado en su código, 0 resultados); sus proveedores gratuitos de
     fundamentales no exponen fecha de publicación. El Bloque 1 sigue
     siendo SimFin directo.
  2. Árbol de dependencias grande y evolución rápida — desproporcionado
     para los dos endpoints que el proyecto necesita (bulk SimFin, CSV
     Dukascopy).
  3. Añade una capa entre la app y la procedencia del dato, contra la
     regla de trazabilidad (D04/§5).
- Si algún día se usara para descargar algo, sería dentro de un *script*
  del patrón `scripts/download_*.py` que guarda CSV con metadatos de
  fuente — nunca importado por `app/`.

**Tarea** (una sola, opcional, sin código del core): T-O1 — crear el venv
aparte, `pip install openbb`, y documentar en `docs/developer/` el comando
de arranque. 10 minutos, sin efectos sobre el repo.

## 4. PySR — experimento de sandbox, jamás dependencia

**Qué es** (verificado: `astroautomata/PySR`, activo): regresión simbólica
que descubre fórmulas cerradas; **requiere runtime de Julia**.

**Decisión**: el score del Bloque 2 se construye con ponderaciones
documentadas (ya decidido en el plan maestro). PySR queda relegado a
**experimento aislado** si hay curiosidad: un notebook en `experiments/`
(«¿la regresión simbólica redescubre el payout ratio como factor dominante
a partir de los factores SimFin del Bloque 1?»).

**Condiciones si el experimento se hace**:

- `experiments/` con su propio venv/lockfile; **jamás** en `pyproject.toml`
  ni importado por `app/`.
- Semillas fijadas y resultado publicado como nota en `docs/` (hallazgo
  cualitativo), no como código del core.
- Regla de salida: si el experimento no redescubre factores conocidos en
  tiempo razonable, se archiva sin más (los eventos raros — recortes de
  dividendo — son terreno natural de sobreajuste para búsqueda evolutiva).

## 5. tick — rechazado con condición de revisión

**Qué es** (verificado: `X-DataInitiative/tick`, vivo — v0.8.0.2, mayo
2026, wheels py3.14): procesos puntuales/Hawkes, supervivencia — modelado
de microestructura y autoexcitación de órdenes.

**Decisión**: rechazado. No es un problema de calidad sino de dominio: el
proyecto opera en horizonte diario/semanal (dividendos, carry) y el Bloque
3 fija datos diarios explícitamente. tick resuelve problemas de HFT que el
proyecto no tiene.

**Condición de revisión**: se re-evalúa solo si aparece análisis de
ejecución intradía real (p. ej. clustering de fills contra IBKR paper una
vez el Bloque 4 esté operativo). No antes.

## 6. Impacto conjunto

- `PLAN_DATOS_REALES_Y_EJECUCION.md`: el Bloque 2 recibe la tarea T2.6
  (MAPIE); nada más cambia. Los Bloques 1, 3 y 4 no se ven afectados.
- `pyproject.toml`: único cambio futuro = `mapie` (con el Bloque 2).
- Nuevo directorio opcional `experiments/` (solo si se ejecuta el sandbox
  PySR); fuera del paquete instalable.
- Orden de trabajo global no cambia: B1 → B2 (ahora con MAPIE) → B3, B4 en
  paralelo. La cola canónica de todos los planes vive en `ORDEN_PLANES.md`;
  el catálogo de estrategias del paper 151 es el Bloque 5
  (`PLAN_B5_ESTRATEGIAS_CATALOGO.md`, tras B1+B3).
