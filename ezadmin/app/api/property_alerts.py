"""
Property Alerts API endpoints
Handles property listing creation, image uploads, and sending alerts to subscribers
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.utils.database import get_db
from app.models.property_alert import PropertyAlert, PropertyImage
from app.models.agent import Agent, PlanTier
from app.middleware.auth import get_current_agent
from app.services.spaces_service import spaces_service

router = APIRouter()

# Pydantic models
class PropertyAlertCreate(BaseModel):
    address: str
    price: int
    square_feet: Optional[int] = None
    bedrooms: int
    bathrooms: float
    description: str
    mls_link: Optional[str] = None
    is_hot: bool = False
    
    @validator('bedrooms')
    def validate_bedrooms(cls, v):
        if v < 0 or v > 20:
            raise ValueError('Bedrooms must be between 0 and 20')
        return v
    
    @validator('bathrooms')
    def validate_bathrooms(cls, v):
        if v < 0 or v > 20:
            raise ValueError('Bathrooms must be between 0 and 20')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price must be positive')
        return v

class PropertyAlertUpdate(BaseModel):
    address: Optional[str] = None
    price: Optional[int] = None
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    description: Optional[str] = None
    mls_link: Optional[str] = None
    is_hot: Optional[bool] = None

class PropertyAlertResponse(BaseModel):
    id: str
    address: str
    price: int
    square_feet: Optional[int]
    bedrooms: int
    bathrooms: float
    description: str
    mls_link: Optional[str]
    is_hot: bool
    sent_at: Optional[datetime]
    email_sent_count: int
    sms_sent_count: int
    images: List[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SubscriberCount(BaseModel):
    vip_sms: int
    email: int
    total: int

class PlanLimits(BaseModel):
    alerts_this_month: int
    max_alerts_per_month: Optional[int]  # None = unlimited
    can_create_more: bool
    remaining: Optional[int]


@router.get("/limits", response_model=PlanLimits)
async def get_plan_limits(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get property alert limits for current agent's plan"""
    
    # Count alerts created this month
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(func.count(PropertyAlert.id))
        .where(
            and_(
                PropertyAlert.agent_id == agent.id,
                PropertyAlert.created_at >= current_month
            )
        )
    )
    alerts_this_month = result.scalar() or 0
    
    # Determine limits based on plan
    if agent.plan_tier in [PlanTier.TRIAL, 'trial']:
        max_alerts = 5
        can_create = alerts_this_month < max_alerts
        remaining = max_alerts - alerts_this_month
    else:
        # Pro, Growth, Scale plans = unlimited
        max_alerts = None
        can_create = True
        remaining = None
    
    return PlanLimits(
        alerts_this_month=alerts_this_month,
        max_alerts_per_month=max_alerts,
        can_create_more=can_create,
        remaining=remaining
    )


@router.get("/subscribers/count", response_model=SubscriberCount)
async def get_subscriber_count(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get count of subscribers who will receive property alerts"""
    
    # Import here to avoid circular dependency
    from app.models.capture_page import CapturePage
    
    # Count total email subscribers (anyone who signed up for listing alerts)
    email_result = await db.execute(
        select(func.count(CapturePage.id))
        .where(
            and_(
                CapturePage.agent_id == agent.id,
                CapturePage.kind == 'listing_alerts'
            )
        )
    )
    email_count = email_result.scalar() or 0
    
    # Count VIP SMS subscribers (those who opted in for SMS)
    # Note: This would need a subscriber table with sms_opt_in field
    # For now, we'll return 0 and you can implement this when subscriber table is ready
    vip_sms_count = 0
    
    return SubscriberCount(
        vip_sms=vip_sms_count,
        email=email_count,
        total=email_count + vip_sms_count
    )


@router.post("/", response_model=PropertyAlertResponse)
async def create_property_alert(
    property_data: PropertyAlertCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Create a new property alert"""
    
    # Check plan limits
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(func.count(PropertyAlert.id))
        .where(
            and_(
                PropertyAlert.agent_id == agent.id,
                PropertyAlert.created_at >= current_month
            )
        )
    )
    alerts_this_month = result.scalar() or 0
    
    # Check limits for trial plans
    if agent.plan_tier in [PlanTier.TRIAL, 'trial'] and alerts_this_month >= 5:
        raise HTTPException(
            status_code=403,
            detail="You've reached your limit of 5 property alerts per month. Upgrade to Pro for unlimited alerts."
        )
    
    # Create property alert
    property_alert = PropertyAlert(
        agent_id=agent.id,
        address=property_data.address,
        price=property_data.price,
        square_feet=property_data.square_feet,
        bedrooms=property_data.bedrooms,
        bathrooms=Decimal(str(property_data.bathrooms)),
        description=property_data.description,
        mls_link=property_data.mls_link,
        is_hot=property_data.is_hot
    )
    
    db.add(property_alert)
    await db.commit()
    await db.refresh(property_alert)
    
    return PropertyAlertResponse(
        id=str(property_alert.id),
        address=property_alert.address,
        price=property_alert.price,
        square_feet=property_alert.square_feet,
        bedrooms=property_alert.bedrooms,
        bathrooms=float(property_alert.bathrooms),
        description=property_alert.description,
        mls_link=property_alert.mls_link,
        is_hot=property_alert.is_hot,
        sent_at=property_alert.sent_at,
        email_sent_count=property_alert.email_sent_count,
        sms_sent_count=property_alert.sms_sent_count,
        images=[],
        created_at=property_alert.created_at
    )


@router.get("/", response_model=List[PropertyAlertResponse])
async def list_property_alerts(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """List all property alerts for current agent"""
    
    result = await db.execute(
        select(PropertyAlert)
        .where(PropertyAlert.agent_id == agent.id)
        .order_by(PropertyAlert.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    properties = result.scalars().all()
    
    # Fetch images for each property
    response_list = []
    for prop in properties:
        images_result = await db.execute(
            select(PropertyImage)
            .where(PropertyImage.property_id == prop.id)
            .order_by(PropertyImage.display_order)
        )
        images = images_result.scalars().all()
        
        response_list.append(PropertyAlertResponse(
            id=str(prop.id),
            address=prop.address,
            price=prop.price,
            square_feet=prop.square_feet,
            bedrooms=prop.bedrooms,
            bathrooms=float(prop.bathrooms),
            description=prop.description,
            mls_link=prop.mls_link,
            is_hot=prop.is_hot,
            sent_at=prop.sent_at,
            email_sent_count=prop.email_sent_count,
            sms_sent_count=prop.sms_sent_count,
            images=[{
                'id': str(img.id),
                'image_url': img.image_url,
                'thumbnail_url': img.thumbnail_url,
                'display_order': img.display_order
            } for img in images],
            created_at=prop.created_at
        ))
    
    return response_list


@router.get("/{property_id}", response_model=PropertyAlertResponse)
async def get_property_alert(
    property_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific property alert"""
    
    result = await db.execute(
        select(PropertyAlert)
        .where(
            and_(
                PropertyAlert.id == property_id,
                PropertyAlert.agent_id == agent.id
            )
        )
    )
    prop = result.scalar_one_or_none()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property alert not found")
    
    # Fetch images
    images_result = await db.execute(
        select(PropertyImage)
        .where(PropertyImage.property_id == prop.id)
        .order_by(PropertyImage.display_order)
    )
    images = images_result.scalars().all()
    
    return PropertyAlertResponse(
        id=str(prop.id),
        address=prop.address,
        price=prop.price,
        square_feet=prop.square_feet,
        bedrooms=prop.bedrooms,
        bathrooms=float(prop.bathrooms),
        description=prop.description,
        mls_link=prop.mls_link,
        is_hot=prop.is_hot,
        sent_at=prop.sent_at,
        email_sent_count=prop.email_sent_count,
        sms_sent_count=prop.sms_sent_count,
        images=[{
            'id': str(img.id),
            'image_url': img.image_url,
            'thumbnail_url': img.thumbnail_url,
            'display_order': img.display_order
        } for img in images],
        created_at=prop.created_at
    )


@router.post("/{property_id}/photos")
async def upload_property_photo(
    property_id: str,
    photo: UploadFile = File(...),
    display_order: int = Form(0),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Upload a photo for a property alert (max 5 photos)"""
    
    # Verify property belongs to agent
    result = await db.execute(
        select(PropertyAlert)
        .where(
            and_(
                PropertyAlert.id == property_id,
                PropertyAlert.agent_id == agent.id
            )
        )
    )
    prop = result.scalar_one_or_none()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property alert not found")
    
    # Check if already has 5 photos
    count_result = await db.execute(
        select(func.count(PropertyImage.id))
        .where(PropertyImage.property_id == property_id)
    )
    photo_count = count_result.scalar() or 0
    
    if photo_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos per property")
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await photo.read()
    
    # Validate file size (10MB max)
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be less than 10MB")
    
    try:
        # Generate unique filename
        filename = spaces_service.generate_unique_filename(
            photo.filename,
            prefix=f"prop-{property_id[:8]}-{photo_count + 1:03d}"
        )
        
        # Upload to Spaces
        folder = f"properties/{agent.slug}"
        full_url, thumbnail_url, metadata = spaces_service.upload_image(
            file_data=file_data,
            folder=folder,
            filename=filename,
            content_type=photo.content_type
        )
        
        # Save to database
        property_image = PropertyImage(
            property_id=property_id,
            image_url=full_url,
            thumbnail_url=thumbnail_url,
            file_size=metadata.get('file_size'),
            width=metadata.get('final_width'),
            height=metadata.get('final_height'),
            display_order=display_order
        )
        
        db.add(property_image)
        await db.commit()
        await db.refresh(property_image)
        
        return {
            "success": True,
            "image_id": str(property_image.id),
            "image_url": property_image.image_url,
            "thumbnail_url": property_image.thumbnail_url,
            "display_order": property_image.display_order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.delete("/{property_id}/photos/{photo_id}")
async def delete_property_photo(
    property_id: str,
    photo_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Delete a property photo"""
    
    # Verify property belongs to agent
    result = await db.execute(
        select(PropertyAlert)
        .where(
            and_(
                PropertyAlert.id == property_id,
                PropertyAlert.agent_id == agent.id
            )
        )
    )
    prop = result.scalar_one_or_none()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property alert not found")
    
    # Get the photo
    photo_result = await db.execute(
        select(PropertyImage)
        .where(
            and_(
                PropertyImage.id == photo_id,
                PropertyImage.property_id == property_id
            )
        )
    )
    photo = photo_result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Delete from Spaces
    spaces_service.delete_image(photo.image_url)
    
    # Delete from database
    await db.delete(photo)
    await db.commit()
    
    return {"success": True, "message": "Photo deleted"}


@router.delete("/{property_id}")
async def delete_property_alert(
    property_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Delete a property alert and all its photos"""
    
    # Get property
    result = await db.execute(
        select(PropertyAlert)
        .where(
            and_(
                PropertyAlert.id == property_id,
                PropertyAlert.agent_id == agent.id
            )
        )
    )
    prop = result.scalar_one_or_none()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property alert not found")
    
    # Get all images
    images_result = await db.execute(
        select(PropertyImage)
        .where(PropertyImage.property_id == property_id)
    )
    images = images_result.scalars().all()
    
    # Delete images from Spaces
    for img in images:
        spaces_service.delete_image(img.image_url)
    
    # Delete property (cascade will delete images from DB)
    await db.delete(prop)
    await db.commit()
    
    return {"success": True, "message": "Property alert deleted"}


@router.post("/{property_id}/send")
async def send_property_alert(
    property_id: str,
    background_tasks: BackgroundTasks,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Send property alert to all subscribers"""
    
    # Get property
    result = await db.execute(
        select(PropertyAlert)
        .where(
            and_(
                PropertyAlert.id == property_id,
                PropertyAlert.agent_id == agent.id
            )
        )
    )
    prop = result.scalar_one_or_none()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property alert not found")
    
    if prop.sent_at:
        raise HTTPException(status_code=400, detail="This property alert has already been sent")
    
    # Get images
    images_result = await db.execute(
        select(PropertyImage)
        .where(PropertyImage.property_id == property_id)
        .order_by(PropertyImage.display_order)
    )
    images = images_result.scalars().all()
    
    # Queue sending in background
    background_tasks.add_task(
        send_alert_to_subscribers,
        property_id=str(prop.id),
        agent_id=str(agent.id),
        is_hot=prop.is_hot
    )
    
    # Mark as sent
    prop.sent_at = datetime.now()
    await db.commit()
    
    return {
        "success": True,
        "message": "Property alert is being sent to subscribers",
        "sent_at": prop.sent_at
    }


async def send_alert_to_subscribers(property_id: str, agent_id: str, is_hot: bool):
    """Background task to send alerts via email/SMS"""
    try:
        from app.utils.database import get_async_session
        
        async with get_async_session() as db:
            # Get property and agent
            prop_result = await db.execute(
                select(PropertyAlert).where(PropertyAlert.id == property_id)
            )
            prop = prop_result.scalar_one_or_none()
            
            agent_result = await db.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = agent_result.scalar_one_or_none()
            
            if not prop or not agent:
                return
            
            # Get images
            images_result = await db.execute(
                select(PropertyImage)
                .where(PropertyImage.property_id == property_id)
                .order_by(PropertyImage.display_order)
            )
            images = images_result.scalars().all()
            
            # TODO: Implement email sending via Brevo
            # TODO: Implement SMS sending via Twilio (if is_hot)
            
            # Update counts
            prop.email_sent_count = 10  # Placeholder - replace with actual count
            prop.sms_sent_count = 5 if is_hot else 0  # Placeholder
            await db.commit()
            
            print(f"[PROPERTY ALERT] Sent alert for property {property_id}")
            
    except Exception as e:
        print(f"[PROPERTY ALERT] Error sending alert: {e}")

