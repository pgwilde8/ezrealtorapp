"""
Twilio API endpoints for voice and SMS webhooks
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.utils.database import get_db
from app.models.agent import Agent
from app.models.lead import Lead
from app.services.twilio_service import twilio_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/twilio", tags=["twilio"])


async def get_agent_from_phone(db: AsyncSession, phone_number: str):
    """
    Get agent by their Twilio phone number
    This is called when a call/SMS comes in to a specific number
    """
    # Look up agent by their assigned Twilio phone number
    result = await db.execute(
        select(Agent).where(
            Agent.twilio_phone_number == phone_number,
            Agent.twilio_phone_status == "active"
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        logger.warning(f"No agent found for phone number {phone_number}")
        # Return first active agent as fallback (for testing)
        result = await db.execute(
            select(Agent).where(Agent.status == "active").limit(1)
        )
        agent = result.scalar_one_or_none()
    
    return agent


@router.post("/voice")
async def handle_incoming_call(
    request: Request,
    db: AsyncSession = Depends(get_db),
    From: str = Form(None),
    To: str = Form(None),
    CallSid: str = Form(None)
):
    """
    Handle incoming voice calls
    Webhook URL: https://ezrealtor.app/api/v1/twilio/voice
    """
    logger.info(f"Incoming call from {From} to {To}, CallSid: {CallSid}")
    
    try:
        # Get agent for this phone number
        agent = await get_agent_from_phone(db, To)
        
        # Generate TwiML response
        twiml = twilio_service.handle_incoming_call(
            agent_name=f"{agent.first_name} {agent.last_name}" if agent else None,
            agent_phone=agent.phone if agent else None
        )
        
        # Log the call as a lead
        if agent and From:
            lead = Lead(
                agent_id=agent.id,
                first_name="Phone Caller",
                phone=From,
                lead_type="phone_call",
                source="twilio_voice",
                status="new",
                notes=f"Incoming call - CallSid: {CallSid}"
            )
            db.add(lead)
            await db.commit()
            logger.info(f"Created lead from call: {From}")
        
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error handling incoming call: {str(e)}")
        # Return basic TwiML even on error
        twiml = twilio_service.handle_incoming_call()
        return Response(content=twiml, media_type="application/xml")


@router.post("/voice/menu")
async def handle_voice_menu(
    request: Request,
    Digits: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle voice menu selection
    """
    logger.info(f"Voice menu selection: {Digits} from {From}")
    
    try:
        # Get agent for this phone number
        agent = await get_agent_from_phone(db, To)
        
        # Update lead with selection
        if agent and From and Digits:
            result = await db.execute(
                select(Lead).where(
                    Lead.agent_id == agent.id,
                    Lead.phone == From
                ).order_by(Lead.created_at.desc()).limit(1)
            )
            lead = result.scalar_one_or_none()
            
            if lead:
                menu_options = {
                    "1": "buyer",
                    "2": "seller",
                    "3": "speak_with_agent"
                }
                lead.lead_type = menu_options.get(Digits, "phone_call")
                lead.notes = f"{lead.notes}\nMenu selection: {Digits}"
                await db.commit()
        
        # Generate TwiML response
        twiml = twilio_service.handle_voice_menu(
            digits=Digits,
            agent_phone=agent.phone if agent else None
        )
        
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error handling voice menu: {str(e)}")
        twiml = twilio_service.handle_recording_complete()
        return Response(content=twiml, media_type="application/xml")


@router.post("/voice/transcription")
async def handle_transcription(
    request: Request,
    db: AsyncSession = Depends(get_db),
    TranscriptionText: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    RecordingUrl: str = Form(None),
    CallSid: str = Form(None)
):
    """
    Handle voice transcription callback
    """
    logger.info(f"Transcription received from {From}: {TranscriptionText[:100]}")
    
    try:
        # Get agent
        agent = await get_agent_from_phone(db, To)
        
        if agent and From:
            # Update existing lead or create new one
            result = await db.execute(
                select(Lead).where(
                    Lead.agent_id == agent.id,
                    Lead.phone == From
                ).order_by(Lead.created_at.desc()).limit(1)
            )
            lead = result.scalar_one_or_none()
            
            if lead:
                # Update existing lead
                lead.notes = f"{lead.notes}\n\nVoicemail Transcription:\n{TranscriptionText}"
                if RecordingUrl:
                    lead.notes = f"{lead.notes}\n\nRecording: {RecordingUrl}"
            else:
                # Create new lead
                lead = Lead(
                    agent_id=agent.id,
                    first_name="Voicemail",
                    phone=From,
                    lead_type="voicemail",
                    source="twilio_voice",
                    status="new",
                    notes=f"Voicemail Transcription:\n{TranscriptionText}\n\nRecording: {RecordingUrl or 'N/A'}"
                )
                db.add(lead)
            
            await db.commit()
            logger.info(f"Updated lead with transcription: {From}")
            
            # Send SMS notification to agent
            if agent.phone:
                twilio_service.send_lead_notification_sms(
                    agent_phone=agent.phone,
                    lead_name="Voicemail",
                    lead_type="New voicemail received"
                )
    
    except Exception as e:
        logger.error(f"Error handling transcription: {str(e)}")
    
    return {"status": "ok"}


@router.post("/voice/recording-complete")
async def handle_recording_complete(
    request: Request,
    RecordingUrl: str = Form(None),
    RecordingDuration: str = Form(None)
):
    """
    Handle recording completion
    """
    logger.info(f"Recording complete: {RecordingUrl} ({RecordingDuration}s)")
    
    twiml = twilio_service.handle_recording_complete()
    return Response(content=twiml, media_type="application/xml")


@router.post("/sms")
async def handle_incoming_sms(
    request: Request,
    db: AsyncSession = Depends(get_db),
    From: str = Form(None),
    To: str = Form(None),
    Body: str = Form(None),
    MessageSid: str = Form(None)
):
    """
    Handle incoming SMS messages
    Webhook URL: https://ezrealtor.app/api/v1/twilio/sms
    """
    logger.info(f"Incoming SMS from {From} to {To}: {Body}")
    
    try:
        # Get agent for this phone number
        agent = await get_agent_from_phone(db, To)
        
        # Create lead from SMS
        if agent and From and Body:
            lead = Lead(
                agent_id=agent.id,
                first_name="SMS Contact",
                phone=From,
                lead_type="sms",
                source="twilio_sms",
                status="new",
                notes=f"SMS Message: {Body}\n\nMessageSid: {MessageSid}"
            )
            db.add(lead)
            await db.commit()
            logger.info(f"Created lead from SMS: {From}")
            
            # Send SMS notification to agent
            if agent.phone and agent.phone != To:
                twilio_service.send_lead_notification_sms(
                    agent_phone=agent.phone,
                    lead_name="SMS Lead",
                    lead_type="New text message"
                )
        
        # Generate TwiML auto-reply
        twiml = twilio_service.handle_incoming_sms(
            from_number=From,
            message_body=Body,
            agent_name=f"{agent.first_name} {agent.last_name}" if agent else None
        )
        
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error handling incoming SMS: {str(e)}")
        # Return basic auto-reply
        twiml = twilio_service.handle_incoming_sms(From, Body)
        return Response(content=twiml, media_type="application/xml")


@router.post("/sms/status")
async def handle_sms_status(
    request: Request,
    MessageSid: str = Form(None),
    MessageStatus: str = Form(None),
    To: str = Form(None)
):
    """
    Handle SMS delivery status callback
    """
    logger.info(f"SMS status: {MessageSid} -> {MessageStatus} (to {To})")
    return {"status": "ok"}

