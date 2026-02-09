#!/bin/bash
# Rollback production deployment
# Phase 4.2: Production Config Management Rollback Script

set -e
set -u
set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
BACKUP_DIR="${PROJECT_ROOT}/backups"

log_info "Rolling back AlgoTrading production deployment..."
log_info "Project root: ${PROJECT_ROOT}"

# ============================================================================
# 1. List available backups
# ============================================================================

log_info "Available backups:"

if [ ! -d "${BACKUP_DIR}" ]; then
    log_error "Backup directory not found: ${BACKUP_DIR}"
    exit 1
fi

# List database backups
db_backups=($(ls -t "${BACKUP_DIR}"/pre-deploy-orders-*.db 2>/dev/null || true))
config_backups=($(ls -t "${BACKUP_DIR}"/pre-deploy-config-*.tar.gz 2>/dev/null || true))

if [ ${#db_backups[@]} -eq 0 ] && [ ${#config_backups[@]} -eq 0 ]; then
    log_error "No backups found"
    exit 1
fi

echo ""
if [ ${#db_backups[@]} -gt 0 ]; then
    log_info "Database backups:"
    for i in "${!db_backups[@]}"; do
        echo "  [$i] $(basename ${db_backups[$i]})"
    done
fi

echo ""
if [ ${#config_backups[@]} -gt 0 ]; then
    log_info "Configuration backups:"
    for i in "${!config_backups[@]}"; do
        echo "  [$i] $(basename ${config_backups[$i]})"
    done
fi

# ============================================================================
# 2. Select backup to restore
# ============================================================================

echo ""
read -p "Enter backup number to restore (or 'q' to quit): " selection

if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
    log_info "Rollback cancelled"
    exit 0
fi

# Validate selection
if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
    log_error "Invalid selection"
    exit 1
fi

# ============================================================================
# 3. Stop service
# ============================================================================

log_info "Stopping service..."

if systemctl is-active --quiet algotrading 2>/dev/null; then
    sudo systemctl stop algotrading
    log_info "Service stopped"
elif pgrep -f "python.*algotrading" > /dev/null; then
    pkill -f "python.*algotrading" || true
    log_info "Killed running processes"
else
    log_info "No running instance found"
fi

sleep 3

# ============================================================================
# 4. Restore backup
# ============================================================================

log_info "Restoring backup..."

# Restore database
if [ ${#db_backups[@]} -gt 0 ] && [ "$selection" -lt ${#db_backups[@]} ]; then
    backup_file="${db_backups[$selection]}"
    log_info "Restoring database from: ${backup_file}"

    mkdir -p "$(dirname "${PROJECT_ROOT}/data/orders.db")"
    cp "${backup_file}" "${PROJECT_ROOT}/data/orders.db"

    log_info "Database restored"
else
    log_warn "No database backup selected"
fi

# Restore configuration (use most recent if not specified)
if [ ${#config_backups[@]} -gt 0 ]; then
    config_backup="${config_backups[0]}"
    log_info "Restoring configuration from: ${config_backup}"

    cd "${PROJECT_ROOT}"
    tar -xzf "${config_backup}"

    log_info "Configuration restored"
else
    log_warn "No configuration backup found"
fi

# ============================================================================
# 5. Create post-rollback backup
# ============================================================================

log_info "Creating post-rollback backup..."

rollback_backup="${BACKUP_DIR}/post-rollback-$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "${rollback_backup}" -C "${PROJECT_ROOT}" data/ config/ 2>/dev/null || true

log_info "Post-rollback state backed up to: ${rollback_backup}"

# ============================================================================
# 6. Restart service
# ============================================================================

log_info "Restarting service..."

if [ -f "/etc/systemd/system/algotrading.service" ]; then
    sudo systemctl start algotrading
    log_info "Service started (systemd)"
else
    log_warn "No systemd service found, starting manually"
    nohup python3 -m app.main > "${PROJECT_ROOT}/logs/production.log" 2>&1 &
    log_info "Service started (background process)"
fi

# ============================================================================
# 7. Verify rollback
# ============================================================================

log_info "Verifying rollback..."
sleep 5

if systemctl is-active --quiet algotrading 2>/dev/null || pgrep -f "python.*algotrading" > /dev/null; then
    log_info "Service is running"
else
    log_error "Service failed to start after rollback"
    log_error "Check logs for details"
    exit 1
fi

log_info "Rollback completed successfully!"
log_info "Monitor logs with: tail -f ${PROJECT_ROOT}/logs/production.log"
