"""
Stripe Webhook Handler
Processes Stripe events for subscription management
"""

import os
import stripe
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.agent import Agent, PlanTier, AgentStatus
from app.utils.database import get_async_session

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeWebhookHandler:
    """Handles Stripe webhook events"""
    
    def __init__(self):
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not self.webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured")
    
    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> stripe.Event:
        """Verify webhook signature and construct event"""
        try:
            return stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    async def handle_event(self, event: stripe.Event) -> Dict[str, Any]:
        """Route webhook events to appropriate handlers"""
        
        event_type = event['type']
        logger.info(f"Processing Stripe event: {event_type}")
        
        try:
            if event_type == 'customer.subscription.created':
                return await self.handle_subscription_created(event)
            
            elif event_type == 'customer.subscription.updated':
                return await self.handle_subscription_updated(event)
            
            elif event_type == 'customer.subscription.deleted':
                return await self.handle_subscription_cancelled(event)
            
            elif event_type == 'invoice.payment_succeeded':
                return await self.handle_payment_succeeded(event)
            
            elif event_type == 'invoice.payment_failed':
                return await self.handle_payment_failed(event)
            
            elif event_type == 'customer.subscription.trial_will_end':
                return await self.handle_trial_ending(event)
            
            elif event_type == 'checkout.session.completed':
                return await self.handle_checkout_completed(event)
            
            elif event_type == 'invoice.payment_action_required':
                return await self.handle_payment_action_required(event)
            
            elif event_type == 'customer.updated':
                return await self.handle_customer_updated(event)
            
            else:
                logger.info(f"Unhandled event type: {event_type}")
                return {"status": "ignored", "event_type": event_type}
                
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def handle_subscription_created(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle new subscription creation"""
        subscription = event['data']['object']
        customer_id = subscription['customer']
        
        # Get plan tier from price ID
        plan_tier = self._get_plan_from_price_id(subscription['items']['data'][0]['price']['id'])
        
        async with get_async_session() as db:
            # Find agent by Stripe customer ID
            result = await db.execute(
                select(Agent).where(Agent.stripe_customer_id == customer_id)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                # Update agent with subscription info
                agent.stripe_subscription_id = subscription['id']
                agent.plan_tier = plan_tier
                agent.status = AgentStatus.ACTIVE
                agent.subscription_end_date = datetime.fromtimestamp(
                    subscription['current_period_end']
                )
                
                await db.commit()
                logger.info(f"Updated agent {agent.email} with subscription {subscription['id']}")
                
                return {
                    "status": "success",
                    "action": "subscription_created",
                    "agent_id": str(agent.id),
                    "plan_tier": plan_tier
                }
            else:
                logger.warning(f"No agent found for customer {customer_id}")
                return {"status": "warning", "message": "Agent not found"}
    
    async def handle_subscription_updated(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle subscription changes (upgrades, downgrades)"""
        subscription = event['data']['object']
        subscription_id = subscription['id']
        
        # Get new plan tier
        plan_tier = self._get_plan_from_price_id(subscription['items']['data'][0]['price']['id'])
        
        async with get_async_session() as db:
            # Find agent by subscription ID
            result = await db.execute(
                select(Agent).where(Agent.stripe_subscription_id == subscription_id)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                old_plan = agent.plan_tier
                
                # Update subscription details
                agent.plan_tier = plan_tier
                agent.subscription_end_date = datetime.fromtimestamp(
                    subscription['current_period_end']
                )
                
                # Update status based on subscription status
                if subscription['status'] == 'active':
                    agent.status = AgentStatus.ACTIVE
                elif subscription['status'] in ['past_due', 'unpaid']:
                    agent.status = AgentStatus.PAST_DUE
                elif subscription['status'] in ['canceled', 'incomplete_expired']:
                    agent.status = AgentStatus.CANCELLED
                
                await db.commit()
                
                # Handle plan change logic
                await self._handle_plan_change(agent, old_plan, plan_tier)
                
                logger.info(f"Updated agent {agent.email} subscription: {old_plan} -> {plan_tier}")
                
                return {
                    "status": "success",
                    "action": "subscription_updated",
                    "agent_id": str(agent.id),
                    "old_plan": old_plan,
                    "new_plan": plan_tier
                }
            else:
                logger.warning(f"No agent found for subscription {subscription_id}")
                return {"status": "warning", "message": "Agent not found"}
    
    async def handle_subscription_cancelled(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle subscription cancellation"""
        subscription = event['data']['object']
        subscription_id = subscription['id']
        
        async with get_async_session() as db:
            # Find and update agent
            result = await db.execute(
                select(Agent).where(Agent.stripe_subscription_id == subscription_id)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                agent.status = AgentStatus.CANCELLED
                agent.plan_tier = PlanTier.TRIAL
                agent.subscription_end_date = datetime.fromtimestamp(
                    subscription['canceled_at']
                ) if subscription.get('canceled_at') else datetime.utcnow()
                
                await db.commit()
                
                # Handle cancellation cleanup
                await self._handle_cancellation(agent)
                
                logger.info(f"Cancelled subscription for agent {agent.email}")
                
                return {
                    "status": "success",
                    "action": "subscription_cancelled",
                    "agent_id": str(agent.id)
                }
            else:
                logger.warning(f"No agent found for cancelled subscription {subscription_id}")
                return {"status": "warning", "message": "Agent not found"}
    
    async def handle_payment_succeeded(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle successful payment"""
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            async with get_async_session() as db:
                # Update agent status to active
                await db.execute(
                    update(Agent)
                    .where(Agent.stripe_subscription_id == subscription_id)
                    .values(status=AgentStatus.ACTIVE)
                )
                await db.commit()
                
                logger.info(f"Payment succeeded for subscription {subscription_id}")
        
        return {
            "status": "success",
            "action": "payment_succeeded",
            "invoice_id": invoice['id']
        }
    
    async def handle_payment_failed(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle failed payment"""
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            async with get_async_session() as db:
                # Mark agent as past due
                result = await db.execute(
                    select(Agent).where(Agent.stripe_subscription_id == subscription_id)
                )
                agent = result.scalar_one_or_none()
                
                if agent:
                    agent.status = AgentStatus.PAST_DUE
                    await db.commit()
                    
                    # Send payment failure notification
                    await self._send_payment_failure_notification(agent)
                    
                    logger.warning(f"Payment failed for agent {agent.email}")
        
        return {
            "status": "success",
            "action": "payment_failed",
            "invoice_id": invoice['id']
        }
    
    async def handle_trial_ending(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle trial ending notification"""
        subscription = event['data']['object']
        subscription_id = subscription['id']
        
        async with get_async_session() as db:
            result = await db.execute(
                select(Agent).where(Agent.stripe_subscription_id == subscription_id)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                # Send trial ending notification
                await self._send_trial_ending_notification(agent)
                logger.info(f"Trial ending for agent {agent.email}")
        
        return {
            "status": "success",
            "action": "trial_ending_notification"
        }
    
    async def handle_checkout_completed(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle completed checkout session"""
        session = event['data']['object']
        
        if session['mode'] == 'subscription':
            customer_id = session['customer']
            subscription_id = session['subscription']
            
            # Link customer to agent if not already linked
            async with get_async_session() as db:
                # This might be handled by metadata or customer email matching
                # Implementation depends on your checkout flow
                pass
        
        return {
            "status": "success",
            "action": "checkout_completed",
            "session_id": session['id']
        }
    
    async def handle_payment_action_required(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle payment requiring action (3D Secure, etc.)"""
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            async with get_async_session() as db:
                result = await db.execute(
                    select(Agent).where(Agent.stripe_subscription_id == subscription_id)
                )
                agent = result.scalar_one_or_none()
                
                if agent:
                    # Send email notification about payment requiring action
                    await self._send_payment_action_required_notification(agent, invoice)
                    logger.info(f"Payment action required for agent {agent.email}")
        
        return {
            "status": "success",
            "action": "payment_action_required",
            "invoice_id": invoice['id']
        }
    
    async def handle_customer_updated(self, event: stripe.Event) -> Dict[str, Any]:
        """Handle customer information updates"""
        customer = event['data']['object']
        customer_id = customer['id']
        
        async with get_async_session() as db:
            result = await db.execute(
                select(Agent).where(Agent.stripe_customer_id == customer_id)
            )
            agent = result.scalar_one_or_none()
            
            if agent:
                # Update agent email if it changed in Stripe
                if customer.get('email') and customer['email'] != agent.email:
                    agent.email = customer['email']
                    await db.commit()
                    logger.info(f"Updated agent email: {customer['email']}")
        
        return {
            "status": "success",
            "action": "customer_updated",
            "customer_id": customer_id
        }
    
    def _get_plan_from_price_id(self, price_id: str) -> PlanTier:
        """Map Stripe price ID to plan tier"""
        price_to_plan = {
            os.getenv("STRIPE_FREE_PRICE_ID"): PlanTier.TRIAL,
            os.getenv("STRIPE_BASIC_PRICE_ID"): PlanTier.BOOSTER,
            os.getenv("STRIPE_PRO_PRICE_ID"): PlanTier.PRO,
        }
        
        return price_to_plan.get(price_id, PlanTier.TRIAL)
    
    async def _handle_plan_change(self, agent: Agent, old_plan: str, new_plan: str):
        """Handle plan upgrade/downgrade logic"""
        # Reset usage counters on plan change
        # Update feature access
        # Send plan change confirmation email
        logger.info(f"Plan changed for {agent.email}: {old_plan} -> {new_plan}")
    
    async def _handle_cancellation(self, agent: Agent):
        """Handle subscription cancellation cleanup"""
        # Disable premium features
        # Send cancellation confirmation
        # Schedule data retention cleanup
        logger.info(f"Handling cancellation for {agent.email}")
    
    async def _send_payment_failure_notification(self, agent: Agent):
        """Send payment failure notification"""
        # Send email notification about failed payment
        # Include link to update payment method
        logger.info(f"Sending payment failure notification to {agent.email}")
    
    async def _send_trial_ending_notification(self, agent: Agent):
        """Send trial ending notification"""
        # Send email about trial ending
        # Include upgrade links
        logger.info(f"Sending trial ending notification to {agent.email}")
    
    async def _send_payment_action_required_notification(self, agent: Agent, invoice):
        """Send payment action required notification"""
        # Send email notification about payment requiring action
        # Include link to complete payment
        logger.info(f"Sending payment action required notification to {agent.email}")

# Global handler instance
webhook_handler = StripeWebhookHandler()