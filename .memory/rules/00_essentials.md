# Essential Rules - AlgoTrading System

## Core Development Principles

### 1. Type Safety First
- **No `any` types** in production code
- **Use specific types** over generics when possible
- **Document all type definitions** with clear examples
- **Use type guards** for runtime validation
- **Maintain type safety** in tests and mocks

### 2. Security by Design
- **OAuth 2.0 + JWT** for all authentication
- **RBAC** for all authorization decisions
- **Input validation** with Pydantic schemas
- **AES-256 encryption** for sensitive data
- **Comprehensive audit logging** for all operations

### 3. Performance Optimization
- **< 1.5s response time** for all database queries
- **Redis caching** for frequently accessed data
- **Connection pooling** for database connections
- **Async/await** for I/O operations
- **Pagination** for large data sets

### 4. Code Quality Standards
- **PEP8 compliance** with black formatting
- **flake8 linting** for code quality
- **>90% test coverage** for all new code
- **Comprehensive documentation** for all APIs
- **Consistent naming conventions** (snake_case for files/functions, PascalCase for classes)

## Architecture Patterns

### 1. Microservices Architecture
- **Clear domain boundaries** between services
- **Independent deployment** and scaling
- **Event-driven communication** between services
- **Database per service** pattern
- **API Gateway** for client requests

### 2. Repository Pattern
- **Data access abstraction** through repositories
- **Interface-based design** for testability
- **Caching integration** at repository level
- **Query optimization** through repository methods
- **Transaction management** within repositories

### 3. Event-Driven Design
- **Event sourcing** for audit trails
- **CQRS** for read/write separation
- **Message queues** for async processing
- **Event handlers** for business logic
- **Eventual consistency** where appropriate

## Database Rules

### 1. PostgreSQL Best Practices
- **ACID compliance** for all transactions
- **Proper indexing** for query performance
- **Connection pooling** for scalability
- **Migration management** with Alembic
- **Backup and recovery** procedures

### 2. Data Modeling
- **Normalized design** to prevent redundancy
- **Foreign key constraints** for data integrity
- **JSONB fields** for flexible data storage
- **Audit fields** (created_at, updated_at) on all tables
- **Soft deletes** where appropriate

### 3. Query Optimization
- **Indexed queries** for performance
- **Query analysis** with EXPLAIN
- **Connection pooling** configuration
- **Read replicas** for scaling reads
- **Query caching** with Redis

## API Design Rules

### 1. RESTful API Standards
- **HTTP methods** used correctly (GET, POST, PUT, DELETE)
- **Status codes** used appropriately
- **Resource naming** follows REST conventions
- **Versioning** through URL path or headers
- **Pagination** for list endpoints

### 2. FastAPI Best Practices
- **Pydantic schemas** for request/response validation
- **Dependency injection** for services and repositories
- **Async endpoints** for I/O operations
- **Automatic documentation** generation
- **Error handling** with proper HTTP status codes

### 3. Security Implementation
- **Authentication middleware** for protected endpoints
- **Authorization checks** for resource access
- **Input validation** with Pydantic
- **Rate limiting** for API abuse prevention
- **CORS configuration** for cross-origin requests

## Testing Rules

### 1. Test Pyramid
- **70% unit tests** for business logic
- **20% integration tests** for service interactions
- **10% end-to-end tests** for user workflows
- **Performance tests** for load validation
- **Security tests** for vulnerability assessment

### 2. Test Quality
- **Descriptive test names** that explain the scenario
- **Arrange-Act-Assert** pattern for test structure
- **Mock external dependencies** for isolation
- **Test data builders** for complex objects
- **Cleanup procedures** for test data

### 3. Test Coverage
- **>90% code coverage** for all new code
- **Branch coverage** for conditional logic
- **Integration coverage** for service interactions
- **API coverage** for all endpoints
- **Security coverage** for authentication/authorization

## Security Rules

### 1. Authentication
- **OAuth 2.0 flow** for user authentication
- **JWT tokens** for stateless authentication
- **Token expiration** and refresh mechanisms
- **Secure token storage** (httpOnly cookies)
- **Multi-factor authentication** for sensitive operations

### 2. Authorization
- **Role-based access control** (RBAC)
- **Permission-based authorization** for fine-grained control
- **Resource-level permissions** where appropriate
- **Audit logging** for all authorization decisions
- **Principle of least privilege** for all users

### 3. Data Protection
- **AES-256 encryption** for sensitive data
- **Password hashing** with bcrypt/argon2
- **Input sanitization** to prevent injection attacks
- **Output encoding** to prevent XSS attacks
- **CSRF protection** for state-changing operations

## Performance Rules

### 1. Response Time
- **< 1.5s** for database queries
- **< 1.0s** for API endpoints
- **< 5.0s** for report generation
- **< 2.0s** for notification delivery
- **Monitoring** and alerting for performance degradation

### 2. Caching Strategy
- **Redis caching** for frequently accessed data
- **Cache invalidation** on data updates
- **Cache warming** for critical data
- **Multi-layer caching** (application, database, CDN)
- **Cache monitoring** and metrics

### 3. Scalability
- **Horizontal scaling** with load balancers
- **Database connection pooling** for efficiency
- **Async processing** for long-running tasks
- **Message queues** for background processing
- **Auto-scaling** based on load metrics

## Deployment Rules

### 1. Containerization
- **Docker containers** for all applications
- **Multi-stage builds** for optimization
- **Health checks** for container monitoring
- **Resource limits** for container constraints
- **Security scanning** for container images

### 2. Infrastructure
- **Infrastructure as Code** with Docker Compose/Terraform
- **Environment parity** between dev/staging/prod
- **Secrets management** with AWS Secrets Manager
- **Monitoring and alerting** with CloudWatch
- **Backup and recovery** procedures

### 3. CI/CD
- **Automated testing** in CI pipeline
- **Code quality checks** before deployment
- **Security scanning** for vulnerabilities
- **Blue-green deployment** for zero downtime
- **Rollback procedures** for failed deployments

## Documentation Rules

### 1. API Documentation
- **OpenAPI/Swagger** documentation for all endpoints
- **Request/response examples** for all operations
- **Error code documentation** with explanations
- **Authentication examples** for protected endpoints
- **Rate limiting information** for all endpoints

### 2. Code Documentation
- **Docstrings** for all public methods and classes
- **Type hints** for all function parameters and returns
- **README files** for all modules and services
- **Architecture diagrams** for system design
- **Deployment guides** for operations team

### 3. Process Documentation
- **Development setup** instructions
- **Testing procedures** and guidelines
- **Deployment procedures** and checklists
- **Troubleshooting guides** for common issues
- **Security procedures** and incident response

## Error Handling Rules

### 1. Exception Management
- **Structured exception handling** with proper logging
- **Custom exception classes** for business logic errors
- **Graceful degradation** for non-critical failures
- **Circuit breaker pattern** for external service failures
- **Retry mechanisms** for transient failures

### 2. Logging Standards
- **Structured logging** with JSON format
- **Log levels** used appropriately (DEBUG, INFO, WARN, ERROR)
- **Sensitive data exclusion** from logs
- **Log aggregation** and analysis
- **Audit logging** for security events

### 3. Monitoring and Alerting
- **Application metrics** for business and technical KPIs
- **Infrastructure metrics** for system health
- **Error rate monitoring** and alerting
- **Performance monitoring** and optimization
- **Security monitoring** for threat detection
