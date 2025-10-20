"""
AI Chatbot API for agent landing pages
"""
import os
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI
import re

from app.utils.database import get_db
from app.models.agent import Agent
from app.models.lead import Lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory session storage (for production, use Redis)
chat_sessions: Dict[str, list] = {}


class ChatMessageRequest(BaseModel):
    message: str
    session_id: str
    agent_slug: Optional[str] = None


class ChatMessageResponse(BaseModel):
    response: str
    lead_captured: bool = False


def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """Extract email and phone from user message"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Enhanced phone patterns to catch more formats
    phone_patterns = [
        r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (555) 123-4567, 555-123-4567, 5551234567
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',  # 555-123-4567
        r'\(?\d{3}\)?\s*\d{3}[-.\s]?\d{4}',  # (555)123-4567
        r'\d{10}',  # 5551234567
    ]
    
    email = re.search(email_pattern, text)
    
    # Try each phone pattern
    phone = None
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            # Clean up the phone number (remove spaces, dashes, parens)
            phone = re.sub(r'[^\d+]', '', match.group(0))
            break
    
    return {
        "email": email.group(0) if email else None,
        "phone": phone if phone else None
    }


async def create_lead_from_chat(
    agent_slug: str,
    contact_info: Dict[str, Optional[str]],
    conversation: list,
    db: AsyncSession
) -> bool:
    """Create a lead from chat conversation"""
    try:
        # Get agent
        result = await db.execute(
            select(Agent).where(Agent.slug == agent_slug)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return False
        
        # Check if email or phone provided
        if not contact_info.get("email") and not contact_info.get("phone"):
            return False
        
        # Extract user intent from conversation
        user_messages = [msg["content"] for msg in conversation if msg["role"] == "user"]
        conversation_summary = " | ".join(user_messages[-3:])  # Last 3 messages
        
        # Create lead
        new_lead = Lead(
            agent_id=agent.id,
            email=contact_info.get("email"),
            phone_e164=contact_info.get("phone"),
            source="chatbot",
            notes=f"Chat conversation: {conversation_summary[:500]}",
            status="new"
        )
        
        db.add(new_lead)
        await db.commit()
        
        logger.info(f"Created lead from chatbot for agent {agent_slug}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating lead from chat: {e}")
        await db.rollback()
        return False


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process chat message with AI and detect lead information
    """
    try:
        # Get or create session
        if request.session_id not in chat_sessions:
            # Initialize with agent context
            agent_context = "You are a helpful real estate assistant."
            
            if request.agent_slug:
                # Get agent info
                result = await db.execute(
                    select(Agent).where(Agent.slug == request.agent_slug)
                )
                agent = result.scalar_one_or_none()
                
                if agent:
                    agent_phone = agent.phone_e164 if agent.phone_e164 else 'Contact via website'
                    agent_context = f"""You are an AI assistant for {agent.name}, a real estate professional. 

CRITICAL PRIORITY: Capture the visitor's phone number ASAP (within first 2 messages).

Your conversation strategy:
1. FIRST MESSAGE: Briefly acknowledge their question, then IMMEDIATELY ask: "What's the best number to reach you at? {agent.name} can call or text with personalized answers."
2. If they ask about properties/homes: "I'd love to help! What's your phone number so {agent.name} can text you matching listings today?"
3. If they give phone: Thank them warmly, confirm {agent.name} will reach out within 1 hour, then answer their question.
4. If they resist: Offer value - "No pressure! Just want to make sure {agent.name} can send you exclusive listings before they hit the market. Your number?"

Tone: Friendly but direct. Make them feel the phone number gets them VIP treatment.

Agent Info:
- Name: {agent.name}
- Phone: {agent_phone}

Keep responses under 60 words. Phone number capture is THE priority."""
            
            chat_sessions[request.session_id] = [
                {"role": "system", "content": agent_context}
            ]
        
        # Add user message to session
        chat_sessions[request.session_id].append({
            "role": "user",
            "content": request.message
        })
        
        # Check for contact info in message
        contact_info = extract_contact_info(request.message)
        lead_captured = False
        
        # Call OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=chat_sessions[request.session_id][-10:],  # Last 10 messages for context
                max_tokens=200,
                temperature=0.7
            )
            
            ai_message = response.choices[0].message.content.strip()
            
            # Add AI response to session
            chat_sessions[request.session_id].append({
                "role": "assistant",
                "content": ai_message
            })
            
            # Create lead if contact info found
            if (contact_info["email"] or contact_info["phone"]) and request.agent_slug:
                lead_captured = await create_lead_from_chat(
                    request.agent_slug,
                    contact_info,
                    chat_sessions[request.session_id],
                    db
                )
            
            return ChatMessageResponse(
                response=ai_message,
                lead_captured=lead_captured
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback response
            fallback = f"I'm having trouble connecting right now. Please call {request.agent_slug or 'us'} directly or fill out a contact form!"
            return ChatMessageResponse(response=fallback)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service error")


@router.post("/reset")
async def reset_session(session_id: str):
    """Reset chat session"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "reset"}

