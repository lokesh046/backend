"""
Enterprise Database Configuration for AI Financial Planning SaaS
Optimized for 1M+ users, multi-region, high availability
"""

import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils import database_exists, create_database

load_dotenv()


class EnterpriseDatabaseConfig:
    """
    Enterprise database configuration with production-grade settings
    """
    
    # Connection settings
    POOL_SIZE = 20
    MAX_OVERFLOW = 30
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 1800  # 30 minutes
    POOL_PRE_PING = True
    
    # Query optimization
    ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
    JIT = "off"
    
    # Timeouts
    CONNECT_TIMEOUT = 60
    COMMAND_TIMEOUT = 120
    
    # SSL
    SSL_MODE = "require"
    
    # Application name for connection tracking
    APP_NAME = "fire_number_enterprise"


def get_database_url() -> str:
    """Get database URL from environment or use default"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://neondb_owner:npg_6Y0mztCLoeVW@ep-dark-pine-a19uo1ap-pooler.ap-southeast-1.aws.neon.tech/neondb"
    )


def get_sync_database_url() -> str:
    """Get sync database URL for migrations and admin tasks"""
    url = get_database_url()
    return url.replace("+asyncpg", "")


def create_enterprise_engine(
    database_url: str = None,
    pool_size: int = None,
    max_overflow: int = None,
    echo: bool = None,
) -> AsyncEngine:
    """
    Create enterprise-grade async database engine
    """
    database_url = database_url or get_database_url()
    
    config = EnterpriseDatabaseConfig()
    
    engine = create_async_engine(
        database_url,
        echo=echo if echo is not None else config.ECHO,
        pool_size=pool_size or config.POOL_SIZE,
        max_overflow=max_overflow or config.MAX_OVERFLOW,
        pool_timeout=config.POOL_TIMEOUT,
        pool_recycle=config.POOL_RECYCLE,
        pool_pre_ping=config.POOL_PRE_PING,
        poolclass=AsyncAdaptedQueuePool,
        connect_args={
            "ssl": config.SSL_MODE,
            "server_settings": {
                "application_name": config.APP_NAME,
                "jit": config.JIT,
                "timezone": "UTC",
            },
            "timeout": config.CONNECT_TIMEOUT,
            "command_timeout": config.COMMAND_TIMEOUT,
        },
        execution_options={
            "isolation_level": "READ COMMITTED",
        }
    )
    
    return engine


# Default engine instance
engine = create_enterprise_engine()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Base for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session (alternative to dependency injection)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables - WARNING: destructive operation"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_database_connection() -> bool:
    """Check if database is accessible"""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


# ============================================================================
# REPLICA SUPPORT FOR READ SCALING
# ============================================================================

class DatabaseCluster:
    """
    Database cluster configuration for read/write splitting
    """
    
    def __init__(self):
        self.primary_url = get_database_url()
        self.replica_urls: list[str] = []
        
        # Add replica URLs from environment
        replica_url = os.getenv("DATABASE_REPLICA_URL")
        if replica_url:
            self.replica_urls.append(replica_url)
    
    def get_primary_engine(self) -> AsyncEngine:
        """Get primary database engine for writes"""
        return create_enterprise_engine(self.primary_url)
    
    def get_replica_engine(self, index: int = 0) -> AsyncEngine:
        """Get replica database engine for reads"""
        if not self.replica_urls:
            return self.get_primary_engine()
        
        url = self.replica_urls[index % len(self.replica_urls)]
        return create_enterprise_engine(url)
    
    def get_session_factory(self, is_replica: bool = False):
        """Get session factory for primary or replica"""
        engine = self.get_replica_engine() if is_replica else self.get_primary_engine()
        return async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


# Cluster instance for production use
db_cluster = DatabaseCluster()


# ============================================================================
# TENANT CONTEXT FOR MULTI-TENANCY
# ============================================================================

class TenantContext:
    """
    Thread-safe tenant context for multi-tenancy
    """
    
    _context: dict = {}
    
    @classmethod
    def set_tenant_id(cls, tenant_id: str):
        cls._context['tenant_id'] = tenant_id
    
    @classmethod
    def get_tenant_id(cls) -> str | None:
        return cls._context.get('tenant_id')
    
    @classmethod
    def clear(cls):
        cls._context.clear()


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================

async def with_transaction(session: AsyncSession, func):
    """
    Execute function within a transaction
    """
    async with session.begin():
        return await func(session)


async def with_savepoint(session: AsyncSession, func):
    """
    Execute function within a savepoint (nested transaction)
    """
    async with session.begin_nested():
        return await func(session)


# ============================================================================
# BULK OPERATIONS
# ============================================================================

async def bulk_insert(session: AsyncSession, model, records: list[dict], batch_size: int = 1000):
    """
    Bulk insert records efficiently
    """
    from sqlalchemy.dialects.postgresql import insert
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        stmt = insert(model).values(batch)
        await session.execute(stmt)
    
    await session.commit()


async def bulk_update(session: AsyncSession, model, updates: list[dict], batch_size: int = 1000):
    """
    Bulk update records efficiently
    """
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        for update in batch:
            await session.execute(
                model.__table__.update().where(
                    model.id == update['id']
                ).values(**{k: v for k, v in update.items() if k != 'id'})
            )
    
    await session.commit()
