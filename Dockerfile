# Multi-stage Dockerfile for AlgoTrading
# FASE 5: Cloud Deployment - Production-ready containerization
# Supports multiple build targets: production, development, testing

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy project definition first for better caching
COPY pyproject.toml ./

# Copy source code (needed for pip install -e)
COPY app/ app/
COPY scripts/ scripts/

# Install all dependencies from pyproject.toml
RUN pip install --no-cache-dir -e ".[dev]"

# Production stage
FROM python:3.11-slim as production

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set labels
LABEL org.opencontainers.image.title="AlgoTrading API" \
      org.opencontainers.image.description="Algorithmic Trading API" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="AlgoTrading Team" \
      org.opencontainers.image.licenses="MIT"

# Set environment variables (MUST be before any numeric library imports)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    MKL_SERVICE_FORCE_INTEL=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    PYTORCH_ENABLE_MPS_FALLBACK=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    CUDA_VISIBLE_DEVICES="" \
    TORCH_USE_CUDA_DSA=0

# Create non-root user
RUN groupadd -r algotrading && useradd -r -g algotrading algotrading

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app /app

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R algotrading:algotrading /app

# Switch to non-root user
USER algotrading

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM production as development

# Switch back to root for development
USER root

# Install additional development tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER algotrading

# Override command for development
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage
FROM builder as testing

# Set environment for testing
ENV ENVIRONMENT=testing \
    PYTEST_CURRENT_TEST=true

# Create test directories
RUN mkdir -p /app/tests /app/.pytest_cache

# Copy test files
COPY tests/ /app/tests/

# Default command for testing
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=xml"]
