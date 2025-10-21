"""
Plan Limits Configuration
Defines usage limits for each subscription tier
"""

from typing import Dict, Any
from app.models.agent import PlanTier

# Usage limits per plan tier (Option 3: Generous/Competitive)
PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    PlanTier.TRIAL: {
        "leads_per_month": 50,
        "voice_minutes_per_month": 15,
        "sms_per_month": 50,
        "emails_per_month": 100,
        "voicemail_transcriptions_per_month": 10,
        "phone_number_included": False,
        "custom_domain": False,
        "ai_tokens_per_month": 150000,
        "daily_limits": {
            "emails": 30,
            "sms": 15,
            "voice_minutes": 5
        }
    },
    PlanTier.STARTER: {
        "leads_per_month": 150,
        "voice_minutes_per_month": 100,
        "sms_per_month": 150,
        "emails_per_month": 500,
        "voicemail_transcriptions_per_month": 30,
        "phone_number_included": True,
        "custom_domain": False,
        "ai_tokens_per_month": 300000,
        "daily_limits": None  # No daily limits on paid plans
    },
    PlanTier.GROWTH: {
        "leads_per_month": 500,
        "voice_minutes_per_month": 300,
        "sms_per_month": 500,
        "emails_per_month": 1500,
        "voicemail_transcriptions_per_month": 100,
        "phone_number_included": True,
        "custom_domain": True,
        "ai_tokens_per_month": 1500000,
        "daily_limits": None
    },
    PlanTier.SCALE: {
        "leads_per_month": 1500,
        "voice_minutes_per_month": 1000,
        "sms_per_month": 1500,
        "emails_per_month": 5000,
        "voicemail_transcriptions_per_month": 300,
        "phone_number_included": True,
        "custom_domain": True,
        "ai_tokens_per_month": 3000000,
        "daily_limits": None
    },
    PlanTier.PRO: {
        "leads_per_month": 4000,
        "voice_minutes_per_month": 3000,
        "sms_per_month": 5000,
        "emails_per_month": 15000,
        "voicemail_transcriptions_per_month": 1000,
        "phone_number_included": True,
        "custom_domain": True,
        "ai_tokens_per_month": 10000000,
        "daily_limits": None
    }
}

# Warning thresholds (percentage of limit)
WARNING_THRESHOLDS = {
    "soft_warning": 0.70,  # 70% - First warning
    "hard_warning": 0.90,  # 90% - Final warning
    "critical": 0.95       # 95% - Critical alert
}

# Cost estimates (for internal tracking)
COST_ESTIMATES = {
    "voice_per_minute": 0.013,
    "sms_incoming": 0.0075,
    "sms_outgoing": 0.0079,
    "voicemail_transcription": 0.05,
    "phone_number_monthly": 1.15
}


def get_plan_limits(plan_tier: str) -> Dict[str, Any]:
    """Get usage limits for a specific plan tier"""
    return PLAN_LIMITS.get(plan_tier, PLAN_LIMITS[PlanTier.TRIAL])


def get_limit_for_metric(plan_tier: str, metric: str) -> int:
    """Get specific limit for a metric"""
    limits = get_plan_limits(plan_tier)
    return limits.get(metric, 0)


def calculate_usage_percentage(current: int, limit: int) -> float:
    """Calculate usage as percentage of limit"""
    if limit == 0:
        return 0.0
    return (current / limit) * 100


def should_send_warning(usage_percentage: float, last_warning_threshold: float = 0) -> tuple[bool, str]:
    """
    Determine if a warning should be sent based on usage percentage
    Returns: (should_send, warning_level)
    """
    if usage_percentage >= 95 and last_warning_threshold < 95:
        return (True, "critical")
    elif usage_percentage >= 90 and last_warning_threshold < 90:
        return (True, "hard_warning")
    elif usage_percentage >= 70 and last_warning_threshold < 70:
        return (True, "soft_warning")
    return (False, "none")


def get_upgrade_message(plan_tier: str, metric: str) -> str:
    """Get upgrade prompt message for a specific metric"""
    messages = {
        PlanTier.TRIAL: "Upgrade to Starter ($97/mo) to continue",
        PlanTier.STARTER: "Upgrade to Growth ($147/mo) for 5x more capacity",
        PlanTier.GROWTH: "Upgrade to Scale ($237/mo) for 3x more capacity",
        PlanTier.SCALE: "Upgrade to Pro ($437/mo) for unlimited capacity"
    }
    return messages.get(plan_tier, "Upgrade to continue")

