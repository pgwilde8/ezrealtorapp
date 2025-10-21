# 🎯 API Endpoints - Complete Implementation

## ✅ What's Been Built

### **1. Property Alerts API** (`app/api/property_alerts.py`)

#### **Property Management:**
```
GET    /api/v1/property-alerts/limits                    ← Check plan limits
GET    /api/v1/property-alerts/subscribers/count        ← Count subscribers
POST   /api/v1/property-alerts/                          ← Create property
GET    /api/v1/property-alerts/                          ← List properties
GET    /api/v1/property-alerts/{id}                      ← Get specific property
DELETE /api/v1/property-alerts/{id}                      ← Delete property
```

#### **Image Management:**
```
POST   /api/v1/property-alerts/{id}/photos               ← Upload photo (max 5)
DELETE /api/v1/property-alerts/{id}/photos/{photo_id}    ← Delete photo
```

#### **Sending:**
```
POST   /api/v1/property-alerts/{id}/send                 ← Send alert to subscribers
```

### **2. Agent Photos API** (`app/api/agents.py`)

```
POST   /api/v1/agents/me/upload-headshot                 ← Upload profile photo
POST   /api/v1/agents/me/upload-secondary-photo          ← Upload about section photo
POST   /api/v1/agents/me/upload-logo                     ← Upload agency logo
DELETE /api/v1/agents/me/photos/{type}                   ← Delete photo
```

### **3. Spaces Service** (`app/services/spaces_service.py`)

- Automatic image optimization
- Thumbnail generation (400x300)
- CDN URL generation
- Image deletion
- PIL/Pillow integration

---

## 📋 API Examples

### **Create Property Alert**

**Request:**
```bash
POST /api/v1/property-alerts/
Authorization: Bearer {token}
Content-Type: application/json

{
  "address": "123 Main Street, City, ST 12345",
  "price": 450000,
  "square_feet": 2100,
  "bedrooms": 3,
  "bathrooms": 2.5,
  "description": "Beautiful updated home in desirable neighborhood...",
  "mls_link": "https://mls.com/listing/12345",
  "is_hot": true
}
```

**Response:**
```json
{
  "id": "abc123-...",
  "address": "123 Main Street...",
  "price": 450000,
  "bedrooms": 3,
  "bathrooms": 2.5,
  "description": "Beautiful updated...",
  "is_hot": true,
  "images": [],
  "created_at": "2025-10-20T12:00:00Z"
}
```

### **Upload Property Photo**

**Request:**
```bash
POST /api/v1/property-alerts/{property_id}/photos
Authorization: Bearer {token}
Content-Type: multipart/form-data

photo: [FILE]
display_order: 1
```

**Response:**
```json
{
  "success": true,
  "image_id": "img-456...",
  "image_url": "https://ezrealtorapp.spaces.sfo3.cdn.digitaloceanspaces.com/properties/test6/prop-abc123-001.jpg",
  "thumbnail_url": "https://ezrealtorapp.spaces.sfo3.cdn.digitaloceanspaces.com/thumbnails/properties/test6/prop-abc123-001_thumb.jpg",
  "display_order": 1
}
```

### **Check Plan Limits**

**Request:**
```bash
GET /api/v1/property-alerts/limits
Authorization: Bearer {token}
```

**Response:**
```json
{
  "alerts_this_month": 3,
  "max_alerts_per_month": 5,
  "can_create_more": true,
  "remaining": 2
}
```

**Pro Plan Response:**
```json
{
  "alerts_this_month": 15,
  "max_alerts_per_month": null,
  "can_create_more": true,
  "remaining": null
}
```

### **Get Subscriber Count**

**Request:**
```bash
GET /api/v1/property-alerts/subscribers/count
Authorization: Bearer {token}
```

**Response:**
```json
{
  "vip_sms": 8,
  "email": 23,
  "total": 31
}
```

### **Send Alert**

**Request:**
```bash
POST /api/v1/property-alerts/{property_id}/send
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "Property alert is being sent to subscribers",
  "sent_at": "2025-10-20T13:30:00Z"
}
```

### **Upload Agent Headshot**

**Request:**
```bash
POST /api/v1/agents/me/upload-headshot
Authorization: Bearer {token}
Content-Type: multipart/form-data

photo: [FILE]
```

**Response:**
```json
{
  "success": true,
  "headshot_url": "https://ezrealtorapp.spaces.sfo3.cdn.digitaloceanspaces.com/agents/test6/profile.jpg",
  "thumbnail_url": "https://ezrealtorapp.spaces.sfo3.cdn.digitaloceanspaces.com/thumbnails/agents/test6/profile_thumb.jpg",
  "message": "Profile photo updated successfully"
}
```

---

## 🔒 Authentication

All endpoints require authentication except public routes. Use JWT tokens:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## ✨ Features Implemented

### **Plan Limits:**
- ✅ Trial: 5 property alerts per month
- ✅ Pro/Growth/Scale: Unlimited
- ✅ Enforcement at creation time
- ✅ API returns remaining count

### **Image Processing:**
- ✅ Automatic resizing (max 1200x900 for properties)
- ✅ Thumbnail generation (400x300)
- ✅ JPEG optimization (85% quality)
- ✅ Proper aspect ratio maintenance
- ✅ RGBA → RGB conversion

### **Security:**
- ✅ File type validation
- ✅ File size limits (10MB properties, 5MB agent photos)
- ✅ Agent ownership verification
- ✅ Maximum 5 photos per property
- ✅ Unique filenames (no collisions)

### **Storage:**
- ✅ DigitalOcean Spaces integration
- ✅ CDN URLs for fast delivery
- ✅ Organized folder structure
- ✅ Automatic cleanup on delete

---

## 🎨 Frontend Needed (Next Steps)

### **1. Property Alert Form Component**
Location: Dashboard → "Send Property Alert" button

**Step 1 Form:**
```html
<form id="propertyForm">
  <input name="address" placeholder="123 Main Street..." />
  <input name="price" type="number" placeholder="$450,000" />
  <input name="square_feet" type="number" placeholder="2,100" />
  <select name="bedrooms">...</select>
  <select name="bathrooms">...</select>
  <textarea name="description"></textarea>
  <input name="mls_link" placeholder="https://..." />
  <label>
    <input type="checkbox" name="is_hot" />
    🔥 Hot Property (instant SMS)
  </label>
  <button>Next: Add Photos</button>
</form>
```

**Step 2 Photo Upload:**
```html
<div id="photoUpload">
  <div class="upload-zone" ondrop="handleDrop(event)" ondragover="allowDrop(event)">
    Click to upload or drag photos here
    <input type="file" accept="image/*" onchange="handleFile(event)" />
  </div>
  
  <div id="photoPreview">
    <!-- Show uploaded photos with crop/rotate controls -->
  </div>
  
  <div class="subscriber-count">
    📊 Who Will Receive This Alert:
    <span id="vipCount">8</span> VIP SMS subscribers
    <span id="emailCount">23</span> Email subscribers
  </div>
  
  <button onclick="sendAlert()">📨 Send Alert</button>
</div>
```

### **2. Image Cropper Integration**

**Include Cropper.js:**
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"></script>
```

**JavaScript:**
```javascript
let cropper;

function handleFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  // Show image in modal
  const img = document.getElementById('cropImage');
  img.src = URL.createObjectURL(file);
  
  // Open crop modal
  showCropModal();
  
  // Initialize Cropper
  cropper = new Cropper(img, {
    aspectRatio: NaN, // Free aspect ratio
    viewMode: 1,
    rotatable: true,
    scalable: true
  });
}

function rotateCropper() {
  cropper.rotate(90);
}

async function uploadCroppedImage() {
  // Get cropped canvas
  const canvas = cropper.getCroppedCanvas();
  
  // Convert to blob
  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append('photo', blob, 'photo.jpg');
    formData.append('display_order', photoCount);
    
    // Upload
    const response = await fetch(`/api/v1/property-alerts/${propertyId}/photos`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    const data = await response.json();
    
    // Show thumbnail in preview
    addPhotoPreview(data.thumbnail_url, data.image_id);
    photoCount++;
  });
}
```

### **3. Agent Photo Upload**

**In Customize/Dashboard:**
```html
<div class="photo-upload-section">
  <h3>Profile Photo</h3>
  <div class="current-photo">
    <img src="{{ agent.headshot_url }}" id="currentHeadshot" />
  </div>
  <input type="file" accept="image/*" onchange="uploadHeadshot(event)" />
  <button onclick="deleteHeadshot()">Delete</button>
</div>

<script>
async function uploadHeadshot(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  // Show crop modal (same as above)
  // After cropping...
  
  const formData = new FormData();
  formData.append('photo', blob, 'profile.jpg');
  
  const response = await fetch('/api/v1/agents/me/upload-headshot', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  const data = await response.json();
  
  // Update preview
  document.getElementById('currentHeadshot').src = data.headshot_url + '?t=' + Date.now();
  
  alert('Profile photo updated!');
}
</script>
```

---

## 📊 Database Schema (Already Created)

### **property_alerts Table:**
```sql
CREATE TABLE property_alerts (
  id              UUID PRIMARY KEY,
  agent_id        UUID REFERENCES agents(id),
  address         VARCHAR(500),
  price           INTEGER,
  square_feet     INTEGER,
  bedrooms        INTEGER,
  bathrooms       NUMERIC(3,1),
  description     TEXT,
  mls_link        VARCHAR(500),
  is_hot          BOOLEAN DEFAULT FALSE,
  sent_at         TIMESTAMPTZ,
  email_sent_count INTEGER DEFAULT 0,
  sms_sent_count  INTEGER DEFAULT 0,
  click_count     INTEGER DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### **property_images Table:**
```sql
CREATE TABLE property_images (
  id              UUID PRIMARY KEY,
  property_id     UUID REFERENCES property_alerts(id),
  image_url       VARCHAR(1000),
  thumbnail_url   VARCHAR(1000),
  file_size       INTEGER,
  width           INTEGER,
  height          INTEGER,
  display_order   INTEGER DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 🚀 Deployment Steps

### **1. Install Dependencies**
```bash
cd /root/ezrealtor/ezadmin
source venv/bin/activate
pip install boto3 Pillow
```

### **2. Run Migration**
```bash
export DATABASE_URL="postgresql+asyncpg://ezrealtor_user:ezrealtor_pass@localhost:5432/ezrealtor_db"
alembic upgrade head
```

### **3. Add AI Columns (if not done)**
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

### **4. Restart Application**
```bash
sudo systemctl restart ezrealtor
```

### **5. Test Endpoints**
```bash
# Check if API is running
curl https://test6.ezrealtor.app/api/docs

# Test property limits
curl -H "Authorization: Bearer {token}" \
  https://test6.ezrealtor.app/api/v1/property-alerts/limits
```

---

## ✅ Testing Checklist

- [ ] Install boto3 and Pillow
- [ ] Run database migration
- [ ] Add AI columns to leads table
- [ ] Restart application
- [ ] Test contact form (should work now!)
- [ ] Test property alert creation API
- [ ] Test photo upload API
- [ ] Test plan limits enforcement
- [ ] Test subscriber counting
- [ ] Verify images appear in Spaces
- [ ] Verify CDN URLs work
- [ ] Test agent headshot upload
- [ ] Build frontend components

---

## 🎯 What's Left to Build

1. **Frontend Property Alert Form** (Step 1: property details)
2. **Frontend Photo Upload UI** (Step 2: photos with crop/rotate)
3. **Cropper.js Integration** (image editing)
4. **Email Sending** (Brevo integration in `send_alert_to_subscribers`)
5. **SMS Sending** (Twilio integration for hot properties)
6. **Subscriber Table/Model** (to track SMS opt-ins properly)
7. **Agent Photo Upload UI** (in customize/dashboard)

---

## 🎉 Summary

### **✅ Complete:**
- Database models and migrations
- Full API endpoints
- Image upload/optimization
- Spaces integration
- Plan limits
- Authentication
- Error handling

### **🔨 In Progress:**
- Frontend components
- Cropper.js integration
- Email/SMS sending

### **📋 TODO:**
- Build property alert form UI
- Build photo upload UI with crop/rotate
- Integrate Brevo for emails
- Integrate Twilio for SMS
- Create subscriber management
- Test end-to-end flow

---

**Ready to build the frontend components! All the backend infrastructure is in place.** 🚀

