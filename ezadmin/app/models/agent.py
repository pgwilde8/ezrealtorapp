"""
Agent model - represents each Realtor tenant
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class PlanTier(str, enum.Enum):
    TRIAL = "trial"
    BOOSTER = "booster"
    PRO = "pro"
    TEAM = "team"

class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(CITEXT, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone_e164 = Column(String(50))  # normalized +15551234567
    slug = Column(String(100), unique=True, index=True, nullable=False)
    
    # Plan and billing
    plan_tier = Column(String(50), default=PlanTier.TRIAL, nullable=False, index=True)
    status = Column(String(50), default=AgentStatus.ACTIVE, nullable=False)
    
    # Stripe billing fields
    stripe_customer_id = Column(String(100), index=True)  # Stripe customer ID
    stripe_subscription_id = Column(String(100), index=True)  # Stripe subscription ID
    subscription_end_date = Column(DateTime(timezone=True))  # When subscription ends
    trial_ends_at = Column(DateTime(timezone=True))  # Trial expiration
    
    # SMS compliance
    sms_opt_in = Column(Boolean, default=False, nullable=False)
    
    # Basic Customization Fields
    logo_url = Column(String(500))  # Agent/brokerage logo
    headshot_url = Column(String(500))  # Agent profile photo
    brand_primary_color = Column(String(7), default="#3B82F6")  # Hex color
    brand_secondary_color = Column(String(7), default="#1F2937")  # Hex color
    brand_accent_color = Column(String(7), default="#10B981")  # Hex color
    
    # Custom Headlines & Copy
    buyer_page_headline = Column(String(200))  # Custom headline for buyer form
    buyer_page_subtitle = Column(String(300))  # Custom subtitle
    valuation_page_headline = Column(String(200))  # Custom headline for valuation
    valuation_page_subtitle = Column(String(300))  # Custom subtitle
    
    # Agent Info
    title = Column(String(100))  # "Senior Realtor", "Team Leader", etc.
    license_number = Column(String(50))  # Real estate license
    brokerage_name = Column(String(200))  # Brokerage/company name
    
    # Contact & Social
    website_url = Column(String(500))
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    linkedin_url = Column(String(500))
    
    # Custom Messages
    submit_button_text = Column(String(100))  # Custom CTA button text
    success_message = Column(Text)  # Custom thank you message
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    domains = relationship("AgentDomain", back_populates="agent", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="agent", cascade="all, delete-orphan")
    capture_pages = relationship("CapturePage", back_populates="agent", cascade="all, delete-orphan")
    provider_credentials = relationship("ProviderCredential", back_populates="agent", cascade="all, delete-orphan")
    usage_counters = relationship("UsageCounter", back_populates="agent", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, email='{self.email}', slug='{self.slug}')>"