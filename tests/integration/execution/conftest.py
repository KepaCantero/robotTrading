"""Fixtures de BD para tests de integración de ejecución.

asyncpg liga cada conexión a su event loop, y pytest crea un loop por test:
el singleton DatabaseManager no puede cachear el engine entre tests o todas
las conexiones quedan "attached to a different loop".
"""

from __future__ import annotations

import asyncio

import pytest

from app.infrastructure.persistence import database as _db


@pytest.fixture(autouse=True)
def _fresh_db_manager():
    """Reset del singleton de BD después de cada test (engine atado al loop)."""
    yield
    manager = getattr(_db, "_db_manager", None)
    if manager is not None:
        try:
            if manager.sync_engine is not None:
                manager.sync_engine.dispose()
        except Exception:
            pass
        try:
            if manager.async_engine is not None:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(manager.async_engine.dispose())
                loop.close()
        except Exception:
            pass
    _db._db_manager = None
    # reset de datos: cada test construye su propio estado desde cero
    try:
        import psycopg

        conn = psycopg.connect("host=127.0.0.1 port=5432 user=postgres dbname=algotrading")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("TRUNCATE lots, transactions, balance_snapshots, tax_reports, accounts CASCADE")
        conn.close()
    except Exception:
        pass  # sin BD local: los tests de BD fallarán por conexión, no por fixture
