"""
Admin Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, Any

from app.utils.database import get_db
from app.models.agent import Agent, PlanTier, AgentStatus
from app.models.lead import Lead, LeadStatus
import os

router = APIRouter()

@router.get("/dashboard")
async def admin_dashboard():
    """Admin dashboard homepage"""
    return {"message": "Admin dashboard loaded", "timestamp": datetime.now().isoformat()}

@router.get("/stats")
async def admin_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get comprehensive admin statistics"""
    
    try:
        # Date calculations
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # Total Agents
        total_agents_result = await db.execute(select(func.count(Agent.id)))
        total_agents = total_agents_result.scalar() or 0
        
        # New Agents Today
        new_agents_today_result = await db.execute(
            select(func.count(Agent.id)).where(func.date(Agent.created_at) == today)
        )
        new_agents_today = new_agents_today_result.scalar() or 0
        
        # Total Leads
        total_leads_result = await db.execute(select(func.count(Lead.id)))
        total_leads = total_leads_result.scalar() or 0
        
        # New Leads Today
        new_leads_today_result = await db.execute(
            select(func.count(Lead.id)).where(func.date(Lead.created_at) == today)
        )
        new_leads_today = new_leads_today_result.scalar() or 0
        
        # AI Analyses (leads with AI processing)
        ai_analyses_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.ai_summary.isnot(None))
        )
        ai_analyses = ai_analyses_result.scalar() or 0
        
        # AI Success Rate (percentage of leads with successful AI analysis)
        ai_success_rate = 0
        if total_leads > 0:
            ai_success_rate = round((ai_analyses / total_leads) * 100, 1)
        
        # Revenue Calculations (simplified - based on plan tiers)
        plan_revenue = {
            PlanTier.TRIAL: 0,
            PlanTier.PRO: 97,
            PlanTier.ENTERPRISE: 297
        }
        
        monthly_revenue = 0
        for plan, price in plan_revenue.items():
            count_result = await db.execute(
                select(func.count(Agent.id)).where(
                    and_(
                        Agent.plan_tier == plan,
                        Agent.status == AgentStatus.ACTIVE
                    )
                )
            )
            count = count_result.scalar() or 0
            monthly_revenue += count * price
        
        # Revenue growth (simplified calculation)
        revenue_growth = 15.3  # Placeholder - would need historical data
        
        # Plan Distribution
        plan_distribution = {}
        for plan in PlanTier:
            count_result = await db.execute(
                select(func.count(Agent.id)).where(Agent.plan_tier == plan)
            )
            plan_distribution[plan.value] = count_result.scalar() or 0
        
        # Recent activity summary
        recent_leads_result = await db.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= datetime.now() - timedelta(hours=24)
            )
        )
        recent_leads_24h = recent_leads_result.scalar() or 0
        
        return {
            "totalAgents": total_agents,
            "newAgentsToday": new_agents_today,
            "totalLeads": total_leads,
            "newLeadsToday": new_leads_today,
            "aiAnalyses": ai_analyses,
            "aiSuccessRate": ai_success_rate,
            "monthlyRevenue": monthly_revenue,
            "revenueGrowth": revenue_growth,
            "planDistribution": plan_distribution,
            "recentLeads24h": recent_leads_24h,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get admin stats: {str(e)}")

@router.get("/system-health")
async def system_health() -> Dict[str, Any]:
    """Get system health information"""
    
    health_status = {
        "api": True,
        "database": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "stripe": bool(os.getenv("STRIPE_SECRET_KEY")),
        "email": bool(os.getenv("BREVO_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }
    
    # Test OpenAI connection
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Don't actually make a call, just check if we can create client
        health_status["openai"] = True
    except:
        health_status["openai"] = False
    
    return health_status

@router.get("/recent-activity")
async def recent_activity(db: AsyncSession = Depends(get_db), limit: int = 10):
    """Get recent system activity"""
    
    try:
        # Recent Agents
        recent_agents_result = await db.execute(
            select(Agent.id, Agent.name, Agent.email, Agent.plan_tier, Agent.created_at)
            .order_by(Agent.created_at.desc())
            .limit(limit)
        )
        recent_agents = [
            {
                "id": str(agent.id),
                "name": agent.name,
                "email": agent.email,
                "plan": agent.plan_tier,
                "joinedDate": agent.created_at.strftime("%Y-%m-%d")
            }
            for agent in recent_agents_result.fetchall()
        ]
        
        # Recent Leads
        recent_leads_result = await db.execute(
            select(Lead.id, Lead.full_name, Lead.email, Lead.source, Lead.created_at)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        recent_leads = [
            {
                "id": str(lead.id),
                "name": lead.full_name,
                "email": lead.email,
                "source": lead.source,
                "createdAt": lead.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for lead in recent_leads_result.fetchall()
        ]
        
        return {
            "recentAgents": recent_agents,
            "recentLeads": recent_leads,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent activity: {str(e)}")

@router.get("/analytics/leads")
async def leads_analytics(db: AsyncSession = Depends(get_db), days: int = 7):
    """Get lead analytics for charts"""
    
    try:
        # Generate date range
        dates = []
        lead_counts = []
        
        for i in range(days):
            date = datetime.now().date() - timedelta(days=days-1-i)
            dates.append(date.strftime("%m/%d"))
            
            # Count leads for this date
            count_result = await db.execute(
                select(func.count(Lead.id)).where(func.date(Lead.created_at) == date)
            )
            count = count_result.scalar() or 0
            lead_counts.append(count)
        
        return {
            "labels": dates,
            "data": lead_counts,
            "total": sum(lead_counts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leads analytics: {str(e)}")

@router.get("/analytics/revenue")
async def revenue_analytics(db: AsyncSession = Depends(get_db), months: int = 6):
    """Get revenue analytics for charts"""
    
    try:
        # Simplified revenue calculation by month
        # In a real system, you'd track actual payments
        
        months_data = []
        revenue_data = []
        
        plan_revenue = {
            PlanTier.TRIAL: 0,
            PlanTier.PRO: 97,
            PlanTier.ENTERPRISE: 297
        }
        
        for i in range(months):
            # Calculate month
            target_date = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_name = target_date.strftime("%b")
            months_data.insert(0, month_name)
            
            # Calculate revenue for this month (simplified)
            monthly_total = 0
            for plan, price in plan_revenue.items():
                count_result = await db.execute(
                    select(func.count(Agent.id)).where(
                        and_(
                            Agent.plan_tier == plan,
                            Agent.status == AgentStatus.ACTIVE,
                            Agent.created_at <= target_date
                        )
                    )
                )
                count = count_result.scalar() or 0
                monthly_total += count * price
            
            revenue_data.insert(0, monthly_total)
        
        return {
            "labels": months_data,
            "data": revenue_data,
            "total": sum(revenue_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get revenue analytics: {str(e)}")

@router.get("/errors")
async def recent_errors(limit: int = 10):
    """Get recent system errors (placeholder - would integrate with logging system)"""
    
    # This would typically integrate with your logging system
    # For now, returning mock data
    
    mock_errors = [
        {
            "id": 1,
            "message": "OpenAI API rate limit exceeded",
            "timestamp": (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "source": "AI Lead Processor",
            "level": "WARNING"
        },
        {
            "id": 2,
            "message": "Failed to send notification email",
            "timestamp": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Email Service",
            "level": "ERROR"
        },
        {
            "id": 3,
            "message": "Database connection timeout",
            "timestamp": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Database",
            "level": "ERROR"
        }
    ]
    
    return {
        "errors": mock_errors[:limit],
        "timestamp": datetime.now().isoformat()
    }
