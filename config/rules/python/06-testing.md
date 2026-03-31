# Testing Standards

Python testing standards using Pytest with AAA pattern and best practices.

## Tool Configuration

### Pytest

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=app",
    "--cov-report=html",
    "--cov-report=term-missing:skip-covered",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Coverage.py

```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

## AAA Pattern (Arrange-Act-Assert)

Structure tests clearly with Arrange, Act, and Assert sections.

### ✅ CORRECT

```python
import pytest
from app.models import User
from app.services import UserService

def test_create_user_success():
    # Arrange - Set up test data and dependencies
    user_data = {
        "name": "Alice",
        "email": "alice@example.com",
    }
    repository = FakeUserRepository()
    service = UserService(repository)

    # Act - Execute the function being tested
    user = service.create_user(user_data["name"], user_data["email"])

    # Assert - Verify the result
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.id > 0
    assert repository.find_by_id(user.id) is not None


def test_create_user_invalid_email():
    # Arrange
    repository = FakeUserRepository()
    service = UserService(repository)

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid email"):
        service.create_user("Bob", "invalid-email")
```

### ❌ INCORRECT

```python
# No clear structure - hard to follow
def test_create_user():
    repo = FakeUserRepository()
    service = UserService(repo)
    user = service.create_user("Alice", "alice@example.com")
    assert user.name == "Alice"
    repo.save(user)
    assert repo.find_by_id(user.id) is not None
    user2 = service.create_user("Bob", "bob@example.com")
```

## Parametrized Tests

Use `@pytest.mark.parametrize` for multiple test cases.

### ✅ CORRECT

```python
@pytest.mark.parametrize(
    "email, is_valid",
    [
        ("user@example.com", True),
        ("user.name@example.com", True),
        ("user+tag@example.com", True),
        ("invalid", False),
        ("@example.com", False),
        ("user@", False),
        ("", False),
    ],
)
def test_email_validation(email: str, is_valid: bool):
    """Test email validation with multiple cases."""
    validator = EmailValidator()
    assert validator.is_valid(email) == is_valid


@pytest.mark.parametrize(
    "price, quantity, expected_total",
    [
        (10.0, 2, 20.0),
        (5.5, 4, 22.0),
        (0.99, 10, 9.90),
        (100.0, 0, 0.0),
    ],
)
def test_calculate_total(price: float, quantity: int, expected_total: float):
    """Test total calculation."""
    calculator = PriceCalculator()
    assert calculator.calculate_total(price, quantity) == expected_total
```

### ❌ INCORRECT

```python
# Duplicated test functions
def test_email_valid():
    validator = EmailValidator()
    assert validator.is_valid("user@example.com")

def test_email_valid_with_dot():
    validator = EmailValidator()
    assert validator.is_valid("user.name@example.com")

def test_email_invalid():
    validator = EmailValidator()
    assert not validator.is_valid("invalid")
```

## Fixtures

Use fixtures for common test setup and teardown.

### ✅ CORRECT

```python
import pytest
from app.models import User, Order
from app.services import OrderService

# Fixture with automatic cleanup
@pytest.fixture
def database():
    """Create a test database."""
    db = TestDatabase()
    db.setup()
    yield db
    db.cleanup()


# Fixture with parameters
@pytest.fixture
def user(database):
    """Create a test user."""
    user = User(name="Test User", email="test@example.com")
    database.save(user)
    return user


# Fixture that can be customized
@pytest.fixture
def order(database, user):
    """Factory fixture for creating orders."""
    def _create(**kwargs):
        defaults = {"user_id": user.id, "total": 100.0}
        defaults.update(kwargs)
        order = Order(**defaults)
        database.save(order)
        return order
    return _create


# Usage
def test_order_total(database, order):
    """Test order total calculation."""
    test_order = order(total=250.0)
    service = OrderService(database)

    assert service.calculate_total(test_order.id) == 250.0


# Session-scoped fixture (expensive setup)
@pytest.fixture(scope="session")
def redis_server():
    """Start Redis server once for all tests."""
    server = TestRedisServer()
    server.start()
    yield server
    server.stop()


# Class-scoped fixture
@pytest.fixture(scope="class")
def authenticated_client():
    """Create authenticated client for test class."""
    client = TestClient()
    client.login("user", "pass")
    yield client
    client.logout()
```

### ❌ INCORRECT

```python
# Setup in each test - duplication
def test_one():
    db = TestDatabase()
    db.setup()
    user = User(name="Test")
    db.save(user)
    # ... test logic
    db.cleanup()

def test_two():
    db = TestDatabase()
    db.setup()
    user = User(name="Test")
    db.save(user)
    # ... test logic
    db.cleanup()
```

## Mocking

Mock external dependencies properly.

### ✅ CORRECT

```python
from unittest.mock import Mock, patch, MagicMock
from app.services import ExternalApiService

def test_api_call_success():
    """Test successful API call."""
    # Create mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}

    # Patch external dependency
    with patch("requests.get", return_value=mock_response) as mock_get:
        service = ExternalApiService()
        result = service.fetch_data("https://api.example.com")

        # Assert mock was called correctly
        mock_get.assert_called_once_with("https://api.example.com")
        assert result == {"result": "success"}


def test_api_call_failure():
    """Test API call failure."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = HTTPError("Not found")

    with patch("requests.get", return_value=mock_response):
        service = ExternalApiService()

        with pytest.raises(HTTPError):
            service.fetch_data("https://api.example.com")


def test_with_mock_open():
    """Test file operations without actual files."""
    fake_content = "line1\nline2\nline3\n"

    with patch("builtins.open", mock_open(read_data=fake_content)):
        result = read_file("test.txt")

    assert result == ["line1", "line2", "line3"]


def test_database_service_with_mock_repo():
    """Test service with mocked repository."""
    mock_repo = Mock()
    mock_repo.find_by_id.return_value = User(id=1, name="Alice")

    service = UserService(mock_repo)
    user = service.get_user(1)

    assert user.name == "Alice"
    mock_repo.find_by_id.assert_called_once_with(1)
```

### ❌ INCORRECT

```python
# Not verifying mock calls
def test_with_mock():
    mock_repo = Mock()
    service = UserService(mock_repo)
    user = service.get_user(1)
    assert user.name == "Alice"
    # Did we call find_by_id? With what args? No verification!

# Mocking too much - testing the mock
def test_over_mocked():
    mock_db = Mock()
    mock_db.query.return_value = [{"id": 1, "name": "Alice"}]
    # ... complex mock setup
    # We're testing our mocks, not real behavior!
```

## Testing Exceptions

Test that exceptions are raised correctly.

### ✅ CORRECT

```python
def test_raises_exception():
    """Test that function raises exception."""
    with pytest.raises(ValueError, match="Invalid email"):
        validate_email("not-an-email")


def test_raises_exception_with_message():
    """Test exception message."""
    with pytest.raises(ValidationError) as exc_info:
        process_order(invalid_data)

    assert "order total" in str(exc_info.value)
    assert "must be positive" in str(exc_info.value)


def test_exception_attributes():
    """Test custom exception attributes."""
    with pytest.raises(CustomError) as exc_info:
        raise CustomError(code=404, message="Not found")

    assert exc_info.value.code == 404
    assert exc_info.value.message == "Not found"


def test_no_exception():
    """Test that exception is NOT raised."""
    # This test passes if no exception is raised
    validate_email("user@example.com")
```

### ❌ INCORRECT

```python
# Not checking exception type
def test_exception():
    try:
        validate_email("bad")
        assert False  # Should not reach here
    except:
        pass  # What exception was raised?

# Using bare except
def test_bad_exception_handling():
    with pytest.raises():
        validate_email("bad")  # Catches any exception - too broad!
```

## Test Organization

Organize tests by feature, not by test type.

### ✅ CORRECT

```
tests/
├── unit/
│   ├── models/
│   │   ├── test_user.py
│   │   └── test_order.py
│   ├── services/
│   │   ├── test_user_service.py
│   │   └── test_order_service.py
│   └── utils/
│       └── test_validators.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database_integration.py
└── conftest.py  # Shared fixtures
```

```python
# tests/unit/models/test_user.py
class TestUserModel:
    """Test User model."""

    def test_create_user(self):
        pass

    def test_user_validation(self):
        pass

    def test_user_age_calculation(self):
        pass


# tests/integration/test_api_endpoints.py
@pytest.mark.integration
class TestUserAPI:
    """Test user API endpoints."""

    def test_create_user_endpoint(self, client):
        pass

    def test_get_user_endpoint(self, client):
        pass
```

### ❌ INCORRECT

```
tests/
├── test_models.py  # Everything in one file
├── test_services.py
└── test_integration.py
```

## Test Naming

Use descriptive test names that describe what is being tested.

### ✅ CORRECT

```python
# Pattern: test_{what}_{when}_{expected_result}
def test_calculate_total_with_discount_applies_discount():
    """Test that total calculation applies discount when provided."""
    pass

def test_user_creation_with_invalid_email_raises_error():
    """Test that user creation raises error for invalid email."""
    pass

def test_order_status_transitions_from_pending_to_shipped():
    """Test order status transition."""
    pass


# Class-based tests
class TestUserService:
    """Test UserService."""

    def test_create_user_returns_user_with_id(self):
        pass

    def test_create_user_with_duplicate_email_raises_error(self):
        pass
```

### ❌ INCORRECT

```python
# Vague names
def test_one():
    pass

def test_user():
    pass

def test_error():
    pass

# Non-descriptive names
def test_a():
    pass

def test_user_test():
    pass
```

## Test Isolation

Each test should be independent and not depend on other tests.

### ✅ CORRECT

```python
# Each test sets up its own data
def test_find_user_by_id(database):
    user = User(name="Alice", email="alice@example.com")
    database.save(user)

    found = database.find_by_id(user.id)
    assert found.name == "Alice"


def test_update_user(database):
    user = User(name="Bob", email="bob@example.com")
    database.save(user)

    user.name = "Robert"
    database.save(user)

    found = database.find_by_id(user.id)
    assert found.name == "Robert"


def test_delete_user(database):
    user = User(name="Charlie", email="charlie@example.com")
    database.save(user)

    database.delete(user.id)

    assert database.find_by_id(user.id) is None
```

### ❌ INCORRECT

```python
# Tests depend on execution order
@pytest.fixture(scope="module")
def database():
    db = TestDatabase()
    yield db
    # Not cleaning up between tests!

def test_first_user(database):
    # Depends on database being empty
    user = User(name="First")
    database.save(user)
    assert len(database.all()) == 1

def test_second_user(database):
    # Assumes previous test ran!
    user = User(name="Second")
    database.save(user)
    # Fails if test_first_user didn't run
```

## Markers and Filtering

Use markers to categorize tests.

### ✅ CORRECT

```python
import pytest

@pytest.mark.unit
def test_user_validation():
    """Fast unit test."""
    pass


@pytest.mark.integration
def test_database_connection():
    """Slower integration test."""
    pass


@pytest.mark.slow
def test_large_file_processing():
    """Slow test that can be skipped."""
    pass


@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("invalid", False),
])
@pytest.mark.unit
def test_email_validation(email, valid):
    pass


# Run specific markers
# pytest -m unit          # Only unit tests
# pytest -m "not slow"    # Everything except slow tests
# pytest -m "integration or slow"  # Integration or slow tests
```

## Property-Based Testing

Use Hypothesis for property-based testing.

### ✅ CORRECT

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a: int, b: int):
    """Test that addition is commutative."""
    assert a + b == b + a


@given(st.lists(st.integers()))
def test_sort_preserves_elements(numbers: list[int]):
    """Test that sorting preserves elements."""
    sorted_numbers = sorted(numbers)
    assert len(sorted_numbers) == len(numbers)
    assert sorted(sorted_numbers) == sorted_numbers
    for n in numbers:
        assert n in sorted_numbers


@given(st.text())
def test_email_validation_rejects_empty(email: str):
    """Test that empty emails are rejected."""
    if not email:
        assert not is_valid_email(email)


@given(st.floats(min_value=0, allow_infinity=False, allow_nan=False))
def test_calculate_total_positive(price: float):
    """Test that total is positive for positive price."""
    total = calculate_total(price, 1)
    assert total >= 0
```

## Testing Checklist

- [ ] Tests follow AAA pattern (Arrange-Act-Assert)
- [ ] Each test has a descriptive name
- [ ] Tests are independent (no order dependencies)
- [ ] External dependencies are mocked
- [ ] Both success and failure paths tested
- [ ] Edge cases covered (empty, None, boundary values)
- [ ] Exceptions tested with pytest.raises
- [ ] Parametrized tests for multiple cases
- [ ] Fixtures used for common setup
- [ ] Coverage > 80%
- [ ] No hardcoded test data in test logic
- [ ] Tests run quickly (unit tests < 0.1s each)
