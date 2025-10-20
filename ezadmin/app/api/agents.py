"""
Agents API endpoints
Handles agent registration, profile management, and authentication
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import logging

from app.utils.database import get_db
from app.models.agent import Agent, PlanTier, AgentStatus
from app.models.lead import Lead
from app.middleware.tenant_resolver import get_current_agent_id
from app.middleware.auth import get_current_agent
from app.services.spaces_service import spaces_service

logger = logging.getLogger(__name__)

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

class AgentStatsResponse(BaseModel):
    totalLeads: int
    newLeadsToday: int
    hotLeads: int
    hotLeadsPercentage: int
    aiAnalyzed: int
    aiSuccessRate: int
    conversionRate: int
    conversionImprovement: int

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

@router.post("/me/upload-headshot")
async def upload_headshot(
    photo: UploadFile = File(...),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Upload agent profile headshot photo"""
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await photo.read()
    
    # Validate file size (5MB max for profile photos)
    if len(file_data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be less than 5MB")
    
    try:
        # Delete old headshot if exists
        if agent.headshot_url:
            spaces_service.delete_image(agent.headshot_url)
        
        # Upload new headshot (square format optimized)
        folder = f"agents/{agent.slug}"
        filename = "profile.jpg"
        
        full_url, thumbnail_url, metadata = spaces_service.upload_image(
            file_data=file_data,
            folder=folder,
            filename=filename,
            content_type=photo.content_type,
            max_size=(800, 800)  # Square profile photo
        )
        
        # Update agent record
        agent.headshot_url = full_url
        await db.commit()
        
        return {
            "success": True,
            "headshot_url": full_url,
            "thumbnail_url": thumbnail_url,
            "message": "Profile photo updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")


@router.post("/me/upload-secondary-photo")
async def upload_secondary_photo(
    photo: UploadFile = File(...),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Upload secondary photo for About section"""
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await photo.read()
    
    # Validate file size
    if len(file_data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be less than 5MB")
    
    try:
        # Delete old photo if exists
        if agent.secondary_photo_url:
            spaces_service.delete_image(agent.secondary_photo_url)
        
        # Upload new photo
        folder = f"agents/{agent.slug}"
        filename = "secondary.jpg"
        
        full_url, thumbnail_url, metadata = spaces_service.upload_image(
            file_data=file_data,
            folder=folder,
            filename=filename,
            content_type=photo.content_type,
            max_size=(1200, 900)  # Landscape format
        )
        
        # Update agent record
        agent.secondary_photo_url = full_url
        await db.commit()
        
        return {
            "success": True,
            "secondary_photo_url": full_url,
            "thumbnail_url": thumbnail_url,
            "message": "Secondary photo updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")


@router.post("/me/upload-logo")
async def upload_logo(
    photo: UploadFile = File(...),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Upload agency logo"""
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await photo.read()
    
    # Validate file size
    if len(file_data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo must be less than 2MB")
    
    try:
        # Delete old logo if exists
        if agent.logo_url:
            spaces_service.delete_image(agent.logo_url)
        
        # Upload new logo
        folder = f"agents/{agent.slug}"
        filename = "logo.png"
        
        full_url, thumbnail_url, metadata = spaces_service.upload_image(
            file_data=file_data,
            folder=folder,
            filename=filename,
            content_type=photo.content_type,
            max_size=(400, 150)  # Small logo
        )
        
        # Update agent record
        agent.logo_url = full_url
        await db.commit()
        
        return {
            "success": True,
            "logo_url": full_url,
            "thumbnail_url": thumbnail_url,
            "message": "Logo updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(e)}")


@router.delete("/me/photos/{photo_type}")
async def delete_agent_photo(
    photo_type: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Delete agent photo (headshot, secondary, or logo)"""
    
    if photo_type not in ['headshot', 'secondary', 'logo']:
        raise HTTPException(status_code=400, detail="Invalid photo type")
    
    # Get the current URL
    url_field = f"{photo_type}_url" if photo_type != 'secondary' else "secondary_photo_url"
    current_url = getattr(agent, url_field, None)
    
    if not current_url:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    try:
        # Delete from Spaces
        spaces_service.delete_image(current_url)
        
        # Update database
        setattr(agent, url_field, None)
        await db.commit()
        
        return {
            "success": True,
            "message": f"{photo_type.capitalize()} photo deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for the current agent's dashboard"""
    
    # Get agent from tenant slug (subdomain)
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    host = request.headers.get("host", "")
    
    logger.info(f"[STATS API] Host: {host}, tenant_slug from state: {tenant_slug}")
    print(f"[STATS API DEBUG] Host: {host}, tenant_slug: {tenant_slug}", flush=True)
    
    if not tenant_slug:
        logger.error(f"[STATS API] No tenant_slug found! Host was: {host}")
        print(f"[STATS API DEBUG] No tenant found! Host: {host}", flush=True)
        raise HTTPException(status_code=401, detail=f"Agent context required. Host: {host}")
    
    # Find agent by slug
    agent_result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
    agent = agent_result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Filter stats by this agent only
    agent_filter = Lead.agent_id == agent.id
    
    today = datetime.now().date()
    
    # Total leads
    total_leads_result = await db.execute(
        select(func.count(Lead.id)).where(agent_filter)
    )
    total_leads = total_leads_result.scalar() or 0
    
    # New leads today
    today_leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(agent_filter, func.date(Lead.created_at) == today)
        )
    )
    new_leads_today = today_leads_result.scalar() or 0
    
    # Hot leads (high AI score)
    hot_leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(agent_filter, Lead.ai_score >= 80)
        )
    )
    hot_leads = hot_leads_result.scalar() or 0
    hot_leads_percentage = int((hot_leads / total_leads * 100)) if total_leads > 0 else 0
    
    # AI analyzed leads
    ai_analyzed_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(agent_filter, Lead.ai_summary.isnot(None))
        )
    )
    ai_analyzed = ai_analyzed_result.scalar() or 0
    ai_success_rate = int((ai_analyzed / total_leads * 100)) if total_leads > 0 else 0
    
    # Mock conversion data (in production, track actual conversions)
    conversion_rate = 24
    conversion_improvement = 12
    
    return AgentStatsResponse(
        totalLeads=total_leads,
        newLeadsToday=new_leads_today,
        hotLeads=hot_leads,
        hotLeadsPercentage=hot_leads_percentage,
        aiAnalyzed=ai_analyzed,
        aiSuccessRate=ai_success_rate,
        conversionRate=conversion_rate,
        conversionImprovement=conversion_improvement
    )