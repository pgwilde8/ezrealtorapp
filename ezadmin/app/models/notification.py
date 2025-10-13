"""
Notification model - email/SMS/callback logs
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class NotifyKind(str, enum.Enum):
    EMAIL_AGENT = "email_agent"
    EMAIL_LEAD = "email_lead"
    SMS_AGENT = "sms_agent"
    SMS_LEAD = "sms_lead"
    VOICE_CALLBACK = "voice_callback"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"))
    
    # Notification details
    kind = Column(String(50), nullable=False)  # NotifyKind enum
    provider_msg_id = Column(String(255))  # Brevo/Twilio message ID
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    agent = relationship("Agent")
    lead = relationship("Lead", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, agent_id={self.agent_id}, kind='{self.kind}', success={self.success})>"