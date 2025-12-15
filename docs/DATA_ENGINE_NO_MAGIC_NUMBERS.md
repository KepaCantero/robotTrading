# Eliminación de Números Mágicos - DataEngine

## ✅ Cambios Realizados

### 1. Archivo de Configuración YAML Creado
**Archivo**: `config/data_engine.yaml`

Contiene TODOS los parámetros configurables:
- Configuración de cache (TTL, Redis, PostgreSQL)
- Configuración de streaming (heartbeat, conexiones máximas)
- Configuración de fuentes de datos (límites, valores por defecto)
- Configuración de IBKR
- Códigos de respuesta API
- Valores por defecto de sentimiento
- Configuración de normalización y limpieza

### 2. Config Loader Creado
**Archivo**: `app/engines/data_engine/config_loader.py`

- Carga configuración desde YAML
- Proporciona métodos específicos para cada componente
- Valida que los parámetros requeridos estén presentes
- Fallback a valores por defecto solo si no existe archivo YAML

### 3. Código Refactorizado

#### `app/engines/data_engine/data_engine.py`
- ✅ Usa `DataEngineConfigLoader` para cargar configuración
- ✅ Eliminados valores hardcodeados (3600, etc.)
- ✅ `get_sentiment()` ahora usa `max_results` desde YAML si no se especifica
- ✅ Valores por defecto de sentimiento desde YAML

#### `app/engines/data_engine/cache/distributed_cache.py`
- ✅ **RAISE ValueError** si `default_ttl`, `use_redis`, `use_postgres` no están en config
- ✅ NO acepta valores por defecto hardcodeados
- ✅ Configuración de esquema PostgreSQL desde YAML

#### `app/engines/data_engine/streaming/websocket_streaming.py`
- ✅ **RAISE ValueError** si `heartbeat_interval`, `max_connections` no están en config
- ✅ NO acepta valores por defecto hardcodeados
- ✅ Código HTTP y mensajes desde YAML

## 🎯 Principios Aplicados

1. **CERO números mágicos**: Todos los valores deben venir de YAML
2. **Validación estricta**: Si falta un parámetro requerido, se lanza ValueError
3. **Configuración centralizada**: Un solo archivo YAML para todo DataEngine
4. **Fallback seguro**: Solo si no existe archivo YAML, se usan valores por defecto mínimos

## 📋 Parámetros Movidos a YAML

### Cache
- `default_ttl` (era 3600 hardcodeado)
- `redis_url` (era 'redis://localhost:6379/0' hardcodeado)
- `use_redis` (era True hardcodeado)
- `use_postgres` (era True hardcodeado)
- Esquema PostgreSQL (nombres de tabla, columnas)

### Streaming
- `heartbeat_interval` (era 30 hardcodeado)
- `max_connections` (era 100 hardcodeado)
- `websocket_path` (era '/ws/data/{client_id}' hardcodeado)
- `max_connection_code` (era 1008 hardcodeado)
- `connection_reason_max_reached` (era 'Maximum connections reached' hardcodeado)

### Sentimiento
- `default_max_results` (era 100 hardcodeado)
- `default_score` (era 0.0 hardcodeado)
- `default_counts` (eran 0 hardcodeados)
- Valores de sentimiento por fuente (positive, negative, neutral)

### Fuentes
- Límites de API por fuente
- Tamaños de muestra
- Valores por defecto de Greeks de opciones

## ✅ Verificación

Para verificar que no hay números mágicos:

```bash
# Buscar números hardcodeados sospechosos
grep -r "config.get.*3600\|config.get.*30\|config.get.*100" app/engines/data_engine/
# Debe retornar vacío o solo con valores desde YAML

# Verificar que el config loader funciona
python -c "from app.engines.data_engine.config_loader import DataEngineConfigLoader; loader = DataEngineConfigLoader(); print('OK')"
```

## 🚀 Uso

```python
from app.engines.data_engine import DataEngine

# Configuración automática desde YAML
engine = DataEngine()  # Carga config/data_engine.yaml automáticamente

# O especificar ruta personalizada
engine = DataEngine({'config_path': 'config/mi_data_engine.yaml'})

# Override específico si necesario
engine = DataEngine({
    'cache_config': {
        'default_ttl': 7200  # Override solo este valor
    }
})
```

## ⚠️ Importante

**NO se pueden usar valores por defecto hardcodeados**. Si un parámetro no está en el YAML y es requerido, el sistema lanzará `ValueError` con un mensaje claro indicando qué falta.

Esto garantiza que:
1. Todos los parámetros están documentados en YAML
2. No hay valores "ocultos" en el código
3. Es fácil cambiar configuración sin tocar código
4. El proyecto es profesional y mantenible

