"""
Domain model - manages subdomains and custom domains (agent_domains table)
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"

class AgentDomain(Base):
    __tablename__ = "agent_domains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Domain details
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    cf_custom_hostname_id = Column(String(100))  # from CF API
    verification_status = Column(String(20), default=VerificationStatus.PENDING, nullable=False)
    is_primary = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")
    
    def __repr__(self):
        return f"<AgentDomain(id={self.id}, hostname='{self.hostname}', status='{self.verification_status}')>"