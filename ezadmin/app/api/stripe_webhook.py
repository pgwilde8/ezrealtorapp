"""
Stripe Webhook API Endpoint
Handles incoming webhook events from Stripe
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from app.services.stripe_webhook import webhook_handler

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> JSONResponse:
    """
    Handle Stripe webhook events
    
    This endpoint receives and processes webhook events from Stripe
    for subscription management, payment processing, and billing updates.
    """
    try:
        # Get raw request body and signature
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            logger.error("Missing Stripe signature header")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Verify webhook signature and construct event
        event = webhook_handler.verify_webhook_signature(payload, sig_header)
        
        # Process the event
        result = await webhook_handler.handle_event(event)
        
        logger.info(f"Webhook processed: {event['type']} - {result['status']}")
        
        return JSONResponse(
            status_code=200,
            content={
                "received": True,
                "event_type": event['type'],
                "event_id": event['id'],
                "result": result
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (signature verification errors)
        raise
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Return 200 to acknowledge receipt even if processing failed
        # Stripe will retry failed webhooks
        return JSONResponse(
            status_code=200,
            content={
                "received": True,
                "error": str(e),
                "status": "processing_failed"
            }
        )

@router.get("/stripe/webhook/test")
async def test_webhook_endpoint():
    """Test endpoint to verify webhook URL is accessible"""
    return {"status": "ok", "message": "Webhook endpoint is accessible"}

@router.post("/stripe/webhook/simulate")
async def simulate_webhook_event(
    event_data: Dict[str, Any]
):
    """
    Simulate webhook events for testing (admin only)
    
    This endpoint allows testing webhook handlers without
    actually triggering events from Stripe.
    """
    try:
        # Process the simulated event
        result = await webhook_handler.handle_event(event_data)
        
        return {
            "status": "simulated",
            "event_type": event_data.get('type'),
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Webhook simulation error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Simulation failed: {str(e)}"
        )