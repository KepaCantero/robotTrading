# Pagination Pattern - AlgoTrading System

## Pattern Overview
**Name**: Cursor-Based Pagination  
**Type**: Data Access Pattern  
**Domain**: API Design & Performance  
**Implementation**: FastAPI + SQLAlchemy + PostgreSQL  

## Problem Statement
Large datasets require efficient pagination to maintain performance and user experience. Traditional offset-based pagination becomes inefficient with large datasets and can cause performance degradation.

## Solution
Implement cursor-based pagination using database cursors and unique identifiers for consistent, efficient data retrieval.

## Implementation

### 1. Database Model
```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. Pydantic Schemas
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PaginationParams(BaseModel):
    limit: int = Field(50, ge=1, le=1000)
    cursor: Optional[str] = None
    direction: str = Field("next", regex="^(next|prev)$")

class PaginatedResponse(BaseModel):
    items: List[ProductResponse]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_next: bool
    has_prev: bool
    total_count: Optional[int] = None
```

### 3. Repository Implementation
```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import Optional, Tuple, List
import base64
import json
from datetime import datetime

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_paginated_products(
        self, 
        limit: int = 50, 
        cursor: Optional[str] = None,
        direction: str = "next"
    ) -> Tuple[List[Product], bool, bool, Optional[str], Optional[str]]:
        """
        Get paginated products using cursor-based pagination
        
        Returns:
            Tuple of (items, has_next, has_prev, next_cursor, prev_cursor)
        """
        query = self.db.query(Product)
        
        # Apply cursor filter
        if cursor:
            cursor_data = self._decode_cursor(cursor)
            if direction == "next":
                query = query.filter(Product.id > cursor_data["id"])
                query = query.order_by(Product.id.asc())
            else:  # prev
                query = query.filter(Product.id < cursor_data["id"])
                query = query.order_by(Product.id.desc())
        else:
            query = query.order_by(Product.id.asc())
        
        # Get one extra item to check if there are more
        items = query.limit(limit + 1).all()
        
        has_next = len(items) > limit
        has_prev = cursor is not None
        
        if has_next:
            items = items[:-1]  # Remove the extra item
        
        # Generate cursors
        next_cursor = None
        prev_cursor = None
        
        if items:
            if has_next:
                next_cursor = self._encode_cursor(items[-1].id, items[-1].created_at)
            if has_prev:
                prev_cursor = self._encode_cursor(items[0].id, items[0].created_at)
        
        return items, has_next, has_prev, next_cursor, prev_cursor
    
    def _encode_cursor(self, id: int, created_at: datetime) -> str:
        """Encode cursor data to base64 string"""
        cursor_data = {
            "id": id,
            "created_at": created_at.isoformat()
        }
        cursor_json = json.dumps(cursor_data)
        return base64.b64encode(cursor_json.encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> dict:
        """Decode base64 cursor string to data"""
        cursor_json = base64.b64decode(cursor.encode()).decode()
        cursor_data = json.loads(cursor_json)
        cursor_data["created_at"] = datetime.fromisoformat(cursor_data["created_at"])
        return cursor_data
```

### 4. Service Layer
```python
from typing import Optional
from fastapi import HTTPException

class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
    
    def get_products_paginated(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        direction: str = "next"
    ) -> PaginatedResponse:
        """Get paginated products with business logic"""
        
        # Validate pagination parameters
        if limit > 1000:
            raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
        
        # Get paginated data
        items, has_next, has_prev, next_cursor, prev_cursor = self.product_repo.get_paginated_products(
            limit=limit,
            cursor=cursor,
            direction=direction
        )
        
        # Convert to response models
        product_responses = [ProductResponse.from_orm(item) for item in items]
        
        return PaginatedResponse(
            items=product_responses,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            total_count=None  # Optional: can be expensive to calculate
        )
```

### 5. API Endpoint
```python
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=PaginatedResponse)
async def get_products(
    limit: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    direction: str = Query("next", regex="^(next|prev)$", description="Pagination direction"),
    product_service: ProductService = Depends(get_product_service)
):
    """
    Get paginated products using cursor-based pagination
    
    - **limit**: Number of items per page (1-1000)
    - **cursor**: Pagination cursor for consistent results
    - **direction**: Pagination direction (next/prev)
    """
    return await product_service.get_products_paginated(
        limit=limit,
        cursor=cursor,
        direction=direction
    )
```

## Benefits

### 1. Performance
- **Consistent Performance**: O(log n) complexity regardless of dataset size
- **No Offset Issues**: Avoids performance degradation with large offsets
- **Efficient Queries**: Uses indexed columns for cursor comparison
- **Reduced Memory Usage**: Only loads requested items

### 2. Consistency
- **Stable Results**: Cursors remain valid during data changes
- **No Duplicates**: Prevents duplicate items in paginated results
- **No Missing Items**: Ensures all items are accessible through pagination
- **Bidirectional**: Supports both forward and backward pagination

### 3. User Experience
- **Fast Loading**: Consistent response times
- **Smooth Navigation**: Seamless forward/backward navigation
- **Large Datasets**: Handles millions of records efficiently
- **Real-time Updates**: Cursors adapt to data changes

## Usage Examples

### 1. First Page Request
```bash
GET /api/products?limit=50
```

### 2. Next Page Request
```bash
GET /api/products?limit=50&cursor=eyJpZCI6NTAsImNyZWF0ZWRfYXQiOiIyMDI1LTAxLTEwVDEwOjAwOjAwIn0=
```

### 3. Previous Page Request
```bash
GET /api/products?limit=50&cursor=eyJpZCI6MTAsImNyZWF0ZWRfYXQiOiIyMDI1LTAxLTEwVDEwOjAwOjAwIn0=&direction=prev
```

## Best Practices

### 1. Cursor Design
- **Use Unique Identifiers**: Primary keys or unique indexes
- **Include Timestamps**: For consistent ordering
- **Base64 Encoding**: For URL-safe cursor strings
- **JSON Structure**: For complex cursor data

### 2. Performance Optimization
- **Indexed Columns**: Use indexed columns for cursor comparison
- **Limit Validation**: Enforce reasonable limits (1-1000)
- **Query Optimization**: Use EXPLAIN to analyze query performance
- **Connection Pooling**: Efficient database connection management

### 3. Error Handling
- **Invalid Cursors**: Handle malformed cursor strings gracefully
- **Empty Results**: Return appropriate empty response structure
- **Database Errors**: Implement proper error handling and logging
- **Rate Limiting**: Prevent abuse of pagination endpoints

## Testing

### 1. Unit Tests
```python
import pytest
from unittest.mock import Mock
from your_app.services.product_service import ProductService
from your_app.repositories.product_repository import ProductRepository

def test_get_products_paginated_first_page():
    # Arrange
    mock_repo = Mock(spec=ProductRepository)
    mock_repo.get_paginated_products.return_value = ([], False, False, None, None)
    service = ProductService(mock_repo)
    
    # Act
    result = service.get_products_paginated(limit=50)
    
    # Assert
    assert result.items == []
    assert result.has_next is False
    assert result.has_prev is False
    mock_repo.get_paginated_products.assert_called_once_with(limit=50, cursor=None, direction="next")
```

### 2. Integration Tests
```python
import pytest
from fastapi.testclient import TestClient
from your_app.main import app

client = TestClient(app)

def test_products_pagination_endpoint():
    # Test first page
    response = client.get("/api/products?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "next_cursor" in data
    assert "has_next" in data
    
    # Test next page if available
    if data["has_next"]:
        next_response = client.get(f"/api/products?limit=10&cursor={data['next_cursor']}")
        assert next_response.status_code == 200
```

## Monitoring

### 1. Performance Metrics
- **Response Time**: Monitor pagination endpoint performance
- **Query Performance**: Track database query execution times
- **Memory Usage**: Monitor memory consumption during pagination
- **Error Rates**: Track pagination-related errors

### 2. Business Metrics
- **Pagination Usage**: Track pagination pattern usage
- **User Behavior**: Monitor pagination navigation patterns
- **Data Access**: Track which data ranges are accessed most
- **Performance Impact**: Measure impact on overall system performance
