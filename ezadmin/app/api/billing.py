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

# --- NEW: centralized price ID helper ---------------------------------------
def get_price_id_map() -> dict:
    return {
        "trial":   os.getenv("STRIPE_FreeTrial_PRICE_ID"),
        "starter": os.getenv("STRIPE_Starter_PRICE_ID"),
        "growth":  os.getenv("STRIPE_Growth_PRICE_ID"),
        "scale":   os.getenv("STRIPE_Scale_PRICE_ID"),
        "pro":     os.getenv("STRIPE_Pro_PRICE_ID"),
    }

def get_price_id_or_400(plan_key: str) -> str:
    price_id = get_price_id_map().get(plan_key)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Price not configured for plan: {plan_key}")
    return price_id
# -----------------------------------------------------------------------------


@router.get("/checkout")
async def simple_checkout_redirect(plan: str):
    """Simple GET endpoint for checkout with URL parameters"""

    # Map URL plan parameter to our plan tiers
    plan_mapping = {
        "trial": "trial",
        "starter": "starter",
        "growth": "growth",
        "scale": "scale",
        "pro": "pro",
    }

    if plan not in plan_mapping:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")

    mapped_plan = plan_mapping[plan]
    price_id = get_price_id_or_400(mapped_plan)

    return {
        "plan": plan,
        "mapped_plan": mapped_plan,
        "price_id": price_id,
        "status": "success",
        "message": f"Checkout endpoint for {plan} plan is working",
        "next_step": "Use POST /checkout-anonymous with email and name to create full Stripe session",
    }


@router.post("/checkout-anonymous", response_model=dict)
async def create_anonymous_checkout_session(
    checkout_request: AnonymousCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe checkout session for new user (no authentication required)"""

    # Check if email already exists
    result = await db.execute(select(Agent).where(Agent.email == checkout_request.email))
    existing_agent = result.scalar_one_or_none()

    if existing_agent:
        raise HTTPException(
            status_code=400,
            detail="Email already registered. Please login to manage your subscription.",
        )

    # Create success and cancel URLs
    base_url = str(request.base_url).rstrip("/")
    success_url = f"{base_url}/api/v1/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/pricing?checkout=cancelled"

    try:
        import stripe

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
                "plan_tier": checkout_request.plan_tier.value,  # <-- ensure .value
                "source": "anonymous_checkout",
            },
        )

        # Create checkout session (use centralized env lookup)
        price_id = get_price_id_or_400(checkout_request.plan_tier.value)

        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            billing_address_collection="required",
            metadata={
                "email": checkout_request.email,
                "name": checkout_request.name,
                "plan_tier": checkout_request.plan_tier.value,  # <-- ensure .value
                "source": "anonymous_checkout",
            },
        )

        return {"checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        logger.error(f"Anonymous checkout error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Checkout error: {str(e)}")


@router.get("/plans", response_model=List[dict])
async def get_available_plans():
    """Get all available subscription plans"""

    plans = [
        {
            "tier": "trial",
            "name": "Free Trial",
            "price_monthly": 0,
            "price_yearly": 0,
            "stripe_price_id": os.getenv("STRIPE_FreeTrial_PRICE_ID"),
            "features": [
                "50 leads per month",
                "Basic AI summaries",
                "Email notifications",
                "Full platform access",
            ],
            "limits": {
                "leads": 50,
                "ai_summaries": 50,
                "emails": 100,
                "sms": 0,
                "custom_domains": 0,
            },
        },
        {
            "tier": "starter",
            "name": "Starter",
            "price_monthly": 97,
            "price_yearly": 970,
            "stripe_price_id": os.getenv("STRIPE_Starter_PRICE_ID"),
            "features": [
                "150 leads per month",
                "Auto-bump protection",
                "Basic AI messaging",
                "Email notifications",
            ],
            "limits": {
                "leads": 150,
                "ai_summaries": 150,
                "emails": 500,
                "sms": 50,
                "custom_domains": 1,
            },
        },
        {
            "tier": "growth",
            "name": "Growth",
            "price_monthly": 147,
            "price_yearly": 1470,
            "stripe_price_id": os.getenv("STRIPE_Growth_PRICE_ID"),
            "features": [
                "500 leads per month",
                "Advanced AI messaging",
                "Weekend boost add-on available",
                "Priority support",
            ],
            "limits": {
                "leads": 500,
                "ai_summaries": 500,
                "emails": 1500,
                "sms": 200,
                "custom_domains": 3,
            },
        },
        {
            "tier": "scale",
            "name": "Scale",
            "price_monthly": 237,
            "price_yearly": 2370,
            "stripe_price_id": os.getenv("STRIPE_Scale_PRICE_ID"),
            "features": [
                "1500 leads per month",
                "Priority support",
                "All Growth features",
                "Advanced integrations",
            ],
            "limits": {
                "leads": 1500,
                "ai_summaries": 1500,
                "emails": 5000,
                "sms": 500,
                "custom_domains": 10,
            },
        },
        {
            "tier": "pro",
            "name": "Pro",
            "price_monthly": 437,
            "price_yearly": 4370,
            "stripe_price_id": os.getenv("STRIPE_Pro_PRICE_ID"),
            "features": [
                "4000 leads per month",
                "Custom integrations",
                "All Scale features",
                "White-label options",
                "Dedicated support",
            ],
            "limits": {
                "leads": 4000,
                "ai_summaries": 4000,
                "emails": 15000,
                "sms": 1500,
                "custom_domains": -1,
            },
        },
    ]

    return plans
