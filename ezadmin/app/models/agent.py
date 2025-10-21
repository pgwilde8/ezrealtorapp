"""
Agent model - represents each Realtor tenant
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid
import enum
# Update /root/ezrealtor/ezadmin/app/models/agent.py
class PlanTier(str, enum.Enum):
    TRIAL = "trial"
    STARTER = "starter"  
    GROWTH = "growth"
    SCALE = "scale"
    PRO = "pro"


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
    google_id = Column(String(100), index=True, unique=True)  # Google OAuth sub
    last_login_at = Column(DateTime(timezone=True))
    email_verified = Column(Boolean, default=False)
    
    # Stripe integration fields
    stripe_customer_id = Column(String(100), index=True)
    stripe_subscription_id = Column(String(100), index=True)
    subscription_end_date = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    
    # Twilio phone number fields
    twilio_phone_number = Column(String(20), unique=True, index=True)  # E.164 format: +17165551234
    twilio_phone_sid = Column(String(100), unique=True)  # Twilio phone number SID
    twilio_phone_status = Column(String(20))  # active, pending, cancelled, porting
    twilio_phone_activated_at = Column(DateTime(timezone=True))
    twilio_phone_friendly_name = Column(String(200))
    
    # Customization fields (branding, photos, text)
    logo_url = Column(String(500))
    headshot_url = Column(String(500))
    secondary_photo_url = Column(String(500))
    brand_primary_color = Column(String(7))
    brand_secondary_color = Column(String(7))
    brand_accent_color = Column(String(7))
    buyer_page_headline = Column(String(200))
    buyer_page_subtitle = Column(String(300))
    valuation_page_headline = Column(String(200))
    valuation_page_subtitle = Column(String(300))
    title = Column(String(100))
    license_number = Column(String(50))
    brokerage_name = Column(String(200))
    website_url = Column(String(500))
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    linkedin_url = Column(String(500))
    submit_button_text = Column(String(100))
    success_message = Column(String(300))
    bio = Column(Text)
    tagline = Column(String(500))
    phone = Column(String(50))
    public_email = Column(String(255))
    office_address = Column(String(500))
    youtube_url = Column(String(500))
    years_experience = Column(Integer)
    sales_volume = Column(BigInteger)
    total_transactions = Column(Integer)
    
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
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', slug='{self.slug}')>"