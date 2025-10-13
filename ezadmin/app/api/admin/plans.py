"""
Admin Plans API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_plans():
    """List all plans (admin only)"""
    return {"message": "Admin plans endpoint - coming soon"}

@router.post("/")
async def create_plan():
    """Create new plan (admin only)"""
    return {"message": "Create plan - coming soon"}
