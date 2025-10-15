# Simple Tiered Pricing Strategy (Current Model)

**Philosophy**: Lead-based tiers with auto-bump protection. No complex overage UI. Customers pick by **leads/month** and get bigger pooled messaging/AI bundles as they scale.

## Current Tier Structure

| Tier        | Price/mo | Lead Events | Pooled Bundle (Emails · SMS · Voice · AI Tokens) |
|-------------|----------|-------------|---------------------------------------------------|
| **Starter** | **$97**  | **150**     | 600 · 180 · 40 min · 0.8M                       |
| **Growth**  | **$147** | **500**     | 2,500 · 700 · 120 min · 3M                      |
| **Scale**   | **$237** | **1,500**   | 6,000 · 2,000 · 400 min · 9M                    |
| **Pro**     | **$437** | **4,000**   | 15,000 · 5,000 · 1,000 min · 25M                |

## Auto-Bump Protection System

* **Soft alerts** at 80% & 95% of lead cap
* **Auto-bump to next tier** when cap hit (max 1 tier/month, pro-rated)
* **One forgiveness per quarter** (can drop back down if spike was temporary)
* **"Pause at cap" toggle** available (default: auto-bump ON)
* **Downgrade suggestion** if usage <60% for 2 consecutive months

## Revenue Growth Drivers

### 1) Natural Tier Progression
**ARPU lift**: $97 → $147 → $237 → $437 as agents grow their business

### 2) Weekend Boost Add-on
* **$49** for extra 300 SMS + 60 voice minutes (Fri-Sun only)
* Perfect for open house weekends
* **ARPU lift**: +$50-200/mo for active agents

### 3) Annual Plans (Future)
* 2 months free discount
* **Improves retention + cash flow**

### 4) Premium Services (Future)
* White-label branding: $49/mo
* Dedicated email IP: $39/mo
* Done-for-you setup: $99 one-time

# The revenue stack (how you make more)

## 1) Usage past the bundle (overages with a safety cap)

* Overages are **OFF by default** in trial and **opt-in** on paid with a clear **$ cap** (e.g., $50).
* When users hit limits, show 3 choices: **Enable overages**, **Buy a pack**, or **Upgrade to Plus**.
* Example rates (from earlier):

  * AI: $0.004 / 1k tokens
  * Email: $0.002 each
  * SMS (US/CA): $0.015 each
  * Voice: $0.03 / minute
* **ARPU lift:** Many agents toggle overages for busy weekends → +$10–$40/mo average.

## 2) Prepaid “Packs” (roll 60 days, debit before overages)

Cheaper than overage rates; improves cash flow.

* Token Pack 10M — $30
* Email Pack 10k — $15
* SMS Pack 1k — $12
* Voice 100 min — $3
  **ARPU lift:** +$10–$25/mo typical.

## 3) Plus tier for heavier teams

* **Concierge Plus (4 Pages) — $249/mo** with bigger quotas, SLA, priority, SSO/roles.
* Discount overages 10% on Plus.
  **ARPU lift:** clear upgrade path when they consistently hit 90%+.

## 4) Seats & pages

* Extra page +$29/mo (pooled quotas).
* Extra seats $8/seat/mo (or bundle of 10 seats for $60).
  **ARPU lift:** +$8–$60/mo.

## 5) Premium deliverability & brand

* Dedicated email IP: $39/mo (Plus: $29).
* White-label domain/branding: $49/mo.
  **ARPU lift:** +$30–$80/mo for serious teams.

## 6) Outcome-based kicker (optional, powerful)

* **Booked appointment fee**: $5–$15 per *qualified* appointment (cap it; allow opt-out).
* Or **Open-House Weekend Boost**: temporary higher SMS/voice limits Fri–Sun for $19.
  **ARPU lift:** wildly variable, but even 2–4 booked appts can add +$10–$40/mo.

## 7) Annual plans

* 2 months free: Concierge $970/yr, Plus $2,490/yr.
* Bundle a bonus (e.g., Dedicated IP free for first 3 months).
  **Improves retention + cash flow**, raises effective ARPU via add-on attach.

## 8) Services (one-time or recurring)

* “Done-in-48h” setup: $99 one-time.
* Quarterly optimization: $149/qtr (review scripts, routing, cadences).
  **ARPU lift:** front-loads cash; high margin.

---

# What this looks like in numbers (realistic scenarios)

**Base ($97) only:** $97 ARPU.

**Typical month with light extras:**

* 1 SMS Pack (+$12) + 100 overage SMS (~$1.50) + Extra page (+$29)
  → **$139.50 ARPU**

**Busy agent hitting limits:**

* Overages to $35 cap + Token Pack (+$30) + Dedicated IP (+$39)
  → **$201 ARPU**

**Team that upgrades:**

* Plus $249 + 2 extra seats (+$16) + 10% discounted overages ($22)
  → **~$287 ARPU**

Your $97 plan is the doorway; **limits trigger upsell moments**.

---

# Don’t create price anxiety—create **choice at the cap**

When a metric hits 90–100%, show a **single-choice card**:

1. **Keep going safely** (enable overages, cap at $50)
2. **Prepay & save** (buy a pack)
3. **Unlock more** (upgrade to Plus)

This preserves trust (no surprise bills) while letting motivated users pay for value.

---

# Pricing page layout (copy you can use)

** — $97/mo**
Includes 2 pages, 5k views, 300 leads, 1.5M tokens, 1k emails, 300 SMS, 60 voice min.
**Hard pause at limits** unless you enable overages (with a spend cap).

* Add-ons: Packs, Extra Page, Seats, Dedicated IP, White-label
* Safety: **You set the cap. We pause at the cap.**

** — $249/mo**
4 pages, 20k views, 1.5k leads, 6M tokens, 5k emails, 1.5k SMS, 300 voice min, priority support, SLA, roles/SSO.
Overages 10% off. Higher default spend cap.

---

# Guardrails so revenue scales without risk

* Overages **off by default**; enabling requires card on file + explicit cap.
* Soft alerts at 70/90%; pause at 100% (or cap).
* Packs debit **before** overages.
* “Weekend Boost” is time-boxed; resets Monday.
* International SMS and long calls priced separately (region/minute tables).

---

# Simple pricing JSON (drop into your config)

```json
{
  "plans": [
    {
      "code": "concierge",*this is legacy
      "price_monthly": 97,
      "included": { "pages": 2, "views": 5000, "leads": 300, "ai_tokens": 1500000, "emails": 1000, "sms_us_ca": 300, "voice_min": 60 },
      "overages": { "ai_per_1k": 0.004, "email": 0.002, "sms_us_ca": 0.015, "voice_min": 0.03 },
      "default_cap_usd": 50
    },
    {
      "code": "concierge_plus",
      "code": "concierge",*this is legacy pricing
      "price_monthly": 249,
      "included": { "pages": 4, "views": 20000, "leads": 1500, "ai_tokens": 6000000, "emails": 5000, "sms_us_ca": 1500, "voice_min": 300 },
      "overages": { "ai_per_1k": 0.0036, "email": 0.0018, "sms_us_ca": 0.0135, "voice_min": 0.027 },
      "default_cap_usd": 250
    }
  ],
  "addons": [
    { "code": "pack_ai_10m", "name": "Token Pack (10M)", "price": 30, "units": { "ai_tokens": 10000000 }, "rollover_days": 60 },
    { "code": "pack_email_10k", "name": "Email Pack (10k)", "price": 15, "units": { "emails": 10000 }, "rollover_days": 60 },
    { "code": "pack_sms_1k", "name": "SMS Pack (1k US/CA)", "price": 12, "units": { "sms_us_ca": 1000 }, "rollover_days": 60 },
    { "code": "pack_voice_100", "name": "Voice Pack (100 min)", "price": 3, "units": { "voice_min": 100 }, "rollover_days": 60 },
    { "code": "extra_page", "name": "Extra Page (+1)", "price_monthly": 29, "units": { "pages": 1 } },
    { "code": "dedicated_ip", "name": "Dedicated Email IP", "price_monthly": 39, "flags": ["email_dedicated_ip"] },
    { "code": "white_label", "name": "White-label Domain & Branding", "price_monthly": 49, "flags": ["whitelabel"] }
  ],
  "kickers": [
    { "code": "appt_fee", "name": "Per Booked Appointment", "price_each": 7, "cap_usd": 49, "opt_in": true },
    { "code": "weekend_boost", "name": "Open-House Weekend Boost", "price": 19, "window": "Fri 12:00 → Sun 23:59" }
  ]
}
```

---

## TL;DR
      "code": *this is updated pricing.

$97 is the **entry**; your revenue scales via **overages with caps**, **packs**, **Plus**, **pages/seats**, **deliverability/branding add-ons**, and optional **per-appointment fees**. Design the product to *gracefully hit limits* and offer a one-click path to **continue now**—that’s where ARPU grows without scaring users.

and i think we want to simple our public facing pricing:Yes—make it **tiered by leads** with **bigger pooled messaging/AI** per tier, and hide all the per-unit math. No overages UI; just soft auto-bumps with guardrails.

# Simple tiered plan (soft steps, no overages)

| Tier                 | Price/mo | Lead events/mo (≤) | Pooled bundle (emails · SMS · voice · AI tokens) |
| -------------------- | -------: | -----------------: | ------------------------------------------------ |
| **Starter**          |  **$97* |            **150** | 600 · 180 · 40 min · 0.8M                        |
| **Growth**           | **$147** |            **500** | 2,500 · 700 · 120 min · 3M                       |
| **Scale**            | **$237** |          **1,500** | 6,000 · 2,000 · 400 min · 9M                     |
| **Pro** *(optional)* | **$437** |          **4,000** | 15,000 · 5,000 · 1,000 min · 25M                 |

* Bundles are **caps, not guarantees**. Everything pooled across your pages.
* **International SMS/voice billed separately** (or restrict to US/CA).

## How the “soft auto-bump” works (client-friendly)

* At **80%** & **95%** of lead cap → in-app + email heads-up.
* If you hit the cap, we **finish the month** in the **next tier** automatically.

  * You’ll see a **pro-rated price** for the remainder of the month.
  * We’ll **never jump more than 1 tier in a month** (guardrail).
* **One-time forgiveness** per account per quarter (drops you back if the spike was a blip).
* If you want zero auto-bumps, toggle **“Pause at cap”** (default Off).

> Copy for settings: “Auto-bump when I hit limits (recommended). We’ll move you up one tier max/month and pro-rate the difference. One forgiveness per quarter.”

## Optional “simple add-on” (keeps pricing clean)

* **Weekend Boost ($49)**: extra **300 SMS + 60 min voice** (Fri–Sun), resets Monday.
* Doesn’t change your tier; great for open houses.

---

## Customer-facing pricing copy (drop-in)

**Starter — $97/mo**
Up to **150 leads/month**. Pooled bundle: **600 emails · 180 SMS · 40 call minutes · 0.8M AI tokens**.
*Hit the limit? We’ll auto-bump you to Growth (1 tier max/month) and pro-rate the difference. Or turn on “Pause at cap.”*

**Growth — $147/mo**
Up to **500 leads/month**. Bundle: **2,500 emails · 700 SMS · 120 call minutes · 3M tokens**.
*Same auto-bump guardrails; one forgiveness per quarter.*

**Scale — $237/mo**
Up to **1,500 leads/month**. Bundle: **6,000 emails · 2,000 SMS · 400 call minutes · 9M tokens**.

**Pro — $437/mo** *(optional)*
Up to **4,000 leads/month**. Bundle: **15,000 emails · 5,000 SMS · 1,000 call minutes · 25M tokens**.

*Footnote:* “Usage caps are processing limits, not guarantees of visitors or leads. Bundles reset monthly. International messaging may be priced separately. Auto-bump: 1 tier max/month, pro-rated; one forgiveness/quarter.”

---

## Backend bump rules (pseudo)

```ts
function evaluateTier(ctx) {
  const { leadsUsed, currentTier, month, autoBumpOn, forgivenessLeftQtr } = ctx
  const caps = TIERS[currentTier].leadCap

  notifyAt(0.8 * caps, '80%'); notifyAt(0.95 * caps, '95%')

  if (!autoBumpOn && leadsUsed >= caps) return pause('cap_reached')

  if (autoBumpOn && leadsUsed > caps) {
    const next = nextTier(currentTier)
    if (!next) return pause('top_tier_cap')
    if (alreadyBumpedThisMonth(ctx)) return pause('bump_limit_1_per_month')

    return bump({
      toTier: next,
      proration: proratePrice(currentTier, next, remainingDaysIn(month)),
      forgivenessEligible: forgivenessLeftQtr > 0
    })
  }
}
```

**Downgrade logic:** if usage stays **<60% of cap** for **2 consecutive months**, suggest a one-click **downgrade next cycle**.

---

## Stripe/catalog mapping

* Prices: `starter_97_monthly`, `growth_147_monthly`, `scale_237_monthly`, `pro_437_monthly`
* Add-on: `weekend_boost_49_onetime`
* Webhook handler: on bump → create **subscription item switch** with **proration_behavior='always_prorate'**, add **metadata** (`bumped_from`, `bump_date`), and set a **flag** so you don’t bump more than once/month.

---

## Seed config (JSON)

```json
{
  "tiers": [
    { "code": "starter", "price": 97, "lead_cap": 150, "bundle": { "emails": 600, "sms_us_ca": 180, "voice_min": 40, "ai_tokens": 800000 } },
    { "code": "growth",  "price": 147, "lead_cap": 500, "bundle": { "emails": 2500, "sms_us_ca": 700, "voice_min": 120, "ai_tokens": 3000000 } },
    { "code": "scale",   "price": 237, "lead_cap": 1500, "bundle": { "emails": 6000, "sms_us_ca": 2000, "voice_min": 400, "ai_tokens": 9000000 } },
    { "code": "pro",     "price": 437, "lead_cap": 4000, "bundle": { "emails": 15000, "sms_us_ca": 5000, "voice_min": 1000, "ai_tokens": 25000000 } }
  ],
  "rules": {
    "notify_thresholds": [0.8, 0.95],
    "max_auto_bumps_per_month": 1,
    "allow_pause_at_cap": true,
    "downgrade_offer_below_pct": 0.6,
    "downgrade_consecutive_months": 2,
    "quarterly_forgiveness": 1
  },
  "addons": [
    { "code": "weekend_boost", "name": "Weekend Boost", "price": 49, "units": { "sms_us_ca": 300, "voice_min": 60 }, "window": "Fri 12:00 → Sun 23:59" }
  ]
}
```

---

## Why this is “simple”

* Customers pick a **single number** to reason about: **leads/month**.
* Messaging/AI are just **bigger buckets** as you go up—no per-unit pricing stress.
* You still protect margin (bundles, auto-bump guard, pause option, intl carve-out).

  code   |    name    | price_month_usd | max_lead_events 
---------+------------+-----------------+-----------------
 trial   | Free Trial |            0.00 |              50
 starter | Starter    |           79.00 |             150
 growth  | Growth     |          129.00 |             500
 scale   | Scale      |          229.00 |            1500
 pro     | Pro        |          399.00 |            4000
(5 rows)

