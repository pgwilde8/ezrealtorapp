"""
Property Alert models for showcasing listings to subscribers
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
import uuid

class PropertyAlert(Base):
    __tablename__ = "property_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Property Details
    address = Column(String(500), nullable=False)
    price = Column(Integer, nullable=False)
    square_feet = Column(Integer)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Numeric(3, 1), nullable=False)  # e.g., 2.5
    description = Column(Text, nullable=False)
    mls_link = Column(String(500))
    
    # Alert Settings
    is_hot = Column(Boolean, default=False, nullable=False)  # Hot property = instant SMS
    sent_at = Column(DateTime(timezone=True))  # When alert was sent
    
    # Stats
    email_sent_count = Column(Integer, default=0)
    sms_sent_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.display_order")
    
    def __repr__(self):
        return f"<PropertyAlert(id={self.id}, address='{self.address}', price={self.price})>"


class PropertyImage(Base):
    __tablename__ = "property_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("property_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Image URLs
    image_url = Column(String(1000), nullable=False)  # Full-size image in Spaces
    thumbnail_url = Column(String(1000))  # Optimized thumbnail
    
    # Metadata
    file_size = Column(Integer)  # In bytes
    width = Column(Integer)  # Original width
    height = Column(Integer)  # Original height
    display_order = Column(Integer, default=0)  # For sorting (1st photo, 2nd, etc.)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    property = relationship("PropertyAlert", back_populates="images")
    
    def __repr__(self):
        return f"<PropertyImage(id={self.id}, property_id={self.property_id}, order={self.display_order})>"

