

# Free Trial — Policy (defaults you can ship today)

* **Duration:** 14 days from workspace creation/activation.
* **No overages, no packs** in trial (hard stop at caps).
* **Included (pooled across 2 pages):**

  * **Page views:** 2,000
  * **Lead events:** 50
  * **AI tokens (in+out):** 150,000
  * **Emails:** 100
  * **SMS (US/CA):** 50
  * **Voice minutes (US/CA):** 15
* **Per-day micro-caps** (anti-abuse, evenly pace trial):

  * Emails: 30/day • SMS: 15/day • Voice: 5 min/day
* **Quiet hours:** 8am–8pm local for SMS/voice (enforced in trial).

# What happens at/near limits

* **Soft alerts** (banner + email to owner):

  * 70% & 90% of any cap → “You’re close to the limit—upgrade to continue without interruption.”
* **Hard stop @ 100%** of a metric:

  * That channel is **paused**. The action turns into an **Upgrade Gate** (see copies below).
  * Non-metered UX still works (view leads, adjust routing), but **no sends/calls**.
* **Trial expiry (day 14 23:59 local)**:

  * All metered actions pause.
  * Leads still collect, but auto-reachouts are queued as **Pending (Upgrade to Send)**.

# Upgrade UX (copy you can drop in)

**Inline toast (hit channel limit)**

> Trial limit reached for **{channel}**. Upgrade to **Concierge ($97/mo)** to keep sending.
> What you get: 1.5M tokens, 1k emails, 300 SMS, 60 call minutes, $50 spend cap.
> [Upgrade now] [See plan details]

**Button gate (send/call attempt)**

> You’ve used your **trial {channel} credits**. Upgrade to continue immediately.
> • Your pending action will be sent right after upgrade.
> [Upgrade for $97/mo]  [Cancel]

**Trial expiry banner (top of app)**

> Your 14-day trial ended. Leads still collect, but messages & calls are paused.
> Upgrade to re-enable automations. [Upgrade]

**Email reminder cadence**

* Day 9: “~40% of trial left—keep momentum with full bundle.”
* Day 13: “Trial ends tomorrow—avoid pauses, upgrade now.”
* Day 15: “We held X pending sends—upgrade to release them.”

# Runtime decision (pseudocode)

```ts
function authorize(action, ctx) {
  const { plan, trialEndsAt, usage, caps } = ctx

  const isTrial = Date.now() < trialEndsAt
  const metric = action.metric // 'ai' | 'email' | 'sms' | 'voice' | 'views' | 'leads'
  const units = action.units

  // Enforce quiet hours for sms/voice during trial
  if (isTrial && (metric === 'sms' || metric === 'voice') && inQuietHours(ctx.localTime)) {
    return deny('quiet_hours')
  }

  // Determine caps
  const capMonthly = isTrial ? caps.trial.monthly[metric] : caps.paid.included[metric]
  const capDaily   = isTrial ? caps.trial.daily[metric]   : null

  // Daily pacing (trial only)
  if (isTrial && capDaily && usage.day[metric] + units > capDaily) {
    return deny('trial_daily_cap_reached')
  }

  // Monthly cap
  if (usage.month[metric] + units > capMonthly) {
    if (isTrial) return deny('trial_cap_reached')
    // Paid: check overages
    if (!ctx.overagesEnabled) return deny('included_exhausted')
    const projectedCost = estimateCost(metric, units, ctx.rates)
    if (ctx.spendUSD + projectedCost > ctx.spendCapUSD) return deny('cap_reached')
  }

  return allow()
}
```

# Config (drop into your seed/config service)

```json
{
  "trial": {
    "days": 14,
    "monthly_caps": {
      "page_views": 2000,
      "lead_events": 50,
      "ai_tokens": 150000,
      "emails": 100,
      "sms_us_ca": 50,
      "voice_minutes_us_ca": 15
    },
    "daily_caps": {
      "emails": 30,
      "sms_us_ca": 15,
      "voice_minutes_us_ca": 5
    },
    "quiet_hours_local": { "start": "20:00", "end": "08:00" },
    "overages_allowed": false,
    "packs_allowed": false
  },
  "paid_defaults": {
    "plan_code": "concierge_2",
    "included": {
      "page_views": 5000,
      "lead_events": 300,
      "ai_tokens": 1500000,
      "emails": 1000,
      "sms_us_ca": 300,
      "voice_minutes_us_ca": 60
    },
    "overages_enabled_by_default": false,
    "spend_cap_usd_default": 50
  }
}
```

# Eventing & comms (hook these)

* `trial.threshold.reached` (70/90): send in-app banner + owner email.
* `trial.cap.hit` (per channel): show gate + email with “what’s pending.”
* `trial.expired`: show global banner; stop metered jobs; queue pending.
* `upgrade.completed`: immediately drain pending queue respecting paid caps.

# Abuse & safety

* ReCAPTCHA on form submissions after 100 views/day during trial.
* Country allowlist for SMS/voice in trial (US/CA default).
* Per-lead call attempts: max 1/day in trial (2/day in paid).

# QA scenarios (brief)

1. Hit 70% email → toast shows; sends continue.
2. Hit 100% SMS → next SMS denied with gate; email still allowed.
3. Trial day 15 → automations paused; upgrade clears queued sends.
4. Quiet hours → SMS/voice denied in trial; email allowed.
5. Daily caps respected even if monthly not exhausted.

If you want, I can fold these into your existing Usage UI (the ZIP I gave) with a “Trial mode” flag and all the copy wired up.
