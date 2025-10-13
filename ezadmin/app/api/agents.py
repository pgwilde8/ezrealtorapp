"""
Agents API endpoints
Handles agent registration, profile management, and authentication
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.utils.database import get_db
from app.models.agent import Agent, PlanTier, AgentStatus
from app.middleware.tenant_resolver import get_current_agent_id

router = APIRouter()

# Pydantic models
class AgentCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    slug: str
    brokerage: Optional[str] = None
    license_number: Optional[str] = None
    service_areas: Optional[List[str]] = None
    bio: Optional[str] = None
    timezone: str = "America/New_York"

class AgentUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    brokerage: Optional[str] = None
    license_number: Optional[str] = None
    service_areas: Optional[List[str]] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None

class AgentResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    slug: str
    plan_tier: str
    status: str
    brokerage: Optional[str]
    license_number: Optional[str]
    service_areas: Optional[str]
    bio: Optional[str]
    timezone: str
    email_notifications: bool
    sms_notifications: bool
    created_at: datetime
    trial_ends_at: Optional[datetime]
    
    class Config:
        from_attributes = True

@router.post("/register", response_model=dict)
async def register_agent(
    agent_data: AgentCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new agent/realtor"""
    
    # Check if email already exists
    result = await db.execute(select(Agent).where(Agent.email == agent_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if slug already exists
    result = await db.execute(select(Agent).where(Agent.slug == agent_data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subdomain already taken")
    
    # Create new agent
    agent = Agent(
        email=agent_data.email,
        full_name=agent_data.full_name,
        phone=agent_data.phone,
        slug=agent_data.slug,
        brokerage=agent_data.brokerage,
        license_number=agent_data.license_number,
        service_areas=",".join(agent_data.service_areas) if agent_data.service_areas else None,
        bio=agent_data.bio,
        timezone=agent_data.timezone,
        plan_tier=PlanTier.TRIAL,
        status=AgentStatus.ACTIVE
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    # TODO: Create default subdomain via Cloudflare
    # TODO: Send welcome email
    
    return {
        "success": True,
        "agent_id": agent.id,
        "subdomain": f"{agent.slug}.ezrealtor.app",
        "message": "Agent registered successfully"
    }

@router.get("/profile", response_model=AgentResponse)
async def get_agent_profile(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current agent's profile"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@router.patch("/profile", response_model=AgentResponse)
async def update_agent_profile(
    updates: AgentUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update current agent's profile"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields that are provided
    update_data = updates.dict(exclude_unset=True)
    
    if "service_areas" in update_data and update_data["service_areas"]:
        update_data["service_areas"] = ",".join(update_data["service_areas"])
    
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return agent

@router.get("/check-slug/{slug}")
async def check_slug_availability(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if a slug/subdomain is available"""
    
    # Basic validation
    if len(slug) < 3 or len(slug) > 50:
        return {"available": False, "reason": "Slug must be 3-50 characters"}
    
    if not slug.isalnum():
        return {"available": False, "reason": "Slug must contain only letters and numbers"}
    
    # Reserved slugs
    reserved = ["www", "app", "api", "admin", "mail", "support", "help", "blog"]
    if slug.lower() in reserved:
        return {"available": False, "reason": "This subdomain is reserved"}
    
    # Check database
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    if result.scalar_one_or_none():
        return {"available": False, "reason": "Subdomain already taken"}
    
    return {"available": True}

@router.get("/stats")
async def get_agent_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get basic stats for current agent"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # TODO: Implement stats queries
    # - Total leads this month
    # - Lead conversion rate
    # - Usage metrics
    # - Plan limits
    
    return {
        "leads_this_month": 0,
        "total_leads": 0,
        "conversion_rate": 0.0,
        "plan_tier": "trial"
    }