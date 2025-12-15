# DataEngine - Guía de Instalación y Configuración

## Dependencias Añadidas

Se han añadido las siguientes dependencias a `requirements.txt`:

- `aiohttp>=3.9.0,<4.0.0` - Para requests HTTP asíncronos en fuentes de datos
- `websockets>=12.0,<13.0` - Para WebSocket streaming en tiempo real

**Dependencias ya existentes** (verificadas):
- `redis>=5.0.0,<6.0.0` - Para cache distribuido
- `sqlalchemy>=2.0.0,<3.0.0` - Para persistencia de cache en PostgreSQL
- `fastapi>=0.104.0,<0.110.0` - Para WebSocket endpoints

## Instalación

### Opción 1: Instalar todas las dependencias
```bash
pip install -r requirements.txt
```

### Opción 2: Instalar solo las nuevas dependencias
```bash
pip install aiohttp>=3.9.0 websockets>=12.0
```

## Configuración en .env

Se han añadido las siguientes variables de configuración a `env.example`:

### Cache Configuration
```bash
DATA_ENGINE_CACHE_ENABLED=true
DATA_ENGINE_CACHE_REDIS_ENABLED=true
DATA_ENGINE_CACHE_POSTGRES_ENABLED=true
DATA_ENGINE_CACHE_DEFAULT_TTL=3600  # 1 hour in seconds
DATA_ENGINE_CACHE_REDIS_URL="${REDIS_URL}"  # Usa REDIS_URL si no está especificado
DATA_ENGINE_CACHE_POSTGRES_URL="${DATABASE_URL}"  # Usa DATABASE_URL si no está especificado
```

### Streaming Configuration
```bash
DATA_ENGINE_STREAMING_ENABLED=false
DATA_ENGINE_STREAMING_HEARTBEAT_INTERVAL=30  # seconds
DATA_ENGINE_STREAMING_MAX_CONNECTIONS=100
```

## Configuración en config/centralized.env

También se han añadido las mismas variables a `config/centralized.env` para compatibilidad con el sistema de configuración centralizada.

## Uso

### Habilitar Cache Distribuido

1. **Con Redis y PostgreSQL**:
```python
from app.engines.data_engine import DataEngine

config = {
    'cache_config': {
        'redis_url': 'redis://localhost:6379/0',
        'postgres_url': 'postgresql://user:pass@localhost:5432/db',
        'default_ttl': 3600
    }
}

engine = DataEngine(config)
```

2. **Solo Redis**:
```python
config = {
    'cache_config': {
        'redis_url': 'redis://localhost:6379/0',
        'use_postgres': False,
        'default_ttl': 3600
    }
}
```

3. **Solo PostgreSQL**:
```python
config = {
    'cache_config': {
        'postgres_url': 'postgresql://user:pass@localhost:5432/db',
        'use_redis': False,
        'default_ttl': 3600
    }
}
```

4. **Cache en memoria** (fallback automático):
```python
config = {
    'cache_config': {
        'use_redis': False,
        'use_postgres': False,
        'default_ttl': 3600
    }
}
```

### Habilitar Streaming WebSocket

1. **Configurar DataEngine**:
```python
config = {
    'streaming_config': {
        'heartbeat_interval': 30,
        'max_connections': 100
    },
    'streaming_enabled': True
}

engine = DataEngine(config)
await engine.initialize()  # Inicia streaming manager
```

2. **Integrar en FastAPI**:
```python
from fastapi import FastAPI
from app.engines.data_engine import DataEngine

app = FastAPI()
engine = DataEngine(config)
await engine.initialize()

# Incluir router de WebSocket
app.include_router(engine.streaming_manager.router)
```

3. **Client WebSocket**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/data/client123');

ws.onopen = () => {
    // Suscribirse a símbolos
    ws.send(JSON.stringify({
        type: 'subscribe',
        symbols: ['AAPL', 'GOOGL']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'quote') {
        console.log('Quote recibido:', data);
    }
};
```

## Verificación

Para verificar que todo está instalado correctamente:

```bash
python -c "from app.engines.data_engine import DataEngine; print('✅ DataEngine OK')"
python -c "from app.engines.data_engine.cache import DistributedCache; print('✅ Cache OK')"
python -c "from app.engines.data_engine.streaming import WebSocketStreamingManager; print('✅ Streaming OK')"
```

## Notas

- Si Redis no está disponible, el sistema usa cache en memoria automáticamente
- Si PostgreSQL no está disponible, el sistema usa solo Redis o memoria
- WebSocket streaming es opcional y puede estar deshabilitado por defecto
- Todas las dependencias son opcionales y el sistema funciona sin ellas (con funcionalidad reducida)

