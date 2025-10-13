"""
Email service using Brevo (Sendinblue) API
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class BrevoEmailService:
    def __init__(self):
        self.api_key = os.getenv("BREVO_API_KEY")
        self.from_email = os.getenv("EMAIL_FROM_ADDRESS", "noreply@ezrealtor.app")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "EZRealtor.app")
        self.base_url = "https://api.brevo.com/v3"
        
        if not self.api_key:
            logger.warning("BREVO_API_KEY not configured - emails will not be sent")
    
    async def send_welcome_email(self, to_email: str, to_name: str, plan_tier: str = "trial", agent_slug: str = None):
        """Send welcome email to new customer"""
        # Create login URL with redirect to their dashboard
        if agent_slug:
            login_url = f"https://login.ezrealtor.app?redirect_to={agent_slug}"
        else:
            login_url = "https://login.ezrealtor.app"
        
        # Plan-specific content
        plan_benefits = {
            "trial": [
                "Up to 10 leads per month",
                "Basic AI lead scoring",
                "Email notifications",
                "Subdomain (you.ezrealtor.app)"
            ],
            "pro": [
                "Unlimited leads",
                "Advanced AI lead scoring", 
                "SMS & Email notifications",
                "Custom domain support",
                "CRM integrations"
            ],
            "enterprise": [
                "Everything in Pro",
                "Phone callbacks",
                "Multiple domains",
                "White-label options",
                "Priority support"
            ]
        }
        
        benefits = plan_benefits.get(plan_tier, plan_benefits["trial"])
        benefits_html = "".join([f"<li>{benefit}</li>" for benefit in benefits])
        
        subject = f"Welcome to EZRealtor.app - Your {plan_tier.title()} Account is Ready!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .benefits {{ background: white; padding: 20px; border-radius: 6px; margin: 20px 0; }}
                .benefits ul {{ margin: 0; padding-left: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to EZRealtor.app! 🎉</h1>
                    <p>Your AI-powered lead generation platform is ready</p>
                </div>
                
                <div class="content">
                    <h2>Hi {to_name}!</h2>
                    
                    <p>Thank you for choosing EZRealtor.app! Your <strong>{plan_tier.title()} plan</strong> is now active and ready to start capturing leads for your real estate business.</p>
                    
                    <div style="text-align: center;">
                        <a href="{login_url}" class="button">Access Your Dashboard</a>
                    </div>
                    
                    <div class="benefits">
                        <h3>Your {plan_tier.title()} Plan Includes:</h3>
                        <ul>
                            {benefits_html}
                        </ul>
                    </div>
                    
                    <h3>What's Next?</h3>
                    <ol>
                        <li><strong>Click the button above</strong> to access your dashboard</li>
                        <li><strong>Customize your lead pages</strong> with your branding</li>
                        <li><strong>Share your unique URLs</strong> to start capturing leads</li>
                        <li><strong>Watch AI analyze</strong> and score your incoming leads</li>
                    </ol>
                    
                    <p>Need help getting started? Our support team is here to help at <a href="mailto:support@ezrealtor.app">support@ezrealtor.app</a></p>
                    
                    <p>Welcome to the future of real estate lead generation!</p>
                    
                    <p>Best regards,<br>
                    The EZRealtor.app Team</p>
                </div>
                
                <div class="footer">
                    <p>EZRealtor.app - AI-Powered Lead Engine for Realtors</p>
                    <p>If you have any questions, reply to this email or contact us at support@ezrealtor.app</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Welcome to EZRealtor.app!
        
        Hi {to_name},
        
        Thank you for choosing EZRealtor.app! Your {plan_tier.title()} plan is now active.
        
        Access your dashboard: {login_url}
        
        Your {plan_tier.title()} plan includes:
        {chr(10).join([f"- {benefit}" for benefit in benefits])}
        
        What's next?
        1. Click the link above to access your dashboard
        2. Customize your lead pages with your branding  
        3. Share your unique URLs to start capturing leads
        4. Watch AI analyze and score your incoming leads
        
        Need help? Contact us at support@ezrealtor.app
        
        Welcome to the future of real estate lead generation!
        
        Best regards,
        The EZRealtor.app Team
        """
        
        return self._send_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    def _send_email(self, to_email: str, to_name: str, subject: str, 
                   html_content: str, text_content: str) -> bool:
        """Send email via Brevo API"""
        
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": self.from_name,
                "email": self.from_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": to_name
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/smtp/email",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Welcome email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    def send_magic_link_email(self, to_email: str, agent_name: str, magic_link: str) -> bool:
        """Send magic link for passwordless login"""
        
        if not self.api_key:
            logger.warning(f"Cannot send magic link to {to_email} - Brevo API key not configured")
            return False
        
        subject = "🔐 Your EZRealtor.app Login Link"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2563eb;">🏠 EZRealtor.app</h1>
                </div>
                
                <h2>Hi {agent_name}!</h2>
                
                <p>Click the button below to securely sign in to your realtor dashboard:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{magic_link}" 
                       style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: bold;
                              display: inline-block;">
                        🔓 Sign In to Dashboard
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    This link will expire in 15 minutes for security reasons.
                </p>
                
                <p style="color: #666; font-size: 14px;">
                    If you didn't request this login link, please ignore this email.
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                
                <p style="color: #888; font-size: 12px; text-align: center;">
                    © 2025 EZRealtor.app - AI-Powered Lead Generation for Realtors
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {agent_name}!

        Click the link below to securely sign in to your realtor dashboard:
        
        {magic_link}
        
        This link will expire in 15 minutes for security reasons.
        
        If you didn't request this login link, please ignore this email.
        
        © 2025 EZRealtor.app - AI-Powered Lead Generation for Realtors
        """
        
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": self.from_name,
                "email": self.from_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": agent_name
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/smtp/email",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Magic link email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send magic link to {to_email}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending magic link to {to_email}: {e}")
            return False

    def send_password_reset_email(self, to_email: str, agent_name: str, reset_link: str) -> bool:
        """Send password reset link"""
        
        if not self.api_key:
            logger.warning(f"Cannot send reset link to {to_email} - Brevo API key not configured")
            return False
        
        subject = "🔑 Reset Your EZRealtor.app Password"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2563eb;">🏠 EZRealtor.app</h1>
                </div>
                
                <h2>Hi {agent_name}!</h2>
                
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: bold;
                              display: inline-block;">
                        🔑 Reset Password
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    This link will expire in 1 hour for security reasons.
                </p>
                
                <p style="color: #666; font-size: 14px;">
                    If you didn't request a password reset, please ignore this email. Your password won't be changed.
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                
                <p style="color: #888; font-size: 12px; text-align: center;">
                    © 2025 EZRealtor.app - AI-Powered Lead Generation for Realtors
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {agent_name}!

        We received a request to reset your password. Click the link below to create a new password:
        
        {reset_link}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, please ignore this email. Your password won't be changed.
        
        © 2025 EZRealtor.app - AI-Powered Lead Generation for Realtors
        """
        
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": self.from_name,
                "email": self.from_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": agent_name
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/smtp/email",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Password reset email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send reset email to {to_email}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reset email to {to_email}: {e}")
            return False

    async def send_magic_link_email(self, to_email: str, to_name: str, magic_token: str, agent_slug: str = None):
        """Send magic login link email"""
        try:
            # Create magic link URL
            if agent_slug:
                magic_url = f"https://login.ezrealtor.app/magic?token={magic_token}&redirect_to={agent_slug}"
            else:
                magic_url = f"https://login.ezrealtor.app/magic?token={magic_token}"
            
            subject = "Your EZRealtor.app Login Link"
            
            # HTML version
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #2c5aa0, #1e3a72); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; }}
                    .button {{ display: inline-block; background: #2c5aa0; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                    .footer {{ background: #e9ecef; padding: 20px; text-align: center; font-size: 14px; color: #666; border-radius: 0 0 10px 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏠 EZRealtor.app</h1>
                        <p>Your secure login link is ready</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hi {to_name}!</h2>
                        
                        <p>Click the button below to securely log in to your EZRealtor.app dashboard:</p>
                        
                        <div style="text-align: center;">
                            <a href="{magic_url}" class="button">🔐 Login to Dashboard</a>
                        </div>
                        
                        <p><strong>This link expires in 15 minutes</strong> for your security.</p>
                        
                        <p>If you didn't request this login link, you can safely ignore this email.</p>
                        
                        <p>Need help? Contact us at <a href="mailto:support@ezrealtor.app">support@ezrealtor.app</a></p>
                    </div>
                    
                    <div class="footer">
                        <p>EZRealtor.app - AI-Powered Lead Engine for Realtors</p>
                        <p>This login link expires in 15 minutes for your security</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            EZRealtor.app - Your Login Link
            
            Hi {to_name}!
            
            Click the link below to securely log in to your dashboard:
            {magic_url}
            
            This link expires in 15 minutes for your security.
            
            If you didn't request this login link, you can safely ignore this email.
            
            Need help? Contact us at support@ezrealtor.app
            
            EZRealtor.app - AI-Powered Lead Engine for Realtors
            """
            
            headers = {
                "accept": "application/json",
                "api-key": self.api_key,
                "content-type": "application/json"
            }
            
            data = {
                "sender": {"name": "EZRealtor.app", "email": "login@ezrealtor.app"},
                "to": [{"email": to_email, "name": to_name}],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text_content
            }
            
            response = await self.session.post(
                f"{self.base_url}/smtp/email",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Magic link email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send magic link to {to_email}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending magic link to {to_email}: {e}")
            return False

# Global instance
email_service = BrevoEmailService()

# Alias for compatibility with auth API
send_email = email_service.send_notification_email
EmailService = BrevoEmailService