"""
Facebook OAuth Service for EZRealtor
Handles Facebook authentication and token management
"""

import httpx
import secrets
import hashlib
import hmac
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class FacebookOAuthService:
    def __init__(self):
        import os
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI", "https://ezrealtor.app/api/v1/facebook/callback")
        self.api_version = os.getenv("FACEBOOK_API_VERSION", "v18.0")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.oauth_url = f"https://www.facebook.com/{self.api_version}/dialog/oauth"
        
        if not self.app_id or not self.app_secret:
            raise ValueError("Facebook App ID and Secret must be set in environment variables")
        
    def generate_state(self) -> str:
        """Generate a random state parameter for OAuth"""
        return secrets.token_urlsafe(32)
    
    def generate_authorization_url(self, state: str = None) -> str:
        """Generate Facebook OAuth authorization URL"""
        if not state:
            state = self.generate_state()
            
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "ads_management,business_management,pages_manage_ads,ads_read",
            "response_type": "code",
            "state": state
        }
        
        query_string = urlencode(params)
        return f"{self.oauth_url}?{query_string}"
    
    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = f"{self.base_url}/oauth/access_token"
        
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Facebook"""
        url = f"{self.base_url}/me"
        
        params = {
            "access_token": access_token,
            "fields": "id,name,email"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        try:
            url = f"{self.base_url}/me"
            params = {"access_token": access_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                return response.status_code == 200
        except Exception:
            return False
