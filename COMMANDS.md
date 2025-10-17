# 🚀 AlgoTrading MVP - Comandos Útiles

Este documento contiene todos los comandos útiles para el desarrollo, testing, y mantenimiento del proyecto AlgoTrading MVP.

## 📋 Índice

- [🔧 Configuración del Entorno](#-configuración-del-entorno)
- [🧪 Testing](#-testing)
- [🚀 Ejecución de la Aplicación](#-ejecución-de-la-aplicación)
- [📦 Gestión de Dependencias](#-gestión-de-dependencias)
- [🔍 Análisis y Linting](#-análisis-y-linting)
- [📊 Cobertura de Código](#-cobertura-de-código)
- [🗂️ Gestión de Archivos](#️-gestión-de-archivos)
- [🔧 Desarrollo](#-desarrollo)
- [📚 Documentación](#-documentación)
- [🔄 Git y Control de Versiones](#-git-y-control-de-versiones)
- [🐳 Docker (Futuro)](#-docker-futuro)
- [🚨 Troubleshooting](#-troubleshooting)

---

## 🔧 Configuración del Entorno

### Activar el Entorno Virtual

```bash
# Activar el entorno virtual
source .venv/bin/activate

# Verificar que está activado (debería mostrar la ruta del venv)
which python
```

### Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp env.example .env

# Editar las variables de entorno
nano .env
# o
vim .env
```

### Verificar la Configuración

```bash
# Verificar que Python puede importar la configuración
python -c "from app.core.config import Settings; print('✅ Configuración OK')"

# Verificar variables de entorno
python -c "import os; print('DEBUG:', os.environ.get('DEBUG', 'No definido'))"
```

---

## 🧪 Testing

### Ejecutar Todos los Tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar todos los tests con output verbose
pytest -v

# Ejecutar todos los tests con output detallado
pytest -v -s
```

### Tests Específicos

```bash
# Tests de la aplicación principal
pytest tests/test_main.py -v

# Tests de configuración
pytest tests/test_config.py -v

# Test específico por nombre
pytest tests/test_main.py::TestHealthEndpoints::test_health_endpoint_returns_200 -v

# Tests que contengan una palabra clave
pytest -k "health" -v
```

### Tests con Cobertura

```bash
# Ejecutar tests con cobertura
pytest --cov=app --cov-report=term-missing

# Cobertura con reporte HTML
pytest --cov=app --cov-report=html

# Cobertura con reporte XML (para CI/CD)
pytest --cov=app --cov-report=xml
```

### Tests en Modo Debug

```bash
# Ejecutar tests con pdb en caso de fallo
pytest --pdb

# Ejecutar tests con pdb en el primer fallo
pytest -x --pdb

# Ejecutar tests con output de logging
pytest -s --log-cli-level=DEBUG
```

### Tests de Integración

```bash
# Tests con cliente HTTP real
pytest tests/test_main.py::TestHealthEndpoints -v

# Tests con base de datos (cuando esté implementada)
pytest tests/test_database.py -v
```

---

## 🚀 Ejecución de la Aplicación

### Desarrollo Local

```bash
# Ejecutar la aplicación en modo desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar con configuración específica
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

# Ejecutar en background
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### Producción

```bash
# Ejecutar con Gunicorn (cuando esté configurado)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Ejecutar con configuración de producción
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --access-logfile - --error-logfile -
```

### Verificar Estado de la Aplicación

```bash
# Health check básico
curl http://localhost:8000/health

# Health check detallado
curl http://localhost:8000/health/detailed

# Información de la aplicación
curl http://localhost:8000/

# Documentación OpenAPI
curl http://localhost:8000/docs
```

---

## 📦 Gestión de Dependencias

### Instalar Dependencias

```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# Instalar dependencia específica
pip install fastapi

# Instalar dependencia de desarrollo
pip install pytest-cov
```

### Actualizar Dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Actualizar dependencia específica
pip install --upgrade fastapi

# Actualizar todas las dependencias
pip list --outdated
```

### Generar requirements.txt

```bash
# Generar requirements.txt actualizado
pip freeze > requirements.txt

# Generar requirements.txt solo con dependencias principales
pip freeze | grep -E "(fastapi|uvicorn|pydantic)" > requirements.txt
```

### Gestión de Entornos

```bash
# Crear nuevo entorno virtual
python -m venv .venv

# Eliminar entorno virtual
rm -rf .venv

# Recrear entorno virtual
rm -rf .venv && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

---

## 🔍 Análisis y Linting

### Linting con flake8

```bash
# Instalar flake8
pip install flake8

# Ejecutar linting
flake8 app/ tests/

# Linting con configuración específica
flake8 app/ tests/ --max-line-length=100 --ignore=E203,W503
```

### Formateo con black

```bash
# Instalar black
pip install black

# Formatear código
black app/ tests/

# Formatear con configuración específica
black app/ tests/ --line-length=100
```

### Análisis de Tipos

```bash
# Instalar mypy
pip install mypy

# Análisis de tipos
mypy app/

# Análisis con configuración
mypy app/ --ignore-missing-imports
```

### Análisis de Seguridad

```bash
# Instalar bandit
pip install bandit

# Análisis de seguridad
bandit -r app/

# Análisis con configuración
bandit -r app/ -f json -o security-report.json
```

---

## 📊 Cobertura de Código

### Generar Reportes de Cobertura

```bash
# Cobertura básica
pytest --cov=app

# Cobertura con reporte HTML
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Cobertura con umbral mínimo
pytest --cov=app --cov-fail-under=80
```

### Análisis de Cobertura

```bash
# Ver archivos con baja cobertura
pytest --cov=app --cov-report=term-missing | grep -E "TOTAL|missing"

# Cobertura por módulo
pytest --cov=app.core --cov-report=term-missing
```

---

## 🗂️ Gestión de Archivos

### Estructura del Proyecto

```bash
# Ver estructura del proyecto
tree -I '__pycache__|*.pyc|.git|.venv|htmlcov|.pytest_cache'

# Ver solo archivos Python
find . -name "*.py" -not -path "./.venv/*" | head -20

# Contar líneas de código
find . -name "*.py" -not -path "./.venv/*" | xargs wc -l
```

### Limpieza de Archivos

```bash
# Eliminar archivos __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +

# Eliminar archivos .pyc
find . -name "*.pyc" -delete

# Limpieza completa
find . -type d -name "__pycache__" -exec rm -rf {} + && find . -name "*.pyc" -delete
```

### Búsqueda en Código

```bash
# Buscar texto en archivos Python
grep -r "Settings" app/ --include="*.py"

# Buscar con contexto
grep -r -n -A 3 -B 3 "FastAPI" app/ --include="*.py"

# Buscar patrones específicos
grep -r "def test_" tests/ --include="*.py"
```

---

## 🔧 Desarrollo

### Debugging

```bash
# Ejecutar con debugger
python -m pdb -c continue app/main.py

# Ejecutar con logging detallado
PYTHONPATH=. python -c "import logging; logging.basicConfig(level=logging.DEBUG); from app.main import app"

# Verificar imports
python -c "import app.core.config; print('✅ Imports OK')"
```

### Desarrollo Interactivo

```bash
# Abrir Python con el proyecto cargado
PYTHONPATH=. python -i -c "from app.core.config import Settings; from app.main import app"

# Ejecutar código específico
python -c "
from app.core.config import Settings
settings = Settings()
print(f'App: {settings.app_name}')
print(f'Debug: {settings.debug}')
"
```

### Validación de Configuración

```bash
# Validar configuración
python -c "
import os
os.environ['DEBUG'] = 'true'
from app.core.config import Settings
settings = Settings()
print('✅ Configuración válida')
"

# Probar endpoints
python -c "
import requests
try:
    response = requests.get('http://localhost:8000/health')
    print(f'✅ API OK: {response.status_code}')
except:
    print('❌ API no disponible')
"
```

---

## 📚 Documentación

### Generar Documentación

```bash
# Instalar sphinx
pip install sphinx sphinx-rtd-theme

# Generar documentación
sphinx-build -b html docs/ docs/_build/

# Ver documentación
open docs/_build/index.html
```

### Documentación de API

```bash
# Acceder a documentación automática
open http://localhost:8000/docs

# Acceder a ReDoc
open http://localhost:8000/redoc

# Obtener esquema OpenAPI
curl http://localhost:8000/openapi.json > openapi.json
```

---

## 🔄 Git y Control de Versiones

### Comandos Básicos

```bash
# Ver estado del repositorio
git status

# Ver diferencias
git diff

# Ver historial
git log --oneline -10

# Ver ramas
git branch -a
```

### Gestión de Ramas

```bash
# Crear nueva rama
git checkout -b feature/nueva-funcionalidad

# Cambiar de rama
git checkout main

# Fusionar rama
git merge feature/nueva-funcionalidad

# Eliminar rama
git branch -d feature/nueva-funcionalidad
```

### Commits y Push

```bash
# Agregar cambios
git add .

# Commit con mensaje
git commit -m "feat: agregar nueva funcionalidad"

# Push a repositorio remoto
git push origin main

# Push de nueva rama
git push -u origin feature/nueva-funcionalidad
```

### Limpieza de Git

```bash
# Limpiar archivos no trackeados
git clean -fd

# Reset suave
git reset --soft HEAD~1

# Reset duro (¡CUIDADO!)
git reset --hard HEAD~1
```

---

## 🐳 Docker (Futuro)

### Comandos Docker (cuando esté implementado)

```bash
# Construir imagen
docker build -t algotrading-mvp .

# Ejecutar contenedor
docker run -p 8000:8000 algotrading-mvp

# Ejecutar con variables de entorno
docker run -p 8000:8000 -e DEBUG=true algotrading-mvp

# Ver logs
docker logs <container_id>

# Ejecutar en background
docker run -d -p 8000:8000 --name algotrading algotrading-mvp
```

---

## 🚨 Troubleshooting

### Problemas Comunes

#### Error de Importación

```bash
# Verificar PYTHONPATH
echo $PYTHONPATH

# Agregar al PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verificar imports
python -c "import sys; print(sys.path)"
```

#### Error de Configuración

```bash
# Verificar variables de entorno
env | grep -E "(DEBUG|SECRET_KEY|DATABASE_URL)"

# Probar configuración
python -c "
import os
os.environ['DEBUG'] = 'true'
from app.core.config import Settings
print('Config OK')
"
```

#### Error de Puerto

```bash
# Verificar qué está usando el puerto 8000
lsof -i :8000

# Matar proceso en puerto 8000
kill -9 $(lsof -t -i:8000)

# Usar puerto diferente
uvicorn app.main:app --reload --port 8001
```

#### Error de Dependencias

```bash
# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt

# Limpiar cache de pip
pip cache purge

# Recrear entorno virtual
rm -rf .venv && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Logs y Debugging

```bash
# Ver logs de la aplicación
tail -f app.log

# Ejecutar con logging detallado
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from app.main import app
"

# Verificar configuración de logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info('Test log message')
"
```

---

## 📝 Notas Adicionales

### Variables de Entorno Importantes

- `DEBUG`: Modo debug (true/false)
- `SECRET_KEY`: Clave secreta para JWT
- `DATABASE_URL`: URL de conexión a base de datos
- `REDIS_URL`: URL de conexión a Redis
- `LOG_LEVEL`: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### URLs Útiles (cuando la app esté ejecutándose)

- `http://localhost:8000/` - Información de la aplicación
- `http://localhost:8000/health` - Health check básico
- `http://localhost:8000/health/detailed` - Health check detallado
- `http://localhost:8000/docs` - Documentación Swagger UI
- `http://localhost:8000/redoc` - Documentación ReDoc
- `http://localhost:8000/openapi.json` - Esquema OpenAPI

### Comandos de Desarrollo Rápido

```bash
# Ejecutar tests y aplicación en una línea
pytest && uvicorn app.main:app --reload

# Verificar todo el proyecto
pytest --cov=app --cov-report=term-missing && flake8 app/ tests/

# Desarrollo completo
source .venv/bin/activate && pytest -v && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎯 Comandos Más Utilizados

### Desarrollo Diario

```bash
# 1. Activar entorno
source .venv/bin/activate

# 2. Ejecutar tests
pytest -v

# 3. Ejecutar aplicación
uvicorn app.main:app --reload

# 4. Verificar health
curl http://localhost:8000/health
```

### Antes de Commit

```bash
# 1. Ejecutar tests
pytest --cov=app

# 2. Verificar linting
flake8 app/ tests/

# 3. Verificar formato
black --check app/ tests/

# 4. Commit
git add . && git commit -m "feat: descripción del cambio"
```

---

**💡 Tip**: Guarda este archivo como referencia y agrega nuevos comandos según vayas descubriendo necesidades específicas del proyecto.

**🚀 Happy Coding!**
