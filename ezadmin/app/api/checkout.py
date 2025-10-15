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
import uuid
import re

from app.utils.database import get_db
from app.models.agent import Agent, AgentStatus, PlanTier
from app.utils.slug_generator import generate_unique_slug

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
        
        # Get the actual subscription to determine the correct plan
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Determine plan tier from Stripe price ID
        actual_plan_tier = PlanTier.TRIAL  # default
        for item in subscription['items']['data']:
            price_id = item['price']['id']
            logger.info(f"Checking price_id from Stripe: {price_id}")
            
            if price_id == os.getenv('STRIPE_Starter_PRICE_ID'):
                actual_plan_tier = PlanTier.STARTER
                logger.info(f"Matched STARTER plan")
            elif price_id == os.getenv('STRIPE_Growth_PRICE_ID'):
                actual_plan_tier = PlanTier.GROWTH
                logger.info(f"Matched GROWTH plan")
            elif price_id == os.getenv('STRIPE_Scale_PRICE_ID'):
                actual_plan_tier = PlanTier.SCALE
                logger.info(f"Matched SCALE plan")
            elif price_id == os.getenv('STRIPE_Pro_PRICE_ID'):
                actual_plan_tier = PlanTier.PRO
                logger.info(f"Matched PRO plan")
            elif price_id == os.getenv('STRIPE_FreeTrial_PRICE_ID'):
                actual_plan_tier = PlanTier.TRIAL
                logger.info(f"Matched TRIAL plan")
            else:
                logger.warning(f"Unknown price_id: {price_id} - defaulting to TRIAL")
        
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
            # Generate unique slug for new agent
            unique_slug = await generate_unique_slug(customer.email, db)
            
            # Generate temporary password for new user
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # Hash the password
            from app.utils.security import hash_password
            hashed_password = hash_password(temp_password)
            
            # Create new agent if none found
            agent = Agent(
                email=customer.email,
                name=customer.name or 'New User',
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=AgentStatus.ACTIVE,
                plan_tier=actual_plan_tier,  # Use actual plan from Stripe
                slug=unique_slug,
                password_hash=hashed_password  # Set initial password
            )
            db.add(agent)
            await db.commit()
            await db.refresh(agent)
            
            # Store temp password to send in email
            agent.temp_password = temp_password
        else:
            # Update existing agent with correct plan from Stripe
            agent.plan_tier = actual_plan_tier
            agent.status = AgentStatus.ACTIVE
            agent.stripe_customer_id = customer_id
            agent.stripe_subscription_id = subscription_id
            await db.commit()
        
        # Send welcome email with login instructions
        try:
            from app.utils.email_brevo import email_service
            # Get temp password if this is a new agent
            temp_password = getattr(agent, 'temp_password', None)
            
            email_sent = await email_service.send_welcome_email(
                to_email=customer.email,
                to_name=customer.name or agent.name,
                plan_tier=agent.plan_tier,
                temp_password=temp_password  # Send password for new users
            )
            if email_sent:
                logger.info(f"Welcome email sent to {customer.email}")
            else:
                logger.warning(f"Failed to send welcome email to {customer.email}")
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
        
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
    """Agent dashboard - requires authentication or valid checkout token"""
    from app.middleware.auth import get_current_agent, get_agent_slug_from_host
    
    # Check for authenticated agent first
    current_agent = await get_current_agent(request, db)
    
    # Get subdomain from request
    host = request.headers.get("host", "")
    expected_slug = get_agent_slug_from_host(host)
    
    if current_agent:
        # Verify the agent matches the subdomain
        if expected_slug and current_agent.slug != expected_slug:
            # Redirect to correct subdomain or login
            return RedirectResponse(url=f"https://login.ezrealtor.app?redirect_to={current_agent.slug}")
        
        return templates.TemplateResponse("realtor_dashboard.html", {
            "request": request,
            "agent": current_agent,
            "is_new_customer": False
        })
    
    # Handle new customer with checkout token
    if token and token.startswith("checkout_") and expected_slug:
        # Find agent by slug for new customer flow
        result = await db.execute(
            select(Agent).where(Agent.slug == expected_slug)
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            return templates.TemplateResponse("realtor_dashboard.html", {
                "request": request,
                "agent": agent,
                "is_new_customer": True
            })
@router.post("/checkout/create-session")
async def create_checkout_session(
    request: Request,
    plan_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for tiered lead-based plans"""
    from app.middleware.auth import get_current_agent
    
    current_agent = await get_current_agent(request, db)
    if not current_agent:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    plan = plan_data.get("plan", "starter")
    
    # Map plan to Stripe price ID
    STRIPE_PLAN_MAPPING = {
        "starter": os.getenv('STRIPE_Starter_PRICE_ID'),
        "growth": os.getenv('STRIPE_Growth_PRICE_ID'), 
        "scale": os.getenv('STRIPE_Scale_PRICE_ID'),
        "pro": os.getenv('STRIPE_Pro_PRICE_ID'),
    }

    price_id = STRIPE_PLAN_MAPPING.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_agent.email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"https://ezrealtor.app/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://ezrealtor.app/onboarding",
        )
        
        return {"checkout_url": checkout_session.url}
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")
    # No authentication and no valid token - redirect to login
    if expected_slug:
        return RedirectResponse(url=f"https://login.ezrealtor.app?redirect_to={expected_slug}")
    else:
        return RedirectResponse(url="https://login.ezrealtor.app")