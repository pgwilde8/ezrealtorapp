"""
Provider credentials model - encrypted BYOK keys (OpenAI, Brevo, Twilio)
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid
import enum

class ProviderType(str, enum.Enum):
    OPENAI = "openai"
    BREVO = "brevo"
    TWILIO = "twilio"

class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Credential details
    provider = Column(String(50), nullable=False)  # ProviderType enum
    key_name = Column(String(100), nullable=False)  # api_key | account_sid | auth_token | from_number
    key_ciphertext = Column(LargeBinary, nullable=False)  # encrypted at app-level
    
    # Verification
    verified_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")
    
    def __repr__(self):
        return f"<ProviderCredential(id={self.id}, agent_id={self.agent_id}, provider='{self.provider}', key_name='{self.key_name}')>"