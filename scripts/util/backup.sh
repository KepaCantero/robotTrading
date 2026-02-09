#!/bin/bash
# Database backup script for production use

DB_PATH="${DB_PATH:-data/orders.db}"
BACKUP_DIR="${BACKUP_DIR:-backups/database}"
RETENTION_HOURS="${RETENTION_HOURS:-24}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.db"

echo "Creating backup: $BACKUP_FILE"
cp "$DB_PATH" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup created successfully"
else
    echo "ERROR: Backup failed"
    exit 1
fi

# Prune old backups
echo "Pruning backups older than $RETENTION_HOURS hours"
find "$BACKUP_DIR" -name "backup_*.db" -mtime +$(($RETENTION_HOURS / 24)) -delete

echo "Backup complete"
