"""
Twilio Service for Voice and SMS handling
"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
import os
import logging

logger = logging.getLogger(__name__)


class TwilioService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "+17163002763")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")

    def send_sms(self, to_number: str, message: str):
        """Send an SMS message"""
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent to {to_number}: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {str(e)}")
            return None

    def handle_incoming_call(self, agent_name: str = None, agent_phone: str = None):
        """
        Handle incoming voice call
        Returns TwiML response
        """
        response = VoiceResponse()
        
        # Greeting
        greeting = f"Thank you for calling {agent_name if agent_name else 'our real estate office'}. "
        
        # Gather input
        gather = Gather(
            num_digits=1,
            action='/api/v1/twilio/voice/menu',
            method='POST',
            timeout=10
        )
        
        gather.say(
            greeting + 
            "Press 1 to leave a message about buying a home. "
            "Press 2 to leave a message about selling your home. "
            "Press 3 to speak with an agent. "
            "Or stay on the line and we'll connect you.",
            voice='alice',
            language='en-US'
        )
        
        response.append(gather)
        
        # If no input, try to forward to agent or take voicemail
        if agent_phone:
            response.say("Connecting you to an agent now.", voice='alice')
            response.dial(agent_phone, timeout=30)
        else:
            response.say(
                "Please leave a detailed message after the beep, and we'll get back to you within 24 hours.",
                voice='alice'
            )
            response.record(
                max_length=120,
                transcribe=True,
                transcribe_callback='/api/v1/twilio/voice/transcription',
                action='/api/v1/twilio/voice/recording-complete'
            )
        
        return str(response)

    def handle_voice_menu(self, digits: str, agent_phone: str = None):
        """
        Handle voice menu selection
        """
        response = VoiceResponse()
        
        if digits == "1":
            # Buyer inquiry
            response.say(
                "Thank you for your interest in buying a home. "
                "Please leave a detailed message with your name, phone number, "
                "and what you're looking for. We'll get back to you within 24 hours.",
                voice='alice'
            )
            response.record(
                max_length=120,
                transcribe=True,
                transcribe_callback='/api/v1/twilio/voice/transcription?type=buyer',
                action='/api/v1/twilio/voice/recording-complete'
            )
        
        elif digits == "2":
            # Seller inquiry
            response.say(
                "Thank you for your interest in selling your home. "
                "Please leave a detailed message with your name, phone number, "
                "and property address. We'll get back to you within 24 hours.",
                voice='alice'
            )
            response.record(
                max_length=120,
                transcribe=True,
                transcribe_callback='/api/v1/twilio/voice/transcription?type=seller',
                action='/api/v1/twilio/voice/recording-complete'
            )
        
        elif digits == "3":
            # Connect to agent
            if agent_phone:
                response.say("Connecting you to an agent now.", voice='alice')
                response.dial(agent_phone, timeout=30)
            else:
                response.say(
                    "All agents are currently unavailable. "
                    "Please leave a message and we'll call you back.",
                    voice='alice'
                )
                response.record(
                    max_length=120,
                    transcribe=True,
                    transcribe_callback='/api/v1/twilio/voice/transcription',
                    action='/api/v1/twilio/voice/recording-complete'
                )
        else:
            # Invalid input
            response.say("Sorry, that's not a valid option.", voice='alice')
            response.redirect('/api/v1/twilio/voice')
        
        return str(response)

    def handle_recording_complete(self):
        """
        Handle completed recording
        """
        response = VoiceResponse()
        response.say(
            "Thank you for your message. We'll be in touch soon. Goodbye!",
            voice='alice'
        )
        response.hangup()
        return str(response)

    def handle_incoming_sms(self, from_number: str, message_body: str, agent_name: str = None):
        """
        Handle incoming SMS message
        Returns TwiML response
        """
        response = MessagingResponse()
        
        # Auto-reply
        reply = (
            f"Hi! Thank you for contacting {agent_name if agent_name else 'us'}. "
            f"We've received your message: '{message_body[:50]}...' "
            f"and will respond within 24 hours. For immediate assistance, call us!"
        )
        
        response.message(reply)
        
        return str(response)

    def send_lead_notification_sms(self, agent_phone: str, lead_name: str, lead_type: str):
        """
        Send SMS notification to agent about new lead
        """
        message = (
            f"🏠 NEW LEAD ALERT!\n"
            f"Name: {lead_name}\n"
            f"Type: {lead_type}\n"
            f"Check your dashboard: https://login.ezrealtor.app/dashboard"
        )
        return self.send_sms(agent_phone, message)


# Singleton instance
twilio_service = TwilioService()

