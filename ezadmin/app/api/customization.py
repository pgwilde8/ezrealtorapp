"""
Agent Customization API endpoints
Handles branding and page customization
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl
from typing import Optional
import os
import uuid
import shutil

from app.utils.database import get_db
from app.models.agent import Agent
from app.middleware.tenant_resolver import get_current_agent_id

router = APIRouter()

class AgentCustomizationUpdate(BaseModel):
    # Brand Colors
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None  
    brand_accent_color: Optional[str] = None
    
    # Page Headlines
    buyer_page_headline: Optional[str] = None
    buyer_page_subtitle: Optional[str] = None
    valuation_page_headline: Optional[str] = None
    valuation_page_subtitle: Optional[str] = None
    
    # Agent Info
    title: Optional[str] = None
    license_number: Optional[str] = None
    brokerage_name: Optional[str] = None
    
    # Contact & Social
    website_url: Optional[HttpUrl] = None
    facebook_url: Optional[HttpUrl] = None
    instagram_url: Optional[HttpUrl] = None
    linkedin_url: Optional[HttpUrl] = None
    
    # Custom Messages
    submit_button_text: Optional[str] = None
    success_message: Optional[str] = None

class AgentCustomizationResponse(BaseModel):
    # Brand Colors
    brand_primary_color: Optional[str]
    brand_secondary_color: Optional[str]  
    brand_accent_color: Optional[str]
    
    # URLs
    logo_url: Optional[str]
    headshot_url: Optional[str]
    
    # Page Headlines
    buyer_page_headline: Optional[str]
    buyer_page_subtitle: Optional[str]
    valuation_page_headline: Optional[str]
    valuation_page_subtitle: Optional[str]
    
    # Agent Info
    title: Optional[str]
    license_number: Optional[str]
    brokerage_name: Optional[str]
    
    # Contact & Social
    website_url: Optional[str]
    facebook_url: Optional[str]
    instagram_url: Optional[str]
    linkedin_url: Optional[str]
    
    # Custom Messages
    submit_button_text: Optional[str]
    success_message: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/customization", response_model=AgentCustomizationResponse)
async def get_agent_customization(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get agent's current customization settings"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@router.put("/customization", response_model=AgentCustomizationResponse)
async def update_agent_customization(
    customization: AgentCustomizationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update agent's customization settings"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    update_data = customization.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(agent, field):
            setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return agent

@router.post("/upload-logo")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload agent logo"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"logo_{agent_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    
    # Create uploads directory if it doesn't exist
    upload_dir = "app/static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update agent record
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if agent:
        agent.logo_url = f"/static/uploads/{unique_filename}"
        await db.commit()
    
    return {
        "success": True,
        "logo_url": f"/static/uploads/{unique_filename}",
        "message": "Logo uploaded successfully"
    }

@router.post("/upload-headshot")
async def upload_headshot(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload agent headshot"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"headshot_{agent_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    
    # Create uploads directory if it doesn't exist
    upload_dir = "app/static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update agent record
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if agent:
        agent.headshot_url = f"/static/uploads/{unique_filename}"
        await db.commit()
    
    return {
        "success": True,
        "headshot_url": f"/static/uploads/{unique_filename}",
        "message": "Headshot uploaded successfully"
    }

@router.get("/preview/{page_type}")
async def preview_customization(
    page_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Preview customized page"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Return preview URL
    if page_type == "buyer":
        preview_url = f"/{agent.slug}/lead-buyer"
    elif page_type == "valuation":
        preview_url = f"/{agent.slug}/lead-home-value"
    else:
        raise HTTPException(status_code=400, detail="Invalid page type")
    
    return {
        "preview_url": preview_url,
        "agent": agent
    }