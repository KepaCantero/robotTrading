"""
Strategy Controller - Strategy API endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


@router.get("/")
async def get_strategies():
    """Get available strategies."""
    return {"strategies": []}


@router.post("/execute")
async def execute_strategy():
    """Execute a strategy."""
    return {"status": "executing"}
