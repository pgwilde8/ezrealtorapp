"""
Billing Management Service
Handle subscription creation, updates, and customer portal access
"""

import os
import stripe
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.agent import Agent, PlanTier

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class BillingService:
    """Manages Stripe billing operations"""
    
    def __init__(self):
        self.price_ids = {
            PlanTier.TRIAL: os.getenv("STRIPE_FREE_PRICE_ID"),
            PlanTier.PRO: os.getenv("STRIPE_BASIC_PRICE_ID"), 
            PlanTier.ENTERPRISE: os.getenv("STRIPE_PRO_PRICE_ID"),
        }
    
    async def create_customer(self, agent: Agent) -> str:
        """Create Stripe customer for agent"""
        try:
            customer = stripe.Customer.create(
                email=agent.email,
                name=f"{agent.first_name} {agent.last_name}",
                metadata={
                    "agent_id": str(agent.id),
                    "agent_slug": agent.slug
                }
            )
            
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(status_code=400, detail=f"Billing error: {str(e)}")
    
    async def create_checkout_session(
        self, 
        agent: Agent, 
        plan_tier: PlanTier, 
        success_url: str, 
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for subscription"""
        
        price_id = self.price_ids.get(plan_tier)
        if not price_id:
            raise HTTPException(status_code=400, detail=f"Invalid plan tier: {plan_tier}")
        
        try:
            # Ensure agent has Stripe customer ID
            if not agent.stripe_customer_id:
                customer_id = await self.create_customer(agent)
                # Update agent with customer ID
                # (This would need to be done in the calling function with DB session)
            else:
                customer_id = agent.stripe_customer_id
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
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
                    "agent_id": str(agent.id),
                    "plan_tier": plan_tier
                }
            )
            
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise HTTPException(status_code=400, detail=f"Billing error: {str(e)}")
    
    async def create_customer_portal_session(
        self, 
        agent: Agent, 
        return_url: str
    ) -> Dict[str, Any]:
        """Create Stripe customer portal session"""
        
        if not agent.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No billing account found")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=agent.stripe_customer_id,
                return_url=return_url,
            )
            
            return {
                "portal_url": session.url
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise HTTPException(status_code=400, detail=f"Billing error: {str(e)}")
    
    async def get_subscription_info(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Get current subscription information"""
        
        if not agent.stripe_subscription_id:
            return None
        
        try:
            subscription = stripe.Subscription.retrieve(agent.stripe_subscription_id)
            
            return {
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(
                    subscription.current_period_start
                ),
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end
                ),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "plan_name": self._get_plan_name_from_price_id(
                    subscription.items.data[0].price.id
                )
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {e}")
            return None
    
    async def cancel_subscription(self, agent: Agent, cancel_at_period_end: bool = True) -> bool:
        """Cancel subscription"""
        
        if not agent.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="No active subscription found")
        
        try:
            if cancel_at_period_end:
                # Cancel at period end (don't charge again)
                stripe.Subscription.modify(
                    agent.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # Cancel immediately
                stripe.Subscription.delete(agent.stripe_subscription_id)
            
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Billing error: {str(e)}")
    
    async def update_subscription(self, agent: Agent, new_plan_tier: PlanTier) -> bool:
        """Update subscription to new plan"""
        
        if not agent.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="No active subscription found")
        
        new_price_id = self.price_ids.get(new_plan_tier)
        if not new_price_id:
            raise HTTPException(status_code=400, detail=f"Invalid plan tier: {new_plan_tier}")
        
        try:
            subscription = stripe.Subscription.retrieve(agent.stripe_subscription_id)
            
            # Update subscription with new price
            stripe.Subscription.modify(
                agent.stripe_subscription_id,
                items=[{
                    'id': subscription.items.data[0].id,
                    'price': new_price_id,
                }],
                proration_behavior='always_invoice'
            )
            
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Billing error: {str(e)}")
    
    def _get_plan_name_from_price_id(self, price_id: str) -> str:
        """Get plan name from Stripe price ID"""
        price_to_name = {
            self.price_ids[PlanTier.TRIAL]: "Trial",
            self.price_ids[PlanTier.PRO]: "Pro",
            self.price_ids[PlanTier.ENTERPRISE]: "Enterprise",
        }
        
        return price_to_name.get(price_id, "Unknown")

# Global service instance
billing_service = BillingService()