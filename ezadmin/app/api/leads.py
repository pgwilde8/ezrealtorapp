"""
Leads API endpoints
Handles lead capture, management, and AI processing
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.utils.database import get_db
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.agent import Agent
from app.models.provider_credentials import ProviderCredential
from app.middleware.tenant_resolver import get_current_agent_id, require_tenant
from app.services.ai_lead_processor import AILeadProcessor

router = APIRouter()

# Pydantic models for request/response
class LeadCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    lead_type: str  # 'buyer_interest' or 'home_valuation'
    
    # Property info (for home valuation)
    property_address: Optional[str] = None
    square_footage: Optional[str] = None
    year_built: Optional[str] = None
    property_type: Optional[str] = None
    lot_size: Optional[str] = None
    features: Optional[List[str]] = []
    recent_improvements: Optional[str] = None
    selling_timeline: Optional[str] = None
    
    # Buyer info (for buyer interest)
    budget_range: Optional[str] = None
    bedrooms: Optional[str] = None
    bathrooms: Optional[str] = None
    preferred_areas: Optional[str] = None
    priorities: Optional[List[str]] = []
    important_features: Optional[str] = None
    timeline: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = {}
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer: Optional[str] = None

class LeadResponse(BaseModel):
    id: str  # UUID as string
    full_name: Optional[str]
    email: Optional[str]
    phone_e164: Optional[str]
    source: str
    status: str
    ai_summary: Optional[str]
    ai_score: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/", response_model=dict)
async def create_lead(
    lead_data: LeadCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new lead from form submission with AI processing"""
    
    # Get tenant context
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    if not tenant_slug:
        # Fallback to require_tenant if not set by middleware
        tenant_slug = await require_tenant(request)
    
    # Find agent by tenant slug
    result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Determine lead source based on lead_type
    lead_source = LeadSource.WEBSITE_FORM
    if lead_data.lead_type == 'home_valuation':
        lead_source = LeadSource.HOME_VALUATION_TOOL
    elif lead_data.lead_type == 'buyer_interest':
        lead_source = LeadSource.BUYER_INTEREST_FORM
    
    # Create lead record
    lead = Lead(
        agent_id=agent.id,
        full_name=lead_data.full_name,
        email=lead_data.email,
        phone_e164=lead_data.phone,  # Will be normalized by AI processor
        source=lead_source,
        address_line=lead_data.property_address,
        message=lead_data.important_features or lead_data.recent_improvements,
        utm_source=lead_data.utm_source,
        utm_medium=lead_data.utm_medium,
        utm_campaign=lead_data.utm_campaign,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        raw_form_data=lead_data.dict()
    )
    
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    
    # Queue AI processing and notifications
    background_tasks.add_task(process_lead_with_ai, str(lead.id), agent.id, lead_data.dict())
    
    return {
        "success": True,
        "lead_id": str(lead.id),
        "message": "Lead captured successfully. You'll receive AI insights within minutes!"
    }

@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[LeadStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """List leads for current agent"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    query = select(Lead).where(Lead.agent_id == agent_id)
    
    if status:
        query = query.where(Lead.status == status.value)
    
    query = query.offset(skip).limit(limit).order_by(Lead.created_at.desc())
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return leads

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get specific lead by ID"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(Lead).where(
            and_(Lead.id == lead_id, Lead.agent_id == agent_id)
        )
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return lead

@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status: LeadStatus,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update lead status"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(Lead).where(
            and_(Lead.id == lead_id, Lead.agent_id == agent_id)
        )
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.status = status.value
    await db.commit()
    
    return {"success": True, "status": status.value}

async def process_lead_with_ai(lead_id: str, agent_id: str, lead_data: Dict[str, Any]):
    """Background task to process lead with AI and send notifications"""
    try:
        from app.utils.database import get_async_session
        
        async with get_async_session() as db:
            # Get agent credentials
            credentials_result = await db.execute(
                select(ProviderCredential).where(ProviderCredential.agent_id == agent_id)
            )
            credentials = credentials_result.scalars().all()
            
            # Convert to dict
            agent_credentials = {}
            for cred in credentials:
                agent_credentials[cred.provider_name] = cred.encrypted_credentials
            
            # Initialize AI processor
            ai_processor = AILeadProcessor(agent_credentials)
            
            # Process based on lead type
            if lead_data.get('lead_type') == 'buyer_interest':
                result = await ai_processor.process_buyer_lead(lead_data)
            elif lead_data.get('lead_type') == 'home_valuation':
                result = await ai_processor.process_valuation_lead(lead_data)
            else:
                result = {'status': 'unknown_type'}
            
            # Update lead with AI insights
            lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_result.scalar_one_or_none()
            
            if lead and result.get('status') == 'processed':
                # Store AI insights
                ai_insights = result.get('ai_insights', {})
                lead.ai_summary = json.dumps(ai_insights)
                lead.ai_score = _calculate_lead_score(lead_data, ai_insights)
                lead.status = LeadStatus.QUALIFIED if lead.ai_score > 70 else LeadStatus.NEW
                
                await db.commit()
                
    except Exception as e:
        print(f"Error processing lead {lead_id}: {e}")

def _calculate_lead_score(lead_data: Dict[str, Any], ai_insights: Dict[str, Any]) -> int:
    """Calculate lead score based on data completeness and AI insights"""
    score = 0
    
    # Basic info completeness (40 points)
    if lead_data.get('email'):
        score += 15
    if lead_data.get('phone'):
        score += 15
    if lead_data.get('full_name'):
        score += 10
    
    # Intent indicators (40 points)
    if lead_data.get('timeline') in ['asap', '1_3_months', 'immediately']:
        score += 20
    elif lead_data.get('timeline') in ['3_6_months']:
        score += 15
    elif lead_data.get('timeline'):
        score += 10
    
    if lead_data.get('budget_range') and lead_data['budget_range'] != '':
        score += 15
    
    if lead_data.get('property_address'):  # Home valuation leads
        score += 5
    
    # Engagement level (20 points)
    if lead_data.get('important_features') and len(lead_data['important_features']) > 50:
        score += 10
    if lead_data.get('recent_improvements') and len(lead_data['recent_improvements']) > 30:
        score += 10
    if lead_data.get('preferred_areas') and len(lead_data['preferred_areas']) > 20:
        score += 10
    if len(lead_data.get('priorities', [])) > 2:
        score += 5
    
    return min(score, 100)

async def process_new_lead(lead_id: int, agent_id: int):
    """Background task to process new lead with AI and notifications"""
    # Legacy function - kept for compatibility
    pass