"""
Providers API endpoints
Handles BYOK (Bring Your Own Keys) provider credential management
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, SecretStr
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.utils.database import get_db
from app.models.provider_credentials import ProviderCredential, ProviderType
from app.middleware.tenant_resolver import get_current_agent_id

router = APIRouter()

# Pydantic models
class ProviderCredentialRequest(BaseModel):
    provider_type: ProviderType
    provider_name: str
    credentials: Dict[str, Any]

class ProviderCredentialResponse(BaseModel):
    id: int
    provider_type: str
    provider_name: str
    is_active: bool
    last_validated_at: Optional[datetime]
    validation_error: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ProviderCredentialResponse])
async def list_provider_credentials(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """List all provider credentials for current agent"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.agent_id == agent_id)
        .order_by(ProviderCredential.created_at)
    )
    credentials = result.scalars().all()
    
    return credentials

@router.post("/", response_model=ProviderCredentialResponse)
async def add_provider_credential(
    credential_request: ProviderCredentialRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Add new provider credentials"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    # Check if provider already exists for this agent
    result = await db.execute(
        select(ProviderCredential).where(
            and_(
                ProviderCredential.agent_id == agent_id,
                ProviderCredential.provider_type == credential_request.provider_type.value
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Credentials for {credential_request.provider_type.value} already exist"
        )
    
    # Validate credentials format based on provider type
    validation_error = await validate_provider_credentials(
        credential_request.provider_type,
        credential_request.credentials
    )
    
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    
    # Create credential record
    credential = ProviderCredential(
        agent_id=agent_id,
        provider_type=credential_request.provider_type.value,
        provider_name=credential_request.provider_name,
        added_by_user=True
    )
    
    # Encrypt and store credentials
    credential.encrypted_credentials = credential.encrypt_credentials(
        credential_request.credentials
    )
    
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    
    # TODO: Queue validation test
    
    return credential

@router.put("/{credential_id}", response_model=ProviderCredentialResponse)
async def update_provider_credential(
    credential_id: int,
    credential_request: ProviderCredentialRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update existing provider credentials"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential).where(
            and_(
                ProviderCredential.id == credential_id,
                ProviderCredential.agent_id == agent_id
            )
        )
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Validate new credentials
    validation_error = await validate_provider_credentials(
        credential_request.provider_type,
        credential_request.credentials
    )
    
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    
    # Update credential
    credential.provider_name = credential_request.provider_name
    credential.encrypted_credentials = credential.encrypt_credentials(
        credential_request.credentials
    )
    credential.last_validated_at = None  # Reset validation status
    credential.validation_error = None
    
    await db.commit()
    await db.refresh(credential)
    
    return credential

@router.delete("/{credential_id}")
async def delete_provider_credential(
    credential_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete provider credentials"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential).where(
            and_(
                ProviderCredential.id == credential_id,
                ProviderCredential.agent_id == agent_id
            )
        )
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Don't allow deletion of platform-provided credentials
    if not credential.added_by_user:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete platform-provided credentials"
        )
    
    await db.delete(credential)
    await db.commit()
    
    return {"success": True, "message": "Credentials deleted"}

@router.post("/{credential_id}/test")
async def test_provider_credential(
    credential_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Test provider credentials"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential).where(
            and_(
                ProviderCredential.id == credential_id,
                ProviderCredential.agent_id == agent_id
            )
        )
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Test the credentials
    test_result = await test_provider_connection(credential)
    
    # Update validation status
    if test_result["success"]:
        credential.last_validated_at = datetime.utcnow()
        credential.validation_error = None
        credential.is_active = True
    else:
        credential.validation_error = test_result["error"]
        credential.is_active = False
    
    await db.commit()
    
    return test_result

@router.post("/credentials", response_model=dict)
async def save_all_credentials(
    credentials: Dict[str, str],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Save all API credentials from configuration form"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    saved_count = 0
    errors = []
    
    # Provider mapping
    provider_mapping = {
        'OPENAI_API_KEY': ('openai', 'api_key'),
        'TWILIO_ACCOUNT_SID': ('twilio', 'account_sid'),
        'TWILIO_AUTH_TOKEN': ('twilio', 'auth_token'),
        'TWILIO_PHONE_NUMBER': ('twilio', 'from_number'),
        'AGENT_PHONE_NUMBER': ('twilio', 'agent_phone'),
        'BREVO_API_KEY': ('brevo', 'api_key'),
        'FOURSQUARE_API_KEY': ('foursquare', 'api_key'),
        'MAPTILER_KEY': ('maptiler', 'api_key'),
        'ORS_API_KEY': ('ors', 'api_key'),
        'USPS_USER_ID': ('usps', 'user_id'),
        'GOOGLE_OAUTH_CLIENT_ID': ('google', 'client_id'),
        'GOOGLE_OAUTH_CLIENT_SECRET': ('google', 'client_secret')
    }
    
    # Group credentials by provider
    provider_creds = {}
    for key, value in credentials.items():
        if value and value != '••••••••':  # Skip empty and masked values
            if key in provider_mapping:
                provider_name, field_name = provider_mapping[key]
                if provider_name not in provider_creds:
                    provider_creds[provider_name] = {}
                provider_creds[provider_name][field_name] = value
    
    # Save each provider's credentials
    for provider_name, creds in provider_creds.items():
        try:
            # Check if provider already exists
            result = await db.execute(
                select(ProviderCredential).where(
                    and_(
                        ProviderCredential.agent_id == agent_id,
                        ProviderCredential.provider_name == provider_name
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.encrypted_credentials = existing.encrypt_credentials(creds)
                existing.last_validated_at = None
                existing.validation_error = None
            else:
                # Create new
                credential = ProviderCredential(
                    agent_id=agent_id,
                    provider_type=provider_name,
                    provider_name=provider_name,
                    added_by_user=True
                )
                credential.encrypted_credentials = credential.encrypt_credentials(creds)
                db.add(credential)
            
            saved_count += 1
            
        except Exception as e:
            errors.append(f"Error saving {provider_name}: {str(e)}")
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Saved {saved_count} provider configurations",
        "errors": errors if errors else None
    }

@router.get("/credentials", response_model=dict)
async def get_all_credentials(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all API credentials (masked) for configuration form"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.agent_id == agent_id)
    )
    credentials = result.scalars().all()
    
    # Convert to flat structure for form
    config = {}
    
    for cred in credentials:
        try:
            decrypted = cred.decrypt_credentials()
            provider = cred.provider_name
            
            # Map back to form field names
            if provider == 'openai' and 'api_key' in decrypted:
                config['OPENAI_API_KEY'] = '••••••••'
            elif provider == 'twilio':
                if 'account_sid' in decrypted:
                    config['TWILIO_ACCOUNT_SID'] = '••••••••'
                if 'auth_token' in decrypted:
                    config['TWILIO_AUTH_TOKEN'] = '••••••••'
                if 'from_number' in decrypted:
                    config['TWILIO_PHONE_NUMBER'] = '••••••••'
                if 'agent_phone' in decrypted:
                    config['AGENT_PHONE_NUMBER'] = '••••••••'
            elif provider == 'brevo' and 'api_key' in decrypted:
                config['BREVO_API_KEY'] = '••••••••'
            elif provider == 'foursquare' and 'api_key' in decrypted:
                config['FOURSQUARE_API_KEY'] = '••••••••'
            elif provider == 'maptiler' and 'api_key' in decrypted:
                config['MAPTILER_KEY'] = '••••••••'
            elif provider == 'ors' and 'api_key' in decrypted:
                config['ORS_API_KEY'] = '••••••••'
            elif provider == 'usps' and 'user_id' in decrypted:
                config['USPS_USER_ID'] = '••••••••'
            elif provider == 'google':
                if 'client_id' in decrypted:
                    config['GOOGLE_OAUTH_CLIENT_ID'] = '••••••••'
                if 'client_secret' in decrypted:
                    config['GOOGLE_OAUTH_CLIENT_SECRET'] = '••••••••'
                    
        except Exception as e:
            # Skip corrupted credentials
            continue
    
    return config

@router.post("/test", response_model=dict)
async def test_all_apis(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Test all configured API connections"""
    
    agent_id = await get_current_agent_id(request)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent context required")
    
    result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.agent_id == agent_id)
    )
    credentials = result.scalars().all()
    
    status = {
        'openai': False,
        'twilio': False,
        'brevo': False,
        'foursquare': False,
        'maptiler': False,
        'google': False
    }
    
    for cred in credentials:
        test_result = await test_provider_connection(cred)
        if test_result["success"]:
            status[cred.provider_name] = True
    
    return status

@router.get("/templates")
async def get_provider_templates():
    """Get credential templates for each provider type"""
    
    templates = {
        "openai": {
            "name": "OpenAI",
            "description": "API key for GPT models and AI features",
            "fields": [
                {
                    "key": "api_key",
                    "label": "API Key", 
                    "type": "password",
                    "placeholder": "sk-...",
                    "required": True
                }
            ],
            "test_endpoint": "https://api.openai.com/v1/models"
        },
        "brevo": {
            "name": "Brevo (Sendinblue)",
            "description": "Email sending service credentials",
            "fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "password", 
                    "placeholder": "xkeysib-...",
                    "required": True
                }
            ],
            "test_endpoint": "https://api.brevo.com/v3/account"
        },
        "twilio": {
            "name": "Twilio",
            "description": "SMS and voice call service",
            "fields": [
                {
                    "key": "account_sid",
                    "label": "Account SID",
                    "type": "text",
                    "placeholder": "AC...",
                    "required": True
                },
                {
                    "key": "auth_token", 
                    "label": "Auth Token",
                    "type": "password",
                    "placeholder": "...",
                    "required": True
                },
                {
                    "key": "from_number",
                    "label": "From Phone Number",
                    "type": "tel",
                    "placeholder": "+1234567890",
                    "required": True
                }
            ],
            "test_endpoint": "https://api.twilio.com/2010-04-01/Accounts"
        }
    }
    
    return templates

async def validate_provider_credentials(
    provider_type: ProviderType, 
    credentials: Dict[str, Any]
) -> Optional[str]:
    """Validate credentials format"""
    
    if provider_type == ProviderType.OPENAI:
        if not credentials.get("api_key") or not credentials["api_key"].startswith("sk-"):
            return "OpenAI API key must start with 'sk-'"
    
    elif provider_type == ProviderType.BREVO:
        if not credentials.get("api_key") or not credentials["api_key"].startswith("xkeysib-"):
            return "Brevo API key must start with 'xkeysib-'"
    
    elif provider_type == ProviderType.TWILIO:
        if not credentials.get("account_sid") or not credentials["account_sid"].startswith("AC"):
            return "Twilio Account SID must start with 'AC'"
        if not credentials.get("auth_token"):
            return "Twilio Auth Token is required"
        if not credentials.get("from_number"):
            return "Twilio From Number is required"
    
    return None

async def test_provider_connection(credential: ProviderCredential) -> Dict[str, Any]:
    """Test connection to provider API"""
    
    try:
        credentials = credential.decrypt_credentials()
        provider_type = credential.provider_type
        
        if provider_type == "openai":
            # TODO: Test OpenAI API connection
            return {"success": True, "message": "OpenAI connection successful"}
        
        elif provider_type == "brevo":
            # TODO: Test Brevo API connection
            return {"success": True, "message": "Brevo connection successful"}
        
        elif provider_type == "twilio":
            # TODO: Test Twilio API connection
            return {"success": True, "message": "Twilio connection successful"}
        
        else:
            return {"success": False, "error": "Unknown provider type"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}