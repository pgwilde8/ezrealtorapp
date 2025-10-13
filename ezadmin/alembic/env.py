"""
Alembic configuration for EZRealtor.app database migrations
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import your models Base
from app.utils.database import Base
# Import all models to ensure they're registered with Base metadata
from app.models import agent, domain, lead, usage, provider_credentials, capture_page, notification, plan_catalog

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

def get_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/ezrealtor_db")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    """Run migrations in async mode"""
    connectable = create_async_engine(get_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    import asyncio
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()