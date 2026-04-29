# Enterprise Database Architecture Design

## Executive Summary

This document outlines the comprehensive database redesign for your AI Financial Planning SaaS platform, designed to support 1M+ users with enterprise-grade features.

---

## 1. Current Schema Analysis

### Issues Identified:
1. **No multi-tenancy** - Single tenant architecture
2. **Missing security tables** - No refresh tokens, login history, API keys
3. **No monetization** - No subscription, payment, invoice tables
4. **No audit trail** - Not compliance-ready
5. **Limited indexing** - Missing composite indexes
6. **No analytics** - No aggregation tables
7. **No data retention** - No archiving strategy
8. **Limited relationships** - No version history for financial data

---

## 2. New Tables Added

### 2.1 Multi-Tenancy (NEW)
| Table | Purpose |
|-------|---------|
| `tenants` | Organizations/companies |
| `organizations` | Sub-departments within tenants |

### 2.2 Authentication & Security (NEW)
| Table | Purpose |
|-------|---------|
| `refresh_tokens` | JWT refresh token management |
| `login_history` | Track all login attempts |
| `api_keys` | Programmatic API access |
| `user_organizations` | User-organization mapping |

### 2.3 Monetization (NEW)
| Table | Purpose |
|-------|---------|
| `subscription_plans` | Plan definitions (Free, Starter, Pro, Enterprise) |
| `subscriptions` | Tenant-level subscriptions |
| `user_subscriptions` | Individual user subscriptions |
| `payments` | Payment records |
| `invoices` | Invoice generation |

### 2.4 Audit & Compliance (NEW)
| Table | Purpose |
|-------|---------|
| `audit_logs` | Comprehensive audit trail |
| `data_exports` | GDPR data export tracking |
| `data_retention_policies` | Retention rules |

### 2.5 Notifications & Integrations (NEW)
| Table | Purpose |
|-------|---------|
| `notifications` | In-app notifications |
| `webhooks` | Webhook configurations |
| `webhook_deliveries` | Webhook delivery tracking |
| `rate_limits` | API rate limiting |

### 2.6 Analytics (NEW)
| Table | Purpose |
|-------|---------|
| `daily_user_activities` | Per-user daily aggregations |
| `daily_tenant_stats` | Per-tenant daily statistics |

---

## 3. Schema Improvements

### 3.1 Enhanced Financial Tables

#### UserFinancialProfile (Enhanced)
```python
# Added:
- version (for audit trail)
- previous_version_id (link to previous)
- Detailed asset breakdown (investments, retirement, real estate)
- Detailed liability breakdown (mortgage, student loans, credit cards)
- Insurance details (health, life, disability)
- Assumptions (return rate, inflation, safe withdrawal rate)
- Goals (retirement age, emergency fund)
- Profile metadata (risk tolerance, dependents)
- is_verified flag for compliance
```

#### FireCalculation (Enhanced)
```python
# Added:
- profile_id (link to financial profile)
- status (pending/completed/failed)
- Detailed breakdown (savings rate, investment growth)
- scenario_name and scenario_type
- calculation_params (for reproducibility)
- result_breakdown (detailed results)
```

#### HealthScore (Enhanced)
```python
# Added:
- Component scores (emergency fund, debt, savings, insurance, retirement)
- Ratios (debt-to-income, debt-to-asset, emergency fund months)
- FIRE alignment (fire_readiness, fire_progress)
- strengths, weaknesses, recommendations arrays
- analysis_details JSONB
```

#### LoanSimulation (Enhanced)
```python
# Added:
- name, loan_type
- Optimal calculations (optimal_emi, interest_savings)
- comparison_scenarios
- amortization_schedule
```

### 3.2 Enhanced Chat Tables

#### ChatSession (Enhanced)
```python
# Added:
- status (active/archived)
- context_data (for AI context)
- current_fire_calculation_id, current_profile_id
- message_count, token_count
- memory_summary, key_insights
- last_message_at, ended_at
```

#### ChatMessage (Enhanced)
```python
# Added:
- content_hash (deduplication)
- model, token_count, input_tokens, output_tokens
- tools_used, tool_results
- attachments, feedback
```

---

## 4. Indexing Strategy

### 4.1 Composite Indexes
```sql
-- User queries
ix_users_tenant_active ON users(tenant_id, is_active)
ix_users_tenant_role ON users(tenant_id, role)

-- Financial profiles
ix_profile_user_active ON user_financial_profiles(user_id, is_active)
ix_financial_profile_user_version ON user_financial_profiles(user_id, version)

-- FIRE calculations
ix_fire_user_created ON fire_calculations(user_id, created_at)
ix_fire_year_score ON fire_calculations(fire_year, fire_number)
ix_fire_user_status ON fire_calculations(user_id, status)

-- Health scores
ix_health_user_created ON health_scores(user_id, created_at)
ix_health_user_score ON health_scores(user_id, overall_score DESC)

-- Chat
ix_session_user_status ON chat_sessions(user_id, status)
ix_session_user_last ON chat_sessions(user_id, last_message_at)
ix_message_session_created ON chat_messages(session_id, created_at)

-- Audit
ix_audit_tenant_created ON audit_logs(tenant_id, created_at)
ix_audit_user_created ON audit_logs(user_id, created_at)
ix_audit_resource ON audit_logs(resource_type, resource_id, created_at)
```

### 4.2 Partial Indexes
```sql
-- Active chat sessions
ix_chat_user_status_active ON chat_sessions(user_id, status) 
    WHERE status = 'active'

-- PII access in audit
ix_audit_pii ON audit_logs(is_pii_access, created_at) 
    WHERE is_pii_access = true
```

---

## 5. Partitioning Strategy

### 5.1 Time-Based Partitioning

| Table | Partition Key | Strategy |
|-------|---------------|----------|
| `audit_logs` | created_at | Monthly |
| `chat_messages` | created_at | Monthly |
| `rate_limits` | reset_at | Daily |
| `daily_tenant_stats` | date | Monthly |
| `daily_user_activities` | date | Monthly |

### 5.2 Example Partition Creation
```sql
-- Audit logs monthly partition
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE audit_logs_2026_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

---

## 6. Security Strategy

### 6.1 Row-Level Security
```sql
-- Enable RLS for tenant isolation
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_tenant_policy ON users
    USING (tenant_id = current_setting('app.tenant_id'));
```

### 6.2 Data Encryption
- **At Rest**: PostgreSQL TDE (enterprise) or pgcrypto
- **In Transit**: SSL/TLS required (already configured)
- **Application**: Sensitive fields encrypted with field-level encryption

### 6.3 PII Handling
```sql
-- Mark PII columns
COMMENT ON COLUMN users.email IS 'PII: personal data';
COMMENT ON COLUMN users.phone IS 'PII: personal data';

-- Audit PII access
CREATE INDEX ix_audit_pii ON audit_logs(is_pii_access, created_at);
```

---

## 7. Data Retention Strategy

### 7.1 Retention Policies
| Data Type | Retention | Archive After | Delete After |
|-----------|-----------|---------------|--------------|
| Chat Messages | 2 years | 1 year | 2 years |
| Audit Logs | 7 years | 3 years | 7 years |
| Login History | 1 year | 6 months | 1 year |
| Financial Profiles | Forever | N/A | N/A |
| Invoices | Forever | N/A | N/A |

### 7.2 Implementation
```python
class DataRetentionPolicy(Base):
    data_type = Column(String(50))
    retention_days = Column(Integer)
    archive_after_days = Column(Integer)
    delete_after_days = Column(Integer)
```

---

## 8. Analytics-Ready Design

### 8.1 Materialized Views (Recommended)
```sql
-- Monthly revenue by plan
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT 
    date_trunc('month', created_at) as month,
    tier,
    COUNT(*) as subscriptions,
    SUM(price) as revenue
FROM subscriptions
JOIN subscription_plans ON subscriptions.plan_id = subscription_plans.id
GROUP BY 1, 2;

-- User engagement metrics
CREATE MATERIALIZED VIEW user_engagement AS
SELECT 
    date_trunc('day', created_at) as day,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(*) as total_sessions,
    SUM(chat_messages_count) as messages
FROM daily_user_activities
GROUP BY 1;
```

### 8.2 Real-time Analytics Tables
```python
# Pre-aggregated tables updated via triggers or scheduled jobs
- daily_user_activities
- daily_tenant_stats
```

---

## 9. Scalability Strategy

### 9.1 Read/Write Splitting
```python
class DatabaseCluster:
    primary_url: str  # Write operations
    replica_urls: list[str]  # Read operations
    
    def get_primary_engine(self):
        # Direct to primary
        pass
    
    def get_replica_engine(self):
        # Round-robin across replicas
        pass
```

### 9.2 Connection Pooling
- Pool size: 20 (adjust based on concurrent users)
- Max overflow: 30
- Pool recycle: 30 minutes
- Pre-ping: Enabled (check connection health)

### 9.3 Caching Strategy
- Redis for session data
- Redis for frequently accessed calculations
- Cache financial profiles per user

### 9.4 Multi-Region Strategy
```python
# Primary region: us-east-1
# Read replicas: us-west-2, eu-west-1, ap-southeast-1

# For multi-region:
# 1. Set up PostgreSQL logical replication
# 2. Use PgBouncer for connection pooling
# 3. Implement geo-routing at DNS level
```

---

## 10. Recommended Dashboard Queries

### 10.1 User Dashboard
```sql
-- Current financial health
SELECT 
    hs.overall_score,
    hs.grade,
    hs.savings_ratio,
    hs.debt_to_income_ratio,
    hs.fire_readiness,
    fc.fire_year,
    fc.fire_number
FROM health_scores hs
LEFT JOIN fire_calculations fc ON fc.user_id = hs.user_id
WHERE hs.user_id = :user_id
ORDER BY hs.created_at DESC
LIMIT 1;

-- Recent FIRE calculations
SELECT 
    fire_year,
    fire_number,
    monthly_savings_needed,
    created_at
FROM fire_calculations
WHERE user_id = :user_id
ORDER BY created_at DESC
LIMIT 10;

-- Loan simulations
SELECT 
    name,
    loan_type,
    principal,
    emi,
    total_interest,
    created_at
FROM loan_simulations
WHERE user_id = :user_id
ORDER BY created_at DESC;
```

### 10.2 Admin Dashboard
```sql
-- Daily active users
SELECT 
    date,
    SUM(active_users) as total_active_users
FROM daily_tenant_stats
WHERE date >= CURRENT_DATE - 30
GROUP BY date
ORDER BY date;

-- Revenue metrics
SELECT 
    date_trunc('day', p.created_at) as day,
    SUM(p.amount) as daily_revenue,
    COUNT(DISTINCT p.id) as transactions
FROM payments p
WHERE p.status = 'completed'
    AND p.created_at >= CURRENT_DATE - 30
GROUP BY 1;

-- Subscription breakdown
SELECT 
    tier,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE status = 'active') as active
FROM subscriptions
GROUP BY tier;
```

### 10.3 Analytics Dashboard
```sql
-- User engagement funnel
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE has_fire_calculation) as did_fire_calc,
    COUNT(*) FILTER (WHERE has_loan_simulation) as did_loan_sim,
    COUNT(*) FILTER (WHERE has_chat_session) as used_chat,
    COUNT(*) FILTER (WHERE has_health_score) as checked_health
FROM (
    SELECT 
        user_id,
        BOOL_OR(id IS NOT NULL) as has_fire_calculation
    FROM fire_calculations
    GROUP BY user_id
) f;

-- FIRE progress distribution
SELECT 
    CASE 
        WHEN fire_progress < 0.25 THEN '0-25%'
        WHEN fire_progress < 0.50 THEN '25-50%'
        WHEN fire_progress < 0.75 THEN '50-75%'
        ELSE '75-100%'
    END as progress_range,
    COUNT(*) as users
FROM health_scores
WHERE created_at >= CURRENT_DATE - 7
GROUP BY 1;
```

---

## 11. Migration Strategy

### 11.1 Phase 1: Add New Tables
1. Create all new tables (tenants, subscriptions, audit_logs, etc.)
2. Add nullable tenant_id to existing tables
3. Create indexes

### 11.2 Phase 2: Data Migration
1. Migrate existing users to default tenant
2. Migrate subscription data
3. Enable RLS

### 11.3 Phase 3: Deprecation
1. Remove non-tenant-aware code
2. Add NOT NULL constraint on tenant_id
3. Remove legacy columns

---

## 12. Files Created

| File | Description |
|------|-------------|
| `shared/models/enterprise_models.py` | All enterprise SQLAlchemy models |
| `shared/database_enterprise.py` | Enterprise database configuration |
| `DATABASE_ARCHITECTURE.md` | This design document |

---

## 13. Next Steps

1. **Review and approve** the schema design
2. **Run migrations** to create new tables
3. **Update application code** to use new tenant context
4. **Set up monitoring** for query performance
5. **Configure backup strategy** for disaster recovery

---

## 14. Compliance Notes

### GDPR
- Data export functionality ready (data_exports table)
- Right to deletion supported via cascade
- Data portability via standardized exports

### SOC 2
- Audit logging comprehensive
- Access logs maintained
- Encryption in place

### PCI-DSS (Future)
- Payment data stored via Stripe (not locally)
- Use Stripe's PCI-compliant infrastructure
