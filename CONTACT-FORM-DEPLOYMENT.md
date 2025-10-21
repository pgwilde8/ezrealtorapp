# 🚀 Contact Form - Quick Deployment Guide

## ✅ What Was Implemented

### 1. **Contact Form Modal on Landing Pages**
- Beautiful popup modal with agent branding
- Fields: Name, Email, Phone (optional), Message
- Auto-integrates with existing lead capture system
- Mobile-responsive design

### 2. **Two Access Points**
- **Hero Section**: "Contact Me" button next to main CTAs
- **Bottom CTA Section**: "Send a Message" button
- **URL Parameter**: `?contact=open` to auto-open modal

### 3. **Backend Integration**
- Added `CONTACT_FORM` to LeadSource enum
- Updated API to handle contact form submissions
- Added fields to Lead model: `ip_address`, `user_agent`, `raw_form_data`
- AI processing for lead scoring and categorization

### 4. **Dashboard Display**
- All contact form messages appear in realtor dashboard
- Filterable by source: "Contact Form"
- Shows full message with AI insights
- Email/SMS notifications sent to realtor

---

## 📋 Deployment Steps

### Step 1: Run Database Migration

```bash
cd /root/ezrealtor/ezadmin
alembic upgrade head
```

This adds the new fields (`ip_address`, `user_agent`, `raw_form_data`) to the `leads` table.

### Step 2: Restart the Application

If using systemd:
```bash
sudo systemctl restart ezrealtor
```

Or if using uvicorn directly:
```bash
# Stop the current process (Ctrl+C)
# Then restart
cd /root/ezrealtor/ezadmin
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Test the Contact Form

1. Visit any realtor landing page: `https://[agent-slug].ezrealtor.app/`
2. Click "Contact Me" button in hero section
3. Fill out the form and submit
4. Verify success message appears
5. Check the realtor dashboard for the new lead
6. Confirm email notification was sent

---

## 🔍 Verification Checklist

- [ ] Migration applied successfully (no errors)
- [ ] Application restarted without issues
- [ ] Contact form button visible on landing page
- [ ] Modal opens when clicking "Contact Me"
- [ ] Form validates required fields
- [ ] Form submits successfully
- [ ] Success message displays
- [ ] Lead appears in dashboard with source "contact_form"
- [ ] Email notification sent to realtor (check spam folder)
- [ ] AI processing completes (lead score visible)
- [ ] Mobile view works correctly

---

## 🎯 How Realtors Access Messages

### Dashboard Access
```
URL: https://[agent-subdomain].ezrealtor.app/dashboard
Login: Use agent email and password
```

### Dashboard Features
1. View all leads in table format
2. Filter by source to show only "Contact Form" leads
3. Click on any lead to see:
   - Full message text
   - Contact information
   - AI lead score (0-100)
   - Priority level (hot/warm/cold)
   - Timestamp
   - IP address and user agent

### Email Notifications
- Realtors receive email for every contact form submission
- Email includes full message and link to dashboard
- Configure email settings in provider credentials

### SMS Notifications (Pro/Team Plans)
- Instant SMS for high-priority leads
- Configure Twilio credentials in dashboard

---

## 📁 Files Modified

```
ezadmin/
├── app/
│   ├── models/
│   │   └── lead.py                          # Added CONTACT_FORM + new fields
│   ├── api/
│   │   └── leads.py                         # Added message field handling
│   └── templates/
│       └── agent_landing.html               # Added contact modal + buttons
└── alembic/
    └── versions/
        └── add_contact_form_fields_to_leads.py  # Database migration
```

---

## 🐛 Troubleshooting

### Issue: Contact form not appearing
- **Solution**: Clear browser cache and hard refresh (Ctrl+Shift+R)
- Check if JavaScript errors in console (F12 Developer Tools)

### Issue: Form submission fails
- **Solution**: Check server logs for errors
- Verify API endpoint `/api/v1/leads/` is accessible
- Check database connection

### Issue: Lead not appearing in dashboard
- **Solution**: Check if lead was created in database:
  ```sql
  SELECT * FROM leads WHERE source = 'contact_form' ORDER BY created_at DESC LIMIT 5;
  ```
- Verify agent_id matches the logged-in agent

### Issue: No email notification received
- **Solution**: Check spam/junk folder
- Verify Brevo/email provider credentials
- Check `notifications` table for delivery status

### Issue: Migration fails
- **Solution**: Check if fields already exist:
  ```sql
  \d leads
  ```
- If fields exist, mark migration as complete:
  ```bash
  alembic stamp head
  ```

---

## 🔐 Security Notes

- All form submissions use HTTPS
- IP addresses logged for fraud prevention
- Rate limiting: 10 submissions per IP per hour
- Input validation and sanitization enabled
- CSRF protection via FastAPI

---

## 📊 Analytics

Track contact form performance:

```sql
-- Total contact form submissions
SELECT COUNT(*) FROM leads WHERE source = 'contact_form';

-- Contact forms by agent
SELECT agent_id, COUNT(*) as total
FROM leads 
WHERE source = 'contact_form'
GROUP BY agent_id
ORDER BY total DESC;

-- Average lead score for contact forms
SELECT AVG(ai_score) as avg_score
FROM leads 
WHERE source = 'contact_form' AND ai_score IS NOT NULL;

-- Conversion rate (contact form to qualified)
SELECT 
    COUNT(CASE WHEN status = 'qualified' THEN 1 END)::float / COUNT(*) * 100 as conversion_rate
FROM leads 
WHERE source = 'contact_form';
```

---

## 🎉 Success!

Your contact form is now live! Realtors can receive and respond to general inquiries directly through their dashboard.

**Next Steps:**
1. Train realtors on how to access dashboard
2. Set up email notifications (Brevo credentials)
3. Configure SMS alerts for Pro/Team tier agents
4. Monitor lead quality and response times
5. Gather feedback from realtors

---

## 📞 Support

For questions or issues:
- Check logs: `/var/log/ezrealtor/` or console output
- Database access: PostgreSQL connection string in `.env`
- API documentation: `https://[domain]/api/docs`

**Common Commands:**
```bash
# Check service status
sudo systemctl status ezrealtor

# View logs
sudo journalctl -u ezrealtor -f

# Check database
psql -U ezrealtor_user -d ezrealtor_db

# Test API
curl -X POST https://[domain]/api/v1/leads/ \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test","email":"test@example.com","lead_type":"contact_form","message":"Test message"}'
```

