import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base


class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    score = Column(Float)
    fire_number = Column(Float)
    debt_ratio = Column(Float)
    savings_ratio = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="health_scores")