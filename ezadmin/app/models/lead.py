"""
Lead model - represents captured leads
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"
    SPAM = "spam"

class LeadSource(str, enum.Enum):
    HOME_VALUATION = "home_valuation"
    BUYER_INTEREST = "buyer_interest"
    CONTACT = "contact"
    IMPORT = "import"
    API = "api"

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    capture_page_id = Column(UUID(as_uuid=True), ForeignKey("capture_pages.id", ondelete="SET NULL"))
    
    # Contact info
    full_name = Column(String(255))
    email = Column(CITEXT)
    phone_e164 = Column(String(50))  # normalized +15551234567
    
    # Lead details
    source = Column(String(50), nullable=False, index=True)  # LeadSource enum
    status = Column(String(50), default=LeadStatus.NEW, nullable=False, index=True)
    
    # Property info (for home valuation leads)
    address_line = Column(String(500))
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    
    # Additional data
    message = Column(Text)
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    
    # AI Analysis
    ai_summary = Column(Text)
    ai_score = Column(Integer)  # 0-100 lead quality score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")
    capture_page = relationship("CapturePage", back_populates="leads")
    notifications = relationship("Notification", back_populates="lead", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lead(id={self.id}, email='{self.email}', source='{self.source}', agent_id={self.agent_id})>"