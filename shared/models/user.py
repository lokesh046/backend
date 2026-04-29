import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False, default="")
    password_hash = Column(String, nullable=False)

    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    financial_profile = relationship(
        "UserFinancialProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete"
    )

    fire_calculations = relationship(
        "FireCalculation",
        back_populates="user",
        cascade="all, delete"
    )

    loan_simulations = relationship(
        "LoanSimulation",
        back_populates="user",
        cascade="all, delete"
    )

    health_scores = relationship(
        "HealthScore",
        back_populates="user",
        cascade="all, delete"
    )

    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete"
    )

class EmailVerificationOTP(Base):
    __tablename__ = "email_verification_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    otp_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)

    user = relationship("User", backref="otp_verification")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", backref="password_resets")