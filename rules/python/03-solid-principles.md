# SOLID Principles

SOLID principles for writing maintainable, scalable object-oriented code in Python.

## S - Single Responsibility Principle (SRP)

A class should have one reason to change. It should have one job.

### ✅ CORRECT

```python
# Separate concerns into different classes
class UserValidator:
    """Validates user data."""

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return "@" in email

    def validate_age(self, age: int) -> bool:
        """Validate age is reasonable."""
        return 0 < age < 150


class UserRepository:
    """Handles database operations for users."""

    def save(self, user: "User") -> None:
        """Save user to database."""
        database.execute("INSERT INTO users ...")

    def find_by_id(self, user_id: int) -> "User | None":
        """Find user by ID."""
        return database.query(f"SELECT * FROM users WHERE id = {user_id}")


class EmailService:
    """Handles email sending."""

    def send_welcome(self, user: "User") -> None:
        """Send welcome email."""
        smtp.send(user.email, "Welcome!")


# Usage - each class has a single responsibility
def register_user(email: str, age: int) -> None:
    validator = UserValidator()
    repo = UserRepository()
    email_service = EmailService()

    if not validator.validate_email(email):
        raise ValueError("Invalid email")
    if not validator.validate_age(age):
        raise ValueError("Invalid age")

    user = User(email=email, age=age)
    repo.save(user)
    email_service.send_welcome(user)
```

### ❌ INCORRECT

```python
# One class doing everything - violates SRP
class UserManager:
    """Handles validation, database, and email."""

    def validate_email(self, email: str) -> bool:
        return "@" in email

    def validate_age(self, age: int) -> bool:
        return 0 < age < 150

    def save_to_db(self, user: "User") -> None:
        database.execute("INSERT INTO users ...")

    def send_email(self, user: "User") -> None:
        smtp.send(user.email, "Welcome!")

# Problem: class changes for validation logic, DB changes, email service changes
```

## O - Open/Closed Principle (OCP)

Software entities should be open for extension but closed for modification.

### ✅ CORRECT

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Define interface (Protocol is more Pythonic)
class PaymentProcessor(Protocol):
    """Payment processor interface."""

    def process_payment(self, amount: float) -> bool:
        """Process payment and return success status."""
        ...

# Implementations can be added without modifying existing code
class CreditCardProcessor:
    """Credit card payment processor."""

    def process_payment(self, amount: float) -> bool:
        print(f"Processing credit card payment: ${amount}")
        return True


class PayPalProcessor:
    """PayPal payment processor."""

    def process_payment(self, amount: float) -> bool:
        print(f"Processing PayPal payment: ${amount}")
        return True


class CryptoProcessor:
    """Crypto payment processor - added later without changing existing code."""

    def process_payment(self, amount: float) -> bool:
        print(f"Processing crypto payment: ${amount}")
        return True


# Payment service uses the interface - closed for modification
class PaymentService:
    """Service for processing payments."""

    def __init__(self, processor: PaymentProcessor) -> None:
        self.processor = processor

    def make_payment(self, amount: float) -> bool:
        return self.processor.process_payment(amount)


# Usage - can add new processors without modifying PaymentService
service = PaymentService(CryptoProcessor())  # New processor!
service.make_payment(100.0)
```

### ❌ INCORRECT

```python
# Requires modification for new payment types
class PaymentService:
    """Payment service that must be modified for new types."""

    def make_payment(self, amount: float, payment_type: str) -> bool:
        if payment_type == "credit_card":
            print(f"Processing credit card: ${amount}")
        elif payment_type == "paypal":
            print(f"Processing PayPal: ${amount}")
        # Must modify this class to add crypto!
        elif payment_type == "crypto":
            print(f"Processing crypto: ${amount}")
        else:
            raise ValueError(f"Unknown payment type: {payment_type}")
        return True
```

## L - Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types without breaking the program.

### ✅ CORRECT

```python
from abc import ABC, abstractmethod

class Bird(ABC):
    """Base bird class."""

    @abstractmethod
    def fly(self) -> None:
        """Fly behavior."""
        pass


class Sparrow(Bird):
    """Sparrow can fly."""

    def fly(self) -> None:
        print("Sparrow flying")


class Penguin(Bird):
    """Penguin cannot fly - design problem fixed."""

    def swim(self) -> None:
        """Penguin swims instead of flying."""
        print("Penguin swimming")

# Better design - use composition or separate behaviors
class FlyingBird(ABC):
    @abstractmethod
    def fly(self) -> None:
        pass


class SwimmingBird(ABC):
    @abstractmethod
    def swim(self) -> None:
        pass


class Eagle(FlyingBird):
    def fly(self) -> None:
        print("Eagle flying")


class Penguin(SwimmingBird):
    def swim(self) -> None:
        print("Penguin swimming")


# Rectangle example - proper inheritance
class Rectangle:
    """Base rectangle."""

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def set_width(self, width: float) -> None:
        self.width = width

    def set_height(self, height: float) -> None:
        self.height = height

    def area(self) -> float:
        return self.width * self.height


class Square(Rectangle):
    """Square - preserves rectangle behavior."""

    def __init__(self, side: float) -> None:
        super().__init__(side, side)

    def set_width(self, width: float) -> None:
        """Square maintains equal sides."""
        self.width = width
        self.height = width

    def set_height(self, height: float) -> None:
        """Square maintains equal sides."""
        self.width = height
        self.height = height


# Substitutable - works correctly
def process_rectangle(rect: Rectangle) -> None:
    rect.set_width(5)
    rect.set_height(4)
    print(f"Area: {rect.area()}")  # Square: 16 (4x4), Rectangle: 20 (5x4)
```

### ❌ INCORRECT

```python
# LSP violation - Square breaks Rectangle behavior
class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def set_width(self, width: float) -> None:
        self.width = width

    def set_height(self, height: float) -> None:
        self.height = height


class Square(Rectangle):
    def __init__(self, side: float) -> None:
        super().__init__(side, side)

    # Not overriding set_width/set_height - breaks behavior!
    # Square with width=5, height=4 is invalid!

# This breaks when Square is substituted for Rectangle
def process_rectangle(rect: Rectangle) -> None:
    rect.set_width(5)
    rect.set_height(4)
    assert rect.width == 5  # Fails for Square!
```

## I - Interface Segregation Principle (ISP)

Clients should not depend on interfaces they don't use. Split large interfaces.

### ✅ CORRECT

```python
from typing import Protocol

# Small, focused interfaces
class Printable(Protocol):
    """Interface for printing."""

    def print(self) -> None:
        ...

class Scannable(Protocol):
    """Interface for scanning."""

    def scan(self) -> None:
        ...

class Faxable(Protocol):
    """Interface for faxing."""

    def fax(self, str) -> None:
        ...

# Implementations only use what they need
class Printer:
    """Simple printer - only prints."""

    def print(self) -> None:
        print("Printing document")


class PrinterScanner:
    """Printer and scanner - no fax needed."""

    def print(self) -> None:
        print("Printing document")

    def scan(self) -> None:
        print("Scanning document")


class MultiFunctionMachine:
    """Full featured machine."""

    def print(self) -> None:
        print("Printing")

    def scan(self) -> None:
        print("Scanning")

    def fax(self, content: str) -> None:
        print(f"Faxing: {content}")


# Functions depend only on what they need
def print_document(printer: Printable) -> None:
    printer.print()


def scan_document(scanner: Scannable) -> None:
    scanner.scan()
```

### ❌ INCORRECT

```python
# Fat interface - forces implementation of unused methods
class OfficeMachine(ABC):
    """Too much in one interface."""

    @abstractmethod
    def print(self) -> None:
        pass

    @abstractmethod
    def scan(self) -> None:
        pass

    @abstractmethod
    def fax(self, content: str) -> None:
        pass


class SimplePrinter(OfficeMachine):
    """Forced to implement methods it doesn't use!"""

    def print(self) -> None:
        print("Printing")

    def scan(self) -> None:
        raise NotImplementedError("Cannot scan")

    def fax(self, content: str) -> None:
        raise NotImplementedError("Cannot fax")
```

## D - Dependency Inversion Principle (DIP)

High-level modules should not depend on low-level modules. Both should depend on abstractions.

### ✅ CORRECT

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Abstraction (dependency)
class DataStorage(Protocol):
    """Storage interface."""

    def save(self, key: str, value: str) -> None:
        ...

    def load(self, key: str) -> str | None:
        ...


# Low-level modules implement the abstraction
class FileStorage:
    """File-based storage."""

    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)

    def save(self, key: str, value: str) -> None:
        (self.base_path / key).write_text(value)

    def load(self, key: str) -> str | None:
        path = self.base_path / key
        return path.read_text() if path.exists() else None


class DatabaseStorage:
    """Database storage."""

    def __init__(self, connection_string: str) -> None:
        self.conn = connect(connection_string)

    def save(self, key: str, value: str) -> None:
        self.conn.execute(f"INSERT INTO store VALUES ('{key}', '{value}')")

    def load(self, key: str) -> str | None:
        return self.conn.query(f"SELECT value FROM store WHERE key = '{key}'")


class CloudStorage:
    """Cloud storage (S3, etc)."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def save(self, key: str, value: str) -> None:
        s3.upload(self.bucket, key, value)

    def load(self, key: str) -> str | None:
        return s3.download(self.bucket, key)


# High-level module depends on abstraction
class UserService:
    """High-level business logic."""

    def __init__(self, storage: DataStorage) -> None:
        # Dependency injection - depends on abstraction
        self.storage = storage

    def save_user(self, user_id: str, data: str) -> None:
        """Save user - storage implementation can change."""
        self.storage.save(f"user:{user_id}", data)

    def get_user(self, user_id: str) -> str | None:
        """Get user - storage implementation can change."""
        return self.storage.load(f"user:{user_id}")


# Can swap implementations without changing high-level code
file_service = UserService(FileStorage("/data"))
db_service = UserService(DatabaseStorage("postgres://..."))
cloud_service = UserService(CloudStorage("my-bucket"))
```

### ❌ INCORRECT

```python
# High-level module directly depends on low-level implementation
class UserService:
    """Directly coupled to FileStorage."""

    def __init__(self, file_path: str) -> None:
        # Hard dependency - cannot change storage!
        self.storage = FileStorage(file_path)

    def save_user(self, user_id: str, data: str) -> None:
        self.storage.save(f"user:{user_id}", data)

# To change storage, must modify UserService - violates DIP
```

## Practical Example: Trading System

```python
from typing import Protocol, Callable
from abc import ABC, abstractmethod

# Single Responsibility
class DataFetcher:
    """Responsible only for fetching data."""

    def fetch(self, symbol: str) -> dict[str, float]:
        return api.get_market_data(symbol)


class Strategy:
    """Responsible only for strategy logic."""

    def generate_signal(self, data: dict[str, float]) -> str:
        return "BUY" if data["price"] < 100 else "SELL"


class OrderExecutor:
    """Responsible only for executing orders."""

    def execute(self, symbol: str, action: str, quantity: int) -> None:
        api.place_order(symbol, action, quantity)


# Open/Closed - extensible strategies
class TradingStrategy(Protocol):
    def evaluate(self, data: dict[str, float]) -> str:
        ...


class MovingAverageStrategy:
    def evaluate(self, data: dict[str, float]) -> str:
        return "BUY" if data["ma_short"] > data["ma_long"] else "SELL"


class MeanReversionStrategy:
    def evaluate(self, data: dict[str, float]) -> str:
        return "BUY" if data["price"] < data["mean"] - 2 * data["std"] else "SELL"


# Liskov Substitution - all strategies are substitutable
class TradingEngine:
    def __init__(self, strategy: TradingStrategy) -> None:
        self.strategy = strategy

    def trade(self, symbol: str) -> None:
        data = DataFetcher().fetch(symbol)
        signal = self.strategy.evaluate(data)
        OrderExecutor().execute(symbol, signal, 100)


# Interface Segregation - focused interfaces
class Notifiable(Protocol):
    def send_notification(self, message: str) -> None:
        ...


class Loggable(Protocol):
    def log(self, message: str) -> None:
        ...


class EmailNotifier:
    def send_notification(self, message: str) -> None:
        send_email(message)


class FileLogger:
    def log(self, message: str) -> None:
        write_log(message)


# Dependency Inversion - depends on abstractions
class TradingService:
    def __init__(
        self,
        strategy: TradingStrategy,
        notifier: Notifiable,
        logger: Loggable,
    ) -> None:
        self.strategy = strategy
        self.notifier = notifier
        self.logger = logger

    def execute_trade(self, symbol: str) -> None:
        self.logger.log(f"Executing trade for {symbol}")
        # ... trading logic
        self.notifier.send_notification(f"Trade executed for {symbol}")
```

## Key Takeaways

1. **SRP**: One class, one responsibility. Split when class has multiple reasons to change.
2. **OCP**: Open for extension, closed for modification. Use interfaces/protocols.
3. **LSP**: Substitutable subtypes. Don't break parent class behavior.
4. **ISP**: Small interfaces. Don't force clients to implement what they don't use.
5. **DIP**: Depend on abstractions. Use dependency injection for flexibility.
