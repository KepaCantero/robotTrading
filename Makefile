# AlgoTrading Makefile

.PHONY: help up down api db logs clean test test-cov migrate migration dev api-dev build deploy prod lint format type-check security

# Default target
help:
	@echo "AlgoTrading - Personal Algorithmic Trading System"
	@echo ""
	@echo "Available commands:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make api         - Start only API"
	@echo "  make db          - Start database"
	@echo "  make logs        - View logs"
	@echo "  make clean       - Clean up"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage (fails under 80%)"
	@echo "  make migrate     - Run database migrations"
	@echo "  make migration   - Create new migration"
	@echo "  make dev         - Start development environment"
	@echo "  make api-dev     - Run API in development mode"
	@echo "  make build       - Build production image"
	@echo "  make deploy      - Deploy to production"
	@echo "  make prod        - Run production environment"
	@echo "  make lint        - Run ruff lint + mypy"
	@echo "  make format      - Auto-format with ruff"
	@echo "  make type-check  - Run mypy type checking"
	@echo "  make security    - Run bandit + safety scans"

# Start all services
up:
	@echo "Starting AlgoTrading services..."
	docker-compose up -d
	@echo "Services started. API available at http://localhost:8000"

# Stop all services
down:
	@echo "Stopping AlgoTrading services..."
	docker-compose down
	@echo "Services stopped"

# Start only API
api:
	@echo "Starting API server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start database
db:
	@echo "Starting database..."
	docker-compose up -d postgres redis
	@echo "Database started"

# View logs
logs:
	docker-compose logs -f

# Clean up
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "Cleanup completed"

# Run tests
test:
	@echo "Running tests..."
	pytest -v --tb=short

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -v

# Run specific test file
test-file:
	@echo "Running test file: $(file)"
	pytest $(file) -v

# Run database migrations
migrate:
	@echo "Running database migrations..."
	alembic upgrade head
	@echo "Migrations completed"

# Create new migration
migration:
	@echo "Creating new migration: $(name)"
	alembic revision --autogenerate -m "$(name)"
	@echo "Migration created"

# Start development environment
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started"

# Run API in development mode
api-dev:
	@echo "Starting API in development mode..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Build production image
build:
	@echo "Building production image..."
	docker build -t algotrading:latest .
	@echo "Production image built"

# Deploy to production
deploy:
	@echo "Deploying to production..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Deployment completed"

# Run production environment
prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Production environment started"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Dependencies installed"

# Setup environment
setup:
	@echo "Setting up AlgoTrading..."
	python -m venv .venv
	@echo "Virtual environment created"
	@echo "Run 'source .venv/bin/activate' to activate"
	@echo "Then run 'make install' to install dependencies"

# Code quality checks
lint:
	@echo "Running code quality checks..."
	ruff check .
	mypy app/
	@echo "Code quality checks completed"

# Format code
format:
	@echo "Formatting code..."
	ruff format .
	ruff check --fix .
	@echo "Code formatted"

# Type checking
type-check:
	@echo "Running type checks..."
	mypy app/
	@echo "Type checks completed"

# Security scan
security:
	@echo "Running security scan..."
	bandit -r app/ -f json -o bandit-report.json
	safety check --json --output safety-report.json || true
	@echo "Security scan completed"

# Performance test
perf-test:
	@echo "Running performance tests..."
	pytest tests/performance/ -v
	@echo "Performance tests completed"

# Integration test
integration-test:
	@echo "Running integration tests..."
	pytest tests/integration/ -v
	@echo "Integration tests completed"

# Load test
load-test:
	@echo "Running load tests..."
	locust -f tests/load/locustfile.py --host=http://localhost:8000
	@echo "Load tests completed"

# Backup database
backup:
	@echo "Backing up database..."
	pg_dump $(DATABASE_URL) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup completed"

# Restore database
restore:
	@echo "Restoring database from $(file)..."
	psql $(DATABASE_URL) < $(file)
	@echo "Database restore completed"

# Generate documentation
docs:
	@echo "Generating documentation..."
	pdoc --html app/ --output-dir docs/
	@echo "Documentation generated in docs/"

# Update dependencies
update-deps:
	@echo "Updating dependencies..."
	pip-compile requirements.in
	@echo "Dependencies updated"

# Check system health
health:
	@echo "Checking system health..."
	curl -f http://localhost:8000/health || echo "API not responding"
	@echo "Health check completed"
