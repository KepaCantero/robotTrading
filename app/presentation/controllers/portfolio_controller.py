"""
Portfolio Controller - Portfolio API endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


@router.get("/")
async def get_portfolio():
    """Get portfolio data."""
    return {"portfolio": "data"}


@router.post("/")
async def create_portfolio():
    """Create new portfolio."""
    return {"status": "created"}
