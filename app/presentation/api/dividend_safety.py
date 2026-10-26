"""Bloque 2 (T2.3) — Dividend Safety Score endpoint.

GET /dividends/safety?tickers=KO,JNJ&as_of=2023-12-31&min_score=60
returns the PUBLIC formula (weights), per-symbol factors, gaps and the
filter verdict — the same report the backtest uses, no parallel truth.
Viewer role suffices (read-only, no account state).
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.presentation.api.security import Principal, get_current_principal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dividends", tags=["dividends"])


@router.get("/safety")
async def dividend_safety(
    tickers: str = Query(..., description="comma-separated tickers, e.g. KO,JNJ,INTC"),
    as_of: date | None = Query(None, description="PIT date (default: today)"),
    min_score: Decimal = Query(Decimal("60"), ge=0, le=100),
    principal: Principal = Depends(get_current_principal),  # noqa: ARG001
) -> dict[str, Any]:
    from app.backtesting.dividend_safety import DividendSafetyScorer

    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not symbols or len(symbols) > 50:
        raise HTTPException(422, "between 1 and 50 tickers")
    query_date = as_of or date.today()

    scorer = DividendSafetyScorer()
    inside, outside, reports = scorer.universe_filter(symbols, query_date, min_score=min_score)
    return {
        "as_of": query_date.isoformat(),
        "min_score": str(min_score),
        "formula": scorer.weights,
        "passes_filter": inside,
        "excluded": outside,
        "reports": [r.to_dict() for r in reports],
        "limitation": (
            "fundamentales SimFree tier desde ~2021 (ventanas 3a computan desde ~2024); "
            "ETFs sin estados — aplica a acciones"
        ),
    }
