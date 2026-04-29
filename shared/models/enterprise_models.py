"""
Enterprise Database Schema for AI Financial Planning SaaS Platform
Designed for 1M+ users, multi-tenancy, compliance, and analytics
"""

import uuid
import enum
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Integer, Float,
    Text, Enum, Index, UniqueConstraint, CheckConstraint, Numeric,
    BigInteger, SmallInteger, Text, JSON, TIMESTAMP, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    API_USER = "api_user"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"
    PAUSED = "paused"


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PlanType(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "failed"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    API_ACCESS = "api_access"


class LoanType(str, enum.Enum):
    HOME = "home"
    PERSONAL = "personal"
    CAR = "car"
    EDUCATION = "education"
    BUSINESS = "business"
    OTHER = "other"


class CalculationStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# TENANT & ORGANIZATION (Multi-Tenancy)
# ============================================================================

class Tenant(Base):
    """
    Multi-tenant support - each organization/company gets a tenant
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    tenant_type = Column(String(50), default="individual")  # individual, business, enterprise
    
    settings = Column(JSONB, default=dict)
    features = Column(JSONB, default=dict)
    
    data_residency = Column(String(100), default="us-east-1")
    timezone = Column(String(50), default="UTC")
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="tenant", uselist=False)
    organizations = relationship("Organization", back_populates="tenant", cascade="all, delete-orphan")


class Organization(Base):
    """
    Sub-organizations within a tenant (departments, teams)
    """
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)
    
    settings = Column(JSONB, default=dict)
    
    parent_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="organizations")
    parent = relationship("Organization", remote_side="Organization.id", backref="children")
    users = relationship("UserOrganization", back_populates="organization")


# ============================================================================
# USERS & AUTHENTICATION
# ============================================================================

class User(Base):
    """
    Core user table with enterprise features
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    email = Column(String(500), nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    avatar_url = Column(String(500))
    
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False, index=True)
    is_superuser = Column(Boolean, default=False)
    
    email_verified_at = Column(DateTime, nullable=True)
    phone_verified_at = Column(DateTime, nullable=True)
    
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45))
    
    preferences = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    organizations = relationship("UserOrganization", back_populates="user")
    
    financial_profile = relationship(
        "UserFinancialProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    fire_calculations = relationship(
        "FireCalculation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    loan_simulations = relationship(
        "LoanSimulation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    health_scores = relationship(
        "HealthScore",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    subscription = relationship("UserSubscription", back_populates="user", uselist=False)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_user_tenant_email'),
    )


class UserOrganization(Base):
    """
    Many-to-many relationship between users and organizations
    """
    __tablename__ = "user_organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(50), default="member")
    is_default = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='uq_user_org'),
    )


class RefreshToken(Base):
    """
    JWT refresh tokens for session management
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    token_family = Column(UUID(as_uuid=True), index=True)
    
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    
    device_info = Column(JSONB, default=dict)
    ip_address = Column(String(45))
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class LoginHistory(Base):
    """
    Track all login attempts for security and compliance
    """
    __tablename__ = "login_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, blocked
    
    ip_address = Column(String(45), index=True)
    user_agent = Column(Text)
    device_info = Column(JSONB, default=dict)
    
    location = Column(JSONB, default=dict)
    fail_reason = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="login_history")


class APIKey(Base):
    """
    API keys for programmatic access
    """
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(20), nullable=False)
    
    permissions = Column(ARRAY(String), default=[])
    rate_limit = Column(Integer, default=1000)
    
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45))
    
    is_active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")


# ============================================================================
# SUBSCRIPTION & MONETIZATION
# ============================================================================

class SubscriptionPlan(Base):
    """
    Subscription plans configuration
    """
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    tier = Column(Enum(SubscriptionTier), nullable=False, index=True)
    plan_type = Column(Enum(PlanType), nullable=False)
    
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2), nullable=False)
    
    features = Column(JSONB, default=dict)
    limits = Column(JSONB, default=dict)
    
    api_calls_limit = Column(Integer, default=1000)
    storage_gb = Column(Integer, default=1)
    users_limit = Column(Integer, default=1)
    ai_chat_limit = Column(Integer, default=100)
    
    is_active = Column(Boolean, default=True, index=True)
    is_public = Column(Boolean, default=True)
    
    trial_days = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    """
    Tenant-level subscription
    """
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False, index=True)
    tier = Column(Enum(SubscriptionTier), nullable=False, index=True)
    
    billing_cycle_start = Column(Date, nullable=False)
    billing_cycle_end = Column(Date, nullable=False)
    
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)
    
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    plan = relationship("SubscriptionPlan")
    invoices = relationship("Invoice", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")


class UserSubscription(Base):
    """
    User-level subscription (for individual plans)
    """
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False)
    tier = Column(Enum(SubscriptionTier), nullable=False)
    
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    cancel_at_period_end = Column(Boolean, default=False)
    
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan")


class Payment(Base):
    """
    Payment records
    """
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    status = Column(Enum(PaymentStatus), nullable=False, index=True)
    
    payment_method = Column(String(50))
    payment_gateway = Column(String(50), default="stripe")
    
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    stripe_charge_id = Column(String(255))
    
    gateway_response = Column(JSONB, default=dict)
    
    refunded_amount = Column(Numeric(10, 2), default=0)
    refunded_at = Column(DateTime, nullable=True)
    
    failure_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="payments")


class Invoice(Base):
    """
    Invoice records
    """
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    status = Column(String(50), nullable=False)  # draft, open, paid, void
    
    stripe_invoice_id = Column(String(255), unique=True, index=True)
    
    line_items = Column(JSONB, default=list)
    
    due_date = Column(Date)
    paid_at = Column(DateTime, nullable=True)
    
    pdf_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")


# ============================================================================
# FINANCIAL DATA
# ============================================================================

class UserFinancialProfile(Base):
    """
    Enhanced financial profile with versioning for audit trail
    """
    __tablename__ = "user_financial_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    version = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Income & Expenses
    monthly_income = Column(Numeric(14, 2))
    additional_income = Column(Numeric(14, 2), default=0)
    living_expense = Column(Numeric(14, 2))
    discretionary_expense = Column(Numeric(14, 2), default=0)
    
    # Assets
    current_savings = Column(Numeric(14, 2), default=0)
    investment_assets = Column(Numeric(14, 2), default=0)
    retirement_assets = Column(Numeric(14, 2), default=0)
    real_estate_value = Column(Numeric(14, 2), default=0)
    other_assets = Column(Numeric(14, 2), default=0)
    
    # Liabilities
    total_debt = Column(Numeric(14, 2), default=0)
    mortgage_balance = Column(Numeric(14, 2), default=0)
    student_loan_balance = Column(Numeric(14, 2), default=0)
    credit_card_balance = Column(Numeric(14, 2), default=0)
    other_debts = Column(Numeric(14, 2), default=0)
    
    # Loan details
    has_loan = Column(Boolean, default=False)
    loan_emi = Column(Numeric(14, 2))
    loan_years_remaining = Column(Integer)
    loan_interest_rate = Column(Numeric(5, 2))
    loan_type = Column(Enum(LoanType))
    
    # Insurance
    has_health_insurance = Column(Boolean, default=False)
    has_life_insurance = Column(Boolean, default=False)
    has_disability_insurance = Column(Boolean, default=False)
    insurance_coverage = Column(Numeric(14, 2), default=0)
    
    # Assumptions
    expected_return_rate = Column(Numeric(5, 2), default=Decimal("0.07"))
    inflation_rate = Column(Numeric(5, 2), default=Decimal("0.03"))
    safe_withdrawal_rate = Column(Numeric(5, 2), default=Decimal("0.04"))
    
    # Goals
    retirement_goal_age = Column(Integer)
    retirement_goal_amount = Column(Numeric(14, 2))
    emergency_fund_goal = Column(Numeric(14, 2))
    
    # Profile metadata
    risk_tolerance = Column(String(20))  # conservative, moderate, aggressive
    investment_experience = Column(String(20))  # beginner, intermediate, advanced
    dependents_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="financial_profile")

    __table_args__ = (
        Index('ix_financial_profile_user_version', 'user_id', 'version'),
    )


class FireCalculation(Base):
    """
    FIRE calculations with version history
    """
    __tablename__ = "fire_calculations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_financial_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    
    status = Column(Enum(CalculationStatus), default=CalculationStatus.PENDING, nullable=False, index=True)
    
    # Inputs
    monthly_income = Column(Numeric(14, 2))
    living_expense = Column(Numeric(14, 2))
    current_savings = Column(Numeric(14, 2))
    expected_return = Column(Numeric(5, 2))
    inflation_rate = Column(Numeric(5, 2))
    
    # Results
    fire_number = Column(Numeric(14, 2), index=True)
    fire_year = Column(Integer, index=True)
    final_wealth = Column(Numeric(14, 2))
    years_to_fire = Column(Integer)
    monthly_savings_needed = Column(Numeric(14, 2))
    
    # Breakdown
    savings_rate = Column(Numeric(5, 4))
    investment_growth = Column(Numeric(14, 2))
    
    # Scenario
    scenario_name = Column(String(100))
    scenario_type = Column(String(50))  # optimistic, baseline, conservative
    
    # Parameters used
    calculation_params = Column(JSONB, default=dict)
    result_breakdown = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="fire_calculations")

    __table_args__ = (
        Index('ix_fire_user_created', 'user_id', 'created_at'),
        Index('ix_fire_year_score', 'fire_year', 'fire_number'),
    )


class HealthScore(Base):
    """
    Financial health scoring with historical tracking
    """
    __tablename__ = "health_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_financial_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Overall score (0-100)
    overall_score = Column(Numeric(5, 2), index=True)
    grade = Column(String(2))  # A+, A, B+, B, C, D, F
    
    # Component scores
    emergency_fund_score = Column(Numeric(5, 2))
    debt_score = Column(Numeric(5, 2))
    savings_score = Column(Numeric(5, 2))
    insurance_score = Column(Numeric(5, 2))
    retirement_score = Column(Numeric(5, 2))
    
    # Ratios
    savings_ratio = Column(Numeric(5, 4), index=True)
    debt_to_income_ratio = Column(Numeric(5, 4), index=True)
    debt_to_asset_ratio = Column(Numeric(5, 4))
    emergency_fund_months = Column(Numeric(5, 2))
    
    # FIRE alignment
    fire_readiness = Column(Numeric(5, 4))
    fire_number = Column(Numeric(14, 2))
    fire_progress = Column(Numeric(5, 4))
    
    # Analysis
    strengths = Column(ARRAY(String), default=[])
    weaknesses = Column(ARRAY(String), default=[])
    recommendations = Column(ARRAY(String), default=[])
    
    analysis_details = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="health_scores")

    __table_args__ = (
        Index('ix_health_user_created', 'user_id', 'created_at'),
    )


class LoanSimulation(Base):
    """
    Loan simulations with amortization schedules
    """
    __tablename__ = "loan_simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100))
    loan_type = Column(Enum(LoanType), default=LoanType.PERSONAL)
    
    # Loan details
    principal = Column(Numeric(14, 2), nullable=False)
    interest_rate = Column(Numeric(7, 4), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    
    # Results
    emi = Column(Numeric(14, 2))
    total_interest = Column(Numeric(14, 2))
    total_payment = Column(Numeric(14, 2))
    
    # Optimization
    optimal_emi = Column(Numeric(14, 2))
    optimal_tenure = Column(Integer)
    interest_savings = Column(Numeric(14, 2))
    tenure_reduction_months = Column(Integer)
    
    # Comparison
    comparison_scenarios = Column(JSONB, default=list)
    
    # Amortization
    amortization_schedule = Column(JSONB, default=list)
    
    # Parameters
    simulation_params = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="loan_simulations")


# ============================================================================
# AI CHAT
# ============================================================================

class ChatSession(Base):
    """
    AI chat sessions with metadata
    """
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255))
    status = Column(String(20), default="active", index=True)  # active, archived
    
    # Context
    context_data = Column(JSONB, default=dict)
    current_fire_calculation_id = Column(UUID(as_uuid=True), nullable=True)
    current_profile_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Stats
    message_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    
    # Memory summary for quick retrieval
    memory_summary = Column(Text)
    key_insights = Column(JSONB, default=list)
    
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_session_user_status', 'user_id', 'status'),
        Index('ix_session_user_last', 'user_id', 'last_message_at'),
    )


class ChatMessage(Base):
    """
    Chat messages with token tracking
    """
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True)
    
    # AI specifics
    model = Column(String(100))
    token_count = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    
    # Tool usage
    tools_used = Column(JSONB, default=list)
    tool_results = Column(JSONB, default=dict)
    
    # Attachments
    attachments = Column(JSONB, default=list)
    
    # Metadata
    message_metadata = Column(JSONB, default=dict)
    feedback = Column(String(20))  # positive, negative, neutral
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index('ix_message_session_created', 'session_id', 'created_at'),
    )


# ============================================================================
# AUDIT & COMPLIANCE
# ============================================================================

class AuditLog(Base):
    """
    Comprehensive audit logging for compliance
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    changes = Column(JSONB, default=dict)
    old_values = Column(JSONB, default=dict)
    new_values = Column(JSONB, default=dict)
    
    ip_address = Column(String(45), index=True)
    user_agent = Column(Text)
    request_id = Column(String(100), index=True)
    session_id = Column(UUID(as_uuid=True), index=True)
    
    api_endpoint = Column(String(500))
    http_method = Column(String(10))
    http_status = Column(Integer)
    
    is_pii_access = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_audit_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_audit_user_created', 'user_id', 'created_at'),
        Index('ix_audit_resource', 'resource_type', 'resource_id', 'created_at'),
    )


class DataExport(Base):
    """
    Track data export requests for GDPR compliance
    """
    __tablename__ = "data_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    
    export_type = Column(String(50), nullable=False)  # full, financial, chat, etc.
    formats = Column(ARRAY(String), default=["json"])
    
    status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    
    file_url = Column(String(500))
    file_size_bytes = Column(BigInteger)
    
    record_count = Column(Integer)
    
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class DataRetentionPolicy(Base):
    """
    Data retention policies for compliance
    """
    __tablename__ = "data_retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    data_type = Column(String(50), nullable=False, unique=True)  # chat_messages, audit_logs, etc.
    
    retention_days = Column(Integer, nullable=False)
    archive_after_days = Column(Integer)
    delete_after_days = Column(Integer)
    
    is_active = Column(Boolean, default=True)
    applies_to = Column(String(20), default="all")  # all, free, paid, enterprise
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# NOTIFICATIONS & COMMUNICATIONS
# ============================================================================

class Notification(Base):
    """
    User notifications
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    type = Column(String(50), nullable=False, index=True)  # email_verification, subscription, alert, etc.
    channel = Column(String(20), default="in_app")  # email, sms, push, in_app
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    data = Column(JSONB, default=dict)
    
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index('ix_notification_user_read', 'user_id', 'is_read'),
    )


class Webhook(Base):
    """
    Webhook configurations for integrations
    """
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    
    events = Column(ARRAY(String), nullable=False)  # subscription.created, payment.completed, etc.
    
    secret = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    
    last_triggered_at = Column(DateTime, nullable=True)
    last_status = Column(Integer)
    last_response = Column(Text)
    
    failure_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookDelivery(Base):
    """
    Webhook delivery attempts
    """
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    event = Column(String(100), nullable=False)
    payload = Column(JSONB, default=dict)
    
    status = Column(String(20), nullable=False)  # pending, success, failed
    status_code = Column(Integer)
    response_body = Column(Text)
    
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    next_attempt_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimit(Base):
    """
    Rate limiting tracking
    """
    __tablename__ = "rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    identifier = Column(String(255), nullable=False, index=True)  # user_id or api_key or ip
    endpoint = Column(String(500), nullable=False)
    
    limit_count = Column(Integer, nullable=False)
    window_seconds = Column(Integer, nullable=False)
    
    current_count = Column(Integer, default=0)
    reset_at = Column(DateTime, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('identifier', 'endpoint', name='uq_rate_limit'),
    )


# ============================================================================
# ANALYTICS (Materialized Views Support)
# ============================================================================

class DailyUserActivity(Base):
    """
    Aggregated daily user activity for analytics
    """
    __tablename__ = "daily_user_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    date = Column(Date, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Activity counts
    fire_calculations_count = Column(Integer, default=0)
    loan_simulations_count = Column(Integer, default=0)
    health_scores_count = Column(Integer, default=0)
    chat_sessions_count = Column(Integer, default=0)
    chat_messages_count = Column(Integer, default=0)
    profile_updates_count = Column(Integer, default=0)
    
    # Time spent (seconds)
    total_session_time = Column(Integer, default=0)
    
    # Features used
    features_used = Column(ARRAY(String), default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('date', 'user_id', 'tenant_id', name='uq_daily_user_activity'),
    )


class DailyTenantStats(Base):
    """
    Aggregated daily tenant statistics
    """
    __tablename__ = "daily_tenant_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    date = Column(Date, nullable=False, index=True)
    
    # User stats
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    churned_users = Column(Integer, default=0)
    
    # Subscription stats
    total_subscriptions = Column(Integer, default=0)
    active_subscriptions = Column(Integer, default=0)
    mrr = Column(Numeric(12, 2), default=0)
    
    # Usage stats
    total_api_calls = Column(BigInteger, default=0)
    total_ai_tokens = Column(BigInteger, default=0)
    total_storage_gb = Column(Numeric(10, 2), default=0)
    
    # Financial
    total_fire_calculations = Column(Integer, default=0)
    total_loan_simulations = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'date', name='uq_daily_tenant_stats'),
    )


# ============================================================================
# INDEXING STRATEGY
# ============================================================================

def create_indexes():
    """
    Additional indexes for performance
    """
    indexes = [
        # User indexes
        "CREATE INDEX IF NOT EXISTS ix_users_tenant_active ON users(tenant_id, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_users_tenant_role ON users(tenant_id, role)",
        
        # Financial profile indexes
        "CREATE INDEX IF NOT EXISTS ix_profile_user_active ON user_financial_profiles(user_id, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_profile_retirement ON user_financial_profiles(retirement_goal_age)",
        
        # FIRE calculation indexes
        "CREATE INDEX IF NOT EXISTS ix_fire_user_status ON fire_calculations(user_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_fire_created_user ON fire_calculations(created_at DESC, user_id)",
        
        # Health score indexes
        "CREATE INDEX IF NOT EXISTS ix_health_user_score ON health_scores(user_id, overall_score DESC)",
        "CREATE INDEX IF NOT EXISTS ix_health_created_user ON health_scores(created_at DESC, user_id)",
        
        # Loan indexes
        "CREATE INDEX IF NOT EXISTS ix_loan_user_type ON loan_simulations(user_id, loan_type)",
        
        # Chat indexes
        "CREATE INDEX IF NOT EXISTS ix_chat_user_status_active ON chat_sessions(user_id, status) WHERE status = 'active'",
        "CREATE INDEX IF NOT EXISTS ix_chat_message_token ON chat_messages(token_count)",
        
        # Audit indexes
        "CREATE INDEX IF NOT EXISTS ix_audit_action_created ON audit_logs(action, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_audit_pii ON audit_logs(is_pii_access, created_at DESC)",
        
        # Notification indexes
        "CREATE INDEX IF NOT EXISTS ix_notification_user_type ON notifications(user_id, type, created_at DESC)",
    ]
    return indexes


# ============================================================================
# PARTITIONING STRATEGY
# ============================================================================

def get_partition_statements():
    """
    PostgreSQL partitioning strategies for scale
    """
    statements = [
        # Partition audit_logs by month
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            LIKE audit_logs INCLUDING ALL
        ) PARTITION BY RANGE (created_at);
        """,
        
        # Create partitions for last 12 months
        """
        CREATE TABLE IF NOT EXISTS audit_logs_2026_01 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
        """,
        
        # Partition chat_messages by month
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            LIKE chat_messages INCLUDING ALL
        ) PARTITION BY RANGE (created_at);
        """,
        
        # Partition rate_limits by day
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            LIKE rate_limits INCLUDING ALL
        ) PARTITION BY RANGE (reset_at);
        """,
        
        # Partition daily stats by month
        """
        CREATE TABLE IF NOT EXISTS daily_tenant_stats (
            LIKE daily_tenant_stats INCLUDING ALL
        ) PARTITION BY RANGE (date);
        """,
    ]
    return statements
