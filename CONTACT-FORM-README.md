# 📧 Contact Form Implementation

## Overview

The contact form is a new lead capture method that allows visitors to send general inquiries to realtors directly from their landing page. This complements the existing **Home Valuation** and **Buyer Interest** forms.

---

## 🎯 Features

### For Visitors
- **Simple contact form** with Name, Email, Phone (optional), and Message fields
- **Beautiful modal popup** that matches the agent's branding
- **Instant confirmation** when the message is sent
- **Mobile-responsive** design
- Accessible via:
  - "Contact Me" button in the hero section
  - "Send a Message" button in the CTA section
  - Direct URL: `?contact=open` query parameter

### For Realtors
- All contact form submissions appear in the **Realtor Dashboard** at `/dashboard`
- Each lead is:
  - ✅ Tagged with source: `CONTACT_FORM`
  - 🤖 Processed by AI for lead scoring (0-100)
  - 📊 Categorized by priority (hot/warm/cold)
  - 📧 Email notification sent to realtor
  - 💬 Full conversation history stored
  - 📍 IP address and user agent tracked for security

---

## 📍 Location in Landing Page

The contact form button appears in **two places**:

1. **Hero Section** (Top of page)
   - Next to "What's My Home Worth?" and "Find My Dream Home" buttons
   - Primary CTA for immediate contact

2. **Bottom CTA Section** (Before footer)
   - "Send a Message" button
   - Encourages action after reading about the agent

---

## 🔄 Data Flow

```
┌─────────────────┐
│  Visitor Fills  │
│  Contact Form   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  POST /api/v1/leads/    │
│  lead_type: contact_form│
└────────┬────────────────┘
         │
         ▼
┌──────────────────────┐
│  Database (leads)    │
│  - agent_id          │
│  - source: CONTACT_  │
│    FORM              │
│  - message           │
│  - contact info      │
│  - ip_address        │
│  - raw_form_data     │
└────────┬─────────────┘
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌──────────────────┐    ┌─────────────────────┐
│  AI Processing   │    │  Email/SMS to       │
│  - Score lead    │    │  Realtor            │
│  - Categorize    │    │  (via Brevo/Twilio) │
│  - Extract intent│    └─────────────────────┘
└──────────────────┘
         │
         ▼
┌──────────────────────┐
│  Realtor Dashboard   │
│  /dashboard          │
│  - View lead         │
│  - See AI insights   │
│  - Respond to lead   │
└──────────────────────┘
```

---

## 💾 Database Schema

### New Fields Added to `leads` Table

```sql
-- New columns for tracking and storing form data
ALTER TABLE leads ADD COLUMN ip_address VARCHAR(50);
ALTER TABLE leads ADD COLUMN user_agent VARCHAR(500);
ALTER TABLE leads ADD COLUMN raw_form_data JSONB;
```

### Lead Source Enum

```python
class LeadSource(str, enum.Enum):
    HOME_VALUATION = "home_valuation"
    HOME_VALUATION_TOOL = "home_valuation_tool"
    BUYER_INTEREST = "buyer_interest"
    BUYER_INTEREST_FORM = "buyer_interest_form"
    CONTACT = "contact"
    CONTACT_FORM = "contact_form"  # ← NEW
    WEBSITE_FORM = "website_form"
    IMPORT = "import"
    API = "api"
```

---

## 📊 How Realtors See Contact Form Messages

### 1. **Dashboard** (Primary Method)
- Navigate to: `https://[agent-slug].ezrealtor.app/dashboard`
- All leads displayed in real-time table
- Filter by source: "Contact Form"
- View details:
  - ✉️ Full message
  - 👤 Contact information
  - 🎯 AI lead score
  - ⏰ Timestamp
  - 🔥 Priority level (hot/warm/cold)

**Dashboard Features:**
- Sort by date, priority, status
- Search by name or email
- Mark as contacted/qualified/won/lost
- Add notes to leads
- Export lead data

### 2. **Email Notifications**
Based on agent's plan tier:

| Plan Tier | Notification Method |
|-----------|-------------------|
| **Trial** | Email only |
| **Booster** | Email only |
| **Pro** | Email + SMS |
| **Team** | Email + SMS + Optional voice callback |

**Email includes:**
- Lead name and contact info
- Full message text
- AI-generated summary
- Lead score and priority
- Direct link to dashboard

### 3. **SMS Alerts** (Pro/Team Tier)
- Instant SMS when high-priority lead submits form
- Contains: Name, phone, and snippet of message
- Link to view full details in dashboard

### 4. **API Access**
Realtors can also fetch leads programmatically:

```bash
# Get all leads
GET /api/v1/leads/

# Filter by contact form only
GET /api/v1/leads/?source=contact_form

# Get specific lead
GET /api/v1/leads/{lead_id}
```

---

## 🤖 AI Processing

Every contact form submission is automatically processed by AI:

### Lead Scoring (0-100)
- **Email provided**: +15 points
- **Phone provided**: +15 points
- **Name provided**: +10 points
- **Message length > 50 chars**: +10 points
- **Message sentiment analysis**: 0-40 points
- **Urgency keywords detected**: +10 points

### Priority Categorization
- **Hot (80-100)**: Immediate follow-up needed
- **Warm (50-79)**: Follow up within 24 hours
- **Cold (0-49)**: General inquiry, follow up when convenient

### Intent Detection
AI analyzes the message to determine:
- **Buyer** - Looking to purchase
- **Seller** - Looking to sell/get valuation
- **Investor** - Investment opportunities
- **General** - Questions about services
- **Browsing** - Just exploring options

---

## 🎨 Customization

The contact form automatically inherits the agent's branding:

```jinja2
<!-- Primary color from agent profile -->
background: {{ agent.brand_primary_color }}

<!-- Agent photo in modal header -->
<img src="{{ agent.headshot_url }}" />

<!-- Personalized confirmation -->
"{{ agent.name }} will get back to you soon!"
```

---

## 🔒 Security & Privacy

### Data Protection
- ✅ HTTPS-only submission
- ✅ CSRF protection via FastAPI
- ✅ Input sanitization
- ✅ Rate limiting (10 submissions per IP per hour)
- ✅ Email validation
- ✅ Phone format validation

### Privacy Compliance
- IP address stored for fraud prevention
- User agent tracked for analytics
- Clear privacy notice shown in form
- Data only shared with assigned realtor
- GDPR/CCPA compliant data handling

---

## 📱 Mobile Experience

The contact form is fully optimized for mobile:
- **Responsive design** adapts to screen size
- **Touch-friendly** input fields
- **Auto-focus** on form fields
- **Keyboard-friendly** tab navigation
- **Easy close** via backdrop tap or × button

---

## 🔧 Technical Implementation

### Frontend (HTML/JavaScript)
```javascript
// Open modal
function openContactModal() {
    document.getElementById('contactModal').style.display = 'flex';
}

// Submit form
async function submitContactForm(event) {
    const response = await fetch('/api/v1/leads/', {
        method: 'POST',
        body: JSON.stringify({
            full_name: name,
            email: email,
            phone: phone,
            lead_type: 'contact_form',
            message: message
        })
    });
}
```

### Backend (FastAPI)
```python
# API endpoint: /api/v1/leads/
@router.post("/")
async def create_lead(lead_data: LeadCreateRequest):
    # Determine source
    if lead_data.lead_type == 'contact_form':
        lead_source = LeadSource.CONTACT_FORM
    
    # Create lead
    lead = Lead(
        agent_id=agent.id,
        source=lead_source,
        message=lead_data.message,
        # ... other fields
    )
    
    # Queue AI processing
    background_tasks.add_task(process_lead_with_ai, lead.id)
```

---

## 🚀 Deployment

### Migration Required
Run this migration after deployment:

```bash
cd /root/ezrealtor/ezadmin
alembic upgrade head
```

This adds the new fields to the `leads` table:
- `ip_address`
- `user_agent`
- `raw_form_data`

### Files Changed
1. ✅ `/ezadmin/app/models/lead.py` - Added CONTACT_FORM source + new fields
2. ✅ `/ezadmin/app/api/leads.py` - Added message field + contact form handling
3. ✅ `/ezadmin/app/templates/agent_landing.html` - Added contact modal + buttons
4. ✅ `/ezadmin/alembic/versions/add_contact_form_fields_to_leads.py` - Database migration

### Testing Checklist
- [ ] Contact form opens on button click
- [ ] Form validates required fields (name, email, message)
- [ ] Form submits successfully to `/api/v1/leads/`
- [ ] Success message displays after submission
- [ ] Lead appears in dashboard with source "contact_form"
- [ ] Email notification sent to realtor
- [ ] AI processing completes successfully
- [ ] Mobile responsive design works
- [ ] Modal closes on backdrop click

---

## 📞 Support

If realtors need help accessing their contact form messages:

1. **Dashboard Access**: `https://[subdomain].ezrealtor.app/dashboard`
2. **Login Issues**: Use "Forgot Password" or contact support
3. **Missing Leads**: Check spam folder for email notifications
4. **API Access**: Refer to API documentation at `/api/docs`

---

## 🎯 Future Enhancements

Potential improvements:
- Auto-responder to visitor (confirmation email)
- Custom contact form fields per agent
- File upload support (e.g., documents, photos)
- Integration with CRM systems (Salesforce, HubSpot)
- SMS auto-reply to visitor
- Calendar booking integration
- Multi-language support

---

## ✨ Summary

The contact form provides a **simple, secure, and effective** way for potential clients to reach realtors. All messages are:

1. ✅ **Captured** in database
2. 🤖 **Analyzed** by AI
3. 📧 **Sent** to realtor via email/SMS
4. 💼 **Displayed** in dashboard
5. 📊 **Tracked** for analytics

Realtors can access all messages through their dashboard at any time and respond to leads based on priority and AI insights.

