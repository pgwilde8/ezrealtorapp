"""
Usage Tracker Service
Tracks and enforces plan usage limits for voice, SMS, email, etc.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.agent import Agent
from app.config.plan_limits import (
    get_plan_limits,
    get_limit_for_metric,
    calculate_usage_percentage,
    should_send_warning,
    get_upgrade_message
)

logger = logging.getLogger(__name__)


class UsageLimitExceeded(Exception):
    """Raised when a usage limit is exceeded"""
    def __init__(self, message: str, metric: str, current: int, limit: int, plan_tier: str):
        self.message = message
        self.metric = metric
        self.current = current
        self.limit = limit
        self.plan_tier = plan_tier
        super().__init__(self.message)


class UsageTracker:
    """Service for tracking and enforcing usage limits"""
    
    async def check_and_increment(
        self,
        agent: Agent,
        metric: str,
        amount: int,
        db: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if usage is within limits and increment if allowed
        
        Args:
            agent: The agent object
            metric: Usage metric (voice_minutes, sms, email, voicemail)
            amount: Amount to increment
            db: Database session
            
        Returns:
            (allowed, error_message)
        """
        # Check if usage needs to be reset (new billing month)
        await self._check_and_reset_usage(agent, db)
        
        # Get current usage and limits
        current_usage = self._get_current_usage(agent, metric)
        limit = get_limit_for_metric(agent.plan_tier, f"{metric}_per_month")
        
        # Check if increment would exceed limit
        if current_usage + amount > limit:
            upgrade_msg = get_upgrade_message(agent.plan_tier, metric)
            error_msg = f"Usage limit exceeded for {metric}. Current: {current_usage}/{limit}. {upgrade_msg}"
            
            logger.warning(
                f"Usage limit exceeded: agent={agent.slug}, metric={metric}, "
                f"current={current_usage}, limit={limit}, plan={agent.plan_tier}"
            )
            
            # Check if we should send a warning email
            await self._send_limit_exceeded_notification(agent, metric, current_usage, limit, db)
            
            return (False, error_msg)
        
        # Increment usage
        await self._increment_usage(agent, metric, amount, db)
        
        # Check if we're approaching limits (send warnings at 70%, 90%)
        new_usage = current_usage + amount
        usage_percentage = calculate_usage_percentage(new_usage, limit)
        
        last_warning_pct = self._get_last_warning_percentage(agent)
        send_warning, warning_level = should_send_warning(usage_percentage, last_warning_pct)
        
        if send_warning:
            await self._send_usage_warning(agent, metric, new_usage, limit, warning_level, db)
        
        logger.info(
            f"Usage tracked: agent={agent.slug}, metric={metric}, "
            f"amount={amount}, new_total={new_usage}/{limit} ({usage_percentage:.1f}%)"
        )
        
        return (True, None)
    
    async def get_usage_stats(self, agent: Agent, db: AsyncSession) -> Dict[str, Any]:
        """Get current usage statistics for an agent"""
        await self._check_and_reset_usage(agent, db)
        
        limits = get_plan_limits(agent.plan_tier)
        
        return {
            "voice_minutes": {
                "current": agent.usage_voice_minutes_month or 0,
                "limit": limits.get("voice_minutes_per_month", 0),
                "percentage": calculate_usage_percentage(
                    agent.usage_voice_minutes_month or 0,
                    limits.get("voice_minutes_per_month", 1)
                )
            },
            "sms": {
                "current": agent.usage_sms_count_month or 0,
                "limit": limits.get("sms_per_month", 0),
                "percentage": calculate_usage_percentage(
                    agent.usage_sms_count_month or 0,
                    limits.get("sms_per_month", 1)
                )
            },
            "email": {
                "current": agent.usage_email_count_month or 0,
                "limit": limits.get("emails_per_month", 0),
                "percentage": calculate_usage_percentage(
                    agent.usage_email_count_month or 0,
                    limits.get("emails_per_month", 1)
                )
            },
            "voicemail": {
                "current": agent.usage_voicemail_count_month or 0,
                "limit": limits.get("voicemail_transcriptions_per_month", 0),
                "percentage": calculate_usage_percentage(
                    agent.usage_voicemail_count_month or 0,
                    limits.get("voicemail_transcriptions_per_month", 1)
                )
            },
            "reset_date": agent.usage_reset_date,
            "plan_tier": agent.plan_tier
        }
    
    async def _check_and_reset_usage(self, agent: Agent, db: AsyncSession):
        """Check if it's time to reset monthly usage counters"""
        now = datetime.utcnow()
        
        if agent.usage_reset_date and agent.usage_reset_date <= now:
            logger.info(f"Resetting usage for agent: {agent.slug}")
            
            # Reset all usage counters
            agent.usage_voice_minutes_month = 0
            agent.usage_sms_count_month = 0
            agent.usage_email_count_month = 0
            agent.usage_voicemail_count_month = 0
            
            # Set next reset date (1 month from now)
            agent.usage_reset_date = now + timedelta(days=30)
            agent.usage_last_warning_sent = None
            
            await db.commit()
            await db.refresh(agent)
    
    def _get_current_usage(self, agent: Agent, metric: str) -> int:
        """Get current usage for a specific metric"""
        metric_map = {
            "voice_minutes": agent.usage_voice_minutes_month,
            "sms": agent.usage_sms_count_month,
            "email": agent.usage_email_count_month,
            "voicemail": agent.usage_voicemail_count_month
        }
        return metric_map.get(metric, 0) or 0
    
    async def _increment_usage(self, agent: Agent, metric: str, amount: int, db: AsyncSession):
        """Increment usage counter for a specific metric"""
        metric_field_map = {
            "voice_minutes": "usage_voice_minutes_month",
            "sms": "usage_sms_count_month",
            "email": "usage_email_count_month",
            "voicemail": "usage_voicemail_count_month"
        }
        
        field = metric_field_map.get(metric)
        if not field:
            logger.error(f"Unknown metric: {metric}")
            return
        
        # Increment the specific field
        current = getattr(agent, field, 0) or 0
        setattr(agent, field, current + amount)
        
        await db.commit()
        await db.refresh(agent)
    
    def _get_last_warning_percentage(self, agent: Agent) -> float:
        """Get the percentage at which last warning was sent"""
        # This is a simplified version - in production you'd track this per metric
        # For now, we'll estimate based on usage_last_warning_sent timestamp
        if not agent.usage_last_warning_sent:
            return 0.0
        
        # If warning was sent recently, assume it was at a high percentage
        time_since_warning = datetime.utcnow() - agent.usage_last_warning_sent
        if time_since_warning.total_seconds() < 3600:  # Less than 1 hour ago
            return 70.0  # Assume it was the first warning
        return 0.0
    
    async def _send_usage_warning(
        self,
        agent: Agent,
        metric: str,
        current: int,
        limit: int,
        warning_level: str,
        db: AsyncSession
    ):
        """Send usage warning notification"""
        percentage = calculate_usage_percentage(current, limit)
        
        logger.warning(
            f"Usage warning: agent={agent.slug}, metric={metric}, "
            f"usage={current}/{limit} ({percentage:.1f}%), level={warning_level}"
        )
        
        # Update last warning sent timestamp
        agent.usage_last_warning_sent = datetime.utcnow()
        await db.commit()
        
        # TODO: Send email notification
        # await email_service.send_usage_warning(agent, metric, current, limit, warning_level)
    
    async def _send_limit_exceeded_notification(
        self,
        agent: Agent,
        metric: str,
        current: int,
        limit: int,
        db: AsyncSession
    ):
        """Send limit exceeded notification"""
        logger.error(
            f"Limit exceeded: agent={agent.slug}, metric={metric}, "
            f"usage={current}/{limit}"
        )
        
        # TODO: Send email notification
        # await email_service.send_limit_exceeded(agent, metric, current, limit)


# Global instance
usage_tracker = UsageTracker()

