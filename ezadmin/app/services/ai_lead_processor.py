"""
AI-Powered Lead Services
Integrates with multiple APIs for enhanced lead capture and processing
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime
import openai
from twilio.rest import Client as TwilioClient
from email_validator import validate_email
import logging

logger = logging.getLogger(__name__)

class AILeadProcessor:
    """AI-powered lead processing using multiple API integrations"""
    
    def __init__(self, agent_credentials: Dict[str, str]):
        """Initialize with agent-specific API credentials"""
        self.credentials = agent_credentials
        self.openai_client = None
        self.twilio_client = None
        self.setup_clients()
    
    def setup_clients(self):
        """Setup API clients with agent credentials"""
        try:
            if self.credentials.get('OPENAI_API_KEY'):
                openai.api_key = self.credentials['OPENAI_API_KEY']
                self.openai_client = openai
            
            if self.credentials.get('TWILIO_ACCOUNT_SID') and self.credentials.get('TWILIO_AUTH_TOKEN'):
                self.twilio_client = TwilioClient(
                    self.credentials['TWILIO_ACCOUNT_SID'],
                    self.credentials['TWILIO_AUTH_TOKEN']
                )
        except Exception as e:
            logger.error(f"Error setting up API clients: {e}")
    
    async def process_buyer_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process buyer interest lead with AI enhancement"""
        try:
            # Validate and normalize data
            processed_data = await self._validate_lead_data(lead_data)
            
            # Generate AI insights
            ai_insights = await self._generate_buyer_insights(processed_data)
            
            # Get location insights
            location_data = await self._get_location_insights(
                processed_data.get('preferred_areas', '')
            )
            
            # Calculate commute times if work address provided
            commute_data = await self._calculate_commute_times(processed_data)
            
            # Send notifications
            await self._send_lead_notifications(processed_data, 'buyer_interest')
            
            return {
                'processed_data': processed_data,
                'ai_insights': ai_insights,
                'location_data': location_data,
                'commute_data': commute_data,
                'status': 'processed'
            }
            
        except Exception as e:
            logger.error(f"Error processing buyer lead: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def process_valuation_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process home valuation lead with AI-powered analysis"""
        try:
            # Validate address with USPS
            validated_address = await self._validate_usps_address(
                lead_data.get('property_address', '')
            )
            
            # Get property insights from Foursquare
            property_insights = await self._get_property_neighborhood_data(validated_address)
            
            # Generate AI valuation insights
            valuation_insights = await self._generate_valuation_insights(lead_data)
            
            # Get comparable properties data
            comparable_data = await self._get_comparable_properties(validated_address)
            
            # Send valuation report
            await self._send_valuation_report(lead_data, valuation_insights)
            
            # Send notifications
            await self._send_lead_notifications(lead_data, 'home_valuation')
            
            return {
                'validated_address': validated_address,
                'property_insights': property_insights,
                'valuation_insights': valuation_insights,
                'comparable_data': comparable_data,
                'status': 'processed'
            }
            
        except Exception as e:
            logger.error(f"Error processing valuation lead: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _validate_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize lead data"""
        processed = lead_data.copy()
        
        # Validate email
        try:
            email_info = validate_email(lead_data.get('email', ''))
            processed['email'] = email_info.email
            processed['email_valid'] = True
        except:
            processed['email_valid'] = False
        
        # Normalize phone number
        if lead_data.get('phone'):
            processed['phone_e164'] = self._normalize_phone(lead_data['phone'])
        
        return processed
    
    async def _generate_buyer_insights(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for buyer leads"""
        if not self.openai_client:
            return {'insights': 'AI insights not available - API key not configured'}
        
        try:
            prompt = f"""
            Analyze this home buyer profile and provide insights:
            
            Budget: {lead_data.get('budget_range', 'Not specified')}
            Preferred areas: {lead_data.get('preferred_areas', 'Not specified')}
            Important features: {lead_data.get('important_features', 'Not specified')}
            Timeline: {lead_data.get('timeline', 'Not specified')}
            Priorities: {', '.join(lead_data.get('priorities', []))}
            
            Provide:
            1. Market opportunity assessment
            2. Recommended property types and features
            3. Suggested neighborhoods or areas to explore
            4. Timeline and budget considerations
            5. Next steps for this buyer
            
            Format as JSON with keys: market_assessment, recommendations, suggested_areas, considerations, next_steps
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error generating buyer insights: {e}")
            return {'insights': f'AI analysis error: {str(e)}'}
    
    async def _generate_valuation_insights(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for property valuation"""
        if not self.openai_client:
            return {'insights': 'AI insights not available - API key not configured'}
        
        try:
            property_details = lead_data.get('metadata', {}).get('property_details', {})
            
            prompt = f"""
            Analyze this property for valuation insights:
            
            Address: {property_details.get('address', 'Not provided')}
            Square Footage: {property_details.get('square_footage', 'Unknown')}
            Year Built: {property_details.get('year_built', 'Unknown')}
            Bedrooms: {property_details.get('bedrooms', 'Unknown')}
            Bathrooms: {property_details.get('bathrooms', 'Unknown')}
            Property Type: {property_details.get('property_type', 'Unknown')}
            Features: {', '.join(property_details.get('features', []))}
            Recent Improvements: {property_details.get('recent_improvements', 'None mentioned')}
            
            Provide:
            1. Key value drivers for this property
            2. Market positioning assessment
            3. Improvement recommendations to increase value
            4. Selling strategy suggestions
            5. Market timing considerations
            
            Format as JSON with keys: value_drivers, market_position, improvement_recommendations, selling_strategy, market_timing
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error generating valuation insights: {e}")
            return {'insights': f'AI analysis error: {str(e)}'}
    
    async def _validate_usps_address(self, address: str) -> Dict[str, Any]:
        """Validate address using USPS API"""
        if not self.credentials.get('USPS_USER_ID'):
            return {'address': address, 'validated': False, 'message': 'USPS validation not configured'}
        
        try:
            # USPS API implementation would go here
            # For now, return mock validation
            return {
                'address': address,
                'validated': True,
                'standardized_address': address,
                'zip_plus_4': '12345-6789',
                'delivery_point': 'Valid'
            }
        except Exception as e:
            logger.error(f"USPS validation error: {e}")
            return {'address': address, 'validated': False, 'error': str(e)}
    
    async def _get_location_insights(self, location: str) -> Dict[str, Any]:
        """Get location insights using Foursquare API"""
        if not self.credentials.get('FOURSQUARE_API_KEY'):
            return {'insights': 'Location insights not available - API key not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                # Foursquare Places API
                headers = {
                    'Authorization': self.credentials['FOURSQUARE_API_KEY'],
                    'Accept': 'application/json'
                }
                
                response = await client.get(
                    'https://api.foursquare.com/v3/places/search',
                    headers=headers,
                    params={
                        'query': location,
                        'categories': '10000,12000,13000',  # Arts, Food, Nightlife
                        'limit': 20
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'nearby_amenities': len(data.get('results', [])),
                        'amenity_types': [place.get('name') for place in data.get('results', [])[:5]],
                        'location_score': min(len(data.get('results', [])) * 5, 100)
                    }
                
        except Exception as e:
            logger.error(f"Foursquare API error: {e}")
        
        return {'insights': 'Location data temporarily unavailable'}
    
    async def _get_property_neighborhood_data(self, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get neighborhood data for property valuation"""
        # Similar to _get_location_insights but focused on property-specific data
        return await self._get_location_insights(address_data.get('address', ''))
    
    async def _calculate_commute_times(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate commute times using ORS API"""
        if not self.credentials.get('ORS_API_KEY'):
            return {'commute_data': 'Commute analysis not available - API key not configured'}
        
        try:
            # ORS API implementation would go here
            # Mock data for now
            return {
                'average_commute': '25 minutes',
                'peak_hour_commute': '35 minutes',
                'public_transport_available': True,
                'walkability_score': 85
            }
        except Exception as e:
            logger.error(f"ORS API error: {e}")
            return {'commute_data': f'Commute analysis error: {str(e)}'}
    
    async def _get_comparable_properties(self, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get comparable properties data"""
        # This would integrate with MLS or other property data APIs
        return {
            'comparable_count': 5,
            'average_price_per_sqft': '$150',
            'market_trend': 'increasing',
            'days_on_market_avg': 25
        }
    
    async def _send_lead_notifications(self, lead_data: Dict[str, Any], lead_type: str):
        """Send notifications via SMS and email"""
        try:
            if self.twilio_client and self.credentials.get('TWILIO_PHONE_NUMBER'):
                # Send SMS notification to agent
                message = f"New {lead_type} lead: {lead_data.get('full_name', 'Unknown')} - {lead_data.get('email', 'No email')}"
                
                # You would have the agent's phone number in their profile
                agent_phone = self.credentials.get('AGENT_PHONE_NUMBER')
                if agent_phone:
                    self.twilio_client.messages.create(
                        body=message,
                        from_=self.credentials['TWILIO_PHONE_NUMBER'],
                        to=agent_phone
                    )
            
            # Send email via Brevo would go here
            await self._send_brevo_notification(lead_data, lead_type)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    async def _send_valuation_report(self, lead_data: Dict[str, Any], insights: Dict[str, Any]):
        """Send valuation report via email"""
        try:
            # Generate and send detailed valuation report
            # This would use Brevo for email delivery
            pass
        except Exception as e:
            logger.error(f"Error sending valuation report: {e}")
    
    async def _send_brevo_notification(self, lead_data: Dict[str, Any], lead_type: str):
        """Send email notification via Brevo"""
        if not self.credentials.get('BREVO_API_KEY'):
            return
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'api-key': self.credentials['BREVO_API_KEY'],
                    'Content-Type': 'application/json'
                }
                
                # Brevo API implementation would go here
                pass
                
        except Exception as e:
            logger.error(f"Brevo API error: {e}")
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format"""
        # Simple phone normalization - would use more robust library in production
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        return phone