"""
Plan Catalog model - centralize tier limits & flags (optional)
"""

from sqlalchemy import Column, String, Integer, Boolean, Numeric, DateTime
from sqlalchemy.sql import func
from app.utils.database import Base

class PlanCatalog(Base):
    __tablename__ = "plan_catalog"
    
    code = Column(String(50), primary_key=True)  # trial|booster|pro|team
    price_month_usd = Column(Numeric(10, 2), nullable=False)
    max_leads = Column(Integer)
    max_emails = Column(Integer)
    max_sms = Column(Integer)
    max_ai_calls = Column(Integer)
    allow_twilio = Column(Boolean, default=False, nullable=False)
    allow_custom_domain = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PlanCatalog(code='{self.code}', price=${self.price_month_usd}, max_leads={self.max_leads})>"