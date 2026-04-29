import uuid
from datetime import datetime
from sqlalchemy import Column, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base


class UserFinancialProfile(Base):
    __tablename__ = "user_financial_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    monthly_income = Column(Float)
    living_expense = Column(Float)
    current_savings = Column(Float)

    loan_emi = Column(Float)
    loan_years = Column(Integer)
    loan_interest_rate = Column(Float)

    return_rate = Column(Float, default=0.1)
    inflation_rate = Column(Float, default=0.06)

    has_loan = Column(Boolean)
    has_insurance = Column(Boolean)

    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="financial_profile")