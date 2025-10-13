"""
Billing API endpoints
Handles Stripe integration, subscriptions, and plan management
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.utils.database import get_db
from app.models.agent import Agent, PlanTier
from app.middleware.tenant_resolver import get_current_agent_id
from app.services.billing import billing_service

router = APIRouter()

# Pydantic models
class CheckoutRequest(BaseModel):
    plan_tier: PlanTier
    billing_cycle: str = "monthly"  # monthly or yearly

class SubscriptionResponse(BaseModel):
    plan_tier: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    trial_ends_at: Optional[datetime]

class UsageResponse(BaseModel):
    leads_captured: int
    leads_limit: int
    ai_summaries: int
    ai_summaries_limit: int
    emails_sent: int
    emails_limit: int
    sms_sent: int
    sms_limit: int

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current subscription details"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get subscription details from Stripe
    subscription_info = await billing_service.get_subscription_info(agent)
    
    return SubscriptionResponse(
        plan_tier=agent.plan_tier.value,
        status=agent.status.value,
        current_period_start=subscription_info['current_period_start'] if subscription_info else None,
        current_period_end=subscription_info['current_period_end'] if subscription_info else None,
        cancel_at_period_end=subscription_info['cancel_at_period_end'] if subscription_info else False,
        trial_ends_at=agent.trial_ends_at
    )

@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    checkout_request: CheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for plan upgrade"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create success and cancel URLs with subdomain redirect
    base_url = str(request.base_url).rstrip('/')
    success_url = f"https://login.ezrealtor.app/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/pricing?checkout=cancelled"
    
    # Create checkout session
    checkout_data = await billing_service.create_checkout_session(
        agent=agent,
        plan_tier=checkout_request.plan_tier,
        success_url=success_url,
        cancel_url=cancel_url
    )
    
    # Update agent with customer ID if created
    if not agent.stripe_customer_id:
        customer_id = await billing_service.create_customer(agent)
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(stripe_customer_id=customer_id)
        )
        await db.commit()
    
    return checkout_data

@router.post("/portal", response_model=dict)
async def create_billing_portal_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe billing portal session for subscription management"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create return URL
    base_url = str(request.base_url).rstrip('/')
    return_url = f"{base_url}/billing"
    
    # Create billing portal session
    portal_data = await billing_service.create_customer_portal_session(
        agent=agent,
        return_url=return_url
    )
    
    return portal_data

@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    db: AsyncSession = Depends(get_db),
    immediate: bool = False
):
    """Cancel current subscription"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Cancel subscription
    success = await billing_service.cancel_subscription(
        agent=agent,
        cancel_at_period_end=not immediate
    )
    
    return {"success": success, "message": "Subscription cancelled"}

@router.post("/change-plan")
async def change_plan(
    new_plan: CheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Change subscription plan"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update subscription
    success = await billing_service.update_subscription(
        agent=agent,
        new_plan_tier=new_plan.plan_tier
    )
    
    return {"success": success, "message": "Plan updated"}

@router.get("/usage", response_model=UsageResponse)
async def get_usage_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current month usage statistics"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # TODO: Query usage_counters table for current month
    # TODO: Get plan limits from plan_catalog
    
    return UsageResponse(
        leads_captured=0,
        leads_limit=100,
        ai_summaries=0,
        ai_summaries_limit=100,
        emails_sent=0,
        emails_limit=1000,
        sms_sent=0,
        sms_limit=100
    )

@router.get("/plans", response_model=List[dict])
async def get_available_plans():
    """Get all available subscription plans"""
    
    plans = [
        {
            "tier": "trial",
            "name": "Free Trial",
            "price_monthly": 0,
            "price_yearly": 0,
            "stripe_price_id": os.getenv("STRIPE_FREE_PRICE_ID"),
            "features": [
                "10 leads per month",
                "Basic AI summaries",
                "Email notifications",
                "Subdomain only"
            ],
            "limits": {
                "leads": 10,
                "ai_summaries": 10,
                "emails": 100,
                "sms": 0,
                "custom_domains": 0
            }
        },
        {
            "tier": "booster",
            "name": "Booster",
            "price_monthly": 97,
            "price_yearly": 970,
            "stripe_price_id": os.getenv("STRIPE_BASIC_PRICE_ID"),
            "features": [
                "Unlimited leads",
                "AI lead scoring",
                "Email & SMS notifications",
                "Custom domain",
                "Basic integrations"
            ],
            "limits": {
                "leads": -1,
                "ai_summaries": -1,
                "emails": -1,
                "sms": 100,
                "custom_domains": 1
            }
        },
        {
            "tier": "pro",
            "name": "Professional",
            "price_monthly": 297,
            "price_yearly": 2970,
            "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID"),
            "features": [
                "Everything in Booster",
                "Advanced AI analysis",
                "Phone callbacks",
                "Multiple domains",
                "CRM integrations", 
                "White-label options",
                "Priority support"
            ],
            "limits": {
                "leads": -1,
                "ai_summaries": -1,
                "emails": -1,
                "sms": -1,
                "custom_domains": -1
            }
        }
    ]
    
    return plans