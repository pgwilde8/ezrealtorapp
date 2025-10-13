"""
Agent model - represents each Realtor tenant
"""

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid
import enum

class PlanTier(str, enum.Enum):
    TRIAL = "trial"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"

class Agent(Base):
    __tablename__ = "agents"
    
    # Core fields that exist in database
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(CITEXT, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone_e164 = Column(String(50))  # normalized +15551234567
    slug = Column(String(100), unique=True, index=True, nullable=False)
    plan_tier = Column(String(50), nullable=False, default=PlanTier.TRIAL, index=True)
    status = Column(String(50), nullable=False, default=AgentStatus.ACTIVE)
    sms_opt_in = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Authentication fields
    password_hash = Column(String(255))  # bcrypt hash
    last_login_at = Column(DateTime(timezone=True))
    email_verified = Column(Boolean, default=False)
    
    # Stripe integration fields
    stripe_customer_id = Column(String(100), index=True)
    stripe_subscription_id = Column(String(100), index=True)
    subscription_end_date = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Agent(email='{self.email}', slug='{self.slug}', plan='{self.plan_tier}')>"
    
    @property
    def first_name(self):
        """Extract first name from full name"""
        return self.name.split(' ')[0] if self.name else ''
    
    @property
    def last_name(self):
        """Extract last name from full name"""
        parts = self.name.split(' ')
        return ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    @property
    def full_name(self):
        """Full name property for compatibility"""
        return self.name