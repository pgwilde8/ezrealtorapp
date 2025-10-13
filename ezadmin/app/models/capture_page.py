"""
Capture Page model - your 2 funnels + any extras
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class CapturePageKind(str, enum.Enum):
    HOME_VALUATION = "home_valuation"
    BUYER_INTEREST = "buyer_interest"
    CUSTOM = "custom"

class CapturePage(Base):
    __tablename__ = "capture_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Page details
    kind = Column(String(50), nullable=False)  # CapturePageKind enum
    slug = Column(String(100), nullable=False)  # e.g. "sell" → /sell
    title = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent")
    leads = relationship("Lead", back_populates="capture_page")
    
    __table_args__ = (
        {"schema": None}  # Default schema
    )
    
    def __repr__(self):
        return f"<CapturePage(id={self.id}, agent_id={self.agent_id}, kind='{self.kind}', slug='{self.slug}')>"