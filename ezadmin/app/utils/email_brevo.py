import aiohttp
import asyncio
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class BrevoEmailService:
    def __init__(self):
        self.api_key = os.getenv("BREVO_API_KEY")
        self.base_url = "https://api.brevo.com/v3"
        
        if not self.api_key:
            logger.warning("BREVO_API_KEY not configured - email sending will fail")
    
    async def send_welcome_email(self, to_email: str, to_name: str = None, plan_tier: str = None, temp_password: str = None) -> bool:
        """Send welcome email using Brevo API
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name (optional)
            plan_tier: Plan tier for personalized messaging (optional)
            temp_password: Temporary password for new users (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("Cannot send email - BREVO_API_KEY not configured")
                return False
            
            url = f"{self.base_url}/smtp/email"
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": self.api_key
            }
            
            # Use name if provided, otherwise use email
            recipient_name = to_name or to_email.split('@')[0]
            
            # Customize message based on plan tier
            plan_message = ""
            if plan_tier:
                plan_message = f"<p>You're on the <strong>{plan_tier.upper()}</strong> plan.</p>"
            
            # Add login credentials section if temp password provided
            login_section = ""
            if temp_password:
                login_section = f"""
                <div style="background: #f3f4f6; border-left: 4px solid #2563eb; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1f2937;">Your Login Credentials:</h3>
                    <p style="margin: 10px 0;"><strong>Email:</strong> {to_email}</p>
                    <p style="margin: 10px 0;"><strong>Password:</strong> <code style="background: white; padding: 4px 8px; border-radius: 4px; font-family: monospace; color: #dc2626;">{temp_password}</code></p>
                    <p style="margin: 10px 0; font-size: 14px; color: #6b7280;">⚠️ Please change this password after your first login for security.</p>
                </div>
                """
            
            data = {
                "sender": {
                    "name": "EZRealtor.app",
                    "email": "noreply@ezrealtor.app"
                },
                "to": [{"email": to_email, "name": recipient_name}],
                "subject": "Welcome to EZRealtor.app - Your AI Lead System is Ready!",
                "htmlContent": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2563eb;">Welcome to EZRealtor.app, {recipient_name}!</h1>
                    <p style="font-size: 16px; line-height: 1.6;">Your AI-powered lead generation system is now active and ready to capture leads.</p>
                    {plan_message}
                    {login_section}
                    <p style="font-size: 16px; line-height: 1.6;">Get started by logging into your dashboard:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="https://login.ezrealtor.app" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Go to Dashboard</a>
                    </p>
                    <p style="font-size: 14px; color: #666; margin-top: 30px;">
                        Need help? Reply to this email or visit our support center.
                    </p>
                </div>
                """
            }
            
            logger.info(f"Sending welcome email to {to_email}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 201:
                        logger.info(f"Welcome email successfully sent to {to_email}")
                        return True
                    else:
                        logger.error(f"Failed to send email to {to_email}. Status: {response.status}, Response: {response_text}")
                        return False
                    
        except Exception as e:
            logger.error(f"Email send error for {to_email}: {e}", exc_info=True)
            return False
    
    async def send_magic_link_email(self, to_email: str, to_name: str, magic_token: str, agent_slug: str) -> bool:
        """Send magic login link email
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            magic_token: Magic link token for authentication
            agent_slug: Agent's subdomain slug
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("Cannot send email - BREVO_API_KEY not configured")
                return False
            
            url = f"{self.base_url}/smtp/email"
            magic_link = f"https://login.ezrealtor.app/auth/magic?token={magic_token}"
            
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
                "to": [{"email": to_email, "name": to_name}],
                "subject": "Your EZRealtor.app Login Link",
                "htmlContent": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2563eb;">Login to EZRealtor.app</h1>
                    <p style="font-size: 16px; line-height: 1.6;">Hi {to_name},</p>
                    <p style="font-size: 16px; line-height: 1.6;">Click the button below to securely log in to your account:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{magic_link}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Login to Dashboard</a>
                    </p>
                    <p style="font-size: 14px; color: #666;">
                        This link will expire in 15 minutes for your security.
                    </p>
                    <p style="font-size: 14px; color: #666; margin-top: 30px;">
                        If you didn't request this login link, you can safely ignore this email.
                    </p>
                </div>
                """
            }
            
            logger.info(f"Sending magic link email to {to_email}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 201:
                        logger.info(f"Magic link email successfully sent to {to_email}")
                        return True
                    else:
                        logger.error(f"Failed to send magic link to {to_email}. Status: {response.status}, Response: {response_text}")
                        return False
                    
        except Exception as e:
            logger.error(f"Magic link email error for {to_email}: {e}", exc_info=True)
            return False
    
    async def send_password_reset_email(self, to_email: str, agent_name: str, reset_link: str) -> bool:
        """Send password reset email
        
        Args:
            to_email: Recipient email address
            agent_name: Agent's full name
            reset_link: Password reset link
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("Cannot send email - BREVO_API_KEY not configured")
                return False
            
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
                "to": [{"email": to_email, "name": agent_name}],
                "subject": "Reset Your EZRealtor.app Password",
                "htmlContent": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2563eb;">Reset Your Password</h1>
                    <p style="font-size: 16px; line-height: 1.6;">Hi {agent_name},</p>
                    <p style="font-size: 16px; line-height: 1.6;">We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
                    </p>
                    <p style="font-size: 14px; color: #666;">
                        This link will expire in 1 hour for your security.
                    </p>
                    <p style="font-size: 14px; color: #666; margin-top: 30px;">
                        If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
                    </p>
                </div>
                """
            }
            
            logger.info(f"Sending password reset email to {to_email}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 201:
                        logger.info(f"Password reset email successfully sent to {to_email}")
                        return True
                    else:
                        logger.error(f"Failed to send password reset to {to_email}. Status: {response.status}, Response: {response_text}")
                        return False
                    
        except Exception as e:
            logger.error(f"Password reset email error for {to_email}: {e}", exc_info=True)
            return False

# Create singleton instance
email_service = BrevoEmailService()

# Also export as brevo_service for backwards compatibility
brevo_service = email_service