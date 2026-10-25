"""Fase 6 parte 2 — local ops panel endpoint.

GET /ops/status answers "is the paper stack healthy?" from real sources
only (see app/services/ops/paper_status.py). Admin-only: it exposes order
ids and account-level accounting state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from app.presentation.api.security import Principal, require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["ops"])

#: repo data/historical — the corpus the quote-staleness check reads
_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "historical"


@router.get("/status")
async def ops_status(
    principal: Principal = Depends(require_roles("admin")),  # noqa: ARG001
) -> dict[str, Any]:
    from app.infrastructure.persistence.database import get_session_factory
    from app.services.ops.paper_status import collect_status

    factory = get_session_factory()
    return await collect_status(factory, _DATA_DIR)
