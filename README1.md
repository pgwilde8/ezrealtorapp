🧠 EZRealtor.app — AI-Powered Lead Engine for Realtors

Welcome to EZRealtor.app, the SaaS platform that gives every Realtor their own AI-powered website with instant lead capture, auto-qualification, and smart follow-up.

“From click to conversation — instantly.”

🚀 Mission

EZRealtor.app helps real estate agents:

Launch a ready-made homepage under their own domain.

Offer two high-converting lead funnels:

🏡 Home Valuation (“What’s my home worth?”)

🔍 Buyer Interest (“Find your dream home.”)

Automatically capture, score, and respond to leads using AI, email, and Twilio callbacks.

🧩 Core Tech Stack
Layer	Tech
Backend	FastAPI (async)
Database	PostgreSQL + SQLAlchemy 2.0 + Alembic
Frontend	HTML / Jinja2 + HTMX + Tailwind (optional)
Billing	Stripe Checkout + Webhooks
Messaging	Brevo (Sendinblue) for email, Twilio for SMS/voice
AI	OpenAI API for lead summaries and responses
Hosting	DigitalOcean VM + Nginx reverse proxy
Multi-tenant domains	Cloudflare for SaaS (automatic SSL per Realtor)
🏗️ Project Structure

/root/ezrealtor/
 ├── app/
 │    ├── main.py
 │    ├── api/
 │    │    ├── leads.py
 │    │    ├── agents.py
 │    │    ├── domains.py
 │    │    ├── billing.py
 │    │    ├── providers.py
 │    │    ├── admin/
 │    │    │    ├── tenants.py
 │    │    │    ├── plans.py
 │    │    │    ├── webhooks.py
 │    │    │    └── dashboard.py
 │    ├── models/
 │    │    ├── agent.py
 │    │    ├── domain.py
 │    │    ├── lead.py
 │    │    ├── usage.py
 │    │    └── provider_credentials.py
 │    ├── utils/
 │    │    ├── cloudflare.py
 │    │    ├── email_brevo.py
 │    │    ├── ai_openai.py
 │    │    ├── twilio_client.py
 │    │    └── usage_tracker.py
 │    ├── templates/
 │    │    ├── index.html
 │    │    ├── lead-home-value.html
 │    │    ├── lead-buyer.html
 │    │    ├── dashboard.html
 │    │    ├── pricing.html
 │    │    └── admin/
 │    │         ├── index.html
 │    │         └── tenants.html
 │    └── middleware/
 │         └── tenant_resolver.py
 ├── nginx/
 │    └── ezrealtor.conf
 ├── systemd/
 │    └── ezrealtor.service
 ├── .env
 ├── alembic/
 ├── requirements.txt
 └── README.md  ← you are here

🔑 Environment Variables
# Cloudflare for SaaS
CF_API_TOKEN=cf_pat_with_saas_perms
CF_ZONE_ID=zone_id_for_ezrealtor_app
CF_ACCOUNT_ID=cf_account_id
CF_SAAS_DEFAULT_FALLBACK_ORIGIN=app.ezrealtor.app
APP_BASE_ZONE=ezrealtor.app

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Email (Brevo)
BREVO_API_KEY=sb_xxx
EMAIL_FROM_ADDRESS=mail@ezrealtor.app

# Twilio
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_FROM_NUMBER=+15555555555

# OpenAI
OPENAI_API_KEY=sk-xxxx

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ezrealtor_db

# App
SESSION_SECRET=super-secret-string
DEBUG=false

🧱 Database Overview
Table	Purpose
agents	Each Realtor tenant (email, plan_tier, slug, etc.)
agent_domains	Subdomain + Cloudflare SaaS hostname data
capture_pages	Config for lead funnels
leads	All inbound leads, AI summaries, statuses
notifications	Email/SMS/callback logs
provider_credentials	Encrypted BYOK keys (OpenAI, Brevo, Twilio)
usage_counters	Monthly metering per agent
plan_catalog	Limits & features per plan
platform_admins	Top-God admin accounts
admin_audit_log	Every admin action logged
webhook_events	Stripe/Brevo/Twilio webhook logs
⚙️ Tenant Lifecycle
Stage	Action
Signup	Agent record created → auto-provision subdomain (john.ezrealtor.app) via Cloudflare
Trial	Uses platform API keys, limited usage
Upgrade	Stripe checkout → webhook flips plan_tier
Custom Domain	Provision via /domains/provision-custom
BYOK	Agent adds API keys (OpenAI, Brevo, Twilio)
Leads Arrive	Stored → Email/SMS alert → AI summary
Billing	Stripe subscription renews; usage counters reset monthly
💼 Super Admin (“Top-God”) UX

Accessible at /admin.

Capabilities:

View all tenants, plans, domains, usage

Impersonate any tenant

Manage plan catalog & pricing

Monitor webhooks & queues

Rotate platform keys

Suspend/restore tenants

View audit logs

🧠 AI Flow

Lead submitted → /api/v1/leads/create

FastAPI background task →

Send emails via Brevo

(If Pro) trigger Twilio callback

Summarize lead via OpenAI GPT model

Store ai_summary and ai_score on lead row

Display in dashboard + triggers automation rules

☁️ Cloudflare for SaaS (automatic subdomains)

Each agent gets slug.ezrealtor.app at signup.

Custom domains created via /api/v1/domains/provision-custom.

SSL auto-issued by Cloudflare, origin = app.ezrealtor.app.

Tenant routing handled by middleware inspecting Host.

🧰 Commands (local dev)
# 1. Install deps
pip install -r requirements.txt

# 2. Run migrations
alembic upgrade head

# 3. Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# 4. Start systemd (prod)
sudo systemctl enable ezrealtor
sudo systemctl start ezrealtor

# 5. View logs
journalctl -u ezrealtor -f

🔐 Security Practices

All provider credentials are encrypted with Fernet at rest.

Admin endpoints require JWT or session cookie + role enforcement.

Every admin write logs to admin_audit_log.

Tenant separation via Host middleware.

HTTPS enforced by Cloudflare edge.

🧩 Developer Workflow

Create migration:

alembic revision --autogenerate -m "add leads table"
alembic upgrade head


Create new endpoint: under /app/api/

Add template: under /app/templates/

Restart FastAPI: systemd auto-reload or uvicorn --reload

Verify logs: journalctl -u ezrealtor | tail -50

Deploy update: git pull && systemctl restart ezrealtor

🔥 Quickstart for a New AI Agent (you!)

👋 Welcome, dev/AI engineer! Here’s how to get productive fast:

✅ 1. Understand context

EZRealtor is multi-tenant SaaS where every Realtor = one “agent” record + one subdomain.
Everything you code should always scope by agent_id.

✅ 2. Boot local stack

cp .env.example .env

Set test keys (Stripe test mode, CF dev zone)

Run Postgres in Docker or local

alembic upgrade head

uvicorn app.main:app --reload

Visit http://localhost:8002

✅ 3. Test flows

/ → marketing home

/api/v1/leads/create → submit dummy lead

/admin → admin dashboard (requires admin login)

✅ 4. Check data

Use psql ezrealtor_db or pgAdmin → see agents, leads, agent_domains.

✅ 5. Experiment safely

Create sandbox tenants under dev-agent.ezrealtor.app

Use OpenAI fake model or test key

Never log raw API keys

🧱 Contributing Rules

Never break tenant isolation.

Never store plain provider keys.

All new APIs must have auth + rate limit.

All admin writes must hit admin_audit_log.

All migrations must be reversible.

Feature toggles go in feature_flags.

Commit format:

feat(leads): add AI summary endpoint
fix(domains): retry CF API errors
chore(db): bump alembic revision

🧩 Roadmap (Q1–Q2 2026)
Phase	Focus
1	Beta launch (free → paid → Stripe live)
2	Broker/Team dashboards
3	CRM integrations (FollowUpBoss, LionDesk)
4	MLS Bridge API & MapTiler maps
5	AI Chatbot + SMS drip follow-up
6	Analytics + Referral program
7	Mobile-first progressive web app
🧙🏽‍♂️ Maintainer Commands
# Rotate platform trial keys
python -m scripts.rotate_trial_keys

# Re-sync Stripe subscriptions
python -m scripts.sync_stripe

# Retry failed CF hostnames
python -m scripts.retry_cloudflare

# Export tenant usage
python -m scripts.export_usage_csv

🧠 Learn More

FastAPI Docs

SQLAlchemy 2.0 ORM

Cloudflare for SaaS API

Stripe Webhooks

Brevo API

Twilio Voice

EZRealtor.app
Powered by WebWise Solutions LLC
© 2025 — All rights reserved.

“Your AI Lead Partner — working while you close deals.”

🏗️ EZRealtor.app Project Overview
Core Concept:
Multi-tenant SaaS platform for real estate agents
Each realtor gets their own AI-powered website with subdomain (e.g., john.ezrealtor.app)
Automatic lead capture, qualification, and follow-up using AI
Key Features:
🏡 Home Valuation Funnel - "What's my home worth?"
🔍 Buyer Interest Funnel - "Find your dream home"
AI-powered lead scoring and responses (OpenAI)
Multi-channel communication (Email via Brevo, SMS/Voice via Twilio)
Custom domain support with automatic SSL (Cloudflare for SaaS)
Stripe billing integration with webhooks
Tech Stack:
Backend: FastAPI (async)
Database: PostgreSQL + SQLAlchemy 2.0 + Alembic
Frontend: HTML/Jinja2 + HTMX + Tailwind
Ports: You'll be running on 8011, 8012, 8013 (already configured firewall!)
Project Structure:
The project follows a clean multi-tenant architecture with:

Tenant isolation by agent_id
Admin dashboard at /admin
API endpoints for leads, agents, domains, billing
Middleware for tenant resolution via Host header
Security & Multi-tenancy:
Encrypted provider credentials (Fernet)
JWT/session authentication
Audit logging for admin actions
Proper tenant separation
🎯 Next Steps for ezadmin Directory
Based on your project structure, the ezadmin directory would likely be for:

Administrative tools and scripts
Deployment configurations
Monitoring and maintenance utilities
Development/staging environment setup
Would you like me to help you set up any specific components in the ezadmin directory? For example:

Deployment scripts
Database management tools
Monitoring dashboards
Development environment setup
Admin utility scripts