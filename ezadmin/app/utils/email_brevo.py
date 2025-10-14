import aiohttp
import asyncio
from typing import Optional
import os
from app.core.config import get_settings

settings = get_settings()

class BrevoEmailService:
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.base_url = "https://api.brevo.com/v3"
    
    async def send_welcome_email(self, to_email: str, first_name: str) -> bool:
        """Send welcome email using Brevo API"""
        try:
            url = f"{self.base_url}/smtp/email"
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": self.api_key
            }
            
            data = {
                "sender": {
                    "name": "EZRealtor.app",
                    "email": "noreply@ezrealtor.app"
                },
                "to": [{"email": to_email, "name": first_name}],
                "subject": "Welcome to EZRealtor.app - Your AI Lead System is Ready!",
                "htmlContent": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #2563eb;">Welcome to EZRealtor.app, {first_name}!</h1>
                    <p>Your AI-powered lead generation system is now active and ready to capture leads.</p>
                    <p><a href="https://ezrealtor.app/dashboard" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Go to Dashboard</a></p>
                </div>
                """
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    return response.status == 201
                    
        except Exception as e:
            print(f"Email send error: {e}")
            return False

# Create singleton instance
brevo_service = BrevoEmailService()