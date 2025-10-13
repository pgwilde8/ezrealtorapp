# 🧱 Tenancy model (simple + safe)

Everything links to an `agent_id` (UUID). We’ll keep PII distinct, encrypt secrets, and index for the queries you’ll actually run.

---

## CORE (ship this first)

### 1) agents (one row per Realtor)

```sql
CREATE TABLE agents (
  id              UUID PRIMARY KEY,
  email           CITEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  slug            TEXT UNIQUE NOT NULL,             -- for subdomain
  plan_tier       TEXT NOT NULL DEFAULT 'trial',    -- trial|booster|pro|team
  status          TEXT NOT NULL DEFAULT 'active',   -- active|past_due|canceled
  phone_e164      TEXT,                             -- normalized +15551234567
  sms_opt_in      BOOLEAN NOT NULL DEFAULT FALSE,   -- for Twilio compliance
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_agents_plan ON agents(plan_tier);
```

### 2) agent_domains (Cloudflare for SaaS)

```sql
CREATE TABLE agent_domains (
  id                       UUID PRIMARY KEY,
  agent_id                 UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  hostname                 TEXT NOT NULL UNIQUE,     -- john.ezrealtor.app or custom
  cf_custom_hostname_id    TEXT,                     -- from CF API
  verification_status      TEXT NOT NULL DEFAULT 'pending', -- pending|active|failed
  is_primary               BOOLEAN NOT NULL DEFAULT TRUE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_agent_domains_agent ON agent_domains(agent_id);
CREATE INDEX ix_agent_domains_host ON agent_domains(hostname);
```

### 3) capture_pages (your 2 funnels + any extras)

```sql
CREATE TABLE capture_pages (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  kind            TEXT NOT NULL,                    -- home_valuation | buyer_interest | custom
  slug            TEXT NOT NULL,                    -- e.g. "sell" → /sell
  title           TEXT,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (agent_id, slug)
);
CREATE INDEX ix_capture_pages_agent ON capture_pages(agent_id);
```

### 4) leads (all inbound leads land here)

```sql
CREATE TYPE lead_status AS ENUM ('new','contacted','qualified','won','lost','spam');
CREATE TYPE lead_source AS ENUM ('home_valuation','buyer_interest','contact','import','api');

CREATE TABLE leads (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  capture_page_id UUID REFERENCES capture_pages(id) ON DELETE SET NULL,
  source          lead_source NOT NULL,
  full_name       TEXT,
  email           CITEXT,
  phone_e164      TEXT,
  address_line    TEXT,          -- for home valuation
  city            TEXT,
  state           TEXT,
  postal_code     TEXT,
  message         TEXT,
  utm_source      TEXT,
  utm_medium      TEXT,
  utm_campaign    TEXT,
  status          lead_status NOT NULL DEFAULT 'new',
  ai_summary      TEXT,          -- short snapshot (OpenAI)
  ai_score        INT,           -- 0..100
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- what you’ll query most:
CREATE INDEX ix_leads_agent_created ON leads(agent_id, created_at DESC);
CREATE INDEX ix_leads_agent_status  ON leads(agent_id, status);
CREATE INDEX ix_leads_email_phone   ON leads((lower(email)), phone_e164);
```

### 5) notifications (email/SMS/callback logs)

```sql
CREATE TYPE notify_kind AS ENUM ('email_agent','email_lead','sms_agent','sms_lead','voice_callback');

CREATE TABLE notifications (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
  kind            notify_kind NOT NULL,
  provider_msg_id TEXT,         -- Brevo/Twilio id
  success         BOOLEAN NOT NULL,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_notifications_agent ON notifications(agent_id, created_at DESC);
```

### 6) provider_credentials (BYOK: encrypted secrets)

> Encrypt in the app layer with Fernet or libsodium. Store **ciphertext only** here.

```sql
CREATE TABLE provider_credentials (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  provider        TEXT NOT NULL CHECK (provider IN ('openai','brevo','twilio')),
  key_name        TEXT NOT NULL,         -- api_key | account_sid | auth_token | from_number
  key_ciphertext  BYTEA NOT NULL,        -- encrypted at app-level
  verified_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (agent_id, provider, key_name)
);
CREATE INDEX ix_provider_creds_agent ON provider_credentials(agent_id);
```

### 7) usage_counters (limits + metering)

Monthly roll-up per agent. Increment via app code (single `UPDATE ... SET used = used + 1` in a tx).

```sql
CREATE TABLE usage_counters (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  period_month    DATE NOT NULL,         -- e.g., 2025-10-01 for October
  leads_created   INT  NOT NULL DEFAULT 0,
  emails_sent     INT  NOT NULL DEFAULT 0,
  sms_sent        INT  NOT NULL DEFAULT 0,
  ai_calls        INT  NOT NULL DEFAULT 0,
  UNIQUE (agent_id, period_month)
);
CREATE INDEX ix_usage_agent_month ON usage_counters(agent_id, period_month DESC);
```

---

## OPTIONAL (add when needed)

### plan_catalog (centralize tier limits & flags)

```sql
CREATE TABLE plan_catalog (
  code            TEXT PRIMARY KEY,      -- trial|booster|pro|team
  price_month_usd NUMERIC(10,2) NOT NULL,
  max_leads       INT,
  max_emails      INT,
  max_sms         INT,
  max_ai_calls    INT,
  allow_twilio    BOOLEAN NOT NULL DEFAULT FALSE,
  allow_custom_domain BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### stripe_subscriptions (mirror Stripe state; handy for audits)

```sql
CREATE TABLE stripe_subscriptions (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  customer_id     TEXT NOT NULL,
  subscription_id TEXT NOT NULL,
  price_code      TEXT NOT NULL,   -- maps to plan_catalog.code
  status          TEXT NOT NULL,   -- active|trialing|past_due|canceled
  current_period_end TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (subscription_id)
);
```

### lead_events (timeline on each lead)

```sql
CREATE TYPE lead_event_kind AS ENUM ('created','email_sent','sms_sent','callback_placed','status_changed','note');

CREATE TABLE lead_events (
  id              UUID PRIMARY KEY,
  lead_id         UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  kind            lead_event_kind NOT NULL,
  payload         JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_lead_events_lead ON lead_events(lead_id, created_at DESC);
```

### testimonials & branding (for their homepage)

```sql
CREATE TABLE branding (
  agent_id        UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
  headline        TEXT,
  subheadline     TEXT,
  logo_url        TEXT,
  theme           TEXT DEFAULT 'light'
);

CREATE TABLE testimonials (
  id              UUID PRIMARY KEY,
  agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  author_name     TEXT NOT NULL,
  quote           TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 🔐 Security & PII notes

* Use **CITEXT** for emails (case-insensitive) and normalize phones to **E.164**.
* App-level **encryption** (Fernet/NaCl) for provider keys before insert; **never** log secrets.
* Consider **Row Level Security (RLS)** later; for now, always filter by `agent_id` server-side.
* Separate **error logs** from PII (e.g., store provider IDs but not raw content where you don’t need it).

---

## ⚡ Practical queries you’ll run a lot

**Newest leads in dashboard**

```sql
SELECT id, full_name, email, phone_e164, ai_score, status, created_at
FROM leads
WHERE agent_id = $1
ORDER BY created_at DESC
LIMIT 50;
```

**Monthly usage check (to enforce limits)**

```sql
SELECT leads_created, emails_sent, sms_sent, ai_calls
FROM usage_counters
WHERE agent_id = $1 AND period_month = date_trunc('month', now())::date;
```

**Find duplicates (same email/phone)**

```sql
SELECT email, phone_e164, count(*) 
FROM leads
WHERE agent_id = $1
GROUP BY email, phone_e164
HAVING count(*) > 1;
```

---

## 🧪 Migration order (Alembic)

1. `agents`
2. `agent_domains`
3. `capture_pages`
4. `leads` (plus enums)
5. `notifications`
6. `provider_credentials`
7. `usage_counters`
8. (optional) `plan_catalog`, `stripe_subscriptions`, `lead_events`, `branding`, `testimonials`

---

## 🧩 How your services hook in

* **Lead intake** (`POST /leads/create`):

  * insert into `leads`
  * `usage_counters.leads_created += 1`
  * queue Brevo/Twilio → insert into `notifications` (success/fail)

* **AI summary** (trial = your key, paid = BYOK):

  * write `ai_summary`, `ai_score` on `leads`
  * `usage_counters.ai_calls += 1`

* **Twilio callback** (Pro+ and verified):

  * on success: `notifications(kind='voice_callback')`

* **Stripe webhook**:

  * upsert `stripe_subscriptions`
  * flip `agents.plan_tier`
  * unlock domain wizard if plan allows

---

## ☑️ Want me to output ready-to-run Alembic migration files next?


