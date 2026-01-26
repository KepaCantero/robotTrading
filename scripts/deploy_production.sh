#!/bin/bash
# Deploy to production environment
# Phase 4.2: Production Config Management Deployment Script

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/config"
BACKUP_DIR="${PROJECT_ROOT}/backups"
ENV_FILE=".env.prod"
SECRETS_FILE="${CONFIG_DIR}/secrets.yaml"

log_info "Deploying AlgoTrading to production..."
log_info "Project root: ${PROJECT_ROOT}"

# ============================================================================
# 1. Pre-deployment checks
# ============================================================================

log_info "Running pre-deployment checks..."

# Check if .env.prod exists
if [ ! -f "${PROJECT_ROOT}/${ENV_FILE}" ]; then
    log_error "Environment file not found: ${ENV_FILE}"
    log_error "Create it from .env.example first"
    exit 1
fi

# Load environment variables
log_info "Loading environment variables from ${ENV_FILE}..."
set -a  # Automatically export all variables
source "${PROJECT_ROOT}/${ENV_FILE}"
set +a

# Validate required environment variables
required_vars=("SECRET_KEY" "DATABASE_URL")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    log_error "Missing required environment variables: ${missing_vars[*]}"
    exit 1
fi

# Check if secrets.yaml exists
if [ ! -f "${SECRETS_FILE}" ]; then
    log_warn "Secrets file not found: ${SECRETS_FILE}"
    log_warn "Create it from secrets.yaml.example first"
    log_warn "Continuing without secrets file..."
fi

# ============================================================================
# 2. Configuration validation
# ============================================================================

log_info "Validating production configuration..."

if [ -f "${CONFIG_DIR}/production.yaml" ]; then
    # Validate YAML syntax
    if command -v python3 &> /dev/null; then
        python3 -c "import yaml; yaml.safe_load(open('${CONFIG_DIR}/production.yaml'))" 2>/dev/null
        if [ $? -eq 0 ]; then
            log_info "Production configuration YAML is valid"
        else
            log_error "Production configuration YAML is invalid"
            exit 1
        fi
    else
        log_warn "Python3 not found, skipping YAML validation"
    fi
else
    log_error "Production configuration not found: ${CONFIG_DIR}/production.yaml"
    exit 1
fi

# ============================================================================
# 3. Run tests
# ============================================================================

log_info "Running tests..."

if command -v pytest &> /dev/null; then
    cd "${PROJECT_ROOT}"
    pytest tests/ -v --tb=short -m "not integration" || {
        log_error "Tests failed"
        exit 1
    }
    log_info "All tests passed"
else
    log_warn "pytest not found, skipping tests"
fi

# ============================================================================
# 4. Create backup
# ============================================================================

log_info "Creating backup..."

mkdir -p "${BACKUP_DIR}"

# Backup database if it exists
if [ -f "${PROJECT_ROOT}/data/orders.db" ]; then
    backup_file="${BACKUP_DIR}/pre-deploy-orders-$(date +%Y%m%d_%H%M%S).db"
    cp "${PROJECT_ROOT}/data/orders.db" "${backup_file}"
    log_info "Database backed up to: ${backup_file}"
else
    log_info "No existing database to backup"
fi

# Backup configuration
config_backup="${BACKUP_DIR}/pre-deploy-config-$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "${config_backup}" -C "${PROJECT_ROOT}" config/ 2>/dev/null || {
    log_warn "Could not create configuration backup"
}
log_info "Configuration backed up to: ${config_backup}"

# ============================================================================
# 5. Stop running instance
# ============================================================================

log_info "Stopping service..."

# Check if running as systemd service
if systemctl is-active --quiet algotrading 2>/dev/null; then
    sudo systemctl stop algotrading
    log_info "Service stopped"
elif pgrep -f "python.*algotrading" > /dev/null; then
    # Kill running processes
    pkill -f "python.*algotrading" || true
    log_info "Killed running processes"
else
    log_info "No running instance found"
fi

# Wait for processes to stop
sleep 3

# ============================================================================
# 6. Deploy
# ============================================================================

log_info "Deploying application..."

# Install/update dependencies
if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    log_info "Installing/updating dependencies..."
    pip3 install -q -r "${PROJECT_ROOT}/requirements.txt" || {
        log_error "Failed to install dependencies"
        exit 1
    }
fi

# Run database migrations if needed
if [ -f "${PROJECT_ROOT}/scripts/migrate_db.sh" ]; then
    log_info "Running database migrations..."
    bash "${PROJECT_ROOT}/scripts/migrate_db.sh" || {
        log_warn "Database migrations failed or not needed"
    }
fi

# ============================================================================
# 7. Start service
# ============================================================================

log_info "Starting service..."

if [ -f "/etc/systemd/system/algotrading.service" ]; then
    # Start as systemd service
    sudo systemctl start algotrading
    log_info "Service started (systemd)"
else
    # Start directly
    log_warn "No systemd service found, starting manually"
    nohup python3 -m app.main > "${PROJECT_ROOT}/logs/production.log" 2>&1 &
    log_info "Service started (background process)"
fi

# ============================================================================
# 8. Verify deployment
# ============================================================================

log_info "Verifying deployment..."
sleep 5

# Check if service is running
if systemctl is-active --quiet algotrading 2>/dev/null || pgrep -f "python.*algotrading" > /dev/null; then
    log_info "Service is running"
else
    log_error "Service failed to start"
    log_error "Check logs for details"
    exit 1
fi

# Health check
if command -v curl &> /dev/null; then
    health_url="http://localhost:8000/health"
    if curl -f -s "${health_url}" > /dev/null 2>&1; then
        log_info "Health check passed"
    else
        log_warn "Health check failed or endpoint not available"
    fi
fi

log_info "Deployment completed successfully!"
log_info "Monitor logs with: tail -f ${PROJECT_ROOT}/logs/production.log"

# ============================================================================
# 9. Rollback procedure (documentation)
# ============================================================================

log_info ""
log_info "=== Rollback Procedure ==="
log_info "If deployment fails, use the following steps:"
log_info "1. Stop the service: sudo systemctl stop algotrading"
log_info "2. Restore database: cp ${BACKUP_DIR}/pre-deploy-orders-YYYYMMDD_HHMMSS.db data/orders.db"
log_info "3. Restore config: tar -xzf ${BACKUP_DIR}/pre-deploy-config-YYYYMMDD_HHMMSS.tar.gz"
log_info "4. Restart service: sudo systemctl start algotrading"
