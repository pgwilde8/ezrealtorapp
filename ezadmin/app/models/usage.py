"""
Usage tracking model - monthly metering per agent (usage_counters table)
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid

class UsageCounter(Base):
    __tablename__ = "usage_counters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Usage details - monthly roll-up
    period_month = Column(Date, nullable=False, index=True)  # e.g., 2025-10-01 for October
    leads_created = Column(Integer, default=0, nullable=False)
    emails_sent = Column(Integer, default=0, nullable=False)
    sms_sent = Column(Integer, default=0, nullable=False)
    ai_calls = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="usage_counters")
    
    __table_args__ = (
        {"schema": None}  # Default schema
    )
    
    def __repr__(self):
        return f"<UsageCounter(id={self.id}, agent_id={self.agent_id}, period={self.period_month}, leads={self.leads_created})>"