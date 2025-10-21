# 🏠 Property Alerts System - Implementation Guide

## ✅ What's Been Created

### **1. Database Models** (`app/models/property_alert.py`)
- `PropertyAlert` - Stores property details (address, price, beds, baths, etc.)
- `PropertyImage` - Stores image URLs and metadata (1-5 photos per property)

### **2. Database Migration** (`alembic/versions/add_property_alerts_tables.py`)
- Creates `property_alerts` table
- Creates `property_images` table
- Proper indexing and foreign keys

### **3. Spaces Service** (`app/services/spaces_service.py`)
- Image upload with automatic optimization
- Thumbnail generation (400x300)
- Full-size image resize (max 1200x900)
- CDN URL generation
- Image deletion
- Unique filename generation

---

## 📦 What Needs to Be Built Next

### **Phase 1: API Endpoints**

#### **Property Alert Endpoints:**
```python
POST   /api/v1/property-alerts/           # Create property
GET    /api/v1/property-alerts/           # List agent's properties  
GET    /api/v1/property-alerts/{id}       # Get specific property
PUT    /api/v1/property-alerts/{id}       # Update property
DELETE /api/v1/property-alerts/{id}       # Delete property
POST   /api/v1/property-alerts/{id}/send  # Send alert
```

#### **Image Upload Endpoints:**
```python
POST   /api/v1/property-alerts/{id}/photos        # Upload photo
DELETE /api/v1/property-alerts/{id}/photos/{photo_id}  # Delete photo
PUT    /api/v1/property-alerts/{id}/photos/{photo_id}/order  # Reorder
```

#### **Agent Photo Endpoints:**
```python
POST   /api/v1/agents/me/upload-headshot         # Upload profile photo
POST   /api/v1/agents/me/upload-secondary-photo  # Upload about section photo
POST   /api/v1/agents/me/upload-logo             # Upload logo
DELETE /api/v1/agents/me/photos/{type}           # Delete photo
```

### **Phase 2: Plan Limits**
- Trial plan: 5 property alerts per month
- Pro plan: Unlimited alerts
- Check limits before allowing create
- Return count of remaining alerts in API response

### **Phase 3: Subscriber Counting**
Need to count:
- VIP SMS subscribers (from listing_alerts table where sms_opt_in = true)
- Email subscribers (from listing_alerts table)

### **Phase 4: Email/SMS Sending**
- Send to email subscribers via Brevo
- Send to SMS subscribers via Twilio (if is_hot = true)
- Track sent counts

### **Phase 5: Frontend**
- Property alert creation form
- Image upload with crop/rotate (using Cropper.js)
- Image preview and reordering
- Subscriber count display
- Send confirmation

---

## 🔧 Installation Requirements

Add these to `requirements.txt`:
```
boto3>=1.28.0          # For DigitalOcean Spaces
Pillow>=10.0.0         # For image processing
```

---

## 🗄️ Environment Variables

Already in your `.env`:
```env
DO_SPACES=https://ezrealtorapp-spaces.sfo3.digitaloceanspaces.com
DO_SPACES_KEY=DO00PM66LMHT4D78QHVW
DO_SPACES_SECRETKEY=WYHrihPBN/M2gWaTGENWSwyDNQMF/SGxJF12CMoCoHQ
SPACES_BUCKET=ezrealtorapp-spaces
SPACES_REGION=sfo3
SPACES_ENDPOINT=https://sfo3.digitaloceanspaces.com
SPACES_CDN_ENDPOINT=https://ezrealtorapp.spaces.sfo3.cdn.digitaloceanspaces.com
```

---

## 📋 Deployment Steps

### **Step 1: Install Dependencies**
```bash
cd /root/ezrealtor/ezadmin
source venv/bin/activate
pip install boto3 Pillow
```

### **Step 2: Run Migration**
```bash
export DATABASE_URL="postgresql+asyncpg://ezrealtor_user:ezrealtor_pass@localhost:5432/ezrealtor_db"
alembic upgrade head
```

### **Step 3: Add Missing AI Columns (if not done yet)**
```bash
sudo -u postgres psql ezrealtor_db << 'EOF'
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_intent VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_urgency INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_timeline VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_budget_min INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_budget_max INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_motivation VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_priority VARCHAR(20);
EOF
```

### **Step 4: Restart Application**
```bash
sudo systemctl restart ezrealtor
```

---

## 🎯 Usage Flow

### **Agent Creates Property Alert:**
1. Go to dashboard
2. Click "🔥 Send Property Alert"
3. Fill in property details (address, price, beds, baths, description)
4. Mark as "Hot Property" if urgent (sends instant SMS)
5. Click "Next: Add Photos"
6. Upload 1-5 photos:
   - Click or drag-and-drop
   - Crop/rotate in browser
   - One-by-one with preview
7. See subscriber count: "8 VIP SMS + 23 Email"
8. Click "Send Alert"
9. Alert sent to all subscribers!

### **What Happens Behind the Scenes:**
1. Property created in database
2. Photos uploaded to Spaces:
   - Full-size: `/properties/test6/prop-abc123-001.jpg`
   - Thumbnail: `/thumbnails/properties/test6/prop-abc123-001_thumb.jpg`
3. URLs saved to `property_images` table
4. Query subscribers from `listing_alerts` table
5. Send emails via Brevo (all subscribers)
6. Send SMS via Twilio (VIP subscribers if is_hot=true)
7. Update sent counts
8. Show success message

---

## 📸 Image Specs

### **Property Photos:**
- **Format:** JPG, PNG, WebP
- **Max file size:** 10MB per photo
- **Max dimensions:** 6000x6000px
- **Output full-size:** Max 1200x900px (maintains aspect ratio)
- **Output thumbnail:** 400x300px
- **Quality:** 85% (full), 80% (thumbnail)
- **Storage:** DigitalOcean Spaces with CDN

### **Agent Photos:**
- **Headshot:** 400x400px square
- **Secondary:** 800x600px
- **Logo:** 200x60px PNG with transparency

---

## 💰 Cost Analysis

### **DigitalOcean Spaces:**
- **Storage:** $5/month for 250GB
- **Bandwidth:** First 1TB FREE, then $0.01/GB

### **Usage Estimate (1,000 agents):**
- 1,000 agents × 2 alerts/month × 4 photos × 600KB = **4.8GB/month**
- Annual storage: ~58GB = **$5/month**
- Bandwidth: Well under 1TB free tier

**Conclusion:** Even with 10,000 agents → **$10/month**

---

## 🔒 Security

1. ✅ File type validation
2. ✅ File size limits
3. ✅ Image dimension checks
4. ✅ Malware prevention (Pillow re-encodes images)
5. ✅ Unique filenames (no collisions)
6. ✅ Public-read ACL (images accessible via CDN)
7. ✅ Agent-isolated folders

---

## 🎨 Frontend Components Needed

### **1. Cropper.js Integration**
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"></script>
```

### **2. Image Upload Component**
- Drag & drop zone
- File input (click to browse)
- Crop modal with rotation controls
- Preview thumbnails
- Reorder with drag-and-drop
- Delete button

### **3. Property Form**
- Address autocomplete (Google Places API)
- Price formatter ($450,000)
- Bedroom/bathroom dropdowns
- Description textarea (500 char max)
- MLS link (optional)
- Hot property checkbox

---

## 📊 Database Queries

### **Count property alerts this month (for plan limits):**
```sql
SELECT COUNT(*) 
FROM property_alerts 
WHERE agent_id = $1 
  AND created_at >= date_trunc('month', CURRENT_TIMESTAMP);
```

### **Count subscribers:**
```sql
-- VIP SMS subscribers
SELECT COUNT(*) 
FROM listing_alerts 
WHERE agent_id = $1 AND sms_opt_in = true;

-- Email subscribers  
SELECT COUNT(*) 
FROM listing_alerts 
WHERE agent_id = $1;
```

### **Get property with images:**
```sql
SELECT p.*, 
       json_agg(
         json_build_object(
           'id', pi.id,
           'image_url', pi.image_url,
           'thumbnail_url', pi.thumbnail_url,
           'display_order', pi.display_order
         ) ORDER BY pi.display_order
       ) as images
FROM property_alerts p
LEFT JOIN property_images pi ON pi.property_id = p.id
WHERE p.id = $1
GROUP BY p.id;
```

---

## ✅ Testing Checklist

- [ ] Migration runs successfully
- [ ] Spaces service uploads images
- [ ] Thumbnails generate correctly
- [ ] Images accessible via CDN
- [ ] Property alert creation works
- [ ] Image upload endpoint works
- [ ] Crop/rotate functionality works
- [ ] Plan limits enforced
- [ ] Subscriber count accurate
- [ ] Emails send via Brevo
- [ ] SMS send via Twilio (hot properties)
- [ ] Stats update correctly

---

## 🚀 Next Steps

1. **Install dependencies** (boto3, Pillow)
2. **Run migration** (create tables)
3. **Add AI columns to leads** (if needed)
4. **Test contact form** (should work now!)
5. **Build API endpoints** (property alerts)
6. **Build frontend upload UI** (with crop/rotate)
7. **Integrate email/SMS sending**
8. **Test end-to-end flow**

---

**Ready to continue? Let me know and I'll build the API endpoints next!** 🎯

