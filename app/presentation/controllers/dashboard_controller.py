"""
Dashboard Controller - Dashboard API endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/")
async def get_dashboard():
    """Get dashboard data."""
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
