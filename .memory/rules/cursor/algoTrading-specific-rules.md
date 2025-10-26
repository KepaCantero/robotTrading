# AlgoTrading Specific Cursor Rules

## Project-Specific Development Rules

### 1. Language & Environment Rules

#### Python Version Enforcement

```yaml
python_version: "3.11+"
compatibility: "3.10+"
enforcement: "strict"
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Any code using Python < 3.10 features
- ✅ **ALERT**: Missing type hints on new functions
- ✅ **REQUIRE**: `from __future__ import annotations` in all files
- ✅ **VALIDATE**: All imports use absolute paths from project root

#### Project Structure Enforcement

```
/project_root
├── /app                 # Application code
│   ├── /api            # FastAPI endpoints
│   ├── /models         # SQLAlchemy models
│   ├── /schemas        # Pydantic schemas
│   ├── /services       # Business logic
│   ├── /core           # Configuration, security
│   └── /utils          # Helper functions
├── /tests              # Test files
│   ├── /unit           # Unit tests
│   └── /integration    # Integration tests
├── /docs               # Documentation
├── /scripts            # Deployment scripts
├── /docker             # Docker configurations
├── requirements.txt    # Production dependencies
├── requirements-dev.txt # Development dependencies
└── docker-compose.yml  # Local development
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Files outside defined structure
- ✅ **ALERT**: Missing `__init__.py` in Python packages
- ✅ **REQUIRE**: Proper module imports (no relative imports beyond one level)
- ✅ **VALIDATE**: All new modules follow naming conventions

### 2. Code Quality & Formatting Rules

#### Formatting Standards

```yaml
formatter: "black"
line_length: 88
linter: "flake8"
type_checker: "mypy"
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Code that doesn't pass `black --check`
- ✅ **BLOCK**: Code that doesn't pass `flake8` with project config
- ✅ **ALERT**: Functions without type hints
- ✅ **REQUIRE**: Docstrings for all public methods and classes
- ✅ **VALIDATE**: Import order follows isort configuration

#### Naming Conventions

```python
# Files and functions: snake_case
user_service.py
def get_user_by_id():

# Classes: PascalCase
class UserService:
class ProductRepository:

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_PAGE_SIZE = 50

# Private methods: _leading_underscore
def _validate_password():
def _hash_sensitive_data():
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Incorrect naming conventions
- ✅ **ALERT**: Variables with unclear names
- ✅ **REQUIRE**: Descriptive variable and function names
- ✅ **VALIDATE**: Consistent naming across similar functions

### 3. Architecture & Design Rules

#### Layered Architecture Enforcement

```python
# ✅ CORRECT: Controller -> Service -> Repository
@router.post("/users")
async def create_user(user_data: UserCreate, service: UserService = Depends()):
    return await service.create_user(user_data)

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        return await self.repo.create(user_data)

# ❌ BLOCKED: Direct database access from controller
@router.post("/users")
async def create_user(user_data: UserCreate, db: Session = Depends()):
    user = User(**user_data.dict())  # BLOCKED: Direct DB access
    db.add(user)
    db.commit()
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Direct database access from controllers
- ✅ **BLOCK**: Business logic in controllers
- ✅ **ALERT**: Missing service layer for complex operations
- ✅ **REQUIRE**: All database operations through repositories
- ✅ **VALIDATE**: Proper dependency injection patterns

#### Model & Schema Rules

```python
# ✅ CORRECT: Separate models and schemas
# app/models/user.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

# app/schemas/user.py
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Pydantic models in models directory
- ✅ **BLOCK**: SQLAlchemy models in schemas directory
- ✅ **REQUIRE**: Validation rules in Pydantic schemas
- ✅ **VALIDATE**: Proper field constraints and types
- ✅ **ALERT**: Missing database constraints

### 4. Security & Data Protection Rules

#### Authentication & Authorization

```python
# ✅ CORRECT: Proper JWT validation
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)) -> User:
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return await get_user_by_id(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ❌ BLOCKED: Plain text password storage
def create_user(username: str, password: str):
    user = User(username=username, password=password)  # BLOCKED: Plain text
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Plain text password storage
- ✅ **BLOCK**: Hardcoded secrets or API keys
- ✅ **REQUIRE**: JWT token validation for protected endpoints
- ✅ **VALIDATE**: Proper password hashing with bcrypt/argon2
- ✅ **ALERT**: Missing authentication on sensitive endpoints

#### Data Encryption & Privacy

```python
# ✅ CORRECT: Encrypted sensitive data
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt_sensitive_data(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# ❌ BLOCKED: Logging sensitive data
logger.info(f"User login: {user.email}, password: {password}")  # BLOCKED
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Logging of sensitive data (passwords, tokens, PII)
- ✅ **REQUIRE**: AES-256 encryption for sensitive fields
- ✅ **VALIDATE**: Proper data sanitization in logs
- ✅ **ALERT**: Missing encryption for sensitive data
- ✅ **REQUIRE**: Secure environment variable handling

### 5. Testing Rules

#### Test Coverage & Structure

```python
# ✅ CORRECT: Comprehensive test structure
# tests/unit/test_user_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.user_service import UserService
from app.schemas.user import UserCreate

class TestUserService:
    @pytest.fixture
    def mock_repo(self):
        return Mock()

    @pytest.fixture
    def user_service(self, mock_repo):
        return UserService(mock_repo)

    async def test_create_user_success(self, user_service, mock_repo):
        # Arrange
        user_data = UserCreate(username="test", email="test@example.com", password="password123")
        mock_repo.create.return_value = User(id=1, **user_data.dict())

        # Act
        result = await user_service.create_user(user_data)

        # Assert
        assert result.id == 1
        assert result.username == "test"
        mock_repo.create.assert_called_once()

# tests/integration/test_user_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user_endpoint():
    response = client.post("/api/users", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    assert "id" in response.json()
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Code with < 80% test coverage
- ✅ **REQUIRE**: Unit tests for all service methods
- ✅ **REQUIRE**: Integration tests for all API endpoints
- ✅ **VALIDATE**: Proper test isolation and cleanup
- ✅ **ALERT**: Missing tests for error conditions

#### Mock & Fixture Rules

```python
# ✅ CORRECT: Proper mocking patterns
@pytest.fixture
def mock_database():
    with patch('app.database.get_db') as mock_db:
        mock_session = Mock()
        mock_db.return_value = mock_session
        yield mock_session

@pytest.fixture
def sample_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }

# ❌ BLOCKED: Mocking internal implementation details
def test_user_service(mock_user_service):  # BLOCKED: Mocking service being tested
    pass
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Mocking the class under test
- ✅ **REQUIRE**: Mock external dependencies only
- ✅ **VALIDATE**: Proper fixture usage and cleanup
- ✅ **ALERT**: Missing async/await in async tests
- ✅ **REQUIRE**: Descriptive test names and assertions

### 6. Deployment & Infrastructure Rules

#### Docker & Containerization

```dockerfile
# ✅ CORRECT: Multi-stage Dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Hardcoded environment variables in Dockerfiles
- ✅ **REQUIRE**: Multi-stage builds for production images
- ✅ **VALIDATE**: Proper .dockerignore files
- ✅ **ALERT**: Missing health checks in containers
- ✅ **REQUIRE**: Non-root user in production containers

#### Environment & Configuration

```python
# ✅ CORRECT: Environment-based configuration
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

# ❌ BLOCKED: Hardcoded configuration
DATABASE_URL = "postgresql://user:pass@localhost/db"  # BLOCKED
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Hardcoded configuration values
- ✅ **REQUIRE**: Environment variable validation
- ✅ **VALIDATE**: Proper secrets management
- ✅ **ALERT**: Missing environment-specific configurations
- ✅ **REQUIRE**: Configuration validation with Pydantic

### 7. Async & Performance Rules

#### Async Patterns

```python
# ✅ CORRECT: Proper async/await usage
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# ❌ BLOCKED: Blocking calls in async functions
async def get_user_data(user_id: int):
    user = db.query(User).filter(User.id == user_id).first()  # BLOCKED: Blocking call
    return user
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Blocking database calls in async functions
- ✅ **REQUIRE**: AsyncSession for async database operations
- ✅ **VALIDATE**: Proper async context managers
- ✅ **ALERT**: Missing await keywords
- ✅ **REQUIRE**: Async-compatible libraries

#### Performance Optimization

```python
# ✅ CORRECT: Efficient database queries
async def get_users_with_orders(db: AsyncSession):
    query = select(User).options(selectinload(User.orders))
    result = await db.execute(query)
    return result.scalars().all()

# ❌ BLOCKED: N+1 query problems
async def get_users_with_orders_bad(db: AsyncSession):
    users = await db.execute(select(User))
    for user in users.scalars():
        user.orders = await db.execute(select(Order).where(Order.user_id == user.id))
    return users
```

**Cursor Validation Rules:**

- ✅ **ALERT**: Potential N+1 query problems
- ✅ **REQUIRE**: Proper use of selectinload/joinedload
- ✅ **VALIDATE**: Query optimization with indexes
- ✅ **ALERT**: Missing pagination for large datasets
- ✅ **REQUIRE**: Connection pooling configuration

### 8. Event-Driven Architecture Rules

#### Celery Task Patterns

```python
# ✅ CORRECT: Proper Celery task definition
from celery import Celery
from app.core.config import settings

celery_app = Celery("algoTrading", broker=settings.redis_url)

@celery_app.task(bind=True, max_retries=3)
async def process_order_notification(self, order_id: int):
    try:
        # Task logic here
        await send_order_confirmation(order_id)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# ❌ BLOCKED: Synchronous tasks in async context
@celery_app.task
def sync_task():  # BLOCKED: Should be async
    pass
```

**Cursor Validation Rules:**

- ✅ **REQUIRE**: Proper task retry mechanisms
- ✅ **VALIDATE**: Async task definitions
- ✅ **ALERT**: Missing error handling in tasks
- ✅ **REQUIRE**: Task result handling
- ✅ **VALIDATE**: Proper task routing and queues

#### Event Handling

```python
# ✅ CORRECT: Event-driven service communication
from app.events import EventBus
from app.events.order_events import OrderCreatedEvent

class OrderService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def create_order(self, order_data: OrderCreate) -> Order:
        order = await self.order_repo.create(order_data)

        # Emit event for other services
        await self.event_bus.emit(OrderCreatedEvent(order_id=order.id))

        return order
```

**Cursor Validation Rules:**

- ✅ **REQUIRE**: Event emission for state changes
- ✅ **VALIDATE**: Proper event handling patterns
- ✅ **ALERT**: Missing event documentation
- ✅ **REQUIRE**: Event versioning for compatibility
- ✅ **VALIDATE**: Proper event serialization

### 9. Monitoring & Observability Rules

#### Logging Standards

```python
# ✅ CORRECT: Structured logging
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def log_user_action(user_id: int, action: str, details: dict = None):
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details or {}
    }
    logger.info(json.dumps(log_data))

# ❌ BLOCKED: Logging sensitive information
logger.info(f"User {user.email} logged in with password {password}")  # BLOCKED
```

**Cursor Validation Rules:**

- ✅ **BLOCK**: Logging of sensitive data
- ✅ **REQUIRE**: Structured JSON logging
- ✅ **VALIDATE**: Appropriate log levels
- ✅ **ALERT**: Missing request correlation IDs
- ✅ **REQUIRE**: Log rotation and retention policies

#### Health Checks & Metrics

```python
# ✅ CORRECT: Comprehensive health checks
from fastapi import APIRouter, Depends
from app.core.health import HealthChecker

router = APIRouter()

@router.get("/health")
async def health_check(health_checker: HealthChecker = Depends()):
    return await health_checker.check_all()

class HealthChecker:
    async def check_database(self) -> bool:
        try:
            await self.db.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def check_redis(self) -> bool:
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
```

**Cursor Validation Rules:**

- ✅ **REQUIRE**: Health check endpoints
- ✅ **VALIDATE**: Database connectivity checks
- ✅ **ALERT**: Missing external service health checks
- ✅ **REQUIRE**: Metrics collection endpoints
- ✅ **VALIDATE**: Proper error handling in health checks

### 10. Documentation Rules

#### API Documentation

```python
# ✅ CORRECT: Comprehensive API documentation
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Creates a new user account with the provided information",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "User already exists"}
    }
)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends()
) -> UserResponse:
    """
    Create a new user account.

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Secure password (minimum 8 characters)
    """
    return await user_service.create_user(user_data)
```

**Cursor Validation Rules:**

- ✅ **REQUIRE**: OpenAPI documentation for all endpoints
- ✅ **VALIDATE**: Proper response model definitions
- ✅ **ALERT**: Missing endpoint descriptions
- ✅ **REQUIRE**: Error response documentation
- ✅ **VALIDATE**: Example request/response data

## Cursor Validation Commands

### Pre-commit Hooks

```bash
# Run before each commit
black --check .
flake8 .
mypy .
pytest --cov=app --cov-report=term-missing
```

### CI/CD Pipeline Validation

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          pytest --cov=app --cov-fail-under=80
      - name: Check code quality
        run: |
          black --check .
          flake8 .
          mypy .
```

## Enforcement Levels

### 🔴 BLOCK (Prevents commit/merge)

- Security vulnerabilities
- Hardcoded secrets
- Direct database access from controllers
- Missing type hints on new code
- Test coverage below 80%

### 🟡 ALERT (Warning, but allows commit)

- Potential performance issues
- Missing documentation
- Code style inconsistencies
- Unused imports or variables

### ✅ REQUIRE (Must be present)

- Proper error handling
- Input validation
- Authentication on protected endpoints
- Health check endpoints
- API documentation

### 🔍 VALIDATE (Automated checking)

- Type safety with mypy
- Code formatting with black
- Linting with flake8
- Test coverage with pytest-cov
- Security scanning with bandit

---

## 🧩 CURSOR STRICT PYTHON POLICY – NIVEL PROFESIONAL

**⚠️ ESTA POLÍTICA SE APLICA AUTOMÁTICAMENTE A TODO CÓDIGO PYTHON**

### 🧩 1. Sintaxis impecable

Antes de mostrar o modificar cualquier archivo `.py`, valida con:

```python
import ast
ast.parse(code)
```

**Reglas de aplicación:**

- ✅ **SI FALLA**: No muestres el código hasta corregirlo internamente
- ✅ **NUNCA**: Generes código que produzca `SyntaxError`, `IndentationError`, `NameError` ni `ImportError`
- ✅ **VALIDAR**: Siempre con `ast.parse()` antes de aplicar cambios

### 🧱 2. Indentación y estructura

```python
# ✅ USAR: 4 espacios por nivel (prohibido tabs)
def my_function():
    if condition:  # 4 espacios
        return result  # 8 espacios

# ❌ BLOQUEAR: Tabs o indentación inconsistente
```

**Reglas de aplicación:**

- ✅ Cada bloque (`def`, `class`, `if`, `for`, `while`, `try`, `with`) debe tener cuerpo y cierre válidos
- ✅ Si modificas código existente, mantén la indentación previa
- ✅ Si hay riesgo de romper la estructura, regenera el archivo completo, no fragmentos

### 📦 3. Imports verificados

Antes de añadir un import, verifica que el módulo existe:

```bash
python -c "from importlib.util import find_spec; print(find_spec('module_name'))"
```

**Reglas de aplicación:**

- ✅ Verifica en la stdlib con `importlib.util.find_spec`
- ✅ Verifica instalado vía `pip freeze`
- ✅ Prohibido inventar módulos, dependencias o rutas que no existan
- ✅ Usa `isort` para ordenar los imports automáticamente

### 🔍 4. Post-validación automática

Después de cualquier cambio, Cursor debe internamente ejecutar:

```bash
python -m ast file.py
black file.py --line-length 100
isort file.py
flake8 file.py --max-line-length=100
```

**Si algo falla, autocorrige con:**

```bash
autopep8 --in-place --aggressive file.py
```

**Reglas de aplicación:**

- ✅ Garantizar 0 errores antes de mostrar el resultado
- ✅ Si falla, autocorregir con `autopep8 --in-place --aggressive file.py`
- ✅ Solo entregar el archivo si pasa todas las verificaciones

### ⚙️ 5. Consistencia estructural

```python
# ✅ CORRECTO: Estructura completa
class MyClass:
    def __init__(self):
        self.value = 0

    def method(self):
        return self.value

# ❌ BLOQUEAR: Bloques incompletos
class MyClass:
    def __init__(self):
        pass  # NO dejar pass vacíos sin lógica

class MyClass:
    def method(self):
        try:  # NO usar try sin except/finally
            pass
```

**Reglas de aplicación:**

- ✅ Cada clase o función debe tener su cuerpo correctamente indentado y cerrado
- ✅ No dejes `pass` vacíos donde debería haber lógica
- ✅ No uses bloques `try:` sin `except:` o `finally:` válidos
- ✅ No introduzcas cambios parciales que rompan la jerarquía de clases

### 🧪 6. Formateo y linting obligatorio

Antes de guardar o mostrar el código:

```bash
# Formatea con black
black --line-length 100 file.py

# Ordena imports con isort
isort file.py

# Verifica errores de estilo con flake8
flake8 --max-line-length=100 file.py

# Y pylint
pylint file.py --disable=C0114,C0116
```

**Reglas de aplicación:**

- ✅ Solo entrega el archivo si pasa todas las verificaciones sin errores
- ✅ No hay excepciones a esta regla

### 🚫 7. Seguridad y estilo

```python
# ❌ PROHIBIDO: eval, exec, os.system
result = eval(user_input)  # NUNCA

# ✅ USAR: Manejo seguro de archivos
with open(path, "r") as f:
    data = f.read()

# ✅ USAR: Tipado estático
from typing import List, Dict

def process_data(data: List[Dict[str, int]]) -> None:
    pass

# ❌ PROHIBIDO: except vacío
try:
    risky_operation()
except:  # NUNCA - especificar la excepción
    pass

# ✅ CORRECTO:
try:
    risky_operation()
except ValueError as e:
    handle_error(e)
```

**Reglas de aplicación:**

- ✅ No uses `eval`, `exec`, `os.system`, ni comandos shell directos
- ✅ No uses variables no inicializadas ni tipos dinámicos no anotados
- ✅ Siempre usa manejo de archivos seguro: `with open(path, "r") as f:`
- ✅ Usa tipado estático (`typing`) en todas las funciones nuevas
- ✅ No uses `except:` vacío. Especifica la excepción: `except Exception as e:`

### 🧾 8. Validación incremental

**Proceso OBLIGATORIO:**

```python
# PASO 1: Genera solo la estructura mínima
import ast

# PASO 2: Verifica con ast.parse
code = """
def my_function():
    pass
"""
ast.parse(code)  # ✅ Si pasa, continúa

# PASO 3: Rellena el cuerpo
code = """
def my_function(x: int) -> int:
    return x * 2
"""
ast.parse(code)  # ✅ Verifica nuevamente
```

**Reglas de aplicación:**

- ✅ Primero genera solo la estructura mínima (`imports`, `class`, `def`) y verifica con `ast.parse`
- ✅ Luego rellena el cuerpo con lógica validada
- ✅ Si una validación falla, corrige automáticamente antes de continuar

### 🛠 9. Modo reparación activa

Si detectas un archivo roto:

```bash
# Ejecuta reparación automática
black .
autopep8 --in-place --aggressive .

# Valida con
python -c "import ast; ast.parse(open('file.py').read())"
```

**Reglas de aplicación:**

- ✅ Solo tras validarlo, reanuda modificaciones
- ✅ No continúes con código roto

### 📊 10. Integración con el proyecto actual

```yaml
# Estas reglas aplican SOLO a:
applies_to:
  - "app/**/*.py" # Código de aplicación
  - "tests/**/*.py" # Tests

# NO aplican a:
excludes:
  - ".memory/**"
  - "docs/**"
  - "*.yaml"
  - "*.json"
```

**Reglas de aplicación:**

- ✅ Solo a archivos Python del proyecto de trading
- ✅ NO a `.memory`, `docs/`, ni archivos de configuración YAML o JSON
- ✅ NO crear ni modificar tareas de `.memory` automáticamente sin aprobación

### 💬 Mensaje recordatorio final (obligatorio)

> **⚠️ "Nunca priorices la velocidad de generación sobre la integridad del código. Cada archivo Python debe poder ejecutarse sin errores inmediatamente después de ser guardado."**

---

**APLICACIÓN AUTOMÁTICA:**

Estas reglas se aplican AUTOMÁTICAMENTE en cada interacción con código Python. El sistema de validación interno de Cursor las ejecuta antes de mostrar cualquier sugerencia de código.
