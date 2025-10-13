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
from openai import OpenAI
from twilio.rest import Client as TwilioClient
from email_validator import validate_email
import logging
import re

logger = logging.getLogger(__name__)

class AILeadProcessor:
    """AI-powered lead processing using multiple API integrations"""
    
    def __init__(self, agent_credentials: Dict[str, str] = None):
        """Initialize with agent-specific API credentials"""
        self.credentials = agent_credentials or {}
        
        # Use global OpenAI key if agent doesn't have their own
        openai_key = self.credentials.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=openai_key) if openai_key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        
        self.twilio_client = None
        self.setup_clients()
    
    def setup_clients(self):
        """Setup API clients with agent credentials"""
        try:
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
            
            # Generate comprehensive AI insights
            ai_insights = await self._generate_buyer_insights(processed_data)
            
            # Generate personalized response email
            response_email = await self._generate_buyer_response_email(processed_data, ai_insights)
            
            # Generate agent alert
            agent_alert = await self._generate_agent_alert(processed_data, ai_insights, 'buyer')
            
            # Get location insights
            location_data = await self._get_location_insights(
                processed_data.get('preferred_areas', '')
            )
            
            # Send notifications
            await self._send_lead_notifications(processed_data, 'buyer_interest', ai_insights)
            
            return {
                'status': 'processed',
                'lead_type': 'buyer_interest',
                'processed_data': processed_data,
                'ai_insights': ai_insights,
                'response_email': response_email,
                'agent_alert': agent_alert,
                'location_data': location_data,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing buyer lead: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def process_valuation_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process home valuation lead with AI-powered analysis"""
        try:
            # Validate and normalize data
            processed_data = await self._validate_lead_data(lead_data)
            
            # Validate address with USPS
            validated_address = await self._validate_usps_address(
                lead_data.get('property_address', '')
            )
            
            # Generate AI valuation insights
            valuation_insights = await self._generate_valuation_insights(lead_data)
            
            # Generate personalized response email
            response_email = await self._generate_valuation_response_email(lead_data, valuation_insights)
            
            # Generate agent alert
            agent_alert = await self._generate_agent_alert(lead_data, valuation_insights, 'valuation')
            
            # Get property insights from Foursquare
            property_insights = await self._get_property_neighborhood_data(validated_address)
            
            # Send notifications
            await self._send_lead_notifications(lead_data, 'home_valuation', valuation_insights)
            
            return {
                'status': 'processed',
                'lead_type': 'home_valuation',
                'processed_data': processed_data,
                'validated_address': validated_address,
                'ai_insights': valuation_insights,
                'response_email': response_email,
                'agent_alert': agent_alert,
                'property_insights': property_insights,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing valuation lead: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _validate_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize lead data"""
        processed = lead_data.copy()
        
        # Validate email
        try:
            if lead_data.get('email'):
                email_info = validate_email(lead_data.get('email', ''))
                processed['email'] = email_info.email
                processed['email_valid'] = True
            else:
                processed['email_valid'] = False
        except:
            processed['email_valid'] = False
        
        # Normalize phone number
        if lead_data.get('phone'):
            processed['phone_e164'] = self._normalize_phone(lead_data['phone'])
        
        return processed
    
    async def _generate_buyer_response_email(self, lead_data: Dict[str, Any], 
                                           ai_insights: Dict[str, Any]) -> str:
        """Generate personalized email response for buyer leads"""
        if not self.openai_client:
            name = lead_data.get('full_name', 'there').split()[0]
            return f"Hi {name},\n\nThank you for your interest in finding a home! I'd love to help you with your home search. Let's schedule a time to discuss your needs.\n\nBest regards"
        
        try:
            name = lead_data.get('full_name', 'there').split()[0]
            timeline = lead_data.get('timeline', '')
            areas = lead_data.get('preferred_areas', '')
            budget = lead_data.get('budget_range', '')
            
            prompt = f"""
Create a personalized, professional email response for a potential home buyer. Keep it warm, helpful, and focused on their specific needs.

BUYER INFO:
- Name: {name}
- Timeline: {timeline}
- Preferred Areas: {areas}
- Budget: {budget}
- AI Analysis: {ai_insights.get('summary', '')}

Write a 3-4 paragraph email that:
1. Thanks them for their interest
2. Acknowledges their specific needs
3. Offers immediate value (market insights, next steps)
4. Includes a clear call-to-action

Tone: Professional but friendly, knowledgeable, helpful
Length: 150-250 words
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional real estate agent writing personalized email responses to leads."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating buyer response email: {e}")
            name = lead_data.get('full_name', 'there').split()[0]
            return f"Hi {name},\n\nThank you for your interest in finding a home! I'd love to help you with your home search. Let's schedule a time to discuss your needs and how I can assist you.\n\nBest regards"
    
    async def _generate_valuation_response_email(self, lead_data: Dict[str, Any], 
                                               ai_insights: Dict[str, Any]) -> str:
        """Generate personalized email response for valuation leads"""
        if not self.openai_client:
            name = lead_data.get('full_name', 'there').split()[0]
            address = lead_data.get('property_address', 'your property')
            return f"Hi {name},\n\nThank you for your property valuation request. I'd be happy to provide you with a comprehensive market analysis for {address}. Let's schedule a time to discuss your property.\n\nBest regards"
        
        try:
            name = lead_data.get('full_name', 'there').split()[0]
            address = lead_data.get('property_address', 'your property')
            timeline = lead_data.get('selling_timeline', '')
            
            prompt = f"""
Create a personalized, professional email response for a home valuation request. Focus on providing immediate value and building trust.

PROPERTY INFO:
- Owner: {name}
- Property: {address}
- Selling Timeline: {timeline}
- AI Analysis: {ai_insights.get('summary', '')}

Write a 3-4 paragraph email that:
1. Thanks them for the valuation request
2. Acknowledges their property and timeline
3. Offers market insights and next steps
4. Includes a clear call-to-action for consultation

Tone: Professional, knowledgeable, trustworthy
Length: 150-250 words
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional real estate agent responding to home valuation requests."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating valuation response email: {e}")
            name = lead_data.get('full_name', 'there').split()[0]
            address = lead_data.get('property_address', 'your property')
            return f"Hi {name},\n\nThank you for your property valuation request. I'd be happy to provide you with a comprehensive market analysis for {address}. Let's schedule a time to discuss your property and market conditions.\n\nBest regards"
    
    async def _generate_agent_alert(self, lead_data: Dict[str, Any], 
                                  ai_insights: Dict[str, Any], lead_type: str) -> str:
        """Generate alert message for the agent"""
        
        score = ai_insights.get('lead_score', 50)
        name = lead_data.get('full_name', 'Unknown')
        email = lead_data.get('email', '')
        
        if score >= 80:
            priority = "🔥 HOT LEAD"
        elif score >= 60:
            priority = "🌟 WARM LEAD"
        else:
            priority = "📝 NEW LEAD"
        
        summary = ai_insights.get('summary', 'No analysis available')
        
        # Get recommended action from AI insights
        recommended_action = "Contact soon"
        if 'recommended_actions' in ai_insights:
            recommended_action = ai_insights['recommended_actions'].get('immediate_response', 'Contact soon')
        elif 'recommended_approach' in ai_insights:
            recommended_action = ai_insights['recommended_approach'].get('contact_method', 'Contact soon')
        
        alert = f"""{priority} - Score: {score}/100

{name} ({email})
Type: {lead_type.replace('_', ' ').title()}

AI Analysis: {summary}

Recommended Action: {recommended_action}
"""
        
        return alert
    
    async def _generate_buyer_insights(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive AI insights for buyer leads"""
        if not self.openai_client:
            return {
                'insights': 'AI insights not available - API key not configured',
                'lead_score': 50,
                'intent_analysis': {'primary_intent': 'unknown', 'confidence_level': 5},
                'urgency_assessment': {'urgency_score': 5, 'timeline_category': 'exploring'}
            }
        
        try:
            # Create comprehensive analysis prompt
            name = lead_data.get('full_name', '')
            message = lead_data.get('important_features', '') or lead_data.get('message', '')
            timeline = lead_data.get('timeline', '')
            budget_range = lead_data.get('budget_range', '')
            preferred_areas = lead_data.get('preferred_areas', '')
            priorities = lead_data.get('priorities', [])
            
            priorities_text = ", ".join(priorities) if priorities else "Not specified"
            
            prompt = f"""
You are an expert real estate AI assistant analyzing a potential buyer lead. Analyze the following information and provide detailed insights in JSON format.

LEAD INFORMATION:
- Name: {name}
- Message/Needs: {message}
- Timeline: {timeline}
- Budget Range: {budget_range}
- Preferred Areas: {preferred_areas}
- Priorities: {priorities_text}

Analyze and return JSON with these fields:

{{
  "intent_analysis": {{
    "primary_intent": "serious_buyer|browsing|investor|relocating",
    "confidence_level": 1-10,
    "intent_indicators": ["list", "of", "key", "phrases"]
  }},
  "urgency_assessment": {{
    "urgency_score": 1-10,
    "timeline_category": "immediate|1-3_months|3-6_months|6-12_months|exploring",
    "urgency_indicators": ["specific", "phrases", "showing", "urgency"]
  }},
  "qualification_status": {{
    "budget_qualified": true/false,
    "timeline_qualified": true/false,
    "location_qualified": true/false,
    "overall_qualification": "hot|warm|cold"
  }},
  "buyer_profile": {{
    "motivation": "upgrade|downsize|first_time|relocation|investment",
    "family_situation": "single|couple|young_family|growing_family|empty_nesters",
    "lifestyle_preferences": ["urban", "suburban", "family_friendly"]
  }},
  "recommended_actions": {{
    "immediate_response": "call|email|text",
    "follow_up_strategy": "aggressive|standard|nurture",
    "talking_points": ["key", "topics", "to", "discuss"]
  }},
  "lead_score": 1-100,
  "summary": "Brief 2-3 sentence analysis of this lead"
}}

Focus on extracting insights that help a realtor prioritize and respond effectively.
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert real estate AI assistant. Always respond with valid JSON only."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse JSON response
            ai_response = response.choices[0].message.content.strip()
            
            # Clean up response (remove any markdown formatting)
            ai_response = re.sub(r'```json\s*', '', ai_response)
            ai_response = re.sub(r'```\s*$', '', ai_response)
            
            return json.loads(ai_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "error": "Failed to parse AI response",
                "lead_score": 50,
                "summary": "AI analysis temporarily unavailable",
                "intent_analysis": {"primary_intent": "unknown", "confidence_level": 5},
                "urgency_assessment": {"urgency_score": 5, "timeline_category": "exploring"}
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "error": str(e),
                "lead_score": 50,
                "summary": "AI analysis temporarily unavailable",
                "intent_analysis": {"primary_intent": "unknown", "confidence_level": 5},
                "urgency_assessment": {"urgency_score": 5, "timeline_category": "exploring"}
            }
    
    async def _generate_valuation_insights(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for property valuation"""
        if not self.openai_client:
            return {
                'insights': 'AI insights not available - API key not configured',
                'lead_score': 50,
                'seller_motivation': {'motivation_level': 5, 'motivation_type': 'exploring'}
            }
        
        try:
            name = lead_data.get('full_name', '')
            address = lead_data.get('property_address', '')
            prop_type = lead_data.get('property_type', '')
            sqft = lead_data.get('square_footage', '')
            year_built = lead_data.get('year_built', '')
            improvements = lead_data.get('recent_improvements', '')
            timeline = lead_data.get('selling_timeline', '')
            
            prompt = f"""
You are an expert real estate AI assistant analyzing a home valuation request. Analyze the following property information and provide insights in JSON format.

PROPERTY INFORMATION:
- Owner: {name}
- Address: {address}
- Property Type: {prop_type}
- Square Footage: {sqft}
- Year Built: {year_built}
- Recent Improvements: {improvements}
- Selling Timeline: {timeline}

Analyze and return JSON with these fields:

{{
  "seller_motivation": {{
    "motivation_level": 1-10,
    "motivation_type": "testing_market|serious_seller|exploring|urgent|downsizing|upgrading",
    "timeline_urgency": 1-10
  }},
  "property_assessment": {{
    "property_type_category": "starter_home|family_home|luxury|investment|unique",
    "condition_indicators": ["well_maintained", "needs_updates", "recently_improved"],
    "market_appeal": 1-10
  }},
  "selling_readiness": {{
    "readiness_score": 1-10,
    "timeline_category": "immediate|1-3_months|3-6_months|6-12_months|just_curious",
    "commitment_level": "high|medium|low"
  }},
  "opportunity_analysis": {{
    "listing_potential": "high|medium|low",
    "referral_potential": "high|medium|low",
    "service_opportunities": ["listing", "buying", "investment", "referrals"]
  }},
  "recommended_approach": {{
    "contact_method": "call|email|text|in_person",
    "response_urgency": "immediate|same_day|24_hours|standard",
    "key_talking_points": ["market", "conditions", "pricing", "strategy"]
  }},
  "lead_score": 1-100,
  "summary": "Brief analysis of this valuation request and opportunity"
}}

Focus on helping the realtor understand the seller's true motivation and the business opportunity.
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert real estate AI assistant. Always respond with valid JSON only."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse JSON response
            ai_response = response.choices[0].message.content.strip()
            
            # Clean up response (remove any markdown formatting)
            ai_response = re.sub(r'```json\s*', '', ai_response)
            ai_response = re.sub(r'```\s*$', '', ai_response)
            
            return json.loads(ai_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "error": "Failed to parse AI response",
                "lead_score": 50,
                "summary": "AI analysis temporarily unavailable",
                "seller_motivation": {"motivation_level": 5, "motivation_type": "exploring"}
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "error": str(e),
                "lead_score": 50,
                "summary": "AI analysis temporarily unavailable",
                "seller_motivation": {"motivation_level": 5, "motivation_type": "exploring"}
            }
    
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
    
    async def _send_lead_notifications(self, lead_data: Dict[str, Any], lead_type: str, ai_insights: Dict[str, Any]):
        """Send notifications via SMS and email"""
        try:
            # Generate agent alert message
            alert_message = await self._generate_agent_alert(lead_data, ai_insights, lead_type)
            
            if self.twilio_client and self.credentials.get('TWILIO_PHONE_NUMBER'):
                # Send SMS notification to agent
                agent_phone = self.credentials.get('AGENT_PHONE_NUMBER')
                if agent_phone:
                    self.twilio_client.messages.create(
                        body=alert_message[:1500],  # SMS length limit
                        from_=self.credentials['TWILIO_PHONE_NUMBER'],
                        to=agent_phone
                    )
                    logger.info(f"SMS notification sent for lead: {lead_data.get('email', 'Unknown')}")
            
            # Send email via Brevo
            await self._send_brevo_notification(lead_data, lead_type, ai_insights)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    async def _send_brevo_notification(self, lead_data: Dict[str, Any], lead_type: str, ai_insights: Dict[str, Any]):
        """Send email notification via Brevo"""
        brevo_key = self.credentials.get('BREVO_API_KEY') or os.getenv('BREVO_API_KEY')
        if not brevo_key:
            logger.warning("Brevo API key not configured - skipping email notification")
            return
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'api-key': brevo_key,
                    'Content-Type': 'application/json'
                }
                
                # Generate agent alert for email
                alert_message = await self._generate_agent_alert(lead_data, ai_insights, lead_type)
                
                # Email payload
                email_data = {
                    "sender": {
                        "email": os.getenv('EMAIL_FROM_ADDRESS', 'noreply@ezrealtor.app'),
                        "name": os.getenv('EMAIL_FROM_NAME', 'EZRealtor.app')
                    },
                    "to": [
                        {
                            "email": self.credentials.get('AGENT_EMAIL', 'agent@example.com'),
                            "name": "Agent"
                        }
                    ],
                    "subject": f"New {lead_type.replace('_', ' ').title()} Lead: {lead_data.get('full_name', 'Unknown')}",
                    "textContent": alert_message
                }
                
                response = await client.post(
                    'https://api.brevo.com/v3/smtp/email',
                    headers=headers,
                    json=email_data
                )
                
                if response.status_code == 201:
                    logger.info(f"Email notification sent for lead: {lead_data.get('email', 'Unknown')}")
                else:
                    logger.error(f"Brevo API error: {response.status_code} - {response.text}")
                
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