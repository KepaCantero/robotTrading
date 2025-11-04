# System Integrity Validation System

Sistema completo de validación e integridad que verifica que DataEngine y ContextEngine funcionan correctamente, que los datos fluyen entre ellos, que los logs se escriben correctamente, y que el dashboard state JSON se genera correctamente.

## 📋 Uso

### Ejecución básica

```bash
python app/system/verify_system_integrity.py
```

O usando el script:

```bash
python scripts/verify_system_integrity.py
```

## ✅ Validaciones Ejecutadas

1. **DataEngine**: Inicialización, métodos disponibles, procesamiento de datos
2. **ContextEngine**: Inicialización, detección de régimen, volatilidad, correlaciones
3. **Integration**: Flujo de datos entre engines
4. **Logs**: Directorio, escritura, archivos presentes
5. **Dashboard State**: Directorio, escritura JSON, validación JSON

## 📊 Formato Dashboard State

```json
{
  "data_engine_status": "ok",
  "context_engine_status": "ok",
  "market_regime": "bull",
  "volatility": 0.23,
  "volatility_regime": "normal",
  "correlation_ok": true,
  "timestamp": "2025-11-04T07:32:22Z"
}
```

## 🎯 Estados

- ✅ OK: Todos los checks pasaron
- ⚠️ WARNING: Advertencias no críticas
- ❌ ERROR: Checks críticos fallaron

