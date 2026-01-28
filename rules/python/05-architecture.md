# Architecture & Clean Code

Python application architecture patterns and clean code principles.

## Layered Architecture

Separate concerns into distinct layers.

### ✅ CORRECT - Four-tier architecture

```
app/
├── domain/              # Business entities and rules
│   ├── models.py
│   └── value_objects.py
├── application/         # Use cases and orchestration
│   ├── services.py
│   └── dto.py
├── infrastructure/      # External concerns
│   ├── database.py
│   ├── api_client.py
│   └── repositories.py
└── presentation/        # Interface layer
    ├── api.py
    ├── cli.py
    └── schemas.py
```

```python
# domain/models.py - Business entities (no framework dependencies)
@dataclass
class User:
    """Domain user entity."""
    id: int
    name: str
    email: str

    def __post_init__(self) -> None:
        self._validate_email()

    def _validate_email(self) -> None:
        if "@" not in self.email:
            raise ValueError("Invalid email")


# application/services.py - Business logic
class UserService:
    """User use cases."""

    def __init__(self, user_repo: "UserRepository") -> None:
        self._user_repo = user_repo

    def create_user(self, name: str, email: str) -> User:
        """Create user with validation."""
        user = User(id=generate_id(), name=name, email=email)
        self._user_repo.save(user)
        return user

    def get_user(self, user_id: int) -> User | None:
        return self._user_repo.find_by_id(user_id)


# infrastructure/repositories.py - Data access
class UserRepository:
    """User repository implementation."""

    def __init__(self, db: "Database") -> None:
        self._db = db

    def save(self, user: User) -> None:
        self._db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            (user.id, user.name, user.email),
        )

    def find_by_id(self, user_id: int) -> User | None:
        row = self._db.query_one(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )
        return User(**row) if row else None


# presentation/api.py - External interface
from fastapi import FastAPI, Depends

app = FastAPI()

def get_user_service() -> UserService:
    return UserService(UserRepository(get_database()))


@app.post("/users")
def create_user(
    name: str,
    email: str,
    service: UserService = Depends(get_user_service),
) -> dict:
    user = service.create_user(name, email)
    return {"id": user.id, "name": user.name}
```

### ❌ INCORRECT - Mixed concerns

```python
# One big file doing everything
class UserHandler:
    def create_user(self, name: str, email: str):
        # Validation
        if "@" not in email:
            raise ValueError("Invalid email")

        # Database logic
        db = Database("localhost")
        db.execute(f"INSERT INTO users ...")

        # API response
        return {"status": "created"}

# Problems:
# - Can't test without database
# - Can't reuse validation logic
# - Can't swap database implementation
# - Multiple reasons to change
```

## Clean Code Principles

### DRY - Don't Repeat Yourself

#### ✅ CORRECT

```python
# Extract common logic
def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency."""
    return f"{amount:,.2f} {currency}"


# Reuse function
def print_invoice(items: list[dict]) -> None:
    total = sum(item["price"] * item["quantity"] for item in items)
    print(f"Total: {format_currency(total)}")


def print_receipt(items: list[dict]) -> None:
    total = sum(item["price"] * item["quantity"] for item in items)
    print(f"Paid: {format_currency(total)}")
```

#### ❌ INCORRECT

```python
# Duplicated logic
def print_invoice(items: list[dict]) -> None:
    total = sum(item["price"] * item["quantity"] for item in items)
    print(f"Total: {total:,.2f} USD")


def print_receipt(items: list[dict]) -> None:
    total = sum(item["price"] * item["quantity"] for item in items)
    print(f"Paid: {total:,.2f} USD")
```

### KISS - Keep It Simple, Stupid

#### ✅ CORRECT

```python
# Simple and readable
def is_even(n: int) -> bool:
    return n % 2 == 0


def get_average(numbers: list[float]) -> float:
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
```

#### ❌ INCORRECT

```python
# Over-engineered
def is_even(n: int) -> bool:
    # Using bitwise AND for... performance?
    return (n & 1) == 0


def get_average(numbers: list[float]) -> float:
    # Unnecessary complexity
    if len(numbers) == 0:
        return 0.0
    elif len(numbers) == 1:
        return numbers[0]
    else:
        total = 0.0
        count = 0
        for num in numbers:
            total += num
            count += 1
        return total / count
```

### YAGNI - You Aren't Gonna Need It

#### ✅ CORRECT

```python
# Implement what you need now
def send_email(to: str, subject: str, body: str) -> None:
    smtp.send(to, subject, body)
```

#### ❌ INCORRECT

```python
# Premature abstraction
class EmailSender:
    def __init__(self):
        self._providers = {}

    def register_provider(self, name: str, provider):
        self._providers[name] = provider

    def set_default_provider(self, name: str):
        pass

    def send_email(self, to: str, subject: str, body: str, provider: str = None):
        # Complex logic for multiple providers we don't need yet
        pass

# We only need one email sender for now!
```

## Descriptive Names

### ✅ CORRECT

```python
# Clear, descriptive names
def calculate_monthly_payment(
    principal: float,
    annual_interest_rate: float,
    loan_term_years: int,
) -> float:
    monthly_rate = annual_interest_rate / 12 / 100
    num_payments = loan_term_years * 12
    return principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / \
           ((1 + monthly_rate) ** num_payments - 1)


# Class names are nouns
class UserValidator:
    pass

class PaymentProcessor:
    pass

# Function names are verbs
def validate_user_input(user_data: dict) -> bool:
    pass

def process_payment(amount: float) -> bool:
    pass

# Boolean names are questions
def is_valid_email(email: str) -> bool:
    pass

def has_permission(user: User, resource: str) -> bool:
    pass
```

### ❌ INCORRECT

```python
# Cryptic abbreviations
def calc_mp(p: float, ir: float, lty: int) -> float:
    mr = ir / 12 / 100
    np = lty * 12
    return p * (mr * (1 + mr) ** np) / ((1 + mr) ** np - 1)


# Non-descriptive names
def do_stuff(x, y):
    pass

def process(data):
    pass
```

## Small Functions

### ✅ CORRECT

```python
# Each function does one thing
def calculate_discount(price: float, discount_percent: float) -> float:
    return price * (discount_percent / 100)


def calculate_tax(price: float, tax_rate: float) -> float:
    return price * (tax_rate / 100)


def calculate_final_price(base_price: float, discount: float, tax: float) -> float:
    discounted_price = base_price - calculate_discount(base_price, discount)
    return discounted_price + calculate_tax(discounted_price, tax)
```

### ❌ INCORRECT

```python
# One function doing too much
def calculate_final_price(base_price: float, discount: float, tax: float) -> float:
    discount_amount = base_price * (discount / 100)
    price_after_discount = base_price - discount_amount
    tax_amount = price_after_discount * (tax / 100)
    final_price = price_after_discount + tax_amount
    return final_price
```

## Avoid Deep Nesting

### ✅ CORRECT

```python
# Early returns reduce nesting
def process_order(order: Order) -> str:
    if not order.is_valid():
        return "Invalid order"

    if not has_inventory(order.items):
        return "Insufficient inventory"

    if not payment Authorized(order.payment_info):
        return "Payment declined"

    ship_order(order)
    return "Order processed"


# Guard clauses
def get_user_discount(user: User) -> float:
    if user is None:
        return 0.0

    if not user.is_active:
        return 0.0

    if user.tier == "gold":
        return 0.20

    if user.tier == "silver":
        return 0.10

    return 0.0
```

### ❌ INCORRECT

```python
# Deep nesting - hard to read
def process_order(order: Order) -> str:
    if order.is_valid():
        if has_inventory(order.items):
            if payment_authorized(order.payment_info):
                ship_order(order)
                return "Order processed"
            else:
                return "Payment declined"
        else:
            return "Insufficient inventory"
    else:
        return "Invalid order"
```

## Error Handling

### ✅ CORRECT

```python
# Custom exceptions
class ValidationError(ValueError):
    """Validation error."""
    pass


class NotFoundError(RuntimeError):
    """Resource not found error."""
    pass


# Raise specific exceptions
def get_user(user_id: int) -> User:
    if user_id <= 0:
        raise ValueError("user_id must be positive")

    user = database.find(user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")

    return user


# Handle specific exceptions
def process_order(order_id: int) -> str:
    try:
        order = get_order(order_id)
        return ship_order(order)
    except NotFoundError as e:
        logger.error(f"Order not found: {e}")
        return "Order not found"
    except ValidationError as e:
        logger.error(f"Invalid order: {e}")
        return "Invalid order data"
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return "Internal error"


# Context managers for resource cleanup
def process_file(path: Path) -> str:
    try:
        with path.open("r") as f:
            return f.read()
    except FileNotFoundError:
        raise NotFoundError(f"File not found: {path}")
    except PermissionError:
        raise RuntimeError(f"Permission denied: {path}")
```

### ❌ INCORRECT

```python
# Bare except - catches everything!
def process_order(order_id: int) -> str:
    try:
        order = get_order(order_id)
        return ship_order(order)
    except:
        return "Error"  # No logging, no info


# Catching Exception too broadly
def divide(a: int, b: int) -> float:
    try:
        return a / b
    except Exception:
        return 0.0  # Hides the actual problem!


# Not releasing resources properly
def process_file(path: Path) -> str:
    f = path.open("r")  # Never closed if exception!
    data = f.read()
    f.close()
    return data
```

## Immutability

### ✅ CORRECT

```python
# Use dataclass with frozen=True
@dataclass(frozen=True)
class Money:
    """Immutable money value object."""
    amount: float
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")


# Return new instances instead of modifying
@dataclass
class ShoppingCart:
    items: list[CartItem]

    def add_item(self, item: CartItem) -> "ShoppingCart":
        """Return new cart with item added."""
        new_items = self.items.copy()
        new_items.append(item)
        return ShoppingCart(new_items)

    def remove_item(self, item_id: int) -> "ShoppingCart":
        """Return new cart with item removed."""
        new_items = [i for i in self.items if i.id != item_id]
        return ShoppingCart(new_items)


# Use tuple for immutable sequences
def get_available_symbols() -> tuple[str, ...]:
    return ("AAPL", "GOOGL", "MSFT")
```

### ❌ INCORRECT

```python
# Mutable dataclass - unexpected mutations
@dataclass
class Money:
    amount: float
    currency: str


price = Money(100.0, "USD")
price.amount = 50.0  # Mutation - hard to track!


# Modifying arguments
def add_tax(price: Money, tax_rate: float) -> Money:
    price.amount *= (1 + tax_rate)  # Modifies original!
    return price


original = Money(100.0, "USD")
add_tax(original, 0.10)
print(original.amount)  # 110.0 - unexpected mutation!
```

## Composition Over Inheritance

### ✅ CORRECT

```python
# Composition - flexible and clear
class EmailValidator:
    def validate(self, email: str) -> bool:
        return "@" in email


class PasswordValidator:
    def validate(self, password: str) -> bool:
        return len(password) >= 8


class UserRegistrationService:
    """Composed of multiple validators."""

    def __init__(self) -> None:
        self._email_validator = EmailValidator()
        self._password_validator = PasswordValidator()

    def register(self, email: str, password: str) -> None:
        if not self._email_validator.validate(email):
            raise ValueError("Invalid email")
        if not self._password_validator.validate(password):
            raise ValueError("Invalid password")
        # Register user...
```

### ❌ INCORRECT

```python
# Deep inheritance - inflexible
class BaseEntity:
    pass


class ValidatedEntity(BaseEntity):
    def validate_email(self, email: str) -> bool:
        return "@" in email


class User(ValidatedEntity):
    def __init__(self, email: str, password: str):
        if not self.validate_email(email):
            raise ValueError("Invalid email")
        # What if we need different validation rules?
```

## Dependency Direction

### ✅ CORRECT - Dependencies point inward

```
Presentation → Application → Domain ← Infrastructure
```

```python
# Domain knows nothing about other layers
@dataclass
class Order:
    id: int
    items: list[OrderItem]
    status: str

    def calculate_total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)


# Infrastructure depends on Domain
class OrderRepository:
    def save(self, order: Order) -> None:
        # Infrastructure implements Domain interface
        pass


# Application orchestrates Domain and Infrastructure
class OrderService:
    def __init__(self, repo: OrderRepository):
        self._repo = repo

    def place_order(self, order: Order) -> None:
        order.validate()
        self._repo.save(order)
```

### ❌ INCORRECT - Domain depends on infrastructure

```python
# Domain depending on infrastructure - tight coupling
@dataclass
class Order:
    id: int
    items: list[OrderItem]

    def save(self) -> None:
        # Domain shouldn't know about database!
        Database.execute(f"INSERT INTO orders ...")
```

## Architecture Checklist

- [ ] Dependencies point toward domain (inward)
- [ ] Domain has no framework dependencies
- [ ] Each layer has a single responsibility
- [ ] Business logic is in domain/application
- [ ] External concerns in infrastructure
- [ ] Interface details in presentation
- [ ] Functions are small (< 20 lines)
- [ ] Names are descriptive and clear
- [ ] No code duplication
- [ ] Deep nesting avoided (early returns)
- [ ] Specific exceptions raised and caught
- [ ] Resources managed with context managers
- [ ] Value objects are immutable
- [ ] Composition preferred over inheritance
