#!/usr/bin/env python
"""
Demonstration script for Database Backup Service.

Shows:
- Automated backup creation
- Point-in-time recovery
- Integrity verification
- Retention policy enforcement
"""

import asyncio
import sqlite3
import sys
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backup.database_backup import (
    DatabaseBackupManager,
    BackupConfig,
    BackupStatus,
)


def create_sample_database(db_path: str) -> None:
    """Create a sample database for testing."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            quantity INTEGER,
            price REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample trades
    cursor.execute("INSERT INTO trades (symbol, side, quantity, price) VALUES (?, ?, ?, ?)",
                   ("AAPL", "BUY", 100, 150.25))
    cursor.execute("INSERT INTO trades (symbol, side, quantity, price) VALUES (?, ?, ?, ?)",
                   ("MSFT", "BUY", 50, 300.50))
    cursor.execute("INSERT INTO trades (symbol, side, quantity, price) VALUES (?, ?, ?, ?)",
                   ("GOOGL", "SELL", 25, 2800.00))

    conn.commit()
    conn.close()


def display_trades(db_path: str) -> None:
    """Display all trades in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades")
    trades = cursor.fetchall()

    print("\n" + "=" * 80)
    print("CURRENT DATABASE CONTENTS")
    print("=" * 80)
    print(f"{'ID':<5} {'Symbol':<10} {'Side':<6} {'Quantity':<10} {'Price':<10} {'Timestamp':<20}")
    print("-" * 80)
    for trade in trades:
        print(f"{trade[0]:<5} {trade[1]:<10} {trade[2]:<6} {trade[3]:<10} {trade[4]:<10.2f} {trade[5]}")
    print("=" * 80)

    conn.close()


async def main():
    """Run the demonstration."""
    print("\n" + "=" * 80)
    print("DATABASE BACKUP SERVICE DEMONSTRATION")
    print("=" * 80)
    print("\nThis demonstration shows the critical backup features for tax compliance.")
    print("The FIFO database must never lose data for Modelo 721 reporting.\n")

    # Create temporary database and backup directory
    temp_dir = tempfile.mkdtemp()
    db_path = str(Path(temp_dir) / "trades.db")
    backup_dir = str(Path(temp_dir) / "backups")

    try:
        # Create sample database
        print("Step 1: Creating sample database with trades...")
        create_sample_database(db_path)
        display_trades(db_path)

        # Configure backup service
        print("\nStep 2: Configuring backup service...")
        config = BackupConfig(
            db_path=db_path,
            backup_dir=backup_dir,
            backup_interval_seconds=2.0,  # Fast for demo
            retention_hours=24,
            max_backups=10,
            verify_on_create=True,
            verify_integrity=True,
        )
        print(f"  - Database: {db_path}")
        print(f"  - Backup directory: {backup_dir}")
        print(f"  - Backup interval: {config.backup_interval_seconds}s")
        print(f"  - Retention: {config.retention_hours} hours")
        print(f"  - Max backups: {config.max_backups}")

        # Create backup manager
        manager = DatabaseBackupManager(config)

        # Manual backup creation
        print("\nStep 3: Creating manual backups...")
        result1 = await manager.create_backup()
        if result1.success:
            backup_dict = result1.backup_info.to_dict()
            print(f"  - Backup 1 created: {result1.backup_info.filename}")
            print(f"    Size: {backup_dict['size_mb']:.2f} MB")
            print(f"    Verified: {result1.backup_info.verified}")
            print(f"    Checksum: {result1.backup_info.checksum[:16]}...")

        # Add more trades
        print("\nStep 4: Modifying database with new trades...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trades (symbol, side, quantity, price) VALUES (?, ?, ?, ?)",
                       ("TSLA", "BUY", 30, 950.75))
        cursor.execute("INSERT INTO trades (symbol, side, quantity, price) VALUES (?, ?, ?, ?)",
                       ("AMZN", "BUY", 20, 3200.25))
        conn.commit()
        conn.close()
        display_trades(db_path)

        # Create another backup
        print("\nStep 5: Creating second backup...")
        result2 = await manager.create_backup()
        if result2.success:
            backup_dict = result2.backup_info.to_dict()
            print(f"  - Backup 2 created: {result2.backup_info.filename}")
            print(f"    Size: {backup_dict['size_mb']:.2f} MB")
            print(f"    Verified: {result2.backup_info.verified}")
            print(f"    Checksum: {result2.backup_info.checksum[:16]}...")

        # List backups
        print("\nStep 6: Listing all backups...")
        backups = manager.list_backups()
        print(f"  Total backups: {len(backups)}")
        for backup in backups:
            print(f"    - {backup.filename} ({backup.created_at.strftime('%Y-%m-%d %H:%M:%S')})")

        # Get statistics
        print("\nStep 7: Backup statistics...")
        stats = manager.get_statistics()
        print(f"  - Total backups: {stats['total_backups']}")
        print(f"  - Total size: {stats['total_size_mb']:.2f} MB")
        print(f"  - Oldest backup: {stats['oldest_backup']}")
        print(f"  - Newest backup: {stats['newest_backup']}")

        # Point-in-time recovery
        print("\nStep 8: Point-in-time recovery demonstration...")
        print("  - Current database has 5 trades")
        print(f"  - Restoring to first backup: {backups[0].filename}")

        await manager.restore_backup(backups[0].filename)
        display_trades(db_path)

        print("  - Database restored to state of first backup (3 trades)")

        # Restore latest
        print(f"\n  - Restoring latest backup: {backups[-1].filename}")
        await manager.restore_backup(backups[-1].filename)
        display_trades(db_path)
        print("  - Database restored to state of latest backup (5 trades)")

        # Automated backup loop
        print("\nStep 9: Starting automated backup loop...")
        print("  - Creating backup every 2 seconds...")
        print("  - Will create 3 backups then stop...")

        await manager.start()
        await asyncio.sleep(7)  # Wait for ~3 backups
        await manager.stop()

        backups_after_loop = manager.list_backups()
        print(f"  - Total backups after loop: {len(backups_after_loop)}")

        # Retention policy
        print("\nStep 10: Retention policy demonstration...")
        print(f"  - Current max_backups: {config.max_backups}")
        print(f"  - If backups exceed limit, oldest will be pruned")

        # Force pruning
        await manager.prune_old_backups()
        final_backups = manager.list_backups()
        print(f"  - Backups after pruning: {len(final_backups)}")

        # Summary
        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE")
        print("=" * 80)
        print("\nKey Features Demonstrated:")
        print("  [✓] Automated backup creation with verification")
        print("  [✓] Point-in-time recovery to any backup")
        print("  [✓] Integrity verification using PRAGMA integrity_check")
        print("  [✓] SHA256 checksum for data integrity")
        print("  [✓] Retention policy enforcement")
        print("  [✓] Backup statistics and monitoring")
        print("\nThis system ensures CRITICAL tax compliance data is never lost.")
        print("=" * 80 + "\n")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
