"""
Usage API endpoints
Track and display plan usage limits
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.utils.database import get_db
from app.models.agent import Agent
from app.services.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
async def get_usage_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current usage statistics for the logged-in agent
    """
    # Get agent from subdomain
    from app.middleware.auth import get_agent_slug_from_host
    
    host = request.headers.get("host", "")
    tenant_slug = get_agent_slug_from_host(host)
    
    if not tenant_slug:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # Get agent
    result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get usage stats
    stats = await usage_tracker.get_usage_stats(agent, db)
    
    return stats

