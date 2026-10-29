# Plan integral: robotTrading en producción paper con IBKR

> **Addenda ZCode (24-10-2026).** Documento de gobierno del proyecto, transcrito
> verbatim del plan aprobado. El estado original («guardado, implementación
> pausada») quedó anulado el 24-10-2026 por instrucción directa del usuario:
> **«quiero que lo implementes»**. La implementación sigue el orden de fases de
> este documento sobre la rama `zcode/produccion-paper` (el nombre `codex/` del
> texto original se sustituye por `zcode/` por decisión del usuario: «no crees
> nada de codex, estamos en zcode»). Las auditorías fuente de los hallazgos
> A01–A24 y D01–D12 están en `docs/audits/2026-10-24/`, y su estado verificado
> contra código, en `docs/plans/MATRIZ_HALLAZGOS_A_D.md`.

Fecha: 24 de octubre de 2026.

**Estado: guardado, implementación pausada por petición del usuario.** Este documento no autoriza ejecutar el plan. Las correcciones del workflow de dividendos realizadas anteriormente permanecen en el árbol de trabajo; después de presentar este plan solo se inspeccionaron el repositorio y el entorno, sin nuevos cambios de implementación ni despliegues.

## 1. Objetivo y decisiones fijadas

Poner el proyecto completo en funcionamiento fiable en **este Mac con Docker y TWS de Interactive Brokers, exclusivamente en cuenta paper**, con dividendos como primera estrategia operativa.

- Corregir los **24 hallazgos generales y los 12 del workflow de dividendos**, incluyendo la integración IBKR pendiente.
- Incorporar y revisar los cambios locales ya realizados; conservar la simulación original como referencia reproducible.
- Reinvertir dividendos efectivamente cobrados, registrando por separado renta distribuida, reinversión y rentabilidad total.
- Utilizar datos disponibles y exportaciones, sin contratar proveedores.
- Mantener GitHub como repositorio de referencia; no migrar a GitLab en este trabajo.
- Excluir operaciones reales, exposición pública de la aplicación y promoción automática de estrategias.

El éxito se medirá por corrección contable, recuperación ante fallos, trazabilidad y estabilidad operativa. La simulación existente **no demuestra una mejora global de rentabilidad ni mayor dividendo cobrado**.

## 2. Implementación por fases

### Fase 0 — Consolidar el punto de partida

- Guardar las correcciones actuales en una rama `codex/`, con pruebas, documentación y resultados reproducibles.
- Crear una matriz A01–A24 y D01–D12 con estado, cambio asociado y prueba de aceptación. Diferenciar «corregido», «validado» y «pendiente».
- Preparar entornos separados de desarrollo, integración y paper, con bases de datos y configuraciones independientes.
- Inventariar Docker, arquitectura del Mac, instalación TWS, cuenta paper y permisos de datos mediante comprobaciones de lectura.
- Fijar dependencias y herramientas en un entorno reproducible; resolver errores de colección y los fallos preexistentes antes de declarar la suite validada.

**Salida:** instalación limpia reproducible y línea base de pruebas conocida.

### Fase 1 — Autenticación y autorización

**Hallazgos A01–A02 y A13–A15.**

- Unificar autenticación mediante dependencias FastAPI y un único principal con roles `viewer`, `trader` y `admin`.
- Proteger por defecto rutas de cuentas, posiciones, señales, configuración, ejecución y resets.
- Eliminar claves de desarrollo y rechazar configuraciones operativas sin credenciales válidas.
- Corregir extracción de `Request`, rate limiting y respuestas: 401 sin autenticación, 403 sin permiso.
- Registrar cambios sensibles con identidad y timestamp, sin incluir secretos en logs.

**Salida:** matriz HTTP completa de rutas y permisos aprobada usando la aplicación real.

### Fase 2 — Riesgo y ejecución recuperable

**Hallazgos A03–A09, A16–A18 y A20.**

- Establecer un servicio de riesgo autoritativo por cuenta, compartido por API, alertas y órdenes.
- Persistir límites y reservas de órdenes pendientes; calcular exposición posterior, efectivo disponible y concentración de forma transaccional.
- Validar todos los tipos de orden, incluyendo STOP y MARKET. Eliminar precios ficticios y rechazar cotizaciones ausentes, obsoletas o no aptas para ejecutar.
- Validar cantidades y precios con `Decimal` finito; aplicar divisa, multiplicador y restricciones del instrumento.
- Unificar la pérdida diaria como `max(0, -PnL)` sobre el patrimonio al inicio de sesión.
- Permitir cierres `reduce-only` durante un bloqueo, sin permitir aumentos de posición ni aperturas cortas accidentales.
- Persistir intención antes del envío, identificador estable, estados, fills y reservas. Ante un timeout ambiguo, reconciliar antes de reintentar.
- Supervisar todas las órdenes abiertas; devolver estados reales, incluidos rechazo y estado desconocido.
- Sustituir cierres y reaperturas de rebalanceo por órdenes de diferencia de cantidades, respetando fills parciales y órdenes pendientes.

**Salida:** reinicios, concurrencia y fallos de red no generan duplicados ni exposición fuera de límites.

### Fase 3 — Integrar IBKR y reparar la contabilidad paper

**Hallazgo A10 e integración adicional.**

- Conectar un adaptador IBKR al contrato de `BrokerConnector`, reutilizando los componentes existentes que superen pruebas de contrato.
- Eliminar el parche global del bucle asíncrono en imports y gestionar conexión, eventos y cierre dentro del ciclo de vida del ejecutor.
- Conectar Docker con TWS en el Mac mediante host configurable; utilizar `client_id` estable y cuenta paper explícitamente autorizada.
- Validar cuenta y entorno al conectar; no considerar el puerto ni una bandera local prueba suficiente de modo paper. Rechazar cuentas no verificadas.
- **Excepción sancionada (29-10, petición del propietario): visión read-only de la cuenta live.** Un adaptador construido explícitamente con `read_only=True` puede VER cuentas `U`-prefijo; `place_order` y `cancel_order` lanzan antes de tocar el socket, siempre. El adaptador por defecto sigue rechazando toda cuenta no-DU. Herramientas: `scripts/view_ibkr_portfolio.py` (cuenta + posiciones) y `scripts/compare_live_portfolio.py --slug <slug>` (diff pesos objetivo del portfolio app vs cuenta broker), ambas read-only y requieren TWS logueado en la cuenta live, puerto 7496. Rebalancear la cuenta live sigue FUERA del alcance: ningún camino de órdenes llega a una cuenta live.
- Resolver instrumentos por identificador de contrato, mercado y divisa; comprobar permisos y disponibilidad sin sustituir activos silenciosamente.
- Reconciliar órdenes, ejecuciones, posiciones y saldos al arrancar, reconectar y periódicamente.
- Reparar el simulador interno: las ventas completas deben acreditar efectivo, y las parciales conservar correctamente cantidades y coste.
- Separar registros confirmados por IBKR de cálculos simulados. Nunca modificar el saldo confirmado del broker para incorporar un dividendo estimado.

**Salida:** circuito señal → riesgo → orden paper → fill → cartera verificable tanto con broker determinista como con TWS paper.

### Fase 4 — Dividendos medidos y reinversión

**Hallazgos D01–D12; completar y validar las correcciones existentes.**

- Añadir importación de eventos de distribución y acciones corporativas desde archivos disponibles, con fuente, identificador, divisa, fechas y momento de conocimiento.
- Registrar unidades con derecho a cobro, importe bruto, retención conocida, importe neto y fecha de disponibilidad.
- Usar precios sin ajuste por dividendos cuando se contabilicen pagos explícitos; gestionar splits coherentemente. Mantener el backtest con precios ajustados como comparación separada.
- Si faltan pagos, retenciones o cobertura temporal, identificar exactamente qué métricas no son calculables; no rellenarlas con yields constantes.
- Reinvertir el efectivo cobrado en el siguiente rebalanceo programado, mediante órdenes normales sujetas a costes, tamaños mínimos y límites. No anticipar pagos.
- Medir dividendos brutos y netos conocidos, renta por unidad de capital inicial, capital reinvertido, retorno total, drawdown y rotación.
- Optimizar renta anual distribuida sobre capital inicial, bajo los límites de riesgo del perfil. Conservar separación cronológica entre selección y evaluación.
- Mantener parámetros efectivos trazables, cadencia en sesiones, refugio predeterminado en efectivo y benchmark de todo el universo con condiciones comparables.
- Mostrar claramente en la UI resultados observados, simulados e incompletos.

**Salida:** dos carteras con igual retorno total y distintos dividendos producen métricas de renta distintas. La falta de datos sigue bloqueando conclusiones sobre dividendos, pero permite ejecutar paper como experimento explícitamente no validado en renta.

### Fase 5 — ML y validez de resultados

**Hallazgos A11–A12.**

- Construir variables únicamente con información disponible en el instante de decisión; beneficios y tasas de acierto solo incluyen operaciones ya cerradas.
- Eliminar el fallback aleatorio cuando falla la validación temporal: el entrenamiento queda fallido o no validado.
- Aplicar separación cronológica y purga según el horizonte de las etiquetas.
- Versionar datos, configuración, semillas y artefactos; marcar modelos afectados como no válidos y recalcularlos.
- Mantener ML fuera del ejecutor paper inicial hasta superar estos controles.

**Salida:** pruebas explícitas contra información futura y resultados reproducibles fuera del periodo de selección.

### Fase 6 — Docker, CI y operación local

**Hallazgos A19 y A21–A24.**

- Separar dependencias de servicio, IBKR, investigación y pruebas; fijar resolución e imágenes, incluyendo configuración no secreta.
- Desplegar API/dashboard, un único ejecutor con planificación, PostgreSQL y las dependencias de cola/cache que realmente requiera el flujo.
- Eliminar los falsos workers que arrancan otra API. El ejecutor será el único propietario de la conexión de órdenes; utilizará bloqueo persistente para impedir dos instancias activas por cuenta.
- Mantener TWS como aplicación del Mac. Publicar la interfaz únicamente en loopback; bases de datos, métricas y logs en red privada.
- Crear migraciones versionadas y readiness que compruebe esquema y servicios esenciales. Separar salud de aplicación de permiso para operar.
- Unificar CI: lint, tipos, seguridad, pruebas, migraciones, arranque real del contenedor e integración determinista. No ignorar fallos con `|| true`.
- Probar también la imagen en la arquitectura del Mac. Consolidar scripts de despliegue y corregir rutas, comprobaciones y errores actualmente silenciados.
- Añadir panel y alertas locales para desconexión, cotizaciones caducadas, órdenes inciertas, divergencias contables y tareas sin ejecutar.
- Configurar backups diarios con retención de 14 días y probar restauración. Un rollback de código no debe borrar órdenes posteriores: reconciliar siempre con IBKR.

**Salida:** despliegue y recuperación repetibles sin depender del entorno temporal de auditoría.

## 3. Interfaces y datos que cambian

- **Identidad:** principal único y permisos compartidos por todos los routers.
- **Órdenes:** identificador de intención, referencia externa, estado explícito, motivo de rechazo y fills acumulados.
- **Riesgo:** configuración versionada, reservas por cuenta y evaluación de cartera proyectada.
- **Broker:** contrato común para conexión, cuenta, cotizaciones, envío, cancelación, eventos y reconciliación.
- **Dividendos:** eventos de distribución, derechos de cobro, pagos y reinversiones, con procedencia y cobertura.
- **Resultados:** configuración efectiva, versión de datos, métricas de renta separadas del retorno y estado de disponibilidad.
- **Persistencia:** migraciones aditivas; los resultados antiguos conservan su versión y no reciben retrospectivamente métricas de renta inventadas.

## 4. Validación y aceptación

Las pruebas deben cubrir:

- Acceso anónimo, claves inválidas y permisos insuficientes en rutas reales.
- Límites modificados por API que se aplican a órdenes y sobreviven a reinicios.
- Órdenes simultáneas, cotizaciones caducadas, valores inválidos y reducción de riesgo con bloqueo activo.
- Timeout antes y después de aceptación, duplicados, fills parciales, cancelaciones, reconexión y reinicio.
- Conservación de efectivo y patrimonio con compras, ventas, comisiones, divisas, splits y dividendos.
- Compra antes/después de la fecha ex-dividendo, cobro posterior, eventos duplicados y reinversión sin doble contabilización.
- Ausencia de información futura en estrategia, optimizador y ML.
- Instalación desde cero, migración de una base existente, backup, restauración y rollback.
- Comparación original/corregida con datos y costes idénticos; resultados de renta solo donde exista cobertura suficiente.

Para cerrar el proyecto: todos los hallazgos tendrán evidencia de resolución, la suite acordada estará verde sin errores de colección y no habrá discrepancias de órdenes o contabilidad pendientes.

## 5. Puesta en producción paper

1. **Integración local:** broker determinista, escenarios de fallo y restauración.
2. **TWS en observación:** conexión sin envíos; verificar cuenta, instrumentos, permisos, datos y reconciliación.
3. **Órdenes controladas en paper:** validar ciclo completo, cancelaciones y fills.
4. **Operación programada:** mantener al menos 20 sesiones de mercado, sin duplicados, discrepancias sin resolver ni incumplimientos de límites. Las incidencias críticas reinician la ventana de aceptación.
5. **Entrega:** versión identificada, matriz de auditoría cerrada, informe de pruebas y manual de arranque, parada, recuperación e importación de datos.

El calendario de dividendos y los rebalanceos largos se verificarán también mediante replay: 20 sesiones no bastan para observarlos todos.

El Mac deberá permanecer despierto y TWS disponible durante las sesiones. Tras una suspensión o pérdida de conexión, se bloquearán nuevas entradas hasta recuperar datos y reconciliar. La indisponibilidad de datos gratuitos se mostrará como una limitación; no se resolverá contratando servicios ni degradando silenciosamente las validaciones.

**La entrega final será producción paper. Activar dinero real queda fuera de este plan.**
