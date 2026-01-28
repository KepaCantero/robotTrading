# Enterprise Architecture

Layered architecture, clean code principles, and enterprise patterns.

## Table of Contents
1. Layered Architecture Structure
2. Domain Layer
3. Application Layer
4. Infrastructure Layer
5. Presentation Layer

---

## Layered Architecture Structure

```
project/
├── app/
│   ├── domain/              # Domain Layer
│   │   ├── __init__.py
│   │   ├── models.py        # Domain entities
│   │   ├── value_objects.py # Value Objects
│   │   └── exceptions.py    # Domain exceptions
│   ├── application/         # Application Layer
│   │   ├── __init__.py
│   │   ├── use_cases/       # Use cases
│   │   ├── dtos.py          # Data Transfer Objects
│   │   └── services.py      # Application services
│   ├── infrastructure/      # Infrastructure Layer
│   │   ├── __init__.py
│   │   ├── database/        # DB implementations
│   │   ├── repositories/    # Concrete repositories
│   │   ├── external/        # External APIs
│   │   └── config.py        # Configuration
│   └── presentation/        # Presentation Layer
│       ├── __init__.py
│       ├── api/             # REST API
│       ├── cli/             # CLI
│       └── schemas.py       # Validation schemas
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── functional/         # Functional tests
│   ├── e2e/               # End-to-end tests
│   ├── performance/       # Performance tests
│   ├── conftest.py        # Shared fixtures
│   └── fixtures/          # Test data
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

---

## Domain Layer (Business Core)

### Domain Models

```python
# ✅ CORRECT - Domain entity with business logic
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class UserStatus(Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


@dataclass
class User:
    """User domain entity - pure business logic."""
    id: int
    email: str
    name: str
    status: UserStatus
    created_at: datetime

    def activate(self) -> None:
        """Activate user account."""
        if self.status == UserStatus.SUSPENDED:
            raise DomainException("Cannot activate suspended user")
        self.status = UserStatus.ACTIVE

    def suspend(self, reason: str) -> None:
        """Suspend user account."""
        self.status = UserStatus.SUSPENDED
        # Log reason, emit event, etc.

    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
```

### Value Objects

```python
# ✅ CORRECT - Immutable value object
@dataclass(frozen=True)
class Email:
    """Email value object - immutable."""
    value: str

    def __post_init__(self) -> None:
        """Validate email format."""
        if "@" not in self.value or "." not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split("@")[0]


@dataclass(frozen=True)
class Money:
    """Money value object."""
    amount: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

    def add(self, other: "Money") -> "Money":
        """Add money amounts."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, factor: float) -> "Money":
        """Multiply amount by factor."""
        return Money(self.amount * factor, self.currency)
```

### Domain Exceptions

```python
# ✅ CORRECT - Domain-specific exceptions
class DomainException(Exception):
    """Base domain exception."""
    pass


class UserNotFoundException(DomainException):
    """User not found exception."""
    pass


class InvalidEmailException(DomainException):
    """Invalid email exception."""
    pass


class InsufficientFundsException(DomainException):
    """Insufficient funds exception."""
    pass
```

---

## Application Layer (Use Cases)

### Command/Result Pattern

```python
# ✅ CORRECT - Use case with Command/Result pattern
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CreateUserCommand:
    """Command for creating a user."""
    email: str
    name: str


@dataclass
class CreateUserResult:
    """Result of user creation."""
    user_id: int
    created_at: datetime


class CreateUserUseCase:
    """Use case for creating a user."""

    def __init__(
        self,
        user_repository: "UserRepository",
        email_service: "EmailService",
    ) -> None:
        self._user_repository = user_repository
        self._email_service = email_service

    def execute(self, command: CreateUserCommand) -> CreateUserResult:
        """Execute user creation use case."""
        # Validate email doesn't exist
        existing_user = self._user_repository.find_by_email(command.email)
        if existing_user:
            raise DomainException(f"Email already exists: {command.email}")

        # Create user
        user = User(
            id=0,  # Will be set by repository
            email=command.email,
            name=command.name,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(),
        )

        # Save user
        saved_user = self._user_repository.save(user)

        # Send welcome email
        self._email_service.send_welcome_email(saved_user)

        return CreateUserResult(
            user_id=saved_user.id,
            created_at=saved_user.created_at,
        )


@dataclass
class UpdateUserEmailCommand:
    """Command for updating user email."""
    user_id: int
    new_email: str


class UpdateUserEmailUseCase:
    """Use case for updating user email."""

    def __init__(
        self,
        user_repository: "UserRepository",
        email_validator: "EmailValidator",
    ) -> None:
        self._user_repository = user_repository
        self._email_validator = email_validator

    def execute(self, command: UpdateUserEmailCommand) -> None:
        """Execute email update use case."""
        # Validate new email format
        if not self._email_validator.is_valid(command.new_email):
            raise InvalidEmailException(f"Invalid email: {command.new_email}")

        # Get user
        user = self._user_repository.find_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User not found: {command.user_id}")

        # Check if email already exists
        existing = self._user_repository.find_by_email(command.new_email)
        if existing and existing.id != command.user_id:
            raise DomainException(f"Email already in use: {command.new_email}")

        # Update email
        user.email = command.new_email
        self._user_repository.save(user)
```

### DTOs (Data Transfer Objects)

```python
# ✅ CORRECT - DTOs for layer boundaries
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserDTO(BaseModel):
    """User data transfer object."""
    id: int
    email: EmailStr
    name: str
    status: str
    created_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class CreateUserRequestDTO(BaseModel):
    """DTO for creating user request."""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100, description="User name")


class UserResponseDTO(BaseModel):
    """DTO for user response."""
    user_id: int
    email: EmailStr
    name: str
    status: str
    created_at: datetime


class PaginatedResponseDTO(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## Infrastructure Layer (Technical Details)

### Repository Implementation

```python
# ✅ CORRECT - SQLAlchemy repository implementation
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class UserRepository(ABC):
    """Abstract user repository."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save user."""
        pass

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        """Find user by ID."""
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        """Find user by email."""
        pass


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of user repository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user: User) -> User:
        """Save user to database."""
        db_user = UserModel(
            email=user.email,
            name=user.name,
            status=user.status.value,
        )
        self._session.add(db_user)
        self._session.commit()
        self._session.refresh(db_user)

        return self._map_to_domain(db_user)

    def find_by_id(self, user_id: int) -> User | None:
        """Find user by ID in database."""
        db_user = self._session.query(UserModel).filter_by(id=user_id).first()
        return self._map_to_domain(db_user) if db_user else None

    def find_by_email(self, email: str) -> User | None:
        """Find user by email in database."""
        db_user = self._session.query(UserModel).filter_by(email=email).first()
        return self._map_to_domain(db_user) if db_user else None

    def _map_to_domain(self, db_user: UserModel) -> User:
        """Map database model to domain model."""
        return User(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            status=UserStatus(db_user.status),
            created_at=db_user.created_at,
        )
```

### External Service Clients

```python
# ✅ CORRECT - External API client with retry logic
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ExternalAPIClient:
    """Client for external API with retry logic."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET request with retry logic."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def post(self, endpoint: str, data: dict) -> dict:
        """POST request with retry logic."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = await self._client.post(url, json=data)
        response.raise_for_status()
        return response.json()
```

---

## Presentation Layer (API/CLI)

### REST API with FastAPI

```python
# ✅ CORRECT - FastAPI endpoint with dependency injection
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

router = APIRouter(prefix="/users", tags=["users"])


# Dependency injection
def get_user_repository() -> SQLAlchemyUserRepository:
    """Get user repository."""
    return SQLAlchemyUserRepository(get_db_session())


def get_create_user_use_case(
    repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> CreateUserUseCase:
    """Get create user use case."""
    email_service = EmailService()
    return CreateUserUseCase(repository, email_service)


# Endpoints
@router.post(
    "/",
    response_model=UserResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account with email and name.",
)
def create_user(
    request: CreateUserRequestDTO,
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
) -> UserResponseDTO:
    """Create a new user endpoint."""
    try:
        command = CreateUserCommand(
            email=request.email,
            name=request.name,
        )
        result = use_case.execute(command)

        return UserResponseDTO(
            user_id=result.user_id,
            email=request.email,
            name=request.name,
            status="active",
            created_at=result.created_at,
        )
    except DomainException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{user_id}",
    response_model=UserResponseDTO,
    summary="Get user by ID",
    description="Retrieve user information by user ID.",
)
def get_user(
    user_id: int,
    repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> UserResponseDTO:
    """Get user by ID endpoint."""
    user = repository.find_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )

    return UserResponseDTO(
        user_id=user.id,
        email=user.email,
        name=user.name,
        status=user.status.value,
        created_at=user.created_at,
    )


@router.get(
    "/",
    response_model=PaginatedResponseDTO[UserDTO],
    summary="List all users",
    description="Retrieve paginated list of users.",
)
def list_users(
    page: int = 1,
    page_size: int = 20,
    repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> PaginatedResponseDTO[UserDTO]:
    """List users endpoint."""
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

    users = repository.get_all()
    total = len(users)

    start = (page - 1) * page_size
    end = start + page_size
    paginated_users = users[start:end]

    return PaginatedResponseDTO(
        items=[UserDTO.model_validate(u) for u in paginated_users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
```

---

## Clean Code Principles

### Descriptive Names

```python
# ✅ CORRECT - Descriptive, meaningful names
def get_even_numbers(count: int) -> list[int]:
    """Get first N even numbers."""
    even_numbers: list[int] = []
    for number in range(count):
        even_numbers.append(number * 2)
    return even_numbers

# ❌ INCORRECT - Ambiguous names
def get_data(x: int) -> list[Any]:
    d = []
    for i in range(x):
        d.append(i * 2)
    return d
```

### Small Functions

```python
# ✅ CORRECT - Small, focused functions
def validate_order(order_data: dict) -> None:
    """Validate order has required items."""
    if not order_data.get("items"):
        raise ValueError("Order must contain items")


def calculate_order_total(items: list[dict]) -> float:
    """Calculate total price for order items."""
    return sum(item["price"] * item["quantity"] for item in items)


def apply_discount(total: float, threshold: float = 100.0) -> float:
    """Apply 10% discount if total exceeds threshold."""
    return total * 0.9 if total > threshold else total

# ❌ INCORRECT - Large function doing too much
def process_order(order_data: dict) -> dict:
    # 50+ lines of mixed logic
    pass
```

### DRY (Don't Repeat Yourself)

```python
# ✅ CORRECT - Reusable abstraction
def filter_users(predicate: Callable[[User], bool]) -> list[User]:
    """Filter users by predicate."""
    return [user for user in all_users if predicate(user)]


def is_active_and_verified(user: User) -> bool:
    """Check if user is active and email verified."""
    return user.status == "active" and user.email_verified


def get_active_users() -> list[User]:
    """Get all active and verified users."""
    return filter_users(is_active_and_verified)

# ❌ INCORRECT - Duplicated logic
def get_active_users():
    users = []
    for user in all_users:
        if user.status == "active" and user.email_verified:
            users.append(user)
    return users
```

### Explicit Error Handling

```python
# ✅ CORRECT - Explicit error handling
class ConfigNotFoundError(Exception):
    """Configuration not found exception."""
    pass


def get_user_config(user_id: int) -> dict:
    """
    Get user configuration.

    Args:
        user_id: User identifier.

    Returns:
        User configuration dictionary.

    Raises:
        ConfigNotFoundError: If configuration doesn't exist.
        DatabaseError: If database connection fails.
    """
    try:
        config = load_config(user_id)
        if config is None:
            raise ConfigNotFoundError(f"Config not found for user {user_id}")
        return config
    except DatabaseError as e:
        logger.error(f"Database error loading config: {e}")
        raise

# ❌ INCORRECT - Silencing errors
def get_user_config(user_id: int) -> dict:
    try:
        return load_config(user_id)
    except:
        return {}
```

---

## Architecture Checklist

- [ ] Dependencies point inward (toward domain)
- [ ] Domain has no framework dependencies
- [ ] Each layer has single responsibility
- [ ] Business logic in domain/application
- [ ] External concerns in infrastructure
- [ ] Interface details in presentation
- [ ] Functions < 20 lines
- [ ] Names descriptive and clear
- [ ] No code duplication
- [ ] Deep nesting avoided
- [ ] Specific exceptions raised/caught
- [ ] Resources managed with context managers
- [ ] Value objects immutable
- [ ] Composition over inheritance
