"""
Checkout Success Handler
Handles post-checkout flow and subdomain setup
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import stripe
import os
import logging

from app.utils.database import get_db
from app.models.agent import Agent, AgentStatus, PlanTier

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter()

@router.get("/checkout/success")
async def checkout_success(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle successful checkout and set up user access"""
    
    try:
        # Retrieve the checkout session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != 'paid':
            raise HTTPException(status_code=400, detail="Payment not completed")
        
        # Get customer and subscription info
        customer_id = session.customer
        subscription_id = session.subscription
        
        # Find the agent by customer ID or email
        customer = stripe.Customer.retrieve(customer_id)
        
        result = await db.execute(
            select(Agent).where(Agent.stripe_customer_id == customer_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            # Try to find by email if customer ID didn't match
            result = await db.execute(
                select(Agent).where(Agent.email == customer.email)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                # Update with Stripe customer ID
                agent.stripe_customer_id = customer_id
                await db.commit()
        
        if not agent:
            # Create new agent if none found
            agent = Agent(
                email=customer.email,
                name=customer.name or 'New User',
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=AgentStatus.ACTIVE,
                plan_tier=PlanTier.BOOSTER,  # Default, will be updated by webhook
                slug=customer.email.split('@')[0].lower().replace('.', '').replace('_', '').replace('-', '')[:20]
            )
            db.add(agent)
            await db.commit()
            await db.refresh(agent)
        
        # TODO: Send welcome email with login instructions here
        
        # Redirect to thank you page instead of trying to auto-login
        return RedirectResponse(
            url=f"https://ezrealtor.app/checkout/thank-you?email={customer.email}&plan={agent.plan_tier}",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Error in checkout success: {e}")
        return templates.TemplateResponse("checkout_error.html", {
            "request": request,
            "error": "Something went wrong"
        })

@router.get("/checkout/cancelled")
async def checkout_cancelled(request: Request):
    """Handle cancelled checkout"""
    return RedirectResponse(url="/pricing?checkout=cancelled")

@router.get("/dashboard")
async def agent_dashboard(
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Agent dashboard after successful checkout"""
    
    # Get subdomain from request
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        if subdomain != "login":
            # Find agent by slug
            result = await db.execute(
                select(Agent).where(Agent.slug == subdomain)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                return templates.TemplateResponse("agent_dashboard.html", {
                    "request": request,
                    "agent": agent,
                    "is_new_customer": bool(token and token.startswith("checkout_"))
                })
    
    # Fallback to main site
    return RedirectResponse(url="https://ezrealtor.app/")