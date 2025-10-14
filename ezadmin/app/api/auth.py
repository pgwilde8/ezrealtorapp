"""
Authentication API endpoints for realtor login system
Handles login, magic links, password reset, and session management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import jwt
import bcrypt
import secrets
import uuid
import os
from google.oauth2 import id_token
from google.auth.transport import requests
import os

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from app.utils.database import get_db
from app.models.agent import Agent
from app.utils.security import create_access_token, verify_token, hash_password, verify_password

router = APIRouter(tags=["authentication"])
security = HTTPBearer()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI_PROD", "https://login.ezrealtor.app/auth/google/callback")

# For development
if os.getenv("DEBUG", "false").lower() == "true":
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI_DEV", "http://localhost:8011/auth/google/callback")

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: Optional[bool] = False

class MagicLinkRequest(BaseModel):
    email: EmailStr

class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token
    redirect_to: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    agent_id: str
    agent_slug: str
    redirect_url: str

class AuthAgent(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    slug: str
    plan_tier: str

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate agent with email and password"""
    
    # Find agent by email
    result = await db.execute(
        select(Agent).where(Agent.email == login_data.email.lower())
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not agent.password_hash or not verify_password(login_data.password, agent.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Update last login
    agent.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create access token
    token_data = {
        "sub": str(agent.id),
        "email": agent.email,
        "slug": agent.slug,
        "type": "access"
    }
    
    expires_delta = timedelta(days=30) if login_data.remember else timedelta(hours=24)
    access_token = create_access_token(token_data, expires_delta)
    
    # Determine redirect URL
    redirect_url = f"https://{agent.slug}.ezrealtor.app/dashboard"
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        agent_id=str(agent.id),
        agent_slug=agent.slug,
        redirect_url=redirect_url
    )

@router.post("/magic-login")
async def send_magic_link(
    email_data: MagicLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send magic login link to email"""
    
    # Find agent by email
    result = await db.execute(select(Agent).where(Agent.email == email_data.email))
    agent = result.scalar_one_or_none()
    
    if not agent:
        # For security, always return success even if email not found
        return {"message": "If an account exists with that email, a login link has been sent"}
    
    # Create magic token (short-lived, 15 minutes)
    magic_token_data = {
        "sub": str(agent.id),
        "email": agent.email,
        "type": "magic_link"
    }
    magic_token = create_access_token(
        magic_token_data, 
        expires_delta=timedelta(minutes=15)
    )
    
    # Send magic link email
    from app.utils.email_brevo import email_service
    success = await email_service.send_magic_link_email(
        to_email=agent.email,
        to_name=f"{agent.first_name} {agent.last_name}",
        magic_token=magic_token,
        agent_slug=agent.slug
    )
    
    if success:
        return {"message": "If an account exists with that email, a login link has been sent"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")

@router.get("/magic")
async def magic_login(
    request: Request,
    token: str,
    redirect_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle magic link login"""
    
    # Verify magic token
    try:
        payload = verify_token(token)
        if payload.get("type") != "magic_link":
            raise HTTPException(status_code=400, detail="Invalid login link")
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")
    
    # Get agent
    agent_id = payload.get("sub")
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=400, detail="Invalid login link")
    
    # Create session token
    session_token = create_access_token({"sub": str(agent.id)})
    
    # Update last login
    agent.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Redirect to dashboard with session cookie
    if redirect_to:
        redirect_url = f"https://{redirect_to}.ezrealtor.app/dashboard"
    else:
        redirect_url = f"https://{agent.slug}.ezrealtor.app/dashboard"
    
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return response

@router.get("/magic/{token}")
async def magic_login(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle magic link login"""
    
    try:
        # Verify magic link token
        payload = verify_token(token)
        
        if payload.get("type") != "magic_link":
            raise HTTPException(status_code=401, detail="Invalid magic link")
        
        agent_id = payload.get("sub")
        agent_slug = payload.get("slug")
        
        # Find agent
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid magic link")
        
        # Update last login
        agent.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Create new session token
        session_data = {
            "sub": str(agent.id),
            "email": agent.email,
            "slug": agent.slug,
            "type": "access"
        }
        
        session_token = create_access_token(session_data, timedelta(days=7))
        
        # Redirect to dashboard with token
        redirect_url = f"https://{agent.slug}.ezrealtor.app/dashboard?token={session_token}"
        
        return {"redirect_url": redirect_url}
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired magic link")

@router.post("/reset-password")
async def send_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset link"""
    
    # Find agent by email
    result = await db.execute(
        select(Agent).where(Agent.email == reset_data.email.lower())
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        # Don't reveal if email exists or not for security
        return {"message": "If an account exists with this email, you'll receive a password reset link shortly."}
    
    # Create reset token
    token_data = {
        "sub": str(agent.id),
        "email": agent.email,
        "type": "password_reset"
    }
    
    reset_token = create_access_token(token_data, timedelta(hours=1))
    reset_link = f"https://login.ezrealtor.app/auth/reset/{reset_token}"
    
    # Send email
    email_service = EmailService()
    await email_service.send_password_reset_email(
        to_email=agent.email,
        agent_name=f"{agent.first_name} {agent.last_name}",
        reset_link=reset_link
    )
    
    return {"message": "Password reset link sent to your email!"}

@router.get("/verify")
async def verify_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Verify current user token and return user info"""
    
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        if payload.get("type") not in ["access", "magic_link"]:
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        agent_id = payload.get("sub")
        
        # Find agent
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=401, detail="User not found")
        
        return AuthAgent(
            id=str(agent.id),
            email=agent.email,
            first_name=agent.first_name,
            last_name=agent.last_name,
            slug=agent.slug,
            plan_tier=agent.plan_tier
        )
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/logout")
async def logout(response: Response):
    """Logout user (client should remove token)"""
    
    # In a stateless JWT system, logout is handled client-side
    # We could implement a token blacklist if needed
    return {"message": "Logged out successfully"}

# Helper function to get current authenticated agent
async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    """Get the currently authenticated agent"""
    
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        if payload.get("type") not in ["access", "magic_link"]:
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        agent_id = payload.get("sub")
        
        # Find agent
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=401, detail="User not found")
        
        return agent
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Google OAuth Endpoints
@router.get("/google/login")
async def google_login(redirect_to: Optional[str] = None):
    """Initiate Google OAuth login"""
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Create Google OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=["openid", "email", "profile"]
    )
    
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    
    # Add state parameter to track redirect destination
    state = redirect_to if redirect_to else "dashboard"
    
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state
    )
    
    return RedirectResponse(url=authorization_url)

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    try:
        # Create Google OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=["openid", "email", "profile"]
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        
        # Get user info from Google
        credentials = flow.credentials
        user_info_request = GoogleRequest()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            user_info_request,
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        email = id_info.get("email")
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        google_id = id_info.get("sub")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Find or create agent
        result = await db.execute(select(Agent).where(Agent.email == email.lower()))
        agent = result.scalar_one_or_none()
        
        if not agent:
            # For security, don't auto-create accounts via Google OAuth
            # Redirect to registration or show error
            return RedirectResponse(
                url=f"https://login.ezrealtor.app?error=account_not_found&email={email}",
                status_code=302
            )
        
        # Update agent with Google ID if not set
        if not agent.google_id:
            agent.google_id = google_id
        
        # Update last login
        agent.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Create session token
        session_token = create_access_token({"sub": str(agent.id), "type": "access"})
        
        # Determine redirect URL
        if state and state != "dashboard":
            redirect_url = f"https://{state}.ezrealtor.app/dashboard"
        else:
            redirect_url = f"https://{agent.slug}.ezrealtor.app/dashboard"
        
        # Set session cookie and redirect
        response = RedirectResponse(url=redirect_url, status_code=302)
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return RedirectResponse(
            url="https://login.ezrealtor.app?error=oauth_failed",
            status_code=302
        )

@router.post("/google/verify")
async def google_verify_token(
    auth_data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify Google ID token for frontend login"""
    
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    try:
        # Verify the Google ID token
        request_adapter = GoogleRequest()
        id_info = id_token.verify_oauth2_token(
            auth_data.credential,
            request_adapter,
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        email = id_info.get("email")
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        google_id = id_info.get("sub")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Find agent by email
        result = await db.execute(select(Agent).where(Agent.email == email.lower()))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=404,
                detail="Account not found. Please contact support to set up your EZRealtor account."
            )
        
        # Update agent with Google ID if not set
        if not agent.google_id:
            agent.google_id = google_id
        
        # Update last login
        agent.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Create access token
        access_token = create_access_token({"sub": str(agent.id), "type": "access"})
        
        # Determine redirect URL
        if auth_data.redirect_to:
            redirect_url = f"https://{auth_data.redirect_to}.ezrealtor.app/dashboard"
        else:
            redirect_url = f"https://{agent.slug}.ezrealtor.app/dashboard"
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            agent_id=str(agent.id),
            agent_slug=agent.slug,
            redirect_url=redirect_url
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except Exception as e:
        print(f"Google token verification error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

# Optional auth (for routes that work with or without auth)
async def get_current_agent_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[Agent]:
    """Get current agent if authenticated, None otherwise"""
    
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        
        if payload.get("type") not in ["access", "magic_link"]:
            return None
        
        agent_id = payload.get("sub")
        
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        return agent
        
    except:
        return None