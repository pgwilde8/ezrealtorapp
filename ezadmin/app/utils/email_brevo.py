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
    
    def send_welcome_email(self, to_email: str, to_name: str, plan_tier: str) -> bool:
        """Send welcome email with login instructions"""
        
        if not self.api_key:
            logger.warning(f"Cannot send email to {to_email} - Brevo API key not configured")
            return False
        
        # Create login URL - we'll build this out next
        login_url = f"https://login.ezrealtor.app?email={to_email}&welcome=true"
        
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

# Global instance
email_service = BrevoEmailService()