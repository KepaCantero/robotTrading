"""
Order Persistence Layer - SQLite-based order storage

Provides persistent storage for orders across system restarts.
Critical for production trading to ensure no orders are lost.

PRODUCTION FEATURES:
- WAL mode for better concurrent reads
- Busy timeout for retries
- UTC timestamps for consistency
- Connection reuse with thread safety
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# Default database path
DEFAULT_DB_PATH = Path("data/orders.db")


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def decimal_decoder(dct: Dict) -> Dict:
    """JSON decoder hook for Decimal fields."""
    decimal_fields = {
        'quantity',
        'price',
        'filled_quantity',
        'average_price',
        'fees',
        'net_proceeds',
    }
    for key in decimal_fields:
        if key in dct and dct[key] is not None:
            dct[key] = Decimal(str(dct[key]))
    # Handle datetime fields
    datetime_fields = {'created_at', 'updated_at', 'execution_time', 'timestamp'}
    for key in datetime_fields:
        if key in dct and dct[key] is not None and isinstance(dct[key], str):
            try:
                dct[key] = datetime.fromisoformat(dct[key])
            except ValueError:
                pass
    return dct


class OrderPersistence:
    """
    SQLite-based persistence layer for orders.

    Tables:
    - orders: Main order storage
    - executions: Execution records
    - order_errors: Error tracking

    PRODUCTION FEATURES:
    - WAL mode: Better concurrent access
    - Busy timeout: 5 second retry on locks
    - Thread-local connections: Safe for multi-threaded access
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize persistence layer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_database()
        logger.info(f"OrderPersistence initialized with WAL mode: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """
        Get database connection with thread-local reuse.

        Features:
        - WAL mode for concurrent reads
        - 5 second busy timeout
        - Thread-local connection reuse
        """
        # Reuse connection per thread
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=5.0,  # 5 second busy timeout
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
            conn.execute("PRAGMA busy_timeout=5000")  # 5 second retry on lock
            self._local.conn = conn

        conn = self._local.conn
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            conn.rollback()
            logger.error(f"Unexpected error: {e}")
            raise

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Orders table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT,
                    stop_price TEXT,
                    status TEXT NOT NULL,
                    filled_quantity TEXT DEFAULT '0',
                    average_price TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    broker_order_id TEXT,
                    metadata TEXT,
                    is_pending INTEGER DEFAULT 1
                )
            """
            )

            # Executions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT NOT NULL,
                    execution_time TEXT NOT NULL,
                    fees TEXT DEFAULT '0',
                    net_proceeds TEXT DEFAULT '0',
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """
            )

            # Order errors table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS order_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    error_code TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """
            )

            # Indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_pending ON orders(is_pending)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_order ON executions(order_id)"
            )

            logger.info("Database schema initialized")

    def save_order(self, order_data: Dict) -> bool:
        """
        Save or update an order.

        Args:
            order_data: Order data dictionary

        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if order exists
                cursor.execute(
                    "SELECT order_id FROM orders WHERE order_id = ?", (order_data['order_id'],)
                )
                exists = cursor.fetchone() is not None

                now = utc_now().isoformat()
                metadata = json.dumps(order_data.get('metadata', {}), cls=DecimalEncoder)

                if exists:
                    cursor.execute(
                        """
                        UPDATE orders SET
                            status = ?,
                            filled_quantity = ?,
                            average_price = ?,
                            updated_at = ?,
                            is_pending = ?,
                            metadata = ?
                        WHERE order_id = ?
                    """,
                        (
                            order_data.get('status', 'unknown'),
                            str(order_data.get('filled_quantity', '0')),
                            (
                                str(order_data.get('average_price'))
                                if order_data.get('average_price')
                                else None
                            ),
                            now,
                            1 if order_data.get('is_pending', True) else 0,
                            metadata,
                            order_data['order_id'],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO orders (
                            order_id, symbol, side, order_type, quantity, price, stop_price,
                            status, filled_quantity, average_price, created_at, updated_at,
                            broker_order_id, metadata, is_pending
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            order_data['order_id'],
                            order_data['symbol'],
                            order_data.get('side', 'unknown'),
                            order_data.get('order_type', 'market'),
                            str(order_data['quantity']),
                            str(order_data.get('price')) if order_data.get('price') else None,
                            (
                                str(order_data.get('stop_price'))
                                if order_data.get('stop_price')
                                else None
                            ),
                            order_data.get('status', 'pending'),
                            str(order_data.get('filled_quantity', '0')),
                            (
                                str(order_data.get('average_price'))
                                if order_data.get('average_price')
                                else None
                            ),
                            order_data.get('created_at', now),
                            now,
                            order_data.get('broker_order_id'),
                            metadata,
                            1 if order_data.get('is_pending', True) else 0,
                        ),
                    )

                return True

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to save order: {e}")
            return False

    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order data dictionary or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_dict(row)
                return None

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get order: {e}")
            return None

    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all pending orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of pending order dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if symbol:
                    cursor.execute(
                        "SELECT * FROM orders WHERE is_pending = 1 AND symbol = ?", (symbol,)
                    )
                else:
                    cursor.execute("SELECT * FROM orders WHERE is_pending = 1")

                return [self._row_to_dict(row) for row in cursor.fetchall()]

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get pending orders: {e}")
            return []

    def get_executed_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all executed orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of executed order dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if symbol:
                    cursor.execute(
                        "SELECT * FROM orders WHERE is_pending = 0 AND symbol = ? AND status IN ('filled', 'executed')",
                        (symbol,),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM orders WHERE is_pending = 0 AND status IN ('filled', 'executed')"
                    )

                return [self._row_to_dict(row) for row in cursor.fetchall()]

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get executed orders: {e}")
            return []

    def get_order_history(self, symbol: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """
        Get order history.

        Args:
            symbol: Optional symbol filter
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if symbol:
                    cursor.execute(
                        "SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                        (symbol, limit),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
                    )

                return [self._row_to_dict(row) for row in cursor.fetchall()]

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get order history: {e}")
            return []

    def mark_order_executed(self, order_id: str) -> bool:
        """
        Mark an order as executed (no longer pending).

        Args:
            order_id: Order ID

        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE orders SET is_pending = 0, updated_at = ? WHERE order_id = ?",
                    (utc_now().isoformat(), order_id),
                )
                return cursor.rowcount > 0

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to mark order executed: {e}")
            return False

    def save_execution(self, execution_data: Dict) -> bool:
        """
        Save an execution record.

        Args:
            execution_data: Execution data dictionary

        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO executions (
                        order_id, symbol, quantity, price, execution_time, fees, net_proceeds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        execution_data['order_id'],
                        execution_data['symbol'],
                        str(execution_data['quantity']),
                        str(execution_data['price']),
                        (
                            execution_data.get('execution_time', utc_now()).isoformat()
                            if isinstance(execution_data.get('execution_time'), datetime)
                            else execution_data.get('execution_time', utc_now().isoformat())
                        ),
                        str(execution_data.get('fees', '0')),
                        str(execution_data.get('net_proceeds', '0')),
                    ),
                )
                return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to save execution: {e}")
            return False

    def get_executions(
        self, order_id: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        Get execution records.

        Args:
            order_id: Optional order ID filter
            symbol: Optional symbol filter

        Returns:
            List of execution dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if order_id:
                    cursor.execute("SELECT * FROM executions WHERE order_id = ?", (order_id,))
                elif symbol:
                    cursor.execute("SELECT * FROM executions WHERE symbol = ?", (symbol,))
                else:
                    cursor.execute(
                        "SELECT * FROM executions ORDER BY execution_time DESC LIMIT 1000"
                    )

                return [self._execution_row_to_dict(row) for row in cursor.fetchall()]

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get executions: {e}")
            return []

    def save_error(self, error_data: Dict) -> bool:
        """
        Save an order error record.

        Args:
            error_data: Error data dictionary

        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO order_errors (
                        order_id, symbol, error_code, error_message, timestamp, retry_count, max_retries
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        error_data['order_id'],
                        error_data['symbol'],
                        error_data['error_code'],
                        error_data['error_message'],
                        (
                            error_data.get('timestamp', utc_now()).isoformat()
                            if isinstance(error_data.get('timestamp'), datetime)
                            else error_data.get('timestamp', utc_now().isoformat())
                        ),
                        error_data.get('retry_count', 0),
                        error_data.get('max_retries', 3),
                    ),
                )
                return True

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to save error: {e}")
            return False

    def get_errors(
        self, order_id: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        Get error records.

        Args:
            order_id: Optional order ID filter
            symbol: Optional symbol filter

        Returns:
            List of error dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if order_id:
                    cursor.execute("SELECT * FROM order_errors WHERE order_id = ?", (order_id,))
                elif symbol:
                    cursor.execute("SELECT * FROM order_errors WHERE symbol = ?", (symbol,))
                else:
                    cursor.execute("SELECT * FROM order_errors ORDER BY timestamp DESC LIMIT 1000")

                return [self._error_row_to_dict(row) for row in cursor.fetchall()]

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get errors: {e}")
            return []

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert SQLite row to dictionary with proper types."""
        data = dict(row)
        # Convert string quantities back to Decimal
        for key in ['quantity', 'price', 'stop_price', 'filled_quantity', 'average_price']:
            if data.get(key) is not None:
                data[key] = Decimal(data[key])
        # Parse metadata
        if data.get('metadata'):
            try:
                data['metadata'] = json.loads(data['metadata'], object_hook=decimal_decoder)
            except json.JSONDecodeError:
                data['metadata'] = {}
        # Convert timestamps
        for key in ['created_at', 'updated_at']:
            if data.get(key):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except ValueError:
                    pass
        return data

    def _execution_row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert execution row to dictionary."""
        data = dict(row)
        for key in ['quantity', 'price', 'fees', 'net_proceeds']:
            if data.get(key) is not None:
                data[key] = Decimal(data[key])
        if data.get('execution_time'):
            try:
                data['execution_time'] = datetime.fromisoformat(data['execution_time'])
            except ValueError:
                pass
        return data

    def _error_row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert error row to dictionary."""
        data = dict(row)
        if data.get('timestamp'):
            try:
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            except ValueError:
                pass
        return data

    def cleanup_old_orders(self, days: int = 30) -> int:
        """
        Clean up orders older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of orders deleted
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cutoff = utc_now().isoformat()
                # Delete old non-pending orders
                cursor.execute(
                    """
                    DELETE FROM orders
                    WHERE is_pending = 0
                    AND datetime(created_at) < datetime(?, '-' || ? || ' days')
                """,
                    (cutoff, days),
                )
                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old orders")
                return deleted

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to cleanup old orders: {e}")
            return 0

    def get_stats(self) -> Dict:
        """Get persistence statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM orders WHERE is_pending = 1")
                pending = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM orders WHERE is_pending = 0")
                executed = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM executions")
                executions = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM order_errors")
                errors = cursor.fetchone()[0]

                return {
                    'pending_orders': pending,
                    'executed_orders': executed,
                    'total_orders': pending + executed,
                    'executions': executions,
                    'errors': errors,
                    'database_path': str(self.db_path),
                }

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def close(self) -> None:
        """Close thread-local database connection."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            try:
                self._local.conn.close()
            except sqlite3.Error:
                pass
            self._local.conn = None
            logger.debug("Database connection closed")


# Singleton instance
_persistence: Optional[OrderPersistence] = None


def get_order_persistence(db_path: Optional[Path] = None) -> OrderPersistence:
    """Get or create singleton OrderPersistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = OrderPersistence(db_path=db_path)
    return _persistence
