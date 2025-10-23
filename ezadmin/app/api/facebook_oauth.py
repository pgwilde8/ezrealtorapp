"""
Facebook OAuth API Endpoints
Handles Facebook authentication flow for agents
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import Dict, Any
import logging

from app.utils.database import get_db
from app.models.agent import Agent
from app.services.facebook_oauth import FacebookOAuthService
from app.middleware.auth import get_current_agent

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/connect")
async def start_facebook_connection(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Start Facebook OAuth flow
    Returns authorization URL for agent to visit
    """
    try:
        # Generate authorization URL
        state = FacebookOAuthService().generate_state()
        auth_url = FacebookOAuthService().generate_authorization_url(state)
        
        return {
            "success": True,
            "authorization_url": auth_url,
            "state": state,
            "message": "Redirect user to authorization URL"
        }
        
    except Exception as e:
        logger.error(f"Error starting Facebook connection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start Facebook connection: {str(e)}")

@router.get("/status")
async def get_facebook_status(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Facebook connection status for current agent
    """
    try:
        return {
            "connected": agent.facebook_connected or False,
            "business_id": agent.facebook_business_id,
            "business_name": agent.facebook_business_name,
            "ad_account_id": agent.facebook_ad_account_id,
            "ad_account_name": agent.facebook_ad_account_name,
            "page_id": agent.facebook_page_id,
            "page_name": agent.facebook_page_name,
            "token_expires_at": agent.facebook_token_expires_at
        }
        
    except Exception as e:
        logger.error(f"Error getting Facebook status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Facebook status: {str(e)}")
