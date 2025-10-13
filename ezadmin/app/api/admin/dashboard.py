"""
Admin Dashboard API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def admin_dashboard():
    """Admin dashboard (admin only)"""
    return {"message": "Admin dashboard - coming soon"}

@router.get("/stats")
async def admin_stats():
    """Admin stats (admin only)"""
    return {"message": "Admin stats - coming soon"}
