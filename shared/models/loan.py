import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base


class LoanSimulation(Base):
    __tablename__ = "loan_simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    loan_amount = Column(Float)
    interest_rate = Column(Float)
    tenure_years = Column(Float)

    optimal_emi = Column(Float)
    total_interest = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="loan_simulations")