# Type Safety Pattern - AlgoTrading System

## Pattern Overview
**Name**: Comprehensive Type Safety  
**Type**: Code Quality Pattern  
**Domain**: TypeScript-like Type Safety in Python  
**Implementation**: Python 3.11+ + Pydantic + mypy + Type Hints  

## Problem Statement
Python's dynamic typing can lead to runtime errors, making it difficult to catch type-related bugs early in development. Large codebases need strong type safety to maintain code quality and prevent production issues.

## Solution
Implement comprehensive type safety using Python's type hints, Pydantic for runtime validation, and mypy for static type checking to achieve TypeScript-like type safety.

## Implementation

### 1. Type Definitions
```python
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from decimal import Decimal

# Enum Types
class UserRole(str, Enum):
    ADMIN = "admin"
    STANDARD = "standard"
    FINANCIAL = "financial"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"

# Base Types
class BaseEntity(BaseModel):
    """Base entity with common fields"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# User Types
class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: UserRole
    is_active: bool = True

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, max_length=128)

class UserUpdate(BaseModel):
    """User update model"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase, BaseEntity):
    """User response model"""
    pass

class UserInDB(UserBase, BaseEntity):
    """User database model"""
    password_hash: str
    last_login: Optional[datetime] = None

# Product Types
class ProductBase(BaseModel):
    """Base product model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(..., ge=0)
    category: ProductCategory
    is_active: bool = True

class ProductCreate(ProductBase):
    """Product creation model"""
    pass

class ProductUpdate(BaseModel):
    """Product update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[ProductCategory] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase, BaseEntity):
    """Product response model"""
    pass

# Order Types
class OrderItemBase(BaseModel):
    """Base order item model"""
    product_id: int
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0, decimal_places=2)

class OrderItemCreate(OrderItemBase):
    """Order item creation model"""
    pass

class OrderItemResponse(OrderItemBase, BaseEntity):
    """Order item response model"""
    order_id: int

class OrderBase(BaseModel):
    """Base order model"""
    customer_id: int
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = Field(None, max_length=500)

class OrderCreate(OrderBase):
    """Order creation model"""
    items: List[OrderItemCreate] = Field(..., min_items=1)

class OrderUpdate(BaseModel):
    """Order update model"""
    status: Optional[OrderStatus] = None
    notes: Optional[str] = Field(None, max_length=500)

class OrderResponse(OrderBase, BaseEntity):
    """Order response model"""
    total: Decimal
    items: List[OrderItemResponse]

# Pagination Types
class PaginationParams(BaseModel):
    """Pagination parameters"""
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool

# API Response Types
class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    error: bool = True
    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
```

### 2. Type Guards
```python
from typing import TypeGuard, Any
from your_app.models.user import UserInDB, UserRole
from your_app.models.product import ProductInDB
from your_app.models.order import OrderInDB, OrderStatus

def is_admin_user(user: UserInDB) -> TypeGuard[UserInDB]:
    """Type guard to check if user is admin"""
    return user.role == UserRole.ADMIN

def is_active_product(product: ProductInDB) -> TypeGuard[ProductInDB]:
    """Type guard to check if product is active"""
    return product.is_active and product.stock > 0

def is_completed_order(order: OrderInDB) -> TypeGuard[OrderInDB]:
    """Type guard to check if order is completed"""
    return order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]

def is_valid_email(email: str) -> TypeGuard[str]:
    """Type guard to validate email format"""
    import re
    pattern = r'^[^@]+@[^@]+\.[^@]+$'
    return bool(re.match(pattern, email))

def is_positive_decimal(value: Any) -> TypeGuard[Decimal]:
    """Type guard to check if value is positive decimal"""
    return isinstance(value, Decimal) and value > 0
```

### 3. Repository with Type Safety
```python
from typing import List, Optional, TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from your_app.models.base import BaseEntity
from your_app.schemas.base import PaginationParams, PaginatedResponse

T = TypeVar('T', bound=BaseEntity)

class BaseRepository(Generic[T]):
    """Base repository with type safety"""
    
    def __init__(self, db: Session, model_class: type[T]):
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID with type safety"""
        return self.db.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination"""
        return self.db.query(self.model_class).offset(offset).limit(limit).all()
    
    def create(self, entity_data: dict) -> T:
        """Create new entity with type safety"""
        entity = self.model_class(**entity_data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update(self, id: int, update_data: dict) -> Optional[T]:
        """Update entity with type safety"""
        entity = self.get_by_id(id)
        if entity:
            for key, value in update_data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self.db.commit()
            self.db.refresh(entity)
        return entity
    
    def delete(self, id: int) -> bool:
        """Delete entity with type safety"""
        entity = self.get_by_id(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False

class UserRepository(BaseRepository[UserInDB]):
    """User repository with type safety"""
    
    def __init__(self, db: Session):
        super().__init__(db, UserInDB)
    
    def get_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email with type safety"""
        return self.db.query(UserInDB).filter(UserInDB.email == email).first()
    
    def get_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username with type safety"""
        return self.db.query(UserInDB).filter(UserInDB.username == username).first()
    
    def get_by_role(self, role: UserRole) -> List[UserInDB]:
        """Get users by role with type safety"""
        return self.db.query(UserInDB).filter(UserInDB.role == role).all()

class ProductRepository(BaseRepository[ProductInDB]):
    """Product repository with type safety"""
    
    def __init__(self, db: Session):
        super().__init__(db, ProductInDB)
    
    def get_by_category(self, category: ProductCategory) -> List[ProductInDB]:
        """Get products by category with type safety"""
        return self.db.query(ProductInDB).filter(ProductInDB.category == category).all()
    
    def get_active_products(self) -> List[ProductInDB]:
        """Get active products with type safety"""
        return self.db.query(ProductInDB).filter(ProductInDB.is_active == True).all()
    
    def update_stock(self, id: int, quantity: int) -> Optional[ProductInDB]:
        """Update product stock with type safety"""
        product = self.get_by_id(id)
        if product:
            product.stock = max(0, product.stock + quantity)
            self.db.commit()
            self.db.refresh(product)
        return product
```

### 4. Service Layer with Type Safety
```python
from typing import List, Optional
from sqlalchemy.orm import Session
from your_app.repositories.user import UserRepository
from your_app.repositories.product import ProductRepository
from your_app.schemas.user import UserCreate, UserUpdate, UserResponse
from your_app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from your_app.schemas.pagination import PaginationParams, PaginatedResponse
from your_app.utils.type_guards import is_admin_user, is_active_product
from your_app.exceptions import ValidationError, ResourceNotFoundError

class UserService:
    """User service with comprehensive type safety"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create user with type safety and validation"""
        # Check if user already exists
        if self.user_repo.get_by_email(user_data.email):
            raise ValidationError("User with this email already exists")
        
        if self.user_repo.get_by_username(user_data.username):
            raise ValidationError("User with this username already exists")
        
        # Create user
        user_dict = user_data.dict()
        password_hash = self._hash_password(user_dict.pop("password"))
        user_dict["password_hash"] = password_hash
        
        user = self.user_repo.create(user_dict)
        return UserResponse.from_orm(user)
    
    def get_user(self, user_id: int) -> UserResponse:
        """Get user by ID with type safety"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        
        return UserResponse.from_orm(user)
    
    def update_user(self, user_id: int, update_data: UserUpdate) -> UserResponse:
        """Update user with type safety"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        
        # Validate update data
        update_dict = update_data.dict(exclude_unset=True)
        if "email" in update_dict:
            existing_user = self.user_repo.get_by_email(update_dict["email"])
            if existing_user and existing_user.id != user_id:
                raise ValidationError("User with this email already exists")
        
        updated_user = self.user_repo.update(user_id, update_dict)
        return UserResponse.from_orm(updated_user)
    
    def get_users_paginated(self, params: PaginationParams) -> PaginatedResponse:
        """Get paginated users with type safety"""
        users = self.user_repo.get_all(limit=params.limit, offset=params.offset)
        total = self.db.query(UserInDB).count()
        
        user_responses = [UserResponse.from_orm(user) for user in users]
        
        return PaginatedResponse(
            items=user_responses,
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_next=params.offset + params.limit < total,
            has_prev=params.offset > 0
        )
    
    def _hash_password(self, password: str) -> str:
        """Hash password with type safety"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)

class ProductService:
    """Product service with comprehensive type safety"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)
    
    def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Create product with type safety"""
        product_dict = product_data.dict()
        product = self.product_repo.create(product_dict)
        return ProductResponse.from_orm(product)
    
    def get_product(self, product_id: int) -> ProductResponse:
        """Get product by ID with type safety"""
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ResourceNotFoundError("Product", str(product_id))
        
        return ProductResponse.from_orm(product)
    
    def update_product(self, product_id: int, update_data: ProductUpdate) -> ProductResponse:
        """Update product with type safety"""
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ResourceNotFoundError("Product", str(product_id))
        
        update_dict = update_data.dict(exclude_unset=True)
        updated_product = self.product_repo.update(product_id, update_dict)
        return ProductResponse.from_orm(updated_product)
    
    def get_active_products(self) -> List[ProductResponse]:
        """Get active products with type safety"""
        products = self.product_repo.get_active_products()
        return [ProductResponse.from_orm(product) for product in products]
    
    def update_stock(self, product_id: int, quantity: int) -> ProductResponse:
        """Update product stock with type safety"""
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ResourceNotFoundError("Product", str(product_id))
        
        if not is_active_product(product):
            raise ValidationError("Cannot update stock for inactive product")
        
        updated_product = self.product_repo.update_stock(product_id, quantity)
        return ProductResponse.from_orm(updated_product)
```

### 5. API Endpoints with Type Safety
```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from your_app.database import get_db
from your_app.schemas.user import UserCreate, UserUpdate, UserResponse
from your_app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from your_app.schemas.pagination import PaginationParams, PaginatedResponse
from your_app.services.user import UserService
from your_app.services.product import ProductService
from your_app.auth import get_current_user, require_admin

router = APIRouter()

# User endpoints
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(require_admin)
) -> UserResponse:
    """Create new user with type safety"""
    user_service = UserService(db)
    return user_service.create_user(user_data)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
) -> UserResponse:
    """Get user by ID with type safety"""
    user_service = UserService(db)
    return user_service.get_user(user_id)

@router.get("/users", response_model=PaginatedResponse)
async def get_users(
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(require_admin)
) -> PaginatedResponse:
    """Get paginated users with type safety"""
    user_service = UserService(db)
    return user_service.get_users_paginated(params)

# Product endpoints
@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(require_admin)
) -> ProductResponse:
    """Create new product with type safety"""
    product_service = ProductService(db)
    return product_service.create_product(product_data)

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
) -> ProductResponse:
    """Get product by ID with type safety"""
    product_service = ProductService(db)
    return product_service.get_product(product_id)

@router.get("/products", response_model=List[ProductResponse])
async def get_active_products(
    db: Session = Depends(get_db)
) -> List[ProductResponse]:
    """Get active products with type safety"""
    product_service = ProductService(db)
    return product_service.get_active_products()
```

## Benefits

### 1. Early Error Detection
- **Static Type Checking**: Catch type errors at development time
- **Runtime Validation**: Pydantic validates data at runtime
- **IDE Support**: Better autocomplete and error detection
- **Refactoring Safety**: Safe refactoring with type information

### 2. Code Quality
- **Self-Documenting Code**: Types serve as documentation
- **Reduced Bugs**: Fewer runtime type-related errors
- **Better Maintainability**: Easier to understand and modify code
- **Consistent Interfaces**: Standardized data structures

### 3. Developer Experience
- **Better IDE Support**: Enhanced autocomplete and error detection
- **Faster Development**: Reduced debugging time
- **Confident Refactoring**: Type safety enables safe changes
- **Clear Contracts**: Explicit interfaces between components

### 4. Production Reliability
- **Fewer Runtime Errors**: Type safety prevents common errors
- **Better Error Messages**: Clear error messages from Pydantic
- **Data Validation**: Automatic validation of incoming data
- **Consistent Behavior**: Predictable data handling

## Best Practices

### 1. Type Definitions
- **Use Specific Types**: Avoid `Any` and `object` types
- **Define Enums**: Use enums for constrained string values
- **Create Base Types**: Share common type definitions
- **Use Generics**: Create reusable generic types

### 2. Validation
- **Pydantic Models**: Use Pydantic for data validation
- **Custom Validators**: Implement business logic validation
- **Type Guards**: Use type guards for runtime type checking
- **Error Handling**: Provide clear validation error messages

### 3. Testing
- **Type-Check Tests**: Run mypy on test files
- **Test Type Guards**: Verify type guard functions
- **Mock with Types**: Use typed mocks in tests
- **Validate Responses**: Test API response types

### 4. Documentation
- **Type Annotations**: Document all function parameters and returns
- **Pydantic Docs**: Use Pydantic's automatic documentation
- **Examples**: Provide type usage examples
- **Migration Guide**: Document type system changes

## Testing

### 1. Type Checking
```python
# mypy.ini configuration
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
```

### 2. Unit Tests
```python
import pytest
from your_app.services.user import UserService
from your_app.schemas.user import UserCreate, UserRole
from your_app.exceptions import ValidationError

def test_create_user_type_safety():
    """Test user creation with type safety"""
    # Arrange
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        role=UserRole.STANDARD,
        password="securepassword123"
    )
    
    # Act & Assert
    with pytest.raises(ValidationError):
        # This should fail due to type validation
        invalid_data = UserCreate(
            username="",  # Invalid: too short
            email="invalid-email",  # Invalid: not an email
            role="invalid-role",  # Invalid: not a valid enum
            password="123"  # Invalid: too short
        )
```

### 3. Integration Tests
```python
def test_api_endpoint_type_safety():
    """Test API endpoints with type safety"""
    response = client.post("/api/users", json={
        "username": "testuser",
        "email": "test@example.com",
        "role": "standard",
        "password": "securepassword123"
    })
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response has correct type structure
    assert "id" in data
    assert "username" in data
    assert "email" in data
    assert "role" in data
    assert "created_at" in data
    assert "updated_at" in data
```

## Monitoring

### 1. Type Safety Metrics
- **Type Coverage**: Percentage of code with type annotations
- **Type Errors**: Number of mypy errors in codebase
- **Runtime Type Errors**: Pydantic validation failures
- **Type Safety Score**: Overall type safety assessment

### 2. Quality Metrics
- **Code Quality**: Impact of type safety on code quality
- **Bug Reduction**: Reduction in type-related bugs
- **Development Speed**: Impact on development velocity
- **Maintenance Cost**: Reduction in maintenance effort

### 3. Performance Impact
- **Runtime Overhead**: Pydantic validation performance
- **Memory Usage**: Impact of type annotations on memory
- **Startup Time**: Impact on application startup time
- **Overall Performance**: System performance with type safety
