"""
Admin Webhooks API endpoints
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_webhooks():
    """List webhook events (admin only)"""
    return {"message": "Admin webhooks endpoint - coming soon"}

@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str):
    """Get webhook details (admin only)"""
    return {"message": f"Webhook {webhook_id} details - coming soon"}
