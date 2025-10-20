"""
Leads API endpoints
Handles lead capture, management, and AI processing
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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
    
    # Contact form (for general inquiries)
    message: Optional[str] = None
    
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
    ai_priority: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AgentStatsResponse(BaseModel):
    totalLeads: int
    newLeadsToday: int
    hotLeads: int
    hotLeadsPercentage: int
    aiAnalyzed: int
    aiSuccessRate: int
    conversionRate: int
    conversionImprovement: int

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
    host = request.headers.get("host", "")
    
    # Log for debugging
    print(f"[LEAD CREATE] Host: {host}, Tenant slug from state: {tenant_slug}")
    
    if not tenant_slug:
        # Fallback to require_tenant if not set by middleware
        try:
            tenant_slug = await require_tenant(request)
            print(f"[LEAD CREATE] Tenant slug from require_tenant: {tenant_slug}")
        except HTTPException as e:
            print(f"[LEAD CREATE] Failed to get tenant: {e.detail}")
            raise HTTPException(
                status_code=404, 
                detail=f"Unable to determine realtor from subdomain. Host: {host}"
            )
    
    # Find agent by tenant slug
    result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
    agent = result.scalar_one_or_none()
    
    if not agent:
        print(f"[LEAD CREATE] Agent not found for slug: {tenant_slug}")
        raise HTTPException(
            status_code=404, 
            detail=f"Realtor profile not found for '{tenant_slug}'. Please contact support."
        )
    
    # Determine lead source based on lead_type
    lead_source = LeadSource.WEBSITE_FORM
    if lead_data.lead_type == 'home_valuation':
        lead_source = LeadSource.HOME_VALUATION_TOOL
    elif lead_data.lead_type == 'buyer_interest':
        lead_source = LeadSource.BUYER_INTEREST_FORM
    elif lead_data.lead_type == 'contact_form':
        lead_source = LeadSource.CONTACT_FORM
    
    # Determine message content based on lead type
    message_content = None
    if lead_data.lead_type == 'contact_form':
        message_content = lead_data.message
    else:
        message_content = lead_data.important_features or lead_data.recent_improvements
    
    # Create lead record
    try:
        lead = Lead(
            agent_id=agent.id,
            full_name=lead_data.full_name,
            email=lead_data.email,
            phone_e164=lead_data.phone,  # Will be normalized by AI processor
            source=lead_source,
            address_line=lead_data.property_address,
            message=message_content,
            utm_source=lead_data.utm_source,
            utm_medium=lead_data.utm_medium,
            utm_campaign=lead_data.utm_campaign,
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            raw_form_data=lead_data.dict()
        )
        
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        print(f"[LEAD CREATE] Successfully created lead {lead.id} for agent {agent.slug}")
    except Exception as db_error:
        await db.rollback()
        print(f"[LEAD CREATE] Database error: {str(db_error)}")
        print(f"[LEAD CREATE] Error type: {type(db_error).__name__}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save lead. This may indicate a database migration is needed. Error: {str(db_error)[:100]}"
        )
    
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
    limit: int = Query(100, le=100),
    status: Optional[LeadStatus] = None,
    priority: Optional[str] = Query(None, description="Filter by priority: hot, warm, cold"),
    db: AsyncSession = Depends(get_db)
):
    """List leads for current agent"""
    
    agent_id = await get_current_agent_id(request)
    if agent_id:
        agent_filter = Lead.agent_id == agent_id
    else:
        # For now, show all leads if no agent context (development mode)
        agent_filter = True
    
    query = select(Lead).where(agent_filter)
    
    if status:
        query = query.where(Lead.status == status.value)
        
    if priority:
        query = query.where(Lead.ai_priority == priority)
    
    query = query.offset(skip).limit(limit).order_by(Lead.created_at.desc())
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    # Convert leads to response format
    lead_responses = []
    for lead in leads:
        lead_responses.append(LeadResponse(
            id=str(lead.id),
            full_name=lead.full_name,
            email=lead.email,
            phone_e164=lead.phone_e164,
            source=lead.source,
            status=lead.status,
            ai_summary=lead.ai_summary,
            ai_score=lead.ai_score,
            ai_priority=lead.ai_priority,
            created_at=lead.created_at
        ))
    
    return lead_responses

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

@router.get("/agents/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for the current agent's dashboard"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        # For now, get global stats if no agent context
        agent_filter = True
    else:
        agent_filter = Lead.agent_id == agent_id
    
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