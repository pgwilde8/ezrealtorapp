"""
Phone Number Management API
Handles phone number provisioning, search, and management for agents
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from app.utils.database import get_db
from app.models.agent import Agent
from app.services.twilio_phone_provisioning import twilio_provisioning_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


# ===== Pydantic Models =====

class PhoneNumberSearchRequest(BaseModel):
    area_code: Optional[str] = Field(None, description="Desired area code (e.g., '716', '212')")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")


class PhoneNumberSearchResponse(BaseModel):
    phone_number: str
    friendly_name: str
    locality: Optional[str]
    region: Optional[str]
    postal_code: Optional[str]
    capabilities: dict
    estimated_monthly_cost: float


class PhoneNumberPurchaseRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to purchase in E.164 format")
    friendly_name: Optional[str] = Field(None, description="Custom name for the number")


class PhoneNumberPurchaseResponse(BaseModel):
    success: bool
    phone_number: str
    twilio_sid: str
    monthly_cost: float
    status: str
    message: str


class PhoneNumberDetailsResponse(BaseModel):
    phone_number: Optional[str]
    twilio_sid: Optional[str]
    friendly_name: Optional[str]
    status: Optional[str]
    activated_at: Optional[datetime]
    capabilities: Optional[dict]
    monthly_cost: float


class PhoneNumberReleaseResponse(BaseModel):
    success: bool
    message: str


# ===== Helper Functions =====

async def get_agent_from_request(request: Request, db: AsyncSession) -> Agent:
    """Get agent from tenant_slug in request state"""
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    
    if not tenant_slug:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.execute(
        select(Agent).where(Agent.slug == tenant_slug)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


# ===== API Endpoints =====

@router.get("/search", response_model=List[PhoneNumberSearchResponse])
async def search_available_numbers(
    area_code: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for available phone numbers
    
    Query parameters:
    - area_code: Filter by area code (e.g., "716", "212")
    - limit: Max results (default 10, max 50)
    """
    logger.info(f"Searching for numbers with area_code={area_code}, limit={limit}")
    
    available_numbers = twilio_provisioning_service.search_available_numbers(
        area_code=area_code,
        limit=min(limit, 50)
    )
    
    if not available_numbers:
        return []
    
    return available_numbers


@router.post("/purchase", response_model=PhoneNumberPurchaseResponse)
async def purchase_phone_number(
    request: Request,
    purchase_request: PhoneNumberPurchaseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase a phone number for the authenticated agent
    
    Requirements:
    - Agent must not already have an active phone number
    - Agent must be on Growth plan or higher (you can add this check)
    """
    agent = await get_agent_from_request(request, db)
    
    # Check if agent already has a phone number
    if agent.twilio_phone_number and agent.twilio_phone_status == "active":
        raise HTTPException(
            status_code=400, 
            detail=f"You already have an active phone number: {agent.twilio_phone_number}"
        )
    
    # Check plan tier (optional - uncomment to enforce)
    # if agent.plan_tier not in ['growth', 'scale', 'pro']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Phone numbers are only available on Growth plan or higher"
    #     )
    
    logger.info(f"Purchasing number {purchase_request.phone_number} for agent {agent.slug}")
    
    # Purchase the number
    result = twilio_provisioning_service.purchase_phone_number(
        phone_number=purchase_request.phone_number,
        agent_slug=agent.slug,
        friendly_name=purchase_request.friendly_name or f"EZRealtor - {agent.name}"
    )
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to purchase phone number. Please try another number or contact support."
        )
    
    # Update agent record
    agent.twilio_phone_number = result["phone_number"]
    agent.twilio_phone_sid = result["sid"]
    agent.twilio_phone_status = "active"
    agent.twilio_phone_activated_at = datetime.utcnow()
    agent.twilio_phone_friendly_name = result["friendly_name"]
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Successfully assigned number {result['phone_number']} to agent {agent.slug}")
    
    return PhoneNumberPurchaseResponse(
        success=True,
        phone_number=result["phone_number"],
        twilio_sid=result["sid"],
        monthly_cost=result["monthly_cost"],
        status="active",
        message=f"Phone number {result['phone_number']} successfully activated!"
    )


@router.get("/me", response_model=PhoneNumberDetailsResponse)
async def get_my_phone_number(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated agent's phone number details
    """
    agent = await get_agent_from_request(request, db)
    
    if not agent.twilio_phone_number:
        return PhoneNumberDetailsResponse(
            phone_number=None,
            twilio_sid=None,
            friendly_name=None,
            status=None,
            activated_at=None,
            capabilities=None,
            monthly_cost=1.15
        )
    
    # Get live details from Twilio
    details = None
    if agent.twilio_phone_sid:
        details = twilio_provisioning_service.get_phone_number_details(agent.twilio_phone_sid)
    
    return PhoneNumberDetailsResponse(
        phone_number=agent.twilio_phone_number,
        twilio_sid=agent.twilio_phone_sid,
        friendly_name=agent.twilio_phone_friendly_name,
        status=agent.twilio_phone_status,
        activated_at=agent.twilio_phone_activated_at,
        capabilities=details.get("capabilities") if details else None,
        monthly_cost=1.15
    )


@router.delete("/me", response_model=PhoneNumberReleaseResponse)
async def release_my_phone_number(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Release (cancel) the authenticated agent's phone number
    
    WARNING: This action is permanent and cannot be undone.
    The phone number will be returned to Twilio's pool.
    """
    agent = await get_agent_from_request(request, db)
    
    if not agent.twilio_phone_number or not agent.twilio_phone_sid:
        raise HTTPException(
            status_code=404,
            detail="You don't have an active phone number"
        )
    
    logger.info(f"Releasing phone number {agent.twilio_phone_number} for agent {agent.slug}")
    
    # Release from Twilio
    success = twilio_provisioning_service.release_phone_number(agent.twilio_phone_sid)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to release phone number. Please contact support."
        )
    
    # Update agent record
    old_number = agent.twilio_phone_number
    agent.twilio_phone_number = None
    agent.twilio_phone_sid = None
    agent.twilio_phone_status = "cancelled"
    
    await db.commit()
    
    logger.info(f"Successfully released number {old_number} from agent {agent.slug}")
    
    return PhoneNumberReleaseResponse(
        success=True,
        message=f"Phone number {old_number} has been released and cancelled."
    )


@router.get("/stats")
async def get_phone_number_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get call and SMS statistics for the agent's phone number
    This is a placeholder - implement based on your analytics needs
    """
    agent = await get_agent_from_request(request, db)
    
    if not agent.twilio_phone_number:
        return {
            "has_phone_number": False,
            "phone_number": None,
            "stats": None
        }
    
    # TODO: Query your leads/calls table for statistics
    # For now, return basic info
    return {
        "has_phone_number": True,
        "phone_number": agent.twilio_phone_number,
        "status": agent.twilio_phone_status,
        "activated_at": agent.twilio_phone_activated_at,
        "stats": {
            "total_calls": 0,  # TODO: Implement
            "total_sms": 0,     # TODO: Implement
            "this_month_calls": 0,
            "this_month_sms": 0
        }
    }

