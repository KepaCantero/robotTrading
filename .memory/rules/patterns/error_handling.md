# Error Handling Pattern - AlgoTrading System

## Pattern Overview
**Name**: Structured Error Handling  
**Type**: System Design Pattern  
**Domain**: Error Management & Resilience  
**Implementation**: FastAPI + Pydantic + Custom Exceptions  

## Problem Statement
Applications need consistent, structured error handling that provides meaningful feedback to users while maintaining security and enabling proper monitoring and debugging.

## Solution
Implement a comprehensive error handling system with custom exception classes, structured error responses, and proper logging for different error types.

## Implementation

### 1. Custom Exception Classes
```python
from typing import Any, Dict, Optional
from fastapi import HTTPException
from enum import Enum

class ErrorCode(str, Enum):
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Business Logic Errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    INVALID_ORDER_STATE = "INVALID_ORDER_STATE"
    
    # System Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

class BaseAppException(Exception):
    """Base exception class for application-specific errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        super().__init__(self.message)

class ValidationError(BaseAppException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )

class AuthenticationError(BaseAppException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401
        )

class AuthorizationError(BaseAppException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=403
        )

class ResourceNotFoundError(BaseAppException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )

class BusinessLogicError(BaseAppException):
    """Raised when business logic constraints are violated"""
    
    def __init__(self, message: str, error_code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )

class ExternalServiceError(BaseAppException):
    """Raised when external service calls fail"""
    
    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"External service '{service_name}' error: {message}"
        super().__init__(
            message=full_message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details=details or {"service_name": service_name}
        )
```

### 2. Error Response Models
```python
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response format"""
    error: bool = True
    message: str
    error_code: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None
    method: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    validation_errors: Optional[list[ErrorDetail]] = None
    request_id: Optional[str] = None

class SuccessResponse(BaseModel):
    """Standard success response format"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
```

### 3. Error Handler Middleware
```python
import logging
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

class ErrorHandler:
    def __init__(self):
        self.logger = logger
    
    async def handle_app_exception(
        self, 
        request: Request, 
        exc: BaseAppException
    ) -> JSONResponse:
        """Handle application-specific exceptions"""
        
        # Log the error
        self.logger.error(
            f"Application error: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.details,
                "traceback": traceback.format_exc()
            }
        )
        
        # Create error response
        error_response = ErrorResponse(
            message=exc.user_message,
            error_code=exc.error_code,
            status_code=exc.status_code,
            path=str(request.url.path),
            method=request.method,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None)
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict()
        )
    
    async def handle_validation_error(
        self, 
        request: Request, 
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        
        # Convert validation errors to structured format
        validation_errors = []
        for error in exc.errors():
            validation_errors.append(ErrorDetail(
                field=".".join(str(loc) for loc in error["loc"]),
                message=error["msg"],
                code=error["type"]
            ))
        
        # Log the error
        self.logger.warning(
            f"Validation error: {len(validation_errors)} validation failures",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "validation_errors": [ve.dict() for ve in validation_errors]
            }
        )
        
        # Create error response
        error_response = ErrorResponse(
            message="Validation failed",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            path=str(request.url.path),
            method=request.method,
            validation_errors=validation_errors,
            request_id=getattr(request.state, "request_id", None)
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response.dict()
        )
    
    async def handle_database_error(
        self, 
        request: Request, 
        exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle database errors"""
        
        # Log the error
        self.logger.error(
            f"Database error: {str(exc)}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        # Create error response
        error_response = ErrorResponse(
            message="Database operation failed",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            path=str(request.url.path),
            method=request.method,
            request_id=getattr(request.state, "request_id", None)
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )
    
    async def handle_generic_exception(
        self, 
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions"""
        
        # Log the error
        self.logger.error(
            f"Unexpected error: {str(exc)}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        # Create error response
        error_response = ErrorResponse(
            message="An unexpected error occurred",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            path=str(request.url.path),
            method=request.method,
            request_id=getattr(request.state, "request_id", None)
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )
```

### 4. FastAPI Exception Handlers
```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()
error_handler = ErrorHandler()

# Register exception handlers
@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    return await error_handler.handle_app_exception(request, exc)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return await error_handler.handle_validation_error(request, exc)

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    return await error_handler.handle_database_error(request, exc)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return await error_handler.handle_generic_exception(request, exc)
```

### 5. Service Layer Usage
```python
from typing import Optional
from sqlalchemy.orm import Session
from your_app.models.product import Product
from your_app.exceptions import ResourceNotFoundError, BusinessLogicError, ErrorCode

class ProductService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_product(self, product_id: int) -> Product:
        """Get product by ID with proper error handling"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise ResourceNotFoundError("Product", str(product_id))
        
        return product
    
    def update_stock(self, product_id: int, quantity: int) -> Product:
        """Update product stock with business logic validation"""
        product = self.get_product(product_id)
        
        if quantity < 0:
            raise BusinessLogicError(
                message="Stock quantity cannot be negative",
                error_code=ErrorCode.VALIDATION_ERROR,
                details={"product_id": product_id, "quantity": quantity}
            )
        
        if product.stock + quantity < 0:
            raise BusinessLogicError(
                message="Insufficient stock available",
                error_code=ErrorCode.INSUFFICIENT_STOCK,
                details={
                    "product_id": product_id,
                    "current_stock": product.stock,
                    "requested_quantity": quantity,
                    "available_quantity": product.stock
                }
            )
        
        product.stock += quantity
        self.db.commit()
        self.db.refresh(product)
        
        return product
```

## Benefits

### 1. Consistency
- **Standardized Error Format**: All errors follow the same structure
- **Consistent Status Codes**: Proper HTTP status code usage
- **Uniform Logging**: Structured logging for all error types
- **Predictable Behavior**: Clients can handle errors consistently

### 2. Security
- **Information Hiding**: Sensitive information not exposed to clients
- **Structured Responses**: No stack traces in production responses
- **Audit Trail**: Comprehensive logging for security monitoring
- **Error Classification**: Different handling for different error types

### 3. Debugging
- **Detailed Logging**: Comprehensive error information in logs
- **Request Tracking**: Request IDs for tracing errors
- **Context Information**: Path, method, and other request details
- **Stack Traces**: Full stack traces in development environment

### 4. User Experience
- **Meaningful Messages**: User-friendly error messages
- **Actionable Information**: Clear guidance on how to resolve errors
- **Validation Details**: Specific field-level validation errors
- **Consistent Interface**: Predictable error response format

## Best Practices

### 1. Error Classification
- **Use Appropriate Status Codes**: Follow HTTP status code conventions
- **Categorize Errors**: Group similar errors with error codes
- **Provide Context**: Include relevant details in error responses
- **Hide Sensitive Information**: Don't expose internal system details

### 2. Logging Strategy
- **Structured Logging**: Use JSON format for log entries
- **Appropriate Log Levels**: Use correct log levels for different errors
- **Include Context**: Add request information to log entries
- **Avoid Logging Sensitive Data**: Don't log passwords, tokens, etc.

### 3. Error Handling
- **Handle All Exception Types**: Cover all possible error scenarios
- **Provide Fallbacks**: Graceful degradation for non-critical errors
- **Implement Retries**: Retry mechanisms for transient failures
- **Monitor Error Rates**: Track and alert on error patterns

### 4. Client Integration
- **Document Error Codes**: Provide clear documentation for all error codes
- **Provide Examples**: Show how to handle different error types
- **Version Error Responses**: Maintain backward compatibility
- **Test Error Scenarios**: Include error handling in API tests

## Testing

### 1. Unit Tests
```python
import pytest
from fastapi.testclient import TestClient
from your_app.main import app
from your_app.exceptions import ResourceNotFoundError, ErrorCode

client = TestClient(app)

def test_resource_not_found_error():
    """Test that resource not found returns proper error response"""
    response = client.get("/api/products/999")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"] is True
    assert data["error_code"] == ErrorCode.RESOURCE_NOT_FOUND
    assert "not found" in data["message"]
    assert "request_id" in data

def test_validation_error():
    """Test that validation errors return proper error response"""
    response = client.post("/api/products", json={"name": ""})
    
    assert response.status_code == 422
    data = response.json()
    assert data["error"] is True
    assert data["error_code"] == ErrorCode.VALIDATION_ERROR
    assert "validation_errors" in data
    assert len(data["validation_errors"]) > 0
```

### 2. Integration Tests
```python
def test_error_handling_integration():
    """Test error handling in full request cycle"""
    # Test with invalid product ID
    response = client.get("/api/products/invalid-id")
    assert response.status_code == 422
    
    # Test with non-existent product
    response = client.get("/api/products/999")
    assert response.status_code == 404
    
    # Test with insufficient stock
    response = client.post("/api/orders", json={
        "product_id": 1,
        "quantity": 1000  # Assuming product has less stock
    })
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorCode.INSUFFICIENT_STOCK
```

## Monitoring

### 1. Error Metrics
- **Error Rate**: Track error rate by endpoint and error type
- **Response Time**: Monitor response times for error responses
- **Error Patterns**: Identify common error patterns and trends
- **Client Impact**: Measure impact of errors on client applications

### 2. Alerting
- **High Error Rate**: Alert when error rate exceeds threshold
- **New Error Types**: Alert on new or unexpected error types
- **Critical Errors**: Immediate alerts for security or system errors
- **Performance Impact**: Alert when errors affect system performance

### 3. Analysis
- **Error Root Causes**: Analyze root causes of common errors
- **Client Behavior**: Understand how clients handle different errors
- **System Health**: Use error patterns to assess system health
- **Improvement Opportunities**: Identify areas for error prevention
