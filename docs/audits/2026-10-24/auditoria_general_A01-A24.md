# Auditoría técnica de robotTrading

> Transcrita verbatim el 24-10-2026 desde la entrega del auditor externo.
> Commit auditado: `e4cb5eac8b5dfc53b92ce9c36621ecd6bf6de04a`. Las rutas
> absolutas `/Users/josu/...` son las del entorno del auditor; en este repo,
> anteponer `app/…` relativo a la raíz. Fuente de los hallazgos A01–A24 del
> plan `docs/plans/PLAN_PRODUCCION_PAPER_IBKR.md`; estado verificado contra
> código en `docs/plans/MATRIZ_HALLAZGOS_A_D.md`.

Fecha: 24 de octubre de 2026. Repositorio: https://github.com/KepaCantero/robotTrading (el enlace facilitado es GitHub).
Commit auditado: `e4cb5eac8b5dfc53b92ce9c36621ecd6bf6de04a`.

## Dictamen

No considero este commit listo para operar con dinero real. Existen defectos verificables en autorización, aplicación del riesgo, recuperación de órdenes, contabilidad paper y preparación de datos de ML. Tampoco usaría los resultados de las rutas afectadas de paper/ML para decidir un despliegue hasta corregirlos y recalcularlos. Esto es una conclusión técnica sobre el código, no una evaluación de rentabilidad.

La arquitectura contiene componentes útiles, pero su integración es el riesgo principal: varios objetos de riesgo independientes, dos mecanismos de autenticación, persistencia que no participa en el envío y distintos caminos de ejecución. Los comentarios “FIXED”, “production-ready” o “fail-closed” no sustituyen pruebas del circuito completo.

## Alcance y método

Se descargó el repositorio completo y se inventariaron 1.013 archivos Python de aplicación (394.059 líneas) y 639 archivos Python bajo tests (232.267 líneas; incluye soporte y fixtures). Se analizó sintaxis de ambos árboles y Ruff/Bandit sobre toda app. La lectura manual se concentró en entrada API, autenticación, órdenes, brokers, riesgo, persistencia, contabilidad, entrenamiento/validación y despliegue/CI.

No se afirma haber leído manualmente cada una de las más de 626.000 líneas. La cobertura automática es global; la revisión semántica es dirigida por criticidad. No es una certificación de ausencia de fallos en módulos no recorridos manualmente. No se modificó el repositorio clonado, no se conectaron cuentas de broker, no se enviaron órdenes ni se desplegaron servicios.

### Comprobaciones ejecutadas

| Comprobación | Resultado | Límite |
|---|---|---|
| Parseo AST app y tests | Sin errores sintácticos | Python 3.12, no demuestra compatibilidad con todo el rango declarado |
| Ruff app | 0 hallazgos | Reglas configuradas en el repo |
| Bandit app | 234 LOW, 0 MEDIUM, 0 HIGH | No son 234 vulnerabilidades confirmadas; no detecta lógica de negocio |
| Tests originales de autenticación | 7/7 pasan | App mínima de decoradores, no middleware ni rutas completas |
| Reproducciones de auditoría | 12/12 confirman el defecto esperado | Código original extraído por AST para aislar dependencias; I/O/config simulados; HTTP real local para middleware/decoradores |
| Colección tests/unit | 1.974 tests recogidos, 217 errores de colección | Entorno de dependencias parcial; NO se presentan como 217 bugs del proyecto |
| Suite completa/cobertura | No ejecutada | No hay porcentaje de cobertura medido en esta auditoría |

El entorno temporal contiene herramientas y dependencias mínimas, no todo el stack ML. La ejecución enfocada de operational_safety quedó bloqueada al importar `requests` en una cadena de imports de app.services. Las ausencias del entorno parcial no se contabilizan como defectos del manifiesto: A19 se basa en imports requeridos que no están declarados. No se ejecutaron Docker, PostgreSQL, Redis ni pruebas reales de broker. No se hizo un análisis de CVE sobre una resolución completa ni una búsqueda exhaustiva de secretos en todo el historial Git. No se ha validado exactitud fiscal/normativa del motor español.

## Hallazgos priorizados

P1: corregir antes de ejecución real o de confiar en la funcionalidad afectada. P2: corregir para operación fiable, reproducible y mantenible. La severidad considera el código y las precondiciones descritas, no presupone exposición pública ni fondos reales.

### A01 · P1 · Operaciones sensibles accesibles sin autenticar

**Ubicación:** `app/presentation/api/portfolio.py:664`.

**Evidencia:** El endpoint de reset no declara autenticación y AuthMiddleware solo protege /strategies, /optimization y /deployment. /signals/execute y los GET de cuenta/posiciones de /live-trading también quedan fuera del filtro global.

**Consecuencia:** Un cliente con acceso de red puede resetear el breaker del servicio de portfolio y consultar información de cuenta; no se afirma que este reset controle el RiskGates del bridge, que es otro objeto.

**Corrección:** Autenticar por defecto todos los routers privados y autorizar cada operación por identidad/rol.

**Verificación:** HTTP anónimo contra cada ruta mutadora y de cuenta debe devolver 401; añadir matriz de autorización.

### A02 · P1 · Clave de desarrollo aceptada en producción

**Ubicación:** `app/presentation/api/middleware.py:102`.

**Evidencia:** El middleware acepta dev-api-key-12345 aun con debug_mode=False. Busca api_keys en model_extra, pero Settings usa extra="ignore" y no declara ese campo. El decorador independiente sí utiliza API_ACCESS_KEYS/API_KEY.

**Consecuencia:** Las rutas protegidas solo por el middleware, como /optimization/validate-config, pueden superar ese control con una clave pública. No supone superar además un decorador independiente.

**Corrección:** Eliminar la clave por defecto, unificar configuración y rechazar arranque/autenticación si faltan claves.

**Verificación:** Reproducción aislada confirmada; verificar también HTTP con la aplicación completa.

### A03 · P1 · Límites actualizados por API desconectados de la ejecución

**Ubicación:** `app/services/live_trading/order_manager.py:601`.

**Evidencia:** get_risk_gates mantiene _gates; get_order_manager construye otro RiskGates y TradingBridgeOrchestrator construye otro más. PATCH /live-trading/risk/limits solo modifica el primero.

**Consecuencia:** La API puede anunciar un límite nuevo que no se aplica a las órdenes. El estado de pérdidas del bridge tampoco recibe el feed de equity de OrderManager en su flujo por defecto.

**Corrección:** Compartir un servicio de riesgo autoritativo y persistente entre API, órdenes y alertas; alimentar PnL desde eventos de cuenta.

**Verificación:** Cambiar el límite por HTTP y comprobar el rechazo de una orden y de una alerta; repetir tras reinicio.

### A04 · P1 · Órdenes STOP pueden saltarse RiskGates

**Ubicación:** `app/services/live_trading/order_manager.py:158`.

**Evidencia:** Toda la validación está condicionada a tener price. Una STOP con stop_price pero price=None llega al broker sin llamar al validador. MARKET sin account también puede eludir este bloque.

**Consecuencia:** El control central no se ejecuta para tipos admitidos por la API. Alpaca añade otra limitación: exige price también para STOP, por lo que puede rechazarla después; no se ha demostrado una ejecución real de STOP en Alpaca.

**Corrección:** Validar siempre tipo, cantidad, cuenta, estado y riesgo; obtener el precio apropiado o rechazar antes de llamar al broker.

**Verificación:** Confirmado con broker simulado: 0 llamadas al riesgo, 1 al broker para STOP.

### A05 · P1 · Precio fijo de 100 en controles de mercado

**Ubicación:** `app/services/live_trading/order_manager.py:155`.

**Evidencia:** OrderManager y el bridge usan 100 como estimación de órdenes MARKET. /risk/validate usa portfolio_value/100. Ninguno representa una cotización del símbolo.

**Consecuencia:** Para un activo a 1.000, el riesgo de la orden se puede infravalorar diez veces. El adaptador Alpaca omite el control de tamaño de posición para MARKET y solo exige cantidad positiva.

**Corrección:** Usar bid/ask reciente, divisa y multiplicador del instrumento, con margen de deslizamiento; rechazar cotizaciones ausentes o caducadas.

**Verificación:** Confirmado precio 100 recibido por el validador; añadir casos multiactivo y cotizaciones obsoletas.

### A06 · P1 · Riesgo calculado antes de la orden, sin exposición proyectada

**Ubicación:** `app/services/live_trading/risk_gates.py:188`.

**Evidencia:** Se descartan las posiciones obtenidas. El límite absoluto compara solo esta orden; concentración es una advertencia; apalancamiento y caja usan el estado previo. Tampoco se reserva riesgo de órdenes pendientes.

**Consecuencia:** Varias órdenes pueden exceder límites agregados aunque cada llamada esté serializada. El lock por proceso no soluciona reservas ni coordinación entre procesos.

**Corrección:** Calcular posiciones, exposición bruta/neta, caja y margen posteriores incluyendo pendientes; reservar atómicamente por cuenta.

**Verificación:** Confirmado: orden de 15.000 con equity 10.000 y límite 2x pasa con advertencia. La cuenta simulada tiene 10.000 invertidos, caja cero y buying power suficiente: añadir 15.000 proyecta 2,5x, pero se valida solo el 1x previo. No se simula el cálculo de margen del broker.

### A07 · P1 · Ganancias diarias activan el límite de pérdidas

**Ubicación:** `app/services/live_trading/risk_gates.py:236`.

**Evidencia:** validate_order pasa abs(daily_pnl) a check_daily_loss: +600 y -600 se tratan igual. Además el denominador es equity actual, distinto del capital inicial usado por check_daily_loss_limit.

**Consecuencia:** Una jornada rentable puede detener el sistema; dos métodos aplican definiciones distintas del mismo límite.

**Corrección:** Usar max(0,-daily_pnl), una base de sesión explícita y una sola implementación del límite.

**Verificación:** Confirmado con +600 y equity 10.000: activa breaker por pérdida del 6%.

### A08 · P1 · Breaker impide también reducir posiciones

**Ubicación:** `app/services/live_trading/risk_gates.py:174`.

**Evidencia:** validate_order devuelve rechazo inmediato sin distinguir apertura de riesgo y cierre de una posición existente.

**Consecuencia:** Las órdenes correctoras que pasan por este circuito pueden quedar bloqueadas justo al alcanzarse el límite de pérdidas.

**Corrección:** Permitir operaciones reduce-only comprobadas contra posición y órdenes pendientes; impedir que una venta excesiva abra un corto.

**Verificación:** Activar breaker con una posición long: cierre parcial/completo permitido, aumento de posición y cambio a short rechazados.

### A09 · P1 · Idempotencia y recuperación del bridge solo en memoria

**Ubicación:** `app/services/live_trading/trading_bridge_orchestrator.py:203`.

**Evidencia:** La alerta se marca antes de consultar cuenta y ejecutar; no se revierte si falla. El envío directo al broker no pasa client_order_id estable; BrokerConnector genera UUID. OrderManager y bridge guardan su estado en colecciones y no llaman a TradePersistenceManager.

**Consecuencia:** Un fallo previo al envío pierde reintentos; un reinicio tras aceptación puede duplicar la misma intención. La existencia del módulo de persistencia no protege este flujo.

**Corrección:** Persistir intención y transición de estados; derivar clave estable del evento; reconciliar con el broker antes de reintentar.

**Verificación:** Pruebas con caídas antes/después de enviar y antes/después de confirmar; exactamente una orden externa por intención.

### A10 · P1 · Paper trading pierde el efectivo de una venta completa

**Ubicación:** `app/services/live_trading/broker_adapters/paper_adapter.py:334`.

**Evidencia:** Cuando SELL deja cantidad cero, _update_position elimina la posición y hace return antes de acreditar los ingresos en cash_available.

**Consecuencia:** Una compra y venta sin variación de precio produce una pérdida artificial. Las métricas de paper no son fiables en esta ruta.

**Corrección:** Actualizar efectivo antes de salir y probar invariantes contables en cierres parciales/completos.

**Verificación:** Confirmado: saldo inicial 1.000, compra 1 a 100 y venta 1 a 100, saldo final 900 en lugar de 1.000.

### A11 · P1 · Variables de ML incorporan resultados futuros

**Ubicación:** `app/domain/strategies/learning/training_data_preparator.py:771`.

**Evidencia:** _get_recent_trades_before_timestamp y _calculate_recent_win_rate filtran por entrada y estado CLOSED final, sin exigir exit_time anterior al instante evaluado. Sus resultados se pasan al extractor de features.

**Consecuencia:** El modelo puede conocer un beneficio que todavía no existía al generar la señal. Invalida la interpretación fuera de muestra de los entrenamientos que usan estas variables.

**Corrección:** Filtrar por cierre conocido en t y reconstruir el estado histórico; no usar estado final global.

**Verificación:** Confirmado: operación que cierra el 10 de enero aporta PnL y win rate del 100% al 2 de enero.

### A12 · P1 · Fallo de validación temporal degrada a split aleatorio

**Ubicación:** `app/domain/strategies/learning/supervised_learning_engine.py:250`.

**Evidencia:** Ante cualquier excepción de purged CV, se utiliza train_test_split con shuffle predeterminado y estratificación.

**Consecuencia:** Muestras y etiquetas temporalmente solapadas pueden cruzar entrenamiento/validación; el fallo del control metodológico queda convertido en un resultado aparentemente válido.

**Corrección:** Fallar de forma explícita o recurrir a una separación cronológica con purga basada en horizonte de etiquetas; marcar resultados no validados.

**Verificación:** Forzar error del splitter y verificar que no se publica una puntuación validada basada en split aleatorio.

### A13 · P2 · Autenticación válida inutilizable en endpoints con roles

**Ubicación:** `app/presentation/api/security.py:555`.

**Evidencia:** Las API keys válidas producen un usuario sin roles. Los Bearer se rechazan. El middleware solo establece user_id, no user con roles, y emplea otra fuente de claves.

**Consecuencia:** Los endpoints que exigen admin/trader/user no tienen un camino operativo de autorización en el ensamblado actual. La clave válida del decorador puede ser rechazada antes por el middleware.

**Corrección:** Unificar autenticación y principal con permisos explícitos, sin otorgar admin automáticamente a todas las claves.

**Verificación:** Confirmado: API key válida y endpoint admin devuelven 403; probar las rutas reales bajo middleware.

### A14 · P2 · Decoradores no reconocen el parámetro http_request

**Ubicación:** `app/presentation/api/security.py:230`.

**Evidencia:** require_auth busca Request en argumentos posicionales o en kwargs["request"]. FastAPI llama por nombre y varios endpoints de estrategias/optimización usan http_request. rate_limit repite el patrón.

**Consecuencia:** Una petición válida recibe 401 por no encontrar Request; el rate limiting puede no aplicarse en esos endpoints.

**Corrección:** Usar dependencias FastAPI o resolver todos los argumentos tipados Request; añadir pruebas de rutas reales.

**Verificación:** Confirmado con endpoint HTTP mínimo y clave válida: http_request produce 401.

### A15 · P2 · Fallo de autenticación global responde 500

**Ubicación:** `app/presentation/api/middleware.py:237`.

**Evidencia:** AuthMiddleware lanza HTTPException fuera de la capa de manejadores del router.

**Consecuencia:** Credenciales ausentes generan error interno en vez de 401; degrada clientes, observabilidad y alertas.

**Corrección:** Devolver JSONResponse con 401 y headers desde el middleware.

**Verificación:** Confirmado con FastAPI y AuthMiddleware reales en app mínima: HTTP 500.

### A16 · P2 · API declara SUBMITTED aunque la orden sea rechazada

**Ubicación:** `app/presentation/api/live_trading.py:184`.

**Evidencia:** place_order devuelve status SUBMITTED incluso cuando OrderManager devuelve None por riesgo o fallo de envío.

**Consecuencia:** El cliente puede creer que hay una orden en curso sin identificador y sin ejecución.

**Corrección:** Modelar rechazo, fallo y estado incierto; responder estado real y código HTTP adecuado.

**Verificación:** Simular rechazo de RiskGates y exigir respuesta de rechazo, nunca SUBMITTED.

### A17 · P2 · Nueva orden cancela la monitorización de la anterior

**Ubicación:** `app/services/live_trading/trading_bridge_orchestrator.py:428`.

**Evidencia:** _execute_trade conserva una única tarea y la cancela al enviar otra orden.

**Consecuencia:** La orden anterior sigue activa en el broker pero deja de actualizarse por este monitor; el historial puede quedar obsoleto.

**Corrección:** Registrar tareas por order_id o usar flujo central de eventos/reconciliación.

**Verificación:** Dos órdenes pendientes: ambas deben alcanzar su estado terminal y registrar fills.

### A18 · P2 · Validación numérica incompleta

**Ubicación:** `app/services/live_trading/risk_gates.py:188`.

**Evidencia:** RiskGates no exige quantity>0 ni price>0/finito. Los endpoints aceptan float sin cotas; los límites dinámicos comprueban techos para algunos campos pero no mínimos ni finitud.

**Consecuencia:** Valores negativos atraviesan el control central; otros adaptadores pueden rechazarlos después, pero paper permite rutas contablemente inválidas.

**Corrección:** Modelos de entrada con Decimal finito y cotas, y validación defensiva en el dominio.

**Verificación:** Confirmado que cantidad -10 pasa RiskGates; añadir cero, NaN, infinito y límites negativos.

### A19 · P1 · Dependencias operativas ausentes del manifiesto

**Ubicación:** `app/services/live_trading/broker_adapters/alpaca_client.py:114`.

**Evidencia:** pyproject.toml no declara alpaca-trade-api, importado para autenticar Alpaca, ni asyncpg, requerido por la URL PostgreSQL asíncrona generada. Tampoco declara safety, ejecutado por CI.

**Consecuencia:** La instalación documentada no garantiza conexión a Alpaca ni persistencia PostgreSQL async. init_database captura y solo registra el fallo async, permitiendo un arranque degradado.

**Corrección:** Declarar extras operativos verificables y usar un entorno limpio para probar cada configuración; no ocultar fallo de almacenamiento requerido.

**Verificación:** Instalar desde manifiesto y verificar import/conexión de cada adaptador y motor async; no confundir con los paquetes que faltan en el entorno parcial de esta auditoría.

### A20 · P1 · Tablas de live trading sin migración ni creación en startup

**Ubicación:** `app/services/live_trading/trade_persistence.py:228`.

**Evidencia:** La documentación de initialize promete creación de tablas en startup, pero init_database solo crea motores. Las tres migraciones existentes no crean order_records/trade_records/position_records.

**Consecuencia:** Una base creada siguiendo Alembic no dispone de las tablas de esta capa. La persistencia puede fallar al usarse aunque la API haya arrancado.

**Corrección:** Añadir migración explícita de estas tablas y comprobar esquema requerido en readiness.

**Verificación:** Base vacía → alembic upgrade head → guardar y leer orden/fill/posición. No se ejecutó PostgreSQL en esta auditoría.

### A21 · P2 · Workers y scheduler despliegan otra API

**Ubicación:** `Dockerfile:151`.

**Evidencia:** Los targets worker y scheduler ejecutan uvicorn app.main:app; docker-compose.prod los presenta como Celery Worker y Beat.

**Consecuencia:** El despliegue no ofrece el procesado en cola o planificación que anuncia; replica procesos API y estado local.

**Corrección:** Implementar los procesos reales o eliminar esos servicios y sus promesas operativas.

**Verificación:** Smoke test que encola una tarea y verifica ejecución y planificación, además de startup API.

### A22 · P2 · CI no proporciona el gate anunciado

**Ubicación:** `.github/workflows/ci-testing.yml:51`.

**Evidencia:** CI-Testing ignora errores de integración con || true y baja cobertura a 40 frente al 80 declarado. Docker-Build-Check ejecuta print("Build OK"), no importa ni arranca la API. Otros workflows invocan safety sin instalarlo.

**Consecuencia:** Un job verde no demuestra integraciones ni arranque; hay varios workflows con criterios inconsistentes. No se han consultado sus ejecuciones remotas.

**Corrección:** Unificar gates; hacer obligatorias integraciones controladas; arrancar contenedor y verificar readiness; instalar herramientas declaradas.

**Verificación:** Introducir fallos controlados y comprobar que CI falla en cada etapa pertinente.

### A23 · P2 · Servicios operativos expuestos en Compose de producción

**Ubicación:** `docker-compose.prod.yml:236`.

**Evidencia:** Kibana publica 5601 a todas las interfaces mientras Elasticsearch desactiva seguridad. También se publican 8000 y 9090; la API puede alcanzarse sin pasar por nginx.

**Consecuencia:** Si el host es accesible sin firewall adicional, logs y métricas pueden quedar expuestos y se eluden políticas exclusivas del proxy. La exposición externa efectiva no se ha comprobado.

**Corrección:** Restringir puertos a loopback/red privada y autenticar el stack de logs; exponer solo el proxy necesario.

**Verificación:** Comprobar desde una red no autorizada que no se accede a Kibana, métricas ni API directa.

### A24 · P2 · Entornos no reproducibles y configuración ausente de imagen

**Ubicación:** `Dockerfile:91`.

**Evidencia:** Dependencias solo con mínimos >= y sin lock; imágenes con latest. La imagen copia app y scripts pero no el directorio config del repositorio; solo crea un /app/config vacío. Compose prod tampoco lo monta.

**Consecuencia:** Cambian versiones sin cambio de commit y faltan configuraciones YAML para los flujos que las requieren; aumenta la distancia entre desarrollo y despliegue.

**Corrección:** Versionar resolución/hashes, separar dependencias de investigación/servicio, copiar configuración no secreta y exigir configuración operativa.

**Verificación:** Build reproducible y smoke test de un flujo que carga YAML dentro de la imagen.

## Orden de reparación y criterios de salida

1. **Cerrar acceso y unificar identidad:** A01–A02, A13–A15. Pruebas HTTP de cada router con anónimo, clave inválida, clave válida sin permiso y usuario autorizado. Evitar pruebas solo del decorador aislado.
2. **Unificar ejecución y riesgo:** A03–A08 y A18. Un servicio por cuenta, datos actuales, órdenes pendientes reservadas y cierres reduce-only. Todos los tipos de orden deben pasar por el mismo control. Probar concurrencia entre API y alertas, no solo dentro de un OrderManager.
3. **Hacer recuperable la ejecución:** A09, A16–A17, A19–A20. Persistencia de intención, idempotencia estable, reconciliación y respuestas que distingan rechazo/aceptación/estado desconocido. Simular caídas en cada frontera externa.
4. **Recuperar validez de resultados:** A10–A12. Rehacer paper afectado y entrenamiento/validación con datos estrictamente disponibles en cada instante. Mantener tests de conservación de efectivo, equity y PnL, incluidos cierres parciales, comisiones, divisas y cambios corporativos.
5. **Reproducir el despliegue:** A21–A24. Lock de dependencias y smoke tests con la imagen exacta; migraciones desde base vacía, restauración de backup y reinicio con órdenes abiertas. El estado saludable debe exigir servicios esenciales operativos.

No basta con “todos los unit tests pasan”: exigir escenarios end-to-end con broker simulado determinista y luego sandbox del proveedor, incluyendo timeout después de aceptación, duplicados, fills parciales, reinicio y pérdida de conectividad.

## Aspectos positivos y deuda de diseño

Se usan Decimal y modelos tipados en buena parte del dominio. Hay validación explícita de claves en security.py, comparaciones de tiempo constante, soporte de claves de idempotencia en adaptadores y tests recientes de seguridad operacional. El motor contiene una ruta explícita de ejecución T+1. Ruff no reporta errores y el factory rechaza IBKR no implementado en vez de cambiar silenciosamente a paper. Estos mecanismos son una base útil; los fallos se concentran en cómo se ensamblan y en caminos alternativos.

IBKR no está conectado a BrokerConnector: el factory lo rechaza expresamente. Es una limitación funcional declarada en código, no una conexión validada por esta auditoría. La presencia de otros adaptadores IB no cambia ese hecho.

La coexistencia de domain/services, services, engines e infrastructure con responsabilidades parecidas dificulta saber cuál es el circuito autoritativo. Antes de añadir estrategias, documentar un único grafo de dependencias para señal → riesgo → intención persistida → broker → fill → contabilidad → reconciliación. Reducir imports con efectos amplios en __init__.py y separar extras de API, investigación, brokers y desarrollo. Mypy excluye errores de grandes áreas del dominio; recuperar progresivamente el chequeo empezando por contratos de ejecución y riesgo.

El README y pyproject difieren en la declaración de licencia (reserva de derechos frente a MIT); acordar una declaración única con el propietario. No se trata aquí de un dictamen legal.

## Artefactos reproducibles

- `comprobar.py`: 12 comprobaciones que afirman la presencia de los defectos actuales. Tras corregirlos, estas aserciones deben cambiar a la conducta segura; que este script pase no significa que el producto sea correcto.
- `evidencias/reproducciones.json`: entradas, efectos observados y confirmación de cada reproducción.
- `evidencias/ruff.json`, `bandit.json` y `bandit.log`: análisis automático sin ocultar resultados mediante baseline.
- `evidencias/pytest-auth.txt`, `pytest-focused.txt`, `pytest-collection.txt`: resultados originales y limitaciones de colección.
- `evidencias/inventario.json` y `entorno.txt`: tamaño, sintaxis y versiones realmente usadas.
- `hallazgos.json`: backlog estructurado con prioridad, localización, corrección y prueba de aceptación.

Ejecutar las reproducciones con el entorno temporal instalado:

```bash
/private/tmp/robottrading-audit-venv/bin/python /Users/josu/Documents/ChatGPT/RoboTreding/auditoria/comprobar.py
```

Los mocks solo sustituyen interfaces externas; las clases/métodos auditados se compilan directamente desde los archivos del commit. No equivale a un arranque completo del producto. Una nueva auditoría debe fijar otro commit y registrar de nuevo versiones y resultados.
