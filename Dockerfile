# Multi-stage Dockerfile for AlgoTrading FastAPI Application
# TASK-2: Dockerización completa

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.local/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r algotrading && useradd -r -g algotrading algotrading

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/backups /app/config \
    && chown -R algotrading:algotrading /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=algotrading:algotrading . .

# Create virtual environment and install dependencies
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# Set proper permissions
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# Switch to non-root user
USER algotrading

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Stage 3: Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN /app/.venv/bin/pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy \
    pre-commit

# Switch back to non-root user
USER algotrading

# Override command for development
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Testing stage
FROM development as testing

# Install additional testing dependencies
RUN /app/.venv/bin/pip install --no-cache-dir \
    pytest-benchmark \
    pytest-mock \
    httpx \
    factory-boy

# Override command for testing
CMD ["/app/.venv/bin/pytest", "tests/", "-v", "--cov=app", "--cov-report=html"]

# Stage 5: Worker stage (for background tasks)
FROM production as worker

# Install additional dependencies for background tasks
RUN /app/.venv/bin/pip install --no-cache-dir \
    celery \
    redis

# Override command for worker
CMD ["/app/.venv/bin/celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]

# Stage 6: Scheduler stage (for scheduled tasks)
FROM worker as scheduler

# Override command for scheduler
CMD ["/app/.venv/bin/celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"]