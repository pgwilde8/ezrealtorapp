"""
Slug Generation Utilities
Handles generating unique slugs for agents to avoid conflicts
"""

import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent


async def generate_unique_slug(email: str, db: AsyncSession) -> str:
    """Generate a unique slug from email, handling conflicts"""
    
    # Base slug from email prefix
    email_prefix = email.split('@')[0].lower()
    # Clean the slug: remove special characters, keep only alphanumeric
    base_slug = re.sub(r'[^a-z0-9]', '', email_prefix)[:15]  # Shorter to leave room for suffix
    
    if not base_slug:
        # Fallback if email prefix is all special characters
        base_slug = "user"
    
    # Check if base slug is available
    result = await db.execute(select(Agent).where(Agent.slug == base_slug))
    if not result.scalar_one_or_none():
        return base_slug
    
    # If conflict, try with numeric suffixes
    for i in range(1, 100):
        candidate_slug = f"{base_slug}{i}"
        result = await db.execute(select(Agent).where(Agent.slug == candidate_slug))
        if not result.scalar_one_or_none():
            return candidate_slug
    
    # Ultimate fallback: use part of UUID
    fallback_slug = f"{base_slug}{str(uuid.uuid4())[:8]}"
    return fallback_slug