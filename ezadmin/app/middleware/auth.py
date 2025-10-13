"""
Authentication middleware for session management
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta
import os

from app.models.agent import Agent
from app.utils.database import get_db
from app.utils.security import create_access_token, verify_token

security = HTTPBearer(auto_error=False)

async def get_current_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Agent]:
    """Get current authenticated agent from JWT token"""
    
    # Try to get token from Authorization header
    if token:
        try:
            payload = verify_token(token.credentials)
            agent_id = payload.get("sub")
            if agent_id:
                result = await db.execute(select(Agent).where(Agent.id == agent_id))
                return result.scalar_one_or_none()
        except HTTPException:
            pass  # Invalid token, continue to next method
    
    # Try to get token from session cookie
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            payload = verify_token(session_token)
            agent_id = payload.get("sub")
            if agent_id:
                result = await db.execute(select(Agent).where(Agent.id == agent_id))
                return result.scalar_one_or_none()
        except HTTPException:
            pass  # Invalid token
    
    return None

async def require_auth(agent: Agent = Depends(get_current_agent)) -> Agent:
    """Require authentication, raise 401 if not authenticated"""
    if not agent:
        raise HTTPException(status_code=401, detail="Authentication required")
    return agent

def is_login_subdomain(host: str) -> bool:
    """Check if the request is for the login subdomain"""
    if not host:
        return False
    
    # Handle different environments
    if host.startswith("login."):
        return True
    
    # For development/localhost
    if host in ["login.localhost", "login.localhost:8011"]:
        return True
        
    return False

def get_agent_slug_from_host(host: str) -> Optional[str]:
    """Extract agent slug from subdomain"""
    if not host or "." not in host:
        return None
    
    subdomain = host.split(".")[0]
    
    # Skip special subdomains
    if subdomain in ["login", "www", "admin", "api"]:
        return None
        
    return subdomain