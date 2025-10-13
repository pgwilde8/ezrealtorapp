"""
Tenant resolution middleware
Handles multi-tenant routing based on Host header
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
from typing import Optional

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to resolve tenant from subdomain or custom domain
    Sets request.state.tenant_slug and request.state.agent_id
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get host from request
        host = request.headers.get("host", "").lower()
        
        # Initialize tenant info
        request.state.tenant_slug = None
        request.state.agent_id = None
        request.state.is_custom_domain = False
        
        # Skip tenant resolution for admin and API docs
        path = request.url.path
        if path.startswith("/admin") or path.startswith("/api/docs") or path.startswith("/health"):
            response = await call_next(request)
            return response
        
        # Extract tenant from subdomain (e.g., john.ezrealtor.app)
        base_domain = "ezrealtor.app"
        if host.endswith(f".{base_domain}"):
            subdomain = host.replace(f".{base_domain}", "")
            if subdomain and subdomain != "app" and subdomain != "www":
                request.state.tenant_slug = subdomain
                # TODO: Look up agent_id from database using tenant_slug
        
        # Check for custom domain
        elif not host.startswith("localhost") and not host.startswith("127.0.0.1"):
            # This is a custom domain
            request.state.is_custom_domain = True
            # TODO: Look up tenant by custom domain in database
        
        response = await call_next(request)
        return response

async def get_current_tenant(request: Request) -> Optional[str]:
    """Get current tenant slug from request state"""
    return getattr(request.state, "tenant_slug", None)

async def get_current_agent_id(request: Request) -> Optional[int]:
    """Get current agent ID from request state"""
    return getattr(request.state, "agent_id", None)

async def require_tenant(request: Request) -> str:
    """Require a valid tenant, raise 404 if not found"""
    tenant_slug = await get_current_tenant(request)
    if not tenant_slug:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_slug