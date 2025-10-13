"""
Admin Tenants API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_tenants():
    """List all tenants (admin only)"""
    return {"message": "Admin tenants endpoint - coming soon"}

@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant details (admin only)"""
    return {"message": f"Tenant {tenant_id} details - coming soon"}
