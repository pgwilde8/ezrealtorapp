"""
Database utilities and connection management
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/ezrealtor_db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_async_session():
    """Get async database session context manager"""
    return AsyncSessionLocal()

async def create_tables():
    """Create all database tables"""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import (
            agent, domain, lead, usage, provider_credentials, 
            capture_page, notification, plan_catalog
        )
        await conn.run_sync(Base.metadata.create_all)