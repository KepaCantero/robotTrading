# 🚀 AlgoTrading MVP - Guía Completa para Principiantes

## 📋 ¿Qué es este proyecto?

**AlgoTrading MVP** es un sistema de **trading algorítmico** (trading automático) que permite ejecutar estrategias de inversión de forma automática usando algoritmos y datos de mercado en tiempo real.

### 🎯 ¿Qué hace un sistema de trading algorítmico?

- **Analiza datos de mercado** (precios, volúmenes, noticias)
- **Ejecuta estrategias de inversión** automáticamente
- **Compra y vende acciones** sin intervención humana
- **Monitorea el rendimiento** de las inversiones
- **Gestiona riesgos** y límites de pérdidas

---

## 🏗️ Tarea 01: Estructura Base FastAPI

### ¿Qué hemos construido?

Hemos creado la **base sólida** de nuestro sistema de trading usando **FastAPI**. Es como construir los cimientos de una casa antes de poner las paredes.

### 📁 Estructura del Proyecto

```
AlgoTrading/
├── app/                    # Código principal de la aplicación
│   ├── __init__.py        # Archivo que convierte la carpeta en un paquete Python
│   └── main.py            # Archivo principal con toda la lógica de FastAPI
├── tests/                 # Pruebas para verificar que todo funciona
│   ├── __init__.py        # Archivo que convierte la carpeta en un paquete Python
│   └── test_main.py       # Pruebas para el archivo main.py
├── .memory/               # Base de datos de conocimiento del proyecto
├── .venv/                 # Entorno virtual de Python (dependencias aisladas)
├── requirements.txt       # Lista de todas las librerías que necesitamos
├── pytest.ini           # Configuración para las pruebas
└── README.md             # Este archivo que estás leyendo
```

---

## 🛠️ Tecnologías Utilizadas

### 1. **Python** 🐍

**¿Qué es?** Python es un lenguaje de programación muy popular y fácil de aprender.

**¿Por qué lo elegimos?**

- ✅ **Fácil de aprender** - Sintaxis simple y clara
- ✅ **Muchas librerías** - Para análisis de datos, matemáticas, etc.
- ✅ **Comunidad grande** - Mucha ayuda disponible
- ✅ **Perfecto para trading** - Librerías como pandas, numpy, etc.

### 2. **FastAPI** ⚡

**¿Qué es?** FastAPI es un framework (herramienta) para crear APIs web muy rápidas.

**¿Qué es una API?**
Una API es como un "menú" que permite a diferentes programas comunicarse entre sí. Por ejemplo:

- Una aplicación móvil puede pedir datos a nuestro servidor
- Un dashboard web puede mostrar información en tiempo real
- Otros sistemas pueden ejecutar operaciones de trading

**¿Por qué FastAPI?**

- ✅ **Súper rápido** - Crítico para trading (cada milisegundo cuenta)
- ✅ **Documentación automática** - Crea documentación sin esfuerzo
- ✅ **Fácil de usar** - Código simple y claro
- ✅ **Validación automática** - Verifica que los datos sean correctos
- ✅ **Soporte para async** - Puede manejar muchas operaciones simultáneamente

### 3. **Uvicorn** 🚀

**¿Qué es?** Uvicorn es el servidor que ejecuta nuestra aplicación FastAPI.

**¿Por qué lo necesitamos?**

- ✅ **Ejecuta FastAPI** - Sin servidor, no hay aplicación
- ✅ **Muy rápido** - Optimizado para Python
- ✅ **Soporte para async** - Maneja muchas conexiones
- ✅ **Hot reload** - Reinicia automáticamente cuando cambias código

### 4. **Pytest** 🧪

**¿Qué es?** Pytest es una herramienta para hacer pruebas automáticas de nuestro código.

**¿Por qué es importante?**

- ✅ **Verifica que todo funciona** - Antes de usar en producción
- ✅ **Detecta errores** - Antes de que causen problemas
- ✅ **Confianza** - Sabemos que el código es confiable
- ✅ **Documentación viva** - Las pruebas explican cómo usar el código

### 5. **CORS** 🌐

**¿Qué es?** CORS (Cross-Origin Resource Sharing) es un mecanismo de seguridad del navegador.

**¿Por qué lo necesitamos?**

- ✅ **Permite comunicación** - Entre frontend y backend
- ✅ **Seguridad controlada** - Define quién puede acceder
- ✅ **Necesario para web** - Sin CORS, las páginas web no pueden usar nuestra API

---

## 🔧 ¿Qué hace cada archivo?

### `app/main.py` - El Corazón de la Aplicación

```python
# 1. Importamos las librerías necesarias
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 2. Creamos la aplicación FastAPI
app = FastAPI(
    title="AlgoTrading MVP",
    description="Algorithmic Trading System MVP",
    version="1.0.0"
)

# 3. Configuramos CORS para permitir comunicación web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite acceso desde cualquier dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Creamos endpoints (puntos de acceso)
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**¿Qué hace cada parte?**

1. **Imports**: Traemos las herramientas que necesitamos
2. **FastAPI app**: Creamos nuestra aplicación web
3. **CORS**: Configuramos la seguridad para permitir acceso web
4. **Endpoints**: Creamos "puertas" por donde otros programas pueden acceder

### Endpoints Disponibles

| Endpoint           | Método | Descripción                       | Ejemplo de Uso                 |
| ------------------ | ------ | --------------------------------- | ------------------------------ |
| `/`                | GET    | Información de la aplicación      | Ver detalles del sistema       |
| `/health`          | GET    | Verificar que el sistema funciona | Monitoreo de salud             |
| `/health/detailed` | GET    | Información detallada del sistema | Diagnóstico completo           |
| `/docs`            | GET    | Documentación interactiva         | Explorar la API                |
| `/redoc`           | GET    | Documentación alternativa         | Leer documentación             |
| `/openapi.json`    | GET    | Esquema técnico de la API         | Integración con otros sistemas |

### `tests/test_main.py` - Las Pruebas

```python
# Importamos las herramientas de testing
import pytest
from fastapi.testclient import TestClient
from app.main import app

# Creamos un cliente de prueba
client = TestClient(app)

# Definimos las pruebas
def test_health_endpoint_returns_200():
    """Verifica que el endpoint /health devuelve código 200"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**¿Qué hace cada prueba?**

- ✅ **Verifica que los endpoints funcionan** - Devuelven las respuestas correctas
- ✅ **Comprueba códigos de estado** - 200 = éxito, 404 = no encontrado, etc.
- ✅ **Valida respuestas JSON** - Los datos son correctos
- ✅ **Prueba manejo de errores** - El sistema responde bien a errores

---

## 🚀 Cómo Ejecutar el Proyecto

### 1. **Instalar Dependencias**

```bash
# Crear entorno virtual (aislar las dependencias)
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Mac/Linux:
source .venv/bin/activate

# Instalar todas las librerías necesarias
pip install -r requirements.txt
```

### 2. **Ejecutar la Aplicación**

```bash
# Ejecutar el servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**¿Qué hace este comando?**

- `uvicorn`: El servidor que ejecuta FastAPI
- `app.main:app`: Busca la variable `app` en el archivo `app/main.py`
- `--reload`: Reinicia automáticamente cuando cambias código
- `--host 0.0.0.0`: Permite acceso desde cualquier IP
- `--port 8000`: Ejecuta en el puerto 8000

### 3. **Acceder a la Aplicación**

- **API**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. **Ejecutar las Pruebas**

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar con más detalles
pytest -v

# Ejecutar con cobertura de código
pytest --cov=app
```

---

## 🎯 ¿Por Qué Estas Tecnologías para Trading?

### **Velocidad es Crítica** ⚡

En trading, **cada milisegundo cuenta**. Si tu sistema es lento:

- ❌ Pierdes oportunidades de ganancia
- ❌ Otros traders te ganan
- ❌ Puedes perder dinero

**FastAPI + Uvicorn** son de los más rápidos disponibles.

### **Confiabilidad es Esencial** 🛡️

Si tu sistema falla:

- ❌ Puedes perder mucho dinero
- ❌ No puedes ejecutar estrategias
- ❌ Pierdes la confianza de los inversores

**Pytest** nos asegura que todo funciona correctamente.

### **Escalabilidad es Necesaria** 📈

Conforme crece tu negocio:

- ✅ Más usuarios accediendo
- ✅ Más datos procesando
- ✅ Más estrategias ejecutando

**FastAPI + Python** escalan fácilmente.

### **Integración es Clave** 🔗

Un sistema de trading necesita:

- ✅ Conectar con brokers (intermediarios)
- ✅ Recibir datos de mercado
- ✅ Enviar órdenes de compra/venta
- ✅ Mostrar dashboards a usuarios

**APIs REST** permiten todas estas conexiones.

---

## 🔮 ¿Qué Viene Después?

### **Próximas Tareas (T002, T003, etc.)**

1. **Base de Datos** - Guardar datos de trading
2. **Autenticación** - Login y seguridad
3. **Estrategias de Trading** - Algoritmos de inversión
4. **Conexión con Brokers** - Ejecutar órdenes reales
5. **Dashboard Web** - Interfaz para usuarios
6. **Análisis de Datos** - Gráficos y métricas
7. **Gestión de Riesgos** - Límites y controles

### **Cómo se Conecta Todo**

```
Usuario → Dashboard Web → API FastAPI → Base de Datos
                ↓
         Estrategias de Trading → Broker → Mercado
```

---

## 🎓 Conceptos Importantes para Entender

### **API REST**

- **GET**: Obtener información (como leer un libro)
- **POST**: Crear algo nuevo (como escribir una carta)
- **PUT**: Actualizar algo existente (como corregir un texto)
- **DELETE**: Eliminar algo (como tirar papel a la basura)

### **JSON**

Formato de datos que usan las APIs:

```json
{
  "status": "ok",
  "data": {
    "price": 100.5,
    "symbol": "AAPL"
  }
}
```

### **Async/Await**

Permite que el servidor maneje muchas operaciones simultáneamente:

```python
async def get_market_data():
    # Puede hacer múltiples operaciones al mismo tiempo
    data1 = await get_stock_price("AAPL")
    data2 = await get_stock_price("GOOGL")
    return [data1, data2]
```

### **Middleware**

Código que se ejecuta antes/después de cada request:

```python
# CORS es un middleware que agrega headers de seguridad
# Se ejecuta automáticamente en cada request
```

---

## 🚨 Errores Comunes y Soluciones

### **Error: "ModuleNotFoundError"**

```bash
# Problema: No encuentra las librerías
# Solución: Activar el entorno virtual
source .venv/bin/activate
pip install -r requirements.txt
```

### **Error: "Port already in use"**

```bash
# Problema: Puerto 8000 ya está ocupado
# Solución: Usar otro puerto
uvicorn app.main:app --reload --port 8001
```

### **Error: "CORS policy blocked"**

```bash
# Problema: Navegador bloquea requests
# Solución: Verificar configuración CORS en main.py
```

---

## 📚 Recursos para Aprender Más

### **Python**

- [Python.org Tutorial](https://docs.python.org/3/tutorial/)
- [Real Python](https://realpython.com/)

### **FastAPI**

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)

### **Trading**

- [Investopedia - Algorithmic Trading](https://www.investopedia.com/terms/a/algorithmictrading.asp)
- [QuantStart](https://www.quantstart.com/)

### **Testing**

- [Pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development](https://testdriven.io/)

---

## 🎉 ¡Felicidades!

Has completado la **Tarea 01** y ahora tienes:

- ✅ **Una API funcional** con FastAPI
- ✅ **Endpoints de salud** para monitoreo
- ✅ **Configuración CORS** para acceso web
- ✅ **Pruebas automáticas** que verifican todo
- ✅ **Documentación automática** de la API
- ✅ **Base sólida** para construir el sistema completo

**¡Estás listo para la siguiente tarea!** 🚀

---

## 🤝 ¿Necesitas Ayuda?

Si tienes dudas o problemas:

1. **Revisa este README** - La respuesta puede estar aquí
2. **Ejecuta las pruebas** - `pytest` te dirá si algo está roto
3. **Revisa los logs** - El servidor te dará pistas sobre errores
4. **Consulta la documentación** - `/docs` en tu navegador

**¡Buen trabajo y sigue adelante!** 💪
