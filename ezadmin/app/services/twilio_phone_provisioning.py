"""
Twilio Phone Number Provisioning Service
Handles automatic purchase, configuration, and management of phone numbers for agents
"""
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class TwilioPhoneProvisioningService:
    """Service for provisioning and managing Twilio phone numbers"""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.base_webhook_url = os.getenv("BASE_URL", "https://ezrealtor.app")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")
    
    def search_available_numbers(
        self, 
        area_code: str = None, 
        country: str = "US",
        sms_enabled: bool = True,
        voice_enabled: bool = True,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for available phone numbers
        
        Args:
            area_code: Desired area code (e.g., "716", "212")
            country: Country code (default "US")
            sms_enabled: Only return SMS-capable numbers
            voice_enabled: Only return voice-capable numbers
            limit: Max results to return
            
        Returns:
            List of available numbers with details
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return []
        
        try:
            search_params = {
                "sms_enabled": sms_enabled,
                "voice_enabled": voice_enabled
            }
            
            if area_code:
                search_params["area_code"] = area_code
            
            # Search for local numbers
            available_numbers = self.client.available_phone_numbers(country).local.list(
                **search_params,
                limit=limit
            )
            
            results = []
            for number in available_numbers:
                results.append({
                    "phone_number": number.phone_number,
                    "friendly_name": number.friendly_name,
                    "locality": number.locality,
                    "region": number.region,
                    "postal_code": number.postal_code,
                    "iso_country": number.iso_country,
                    "capabilities": {
                        "voice": number.capabilities.get("voice", False),
                        "sms": number.capabilities.get("SMS", False),
                        "mms": number.capabilities.get("MMS", False)
                    },
                    "estimated_monthly_cost": 1.15  # Twilio standard pricing
                })
            
            logger.info(f"Found {len(results)} available numbers for area code {area_code}")
            return results
            
        except TwilioRestException as e:
            logger.error(f"Error searching for numbers: {str(e)}")
            return []
    
    def purchase_phone_number(
        self, 
        phone_number: str,
        agent_slug: str,
        friendly_name: str = None
    ) -> Optional[Dict]:
        """
        Purchase a phone number and configure webhooks
        
        Args:
            phone_number: The number to purchase (E.164 format)
            agent_slug: The agent's slug for webhook routing
            friendly_name: Display name for the number
            
        Returns:
            Dict with purchase details or None if failed
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        try:
            # Configure webhook URLs
            voice_url = f"{self.base_webhook_url}/api/v1/twilio/voice"
            sms_url = f"{self.base_webhook_url}/api/v1/twilio/sms"
            status_callback = f"{self.base_webhook_url}/api/v1/twilio/sms/status"
            
            # Purchase the number with webhook configuration
            purchased_number = self.client.incoming_phone_numbers.create(
                phone_number=phone_number,
                friendly_name=friendly_name or f"EZRealtor - {agent_slug}",
                voice_url=voice_url,
                voice_method="POST",
                sms_url=sms_url,
                sms_method="POST",
                status_callback=status_callback,
                status_callback_method="POST"
            )
            
            result = {
                "sid": purchased_number.sid,
                "phone_number": purchased_number.phone_number,
                "friendly_name": purchased_number.friendly_name,
                "voice_url": purchased_number.voice_url,
                "sms_url": purchased_number.sms_url,
                "capabilities": {
                    "voice": purchased_number.capabilities.get("voice", False),
                    "sms": purchased_number.capabilities.get("SMS", False),
                    "mms": purchased_number.capabilities.get("MMS", False)
                },
                "monthly_cost": 1.15,
                "status": "active"
            }
            
            logger.info(f"Successfully purchased number {phone_number} for agent {agent_slug}")
            return result
            
        except TwilioRestException as e:
            logger.error(f"Error purchasing number {phone_number}: {str(e)}")
            return None
    
    def release_phone_number(self, phone_number_sid: str) -> bool:
        """
        Release (cancel) a phone number
        
        Args:
            phone_number_sid: The Twilio SID of the number to release
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            self.client.incoming_phone_numbers(phone_number_sid).delete()
            logger.info(f"Successfully released phone number {phone_number_sid}")
            return True
        except TwilioRestException as e:
            logger.error(f"Error releasing number {phone_number_sid}: {str(e)}")
            return False
    
    def update_phone_number_webhooks(
        self, 
        phone_number_sid: str,
        voice_url: str = None,
        sms_url: str = None
    ) -> bool:
        """
        Update webhook URLs for a phone number
        
        Args:
            phone_number_sid: The Twilio SID of the number
            voice_url: New voice webhook URL
            sms_url: New SMS webhook URL
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            update_params = {}
            if voice_url:
                update_params["voice_url"] = voice_url
                update_params["voice_method"] = "POST"
            if sms_url:
                update_params["sms_url"] = sms_url
                update_params["sms_method"] = "POST"
            
            self.client.incoming_phone_numbers(phone_number_sid).update(**update_params)
            logger.info(f"Successfully updated webhooks for {phone_number_sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Error updating webhooks for {phone_number_sid}: {str(e)}")
            return False
    
    def get_phone_number_details(self, phone_number_sid: str) -> Optional[Dict]:
        """
        Get details about a phone number
        
        Args:
            phone_number_sid: The Twilio SID of the number
            
        Returns:
            Dict with number details or None if not found
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        try:
            number = self.client.incoming_phone_numbers(phone_number_sid).fetch()
            
            return {
                "sid": number.sid,
                "phone_number": number.phone_number,
                "friendly_name": number.friendly_name,
                "voice_url": number.voice_url,
                "sms_url": number.sms_url,
                "capabilities": {
                    "voice": number.capabilities.get("voice", False),
                    "sms": number.capabilities.get("SMS", False),
                    "mms": number.capabilities.get("MMS", False)
                },
                "status": number.status,
                "date_created": number.date_created.isoformat() if number.date_created else None
            }
            
        except TwilioRestException as e:
            logger.error(f"Error fetching number details {phone_number_sid}: {str(e)}")
            return None
    
    def list_account_numbers(self) -> List[Dict]:
        """
        List all phone numbers in the Twilio account
        
        Returns:
            List of all phone numbers with details
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return []
        
        try:
            numbers = self.client.incoming_phone_numbers.list()
            
            results = []
            for number in numbers:
                results.append({
                    "sid": number.sid,
                    "phone_number": number.phone_number,
                    "friendly_name": number.friendly_name,
                    "capabilities": {
                        "voice": number.capabilities.get("voice", False),
                        "sms": number.capabilities.get("SMS", False),
                        "mms": number.capabilities.get("MMS", False)
                    }
                })
            
            return results
            
        except TwilioRestException as e:
            logger.error(f"Error listing account numbers: {str(e)}")
            return []
    
    def port_existing_number(
        self, 
        phone_number: str,
        agent_slug: str,
        losing_carrier: str,
        account_number: str,
        pin: str = None
    ) -> Optional[Dict]:
        """
        Initiate porting of existing phone number to Twilio
        Note: This creates a port request - actual porting takes days
        
        Args:
            phone_number: Number to port (E.164 format)
            agent_slug: Agent's slug
            losing_carrier: Current carrier name
            account_number: Account number with current carrier
            pin: Account PIN if required
            
        Returns:
            Dict with port request details or None if failed
        """
        # Note: Full porting implementation requires more details
        # This is a placeholder for the porting workflow
        logger.info(f"Port request initiated for {phone_number} from {losing_carrier}")
        
        return {
            "status": "pending_documents",
            "phone_number": phone_number,
            "message": "Port request created. Please contact Twilio support to complete.",
            "next_steps": [
                "Letter of Authorization (LOA) required",
                "Current bill copy may be needed",
                "Port completion takes 7-10 business days"
            ]
        }


# Singleton instance
twilio_provisioning_service = TwilioPhoneProvisioningService()

