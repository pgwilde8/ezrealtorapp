"""
Domains API endpoints
Handles subdomain and custom domain management via Cloudflare
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.utils.database import get_db
from app.models.domain import AgentDomain, VerificationStatus
from app.models.agent import Agent
from app.middleware.tenant_resolver import get_current_agent_id

router = APIRouter()

# Pydantic models
class CustomDomainRequest(BaseModel):
    domain: str

class DomainResponse(BaseModel):
    id: str  # UUID as string
    hostname: str
    verification_status: str
    is_primary: bool
    cf_custom_hostname_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[DomainResponse])
async def list_domains(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """List all domains for current agent"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(AgentDomain)
        .where(AgentDomain.agent_id == agent_id)
        .order_by(AgentDomain.created_at)
    )
    domains = result.scalars().all()
    
    return domains

@router.post("/provision-subdomain", response_model=dict)
async def provision_subdomain(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Provision default subdomain for agent (called during signup)"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # Get agent to find their slug
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    subdomain = f"{agent.slug}.ezrealtor.app"
    
    # Check if subdomain already exists
    result = await db.execute(
        select(AgentDomain).where(
            and_(
                AgentDomain.agent_id == agent_id,
                AgentDomain.hostname == subdomain
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subdomain already exists")
    
    # Create domain record
    domain = AgentDomain(
        agent_id=agent_id,
        hostname=subdomain,
        verification_status=VerificationStatus.PENDING.value
    )
    
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    
    # Queue Cloudflare provisioning
    background_tasks.add_task(provision_cloudflare_hostname, domain.id)
    
    return {
        "success": True,
        "domain": subdomain,
        "message": "Subdomain provisioning started"
    }

@router.post("/provision-custom", response_model=dict)
async def provision_custom_domain(
    domain_request: CustomDomainRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Provision custom domain for agent"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    domain_name = domain_request.domain.lower().strip()
    
    # Basic domain validation
    if not domain_name or "." not in domain_name:
        raise HTTPException(status_code=400, detail="Invalid domain name")
    
    # Check if domain already exists
    result = await db.execute(
        select(AgentDomain).where(AgentDomain.hostname == domain_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain already registered")
    
    # Create domain record
    domain = AgentDomain(
        agent_id=agent_id,
        hostname=domain_name,
        verification_status=VerificationStatus.PENDING.value,
        is_primary=False
    )
    
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    
    # Queue Cloudflare provisioning
    background_tasks.add_task(provision_cloudflare_hostname, domain.id)
    
    return {
        "success": True,
        "domain": domain_name,
        "message": "Custom domain provisioning started"
    }

@router.get("/{domain_id}/status", response_model=DomainResponse)
async def get_domain_status(
    domain_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get status of domain provisioning"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(AgentDomain).where(
            and_(
                AgentDomain.id == domain_id,
                AgentDomain.agent_id == agent_id
            )
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    return domain

@router.post("/{domain_id}/verify")
async def verify_domain(
    domain_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger domain verification"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(AgentDomain).where(
            and_(
                AgentDomain.id == domain_id,
                AgentDomain.agent_id == agent_id
            )
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Queue verification check
    background_tasks.add_task(verify_cloudflare_hostname, domain.id)
    
    return {
        "success": True,
        "message": "Domain verification started"
    }

@router.delete("/{domain_id}")
async def delete_domain(
    domain_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Delete a custom domain (subdomains cannot be deleted)"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(AgentDomain).where(
            and_(
                AgentDomain.id == domain_id,
                AgentDomain.agent_id == agent_id
            )
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    if domain.hostname.endswith('.ezrealtor.app'):
        raise HTTPException(status_code=400, detail="Cannot delete subdomain")
    
    # Queue Cloudflare cleanup
    if domain.cf_custom_hostname_id:
        background_tasks.add_task(delete_cloudflare_hostname, domain.cf_custom_hostname_id)
    
    # Delete from database
    await db.delete(domain)
    await db.commit()
    
    return {
        "success": True,
        "message": "Domain deleted successfully"
    }

async def provision_cloudflare_hostname(domain_id: int):
    """Background task to provision hostname via Cloudflare for SaaS"""
    # TODO: Implement Cloudflare for SaaS hostname creation
    # 1. Create hostname via CF API
    # 2. Update domain record with CF hostname ID and CNAME target
    # 3. Generate verification TXT record if needed
    pass

async def verify_cloudflare_hostname(domain_id: int):
    """Background task to check hostname verification status"""
    # TODO: Implement Cloudflare hostname verification check
    # 1. Query CF API for hostname status
    # 2. Update domain record with current status
    # 3. Mark as active if SSL is ready
    pass

async def delete_cloudflare_hostname(cf_hostname_id: str):
    """Background task to delete hostname from Cloudflare"""
    # TODO: Implement Cloudflare hostname deletion
    pass