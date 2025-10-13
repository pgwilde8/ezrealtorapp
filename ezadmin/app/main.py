"""
EZRealtor.app - Main FastAPI Application
AI-Powered Lead Engine for Realtors
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import API routers
from app.api import leads, agents, domains, billing, providers, customization, stripe_webhook, checkout
from app.api.admin import tenants, plans, webhooks, dashboard
from app.middleware.tenant_resolver import TenantMiddleware
from app.utils.database import engine, create_tables, get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await create_tables()
    yield
    # Shutdown
    await engine.dispose()

# Initialize FastAPI app
app = FastAPI(
    title="EZRealtor.app",
    description="AI-Powered Lead Engine for Realtors",
    version="1.0.0",
    docs_url="/api/docs" if os.getenv("DEBUG", "false").lower() == "true" else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

# Templates
templates = Jinja2Templates(directory="app/templates")

# Static files (for CSS, JS, images)
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API Routes
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(domains.router, prefix="/api/v1/domains", tags=["domains"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])
app.include_router(customization.router, prefix="/api/v1", tags=["customization"])
app.include_router(stripe_webhook.router, prefix="/api/v1", tags=["stripe"])
app.include_router(checkout.router, prefix="", tags=["checkout"])

# Admin Routes
app.include_router(tenants.router, prefix="/admin/tenants", tags=["admin-tenants"])
app.include_router(plans.router, prefix="/admin/plans", tags=["admin-plans"])
app.include_router(webhooks.router, prefix="/admin/webhooks", tags=["admin-webhooks"])
app.include_router(dashboard.router, prefix="/admin", tags=["admin-dashboard"])

# Root routes
@app.get("/")
async def homepage(request: Request):
    """Marketing homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/lead-buyer")
async def lead_buyer_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Buyer interest lead capture form"""
    # Get agent context from tenant middleware
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    
    # Get full agent data for customization
    agent = None
    if tenant_slug:
        from sqlalchemy import select
        from app.models.agent import Agent
        result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
        agent = result.scalar_one_or_none()
    
    return templates.TemplateResponse("lead-buyer.html", {
        "request": request,
        "agent": agent
    })

@app.get("/lead-home-value")
async def lead_home_value_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Home valuation lead capture form"""
    # Get agent context from tenant middleware
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    
    # Get full agent data for customization
    agent = None
    if tenant_slug:
        from sqlalchemy import select
        from app.models.agent import Agent
        result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
        agent = result.scalar_one_or_none()
    
    return templates.TemplateResponse("lead-home-value.html", {
        "request": request,
        "agent": agent
    })

@app.get("/pricing")
async def pricing_page(request: Request):
    """Pricing plans page"""
    return templates.TemplateResponse("pricing.html", {"request": request})

@app.get("/config")
async def config_page(request: Request):
    """Agent configuration page for API keys"""
    # Get agent context from tenant middleware
    agent_name = getattr(request.state, 'agent_name', None)
    agent_id = getattr(request.state, 'agent_id', None)
    
    return templates.TemplateResponse("config.html", {
        "request": request,
        "agent_name": agent_name,
        "agent_id": agent_id
    })

@app.get("/customize")
async def customize_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Agent customization dashboard"""
    # Get agent context from tenant middleware
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    
    # Get full agent data for customization
    agent = None
    if tenant_slug:
        from sqlalchemy import select
        from app.models.agent import Agent
        result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
        agent = result.scalar_one_or_none()
    
    return templates.TemplateResponse("customize.html", {
        "request": request,
        "agent": agent
    })

@app.get("/billing")
async def billing_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Billing and subscription management page"""
    # Get agent context from tenant middleware
    tenant_slug = getattr(request.state, 'tenant_slug', None)
    
    # Get full agent data for billing context
    agent = None
    if tenant_slug:
        from sqlalchemy import select
        from app.models.agent import Agent
        result = await db.execute(select(Agent).where(Agent.slug == tenant_slug))
        agent = result.scalar_one_or_none()
    
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "agent": agent
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ezrealtor-api"}

@app.get("/api/v1/health")
async def api_health():
    """API health check"""
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/v1/test-db")
async def test_database(db: AsyncSession = Depends(get_db)):
    """Test database connection and Agent model"""
    try:
        from sqlalchemy import select
        from app.models.agent import Agent
        
        # Test basic query
        result = await db.execute(select(Agent).where(Agent.email == "nonexistent@test.com"))
        agent = result.scalar_one_or_none()
        
        return {"status": "success", "agent_found": agent is not None}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/v1/debug-env")
async def debug_environment():
    """Debug endpoint to check environment variables"""
    return {
        "stripe_secret_key": "LOADED" if os.getenv("STRIPE_SECRET_KEY") else "NOT_FOUND",
        "stripe_free_price": os.getenv("STRIPE_FREE_PRICE_ID", "NOT_FOUND"),
        "stripe_basic_price": os.getenv("STRIPE_BASIC_PRICE_ID", "NOT_FOUND"),
        "stripe_pro_price": os.getenv("STRIPE_PRO_PRICE_ID", "NOT_FOUND"),
    }

@app.post("/api/v1/test-stripe")
async def test_stripe():
    """Test Stripe connection"""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Try to create a simple customer
        customer = stripe.Customer.create(
            email="test-stripe@example.com",
            name="Test Customer"
        )
        
        return {"status": "success", "customer_id": customer.id}
    except Exception as e:
        return {"status": "error", "error": str(e), "error_type": str(type(e))}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8011")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )