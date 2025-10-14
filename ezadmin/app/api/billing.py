"""
Billing API endpoints
Handles Stripe integration, subscriptions, and plan management
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.utils.database import get_db
from app.models.agent import Agent, PlanTier
from app.middleware.tenant_resolver import get_current_agent_id
from app.services.billing import billing_service
from app.utils.slug_generator import generate_unique_slug
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class CheckoutRequest(BaseModel):
    plan_tier: PlanTier
    billing_cycle: str = "monthly"  # monthly or yearly

class AnonymousCheckoutRequest(BaseModel):
    plan_tier: PlanTier
    email: str
    name: str
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

@router.get("/checkout")
async def simple_checkout_redirect(plan: str):
    """Simple GET endpoint for checkout with URL parameters"""
    
    # Map URL plan parameter to our plan tiers  
    plan_mapping = {
        'trial': 'trial',
        'pro': 'pro',  # Your "pro" maps to our basic price ($97)
        'enterprise': 'enterprise'  # Enterprise maps to pro price ($297)
    }
    
    if plan not in plan_mapping:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")
    
    price_ids = {
        "trial": os.getenv("STRIPE_FREE_PRICE_ID"),
        "pro": os.getenv("STRIPE_BASIC_PRICE_ID"), 
        "enterprise": os.getenv("STRIPE_PRO_PRICE_ID"),
    }
    
    mapped_plan = plan_mapping[plan]
    price_id = price_ids.get(mapped_plan)
    
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Price not configured for plan: {plan}")
    
    return {
        "plan": plan,
        "mapped_plan": mapped_plan, 
        "price_id": price_id,
        "status": "success",
        "message": f"Checkout endpoint for {plan} plan is working",
        "next_step": "Use POST /checkout-anonymous with email and name to create full Stripe session"
    }

@router.post("/checkout-anonymous", response_model=dict)
async def create_anonymous_checkout_session(
    checkout_request: AnonymousCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for new user (no authentication required)"""
    
    # Check if email already exists
    result = await db.execute(select(Agent).where(Agent.email == checkout_request.email))
    existing_agent = result.scalar_one_or_none()
    
    if existing_agent:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered. Please login to manage your subscription."
        )
    
    # Create success and cancel URLs
    base_url = str(request.base_url).rstrip('/')
    success_url = f"{base_url}/api/v1/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/pricing?checkout=cancelled"
    
    try:
        # Import stripe here to avoid circular imports
        import stripe
        
        # Debug the stripe key loading
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        logger.info(f"Stripe key loaded: {'LOADED' if stripe_key else 'MISSING'}")
        
        if not stripe_key:
            raise HTTPException(status_code=500, detail="Stripe API key not configured")
        
        stripe.api_key = stripe_key
        
        # Create Stripe customer first
        customer = stripe.Customer.create(
            email=checkout_request.email,
            name=checkout_request.name,
            metadata={
                "plan_tier": checkout_request.plan_tier.value,
                "source": "anonymous_checkout"
            }
        )
        
        # Create checkout session
        price_ids = {
            "trial": os.getenv("STRIPE_FREE_PRICE_ID"),
            "pro": os.getenv("STRIPE_BASIC_PRICE_ID"),
            "enterprise": os.getenv("STRIPE_PRO_PRICE_ID"),
        }
        
        price_id = price_ids.get(checkout_request.plan_tier)
        if not price_id:
            raise HTTPException(status_code=400, detail=f"Invalid plan tier: {checkout_request.plan_tier}")
        
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            billing_address_collection='required',
            metadata={
                "email": checkout_request.email,
                "name": checkout_request.name,
                "plan_tier": checkout_request.plan_tier.value,
                "source": "anonymous_checkout"
            }
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except Exception as e:
        logger.error(f"Anonymous checkout error: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Checkout error: {str(e)}")

@router.get("/checkout/success")
async def checkout_success(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle successful Stripe checkout redirect"""
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Get customer and subscription info
            customer_id = session.customer
            subscription_id = session.subscription
            
            # Get customer details
            customer = stripe.Customer.retrieve(customer_id)
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Extract metadata
            email = session.metadata.get('email') or customer.email
            name = session.metadata.get('name') or customer.name
            plan_tier = session.metadata.get('plan_tier', 'trial')
            
            # Create or update agent record
            from sqlalchemy import select
            from app.models.agent import Agent, PlanTier, AgentStatus
            
            result = await db.execute(select(Agent).where(Agent.email == email))
            existing_agent = result.scalar_one_or_none()
            
            if existing_agent:
                # Update existing agent
                existing_agent.plan_tier = PlanTier(plan_tier)
                existing_agent.status = AgentStatus.ACTIVE
                existing_agent.stripe_customer_id = customer_id
                existing_agent.stripe_subscription_id = subscription_id
                agent = existing_agent
            else:
                # Generate unique slug for new agent
                unique_slug = await generate_unique_slug(email, db)
                
                # Create new agent
                import uuid
                agent = Agent(
                    id=uuid.uuid4(),
                    email=email,
                    name=name,
                    plan_tier=PlanTier(plan_tier),
                    status=AgentStatus.ACTIVE,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    slug=unique_slug
                )
                db.add(agent)
            
            await db.commit()
            
            # Redirect to login with success message
            return RedirectResponse(
                url=f"https://login.ezrealtor.app?welcome=true&plan={plan_tier}",
                status_code=302
            )
        else:
            # Payment not completed
            return RedirectResponse(
                url="https://ezrealtor.app/pricing?error=payment_failed",
                status_code=302
            )
            
    except Exception as e:
        logger.error(f"Checkout success error: {e}")
        # Redirect to pricing with error
        return RedirectResponse(
            url="https://ezrealtor.app/pricing?error=checkout_failed",
            status_code=302
        )

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
            "tier": "pro",
            "name": "Pro",
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
            "tier": "enterprise",
            "name": "Enterprise",
            "price_monthly": 297,
            "price_yearly": 2970,
            "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID"),
            "features": [
                "Everything in Pro",
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