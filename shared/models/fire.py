import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base
from sqlalchemy import Integer

class FireCalculation(Base):
    __tablename__ = "fire_calculations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    monthly_income = Column(Float)
    living_expense = Column(Float)
    current_savings = Column(Float)

    fire_number = Column(Float)
    fire_year = Column(Integer)
    final_wealth = Column(Float)

    scenario_name = Column(String, default="Primary Goal")

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="fire_calculations")