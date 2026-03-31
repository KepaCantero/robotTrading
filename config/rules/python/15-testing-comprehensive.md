# Comprehensive Testing Standards

Complete testing standards for enterprise Python applications.

## Table of Contents
1. Test Structure
2. Naming Conventions
3. AAA Pattern
4. Fixtures and Setup
5. Parametrized Tests
6. Mocking and Patching
7. Exception Testing
8. Async Testing
9. Integration Tests
10. Property-Based Testing
11. Performance Testing
12. Contract Testing
13. Snapshot Testing
14. Test Markers
15. Test Data Builders
16. Smoke Tests

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Global fixtures
├── fixtures/
│   ├── __init__.py
│   ├── user_fixtures.py       # User fixtures
│   └── database_fixtures.py   # DB fixtures
├── unit/                      # Unit tests (isolated)
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/               # Integration tests
│   ├── test_database.py
│   └── test_api_endpoints.py
├── functional/                # Functional tests
├── e2e/                      # End-to-end tests
├── performance/              # Performance tests
└── security/                 # Security tests
```

---

## Naming Conventions

### ✅ CORRECT - Descriptive names

```python
def test_create_user_with_valid_email_returns_user() -> None:
    """Test user creation succeeds with valid email."""
    pass


def test_create_user_with_duplicate_email_raises_exception() -> None:
    """Test user creation fails with duplicate email."""
    pass


def test_create_user_with_invalid_email_raises_validation_error() -> None:
    """Test user creation fails with invalid email format."""
    pass
```

### Pattern

```
test_<what>_<condition>_<expected_result>()

Examples:
- test_user_activate_when_inactive_sets_status_active()
- test_repository_save_with_duplicate_id_raises_integrity_error()
- test_api_get_user_when_not_found_returns_404()
```

### ❌ INCORRECT - Vague names

```python
def test_user() -> None:
    pass

def test_create() -> None:
    pass
```

---

## AAA Pattern (Arrange-Act-Assert)

### ✅ CORRECT - Clear AAA structure

```python
def test_create_user_success() -> None:
    """Test successful user creation following AAA pattern."""

    # ============== ARRANGE ==============
    repository = Mock(spec=UserRepository)
    email_service = Mock(spec=EmailService)
    use_case = CreateUserUseCase(repository, email_service)

    command = CreateUserCommand(
        email="test@example.com",
        name="Test User"
    )

    expected_user = User(
        id=1,
        email="test@example.com",
        name="Test User",
        status=UserStatus.ACTIVE,
        created_at=datetime.now()
    )

    repository.find_by_email.return_value = None
    repository.save.return_value = expected_user

    # ============== ACT ==============
    result = use_case.execute(command)

    # ============== ASSERT ==============
    assert result.user_id == expected_user.id
    assert result.created_at == expected_user.created_at

    repository.find_by_email.assert_called_once_with("test@example.com")
    repository.save.assert_called_once()
    email_service.send_welcome_email.assert_called_once_with(expected_user)
```

---

## Fixtures and Setup

### ✅ CORRECT - Global fixtures in conftest.py

```python
# conftest.py
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

@pytest.fixture(scope="session")
def database_engine():
    """Create test database engine for entire test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def database_session(database_engine) -> Generator[Session, None, None]:
    """Provide clean database session for each test."""
    SessionLocal = sessionmaker(bind=database_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def user_repository(database_session: Session) -> SQLAlchemyUserRepository:
    """Provide user repository with database session."""
    return SQLAlchemyUserRepository(database_session)


@pytest.fixture
def mock_email_service() -> Mock:
    """Provide mock email service."""
    return Mock(spec=EmailService)


@pytest.fixture
def sample_user() -> User:
    """Provide sample user for tests."""
    return User(
        id=1,
        email="test@example.com",
        name="Test User",
        status=UserStatus.ACTIVE,
        created_at=datetime(2024, 1, 1, 12, 0, 0)
    )


@pytest.fixture(params=["development", "staging", "production"])
def environment(request) -> str:
    """Provide different environments."""
    return request.param
```

---

## Parametrized Tests

### ✅ CORRECT - Simple parametrization

```python
@pytest.mark.parametrize("email,is_valid", [
    ("valid@example.com", True),
    ("also.valid@example.co.uk", True),
    ("user+tag@example.com", True),
    ("invalid@", False),
    ("@invalid.com", False),
    ("no-at-sign.com", False),
    ("", False),
])
def test_email_validation(email: str, is_valid: bool) -> None:
    """Test email validation with various inputs."""
    if is_valid:
        Email(email)  # Should not raise
    else:
        with pytest.raises(ValueError, match="Invalid email"):
            Email(email)
```

### Multiple parametrization

```python
@pytest.mark.parametrize("status", [
    UserStatus.ACTIVE,
    UserStatus.INACTIVE,
    UserStatus.SUSPENDED,
])
@pytest.mark.parametrize("email_verified", [True, False])
def test_user_permissions(status: UserStatus, email_verified: bool) -> None:
    """Test user permissions with different status and verification combinations."""
    user = User(
        id=1,
        email="test@example.com",
        name="Test",
        status=status,
        created_at=datetime.now()
    )

    can_login = user.can_login()

    if status == UserStatus.ACTIVE and email_verified:
        assert can_login is True
    else:
        assert can_login is False
```

### With descriptive IDs

```python
@pytest.mark.parametrize("user_data,expected_error", [
    pytest.param(
        {"name": "", "email": "test@example.com"},
        "Name cannot be empty",
        id="empty_name"
    ),
    pytest.param(
        {"name": "Test", "email": ""},
        "Email cannot be empty",
        id="empty_email"
    ),
])
def test_user_validation_errors(
    user_data: dict[str, str],
    expected_error: str
) -> None:
    """Test user validation with invalid data."""
    with pytest.raises(ValidationError, match=expected_error):
        User(**user_data)
```

---

## Mocking and Patching

### ✅ CORRECT - Basic mocking

```python
def test_send_email_calls_smtp_service() -> None:
    """Test email service uses SMTP correctly."""
    smtp_service = Mock()
    email_service = EmailService(smtp_service)

    email_service.send("test@example.com", "Subject", "Body")

    smtp_service.send.assert_called_once_with(
        to="test@example.com",
        subject="Subject",
        body="Body"
    )
```

### Mock with return values

```python
def test_repository_returns_mocked_user() -> None:
    """Test repository mock returns configured user."""
    mock_repo = Mock(spec=UserRepository)
    expected_user = User(
        id=1,
        email="test@example.com",
        name="Test",
        status=UserStatus.ACTIVE,
        created_at=datetime.now()
    )
    mock_repo.find_by_id.return_value = expected_user

    user = mock_repo.find_by_id(1)

    assert user == expected_user
    mock_repo.find_by_id.assert_called_once_with(1)
```

### Mock with side effects

```python
def test_repository_handles_database_error() -> None:
    """Test repository handles database errors correctly."""
    mock_repo = Mock(spec=UserRepository)
    mock_repo.save.side_effect = DatabaseError("Connection failed")

    with pytest.raises(DatabaseError, match="Connection failed"):
        mock_repo.save(User(...))
```

### Patching

```python
@patch('app.services.user_service.datetime')
def test_user_creation_timestamp(mock_datetime: Mock) -> None:
    """Test user creation uses current timestamp."""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time

    service = UserService()
    user = service.create_user("test@example.com", "Test")

    assert user.created_at == fixed_time
```

---

## Exception Testing

### ✅ CORRECT - Exception testing

```python
def test_invalid_email_raises_value_error() -> None:
    """Test that invalid email raises ValueError."""
    with pytest.raises(ValueError):
        Email("invalid-email")


def test_duplicate_email_raises_specific_error() -> None:
    """Test duplicate email raises error with specific message."""
    repository = UserRepository()
    repository.save(User(email="test@example.com", ...))

    with pytest.raises(DomainException, match="Email already exists"):
        repository.save(User(email="test@example.com", ...))


def test_exception_details() -> None:
    """Test exception contains expected details."""
    with pytest.raises(CustomException) as exc_info:
        raise_custom_exception()

    assert exc_info.value.error_code == "E001"
    assert "details" in exc_info.value.context
```

---

## Async Testing

### ✅ CORRECT - Async tests

```python
@pytest.mark.asyncio
async def test_async_fetch_user() -> None:
    """Test async user fetching."""
    service = AsyncUserService()
    user = await service.get_user(1)

    assert user.id == 1


@pytest.mark.asyncio
async def test_concurrent_operations() -> None:
    """Test concurrent async operations."""
    service = AsyncUserService()

    users = await asyncio.gather(
        service.get_user(1),
        service.get_user(2),
        service.get_user(3),
    )

    assert len(users) == 3
```

### Async fixtures

```python
@pytest.fixture
async def async_database() -> AsyncGenerator[AsyncDatabase, None]:
    """Provide async database connection."""
    db = AsyncDatabase()
    await db.connect()
    yield db
    await db.disconnect()
```

---

## Integration Tests

### ✅ CORRECT - Integration test with real database

```python
def test_user_repository_integration(integration_database) -> None:
    """Integration test for user repository with real database."""
    Session = sessionmaker(bind=integration_database)
    session = Session()
    repository = SQLAlchemyUserRepository(session)

    user = User(
        id=0,
        email="integration@test.com",
        name="Integration Test",
        status=UserStatus.ACTIVE,
        created_at=datetime.now()
    )

    try:
        # Save
        saved_user = repository.save(user)
        session.commit()

        # Retrieve
        found_user = repository.find_by_id(saved_user.id)
        assert found_user is not None
        assert found_user.email == user.email

    finally:
        session.rollback()
        session.close()
```

---

## Property-Based Testing

### ✅ CORRECT - Hypothesis tests

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=1000))
def test_calculate_discount_always_reduces_price(price: int) -> None:
    """Property: Discount should always reduce or maintain price."""
    discounted = calculate_discount(price, discount_percent=10)
    assert discounted <= price


@given(
    email=st.emails(),
    name=st.text(min_size=1, max_size=100)
)
def test_user_creation_with_random_valid_data(
    email: str,
    name: str
) -> None:
    """Test user creation with randomly generated valid data."""
    user = User(
        id=0,
        email=email,
        name=name,
        status=UserStatus.ACTIVE,
        created_at=datetime.now()
    )
    assert user.email == email
    assert user.name == name
```

---

## Performance Testing

### ✅ CORRECT - Performance tests

```python
@pytest.mark.timeout(5)  # Must complete in 5 seconds
def test_bulk_user_creation_performance() -> None:
    """Test bulk user creation completes within time limit."""
    repository = UserRepository()

    users = [
        User(id=i, email=f"user{i}@test.com", name=f"User {i}",
             status=UserStatus.ACTIVE, created_at=datetime.now())
        for i in range(1000)
    ]

    start = time.time()
    repository.bulk_create(users)
    duration = time.time() - start

    assert duration < 5.0
```

---

## Contract Testing

### ✅ CORRECT - Contract testing with Pydantic

```python
def test_api_response_contract_valid() -> None:
    """Test API response matches expected contract."""
    response_data = {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "created_at": "2024-01-01T12:00:00"
    }

    user_response = UserResponseSchema(**response_data)
    assert user_response.id == 1
    assert user_response.email == "test@example.com"


def test_api_response_contract_invalid() -> None:
    """Test API rejects invalid contract."""
    response_data = {
        "id": 1,
        "name": "Test User"  # Missing email
    }

    with pytest.raises(ValidationError) as exc_info:
        UserResponseSchema(**response_data)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("email",) for e in errors)
```

---

## Test Markers

### ✅ CORRECT - Using markers

```python
@pytest.mark.unit
def test_user_validation() -> None:
    """Unit test for user validation."""
    pass


@pytest.mark.integration
@pytest.mark.database
def test_user_repository_save() -> None:
    """Integration test with database."""
    pass


@pytest.mark.slow
@pytest.mark.timeout(30)
def test_bulk_operation() -> None:
    """Slow test with timeout."""
    pass


@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature() -> None:
    """Test for future feature."""
    pass
```

### Run specific markers

```bash
pytest -m unit              # Only unit tests
pytest -m "not slow"        # Exclude slow tests
pytest -m "database and integration"
```

---

## Test Data Builders

### ✅ CORRECT - Builder pattern

```python
class UserBuilder:
    """Builder for creating test users easily."""

    def __init__(self) -> None:
        self._id = 1
        self._email = "default@example.com"
        self._name = "Default User"
        self._status = UserStatus.ACTIVE
        self._created_at = datetime(2024, 1, 1, 12, 0, 0)

    def with_id(self, id: int) -> "UserBuilder":
        self._id = id
        return self

    def with_email(self, email: str) -> "UserBuilder":
        self._email = email
        return self

    def inactive(self) -> "UserBuilder":
        self._status = UserStatus.INACTIVE
        return self

    def build(self) -> User:
        return User(
            id=self._id,
            email=self._email,
            name=self._name,
            status=self._status,
            created_at=self._created_at
        )


# Usage
def test_inactive_user_cannot_login() -> None:
    user = UserBuilder().inactive().build()
    assert user.can_login() is False
```

---

## Smoke Tests

### ✅ CORRECT - Critical functionality tests

```python
@pytest.mark.smoke
class TestSmokeTests:
    """Quick smoke tests for critical functionality."""

    def test_database_connection(self) -> None:
        """Verify database is accessible."""
        db = Database()
        assert db.is_connected()

    def test_api_health_endpoint(self, test_client) -> None:
        """Verify API is responding."""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_can_create_user(self, user_repository) -> None:
        """Verify basic user creation works."""
        user = User(
            id=0,
            email="smoke@test.com",
            name="Smoke Test",
            status=UserStatus.ACTIVE,
            created_at=datetime.now()
        )
        saved = user_repository.save(user)
        assert saved.id > 0
```

---

## Testing Checklist

- [ ] Tests follow AAA pattern
- [ ] Descriptive test names (what-condition-expected)
- [ ] Each test is independent
- [ ] External dependencies are mocked
- [ ] Both success and failure paths tested
- [ ] Edge cases covered (empty, None, boundaries)
- [ ] Exceptions tested with pytest.raises
- [ ] Parametrized tests for multiple cases
- [ ] Fixtures used for common setup
- [ ] Coverage > 80%
- [ ] No hardcoded test data in logic
- [ ] Tests run quickly (unit tests < 0.1s)
- [ ] Integration tests use real resources
- [ ] Property-based tests where applicable
- [ ] Performance tests with time limits
- [ ] Contract tests for API schemas
- [ ] Smoke tests for critical paths
- [ ] Tests marked appropriately (unit, integration, slow)
