# Quick Start Guide - MegaLLM Blog Generation Platform

## 🚀 Get Running in 5 Minutes

### Step 1: Install Requirements
```bash
cd blog_platform
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy example to .env
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux

# Edit .env and add your API key:
# MEGALLM_API_KEY=sk-mega-xxxxx...
```

### Step 3: Start MongoDB
```bash
# Option A: If MongoDB installed
mongod

# Option B: Using Docker
docker run -d -p 27017:27017 mongo

# Option C: Skip if running remotely
# (Just update MONGODB_URI in .env)
```

### Step 4: Run Setup Check
```bash
python setup.py
```

This will verify:
- ✓ All Python packages installed
- ✓ MongoDB connection working
- ✓ .env file configured
- ✓ API key is valid

### Step 5: Start the Platform
```bash
python main.py
```

You should see:
```
================== BLOG GENERATION PLATFORM - STARTUP ===================
Starting background scheduler...
MegaLLM Model: deepseek-ai/deepseek-v3.1
Blogs per 24h: 12
Generation interval: 120 minutes
Blog length: 500-800 words
Number of accounts: 5
Number of topics: 4
.......................... Ready to Start! ..........................
Web UI: http://localhost:5000
API: http://localhost:5000/api
=====================================
```

### Step 6: Open Dashboard
Visit: **http://localhost:5000**

---

## 📋 Dashboard Usage

### 1. Select an Account
Click one of: **Account 1**, **Account 2**, **Account 3**, **Account 4**, **Account 5**

### 2. View Statistics
- **Total Blogs** - All blogs for this account
- **Draft** - Not yet posted
- **Posted** - Published blogs
- **By Topic** - Breakdown across 4 topics

### 3. Generate Blogs
Click **🚀 Generate Blogs Now** to:
- Generate 12 new blogs
- 3 blogs per topic (Cost, Performance, Reliability, Infrastructure)
- Takes ~2-3 minutes
- Saves to database automatically

### 4. Manage Blogs

#### Copy Content
- Click **📋 Copy** on any blog
- Modal shows:
  - **Title** - Click "Copy Title" for headline only
  - **Body** - Click "Copy Body" for full article
- Paste into your CMS, LinkedIn, blog platform, etc.

#### Mark as Posted
- After publishing, click **✅ Mark Posted**
- Blog moves from "Draft" to "Posted" status
- Dashboard updates automatically

#### Filter Blogs
- **All** - Show all blogs
- **Draft** - Only unpublished
- **Posted** - Only published

### 5. View Generation History
Click **📊 Generation History** to see:
- When blogs were generated
- How many each time
- Any errors

---

## 🔄 Automatic Generation

The system automatically generates 12 blogs every 24 hours per account:

```
Account 1:
  - 3 blogs on Cost Optimization
  - 3 blogs on Performance
  - 3 blogs on Reliability
  - 3 blogs on Infrastructure

Account 2-5: (same structure)
```

**Generation happens automatically every 2 hours** (3 blogs per generation).

You can also click **"🚀 Generate Blogs Now"** to manually trigger anytime.

---

## 📊 Database

Everything is saved in MongoDB:
- **Accounts** - 5 predefined accounts
- **Blogs** - All generated blogs (title, body, topic, status)
- **Generation History** - When and how many blogs generated

---

## ✅ Features Checklist

- [x] Blog generation only (no Twitter, LinkedIn, Newsletter)
- [x] 5 separate accounts
- [x] 12 blogs every 24 hours per account
- [x] 4 topic categories
- [x] Copy content button (title + body separate)
- [x] Mark posted button
- [x] Draft vs Posted tracking
- [x] Generation history
- [x] Web dashboard UI
- [x] Automatic scheduling
- [x] MongoDB integration

---

## 🐛 Troubleshooting

### "MongoDB connection failed"
```bash
# Start MongoDB
mongod

# Or verify it's running
mongo --eval "db.adminCommand('ping')"
```

### "API key error" or "402 Insufficient Credits"
```bash
# Check your API key in .env
# Make sure it starts with: sk-mega-

# Test the key:
python setup.py
# Then run "Testing API Key" check
```

### "No blogs generating"
1. Click **"🚀 Generate Blogs Now"** manually
2. Wait 2-3 minutes (API takes time)
3. Refresh dashboard
4. Check `blog_platform.log` for errors

### Dashboard not loading (http://localhost:5000)
1. Check Flask is running (console output should show server started)
2. Try opening http://localhost:5000/api/health
3. Check for port 5000 conflicts: `netstat -ano | grep :5000`

---

## 📁 Project Structure

```
blog_platform/
├── main.py                 # Start here → python main.py
├── app.py                  # Flask API backend
├── scheduler.py            # Auto-generation scheduling
├── blog_generator.py       # MegaLLM integration
├── database.py             # MongoDB operations
├── config.py               # Settings & configuration
├── templates/
│   └── index.html          # Web dashboard UI
├── requirements.txt        # Python dependencies
├── setup.py                # Verify everything works
├── .env.example            # Copy to .env and configure
├── README.md               # Full documentation
├── QUICKSTART.md           # This file
└── blog_platform.log       # Logs (auto-created)
```

---

## 🎯 Next Steps

1. **Generate your first batch:**
   - Select an account
   - Click "🚀 Generate Blogs Now"
   - Wait a few minutes
   - See 12 new blogs appear

2. **Copy and publish:**
   - Click "📋 Copy" on a blog
   - Copy title and body
   - Paste into your platform (LinkedIn, Medium, blog, etc.)
   - Come back and click "✅ Mark Posted"

3. **Let it run 24 hours:**
   - Platform auto-generates 12 blogs per day
   - Just keep dashboard open or check periodically
   - View generation history anytime

4. **Customize topics:**
   - Edit `config.py` to change topics
   - Modify generation frequency
   - Add more accounts if needed

---

## 📞 API Reference

### Generate Blogs
```bash
curl -X POST http://localhost:5000/api/blogs/generate
  -H "Content-Type: application/json"
  -d '{"account_id": "account_1"}'
```

### Get All Blogs
```bash
curl http://localhost:5000/api/blogs?account_id=account_1
```

### Copy a Blog
```bash
curl http://localhost:5000/api/blogs/{blog_id}/copy
```

### Mark as Posted
```bash
curl -X PUT http://localhost:5000/api/blogs/{blog_id}/mark-posted
```

### Dashboard Stats
```bash
curl http://localhost:5000/api/dashboard/account_1
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

---

## 💡 Tips & Tricks

1. **Keep dashboard open** - Auto-refreshes every 30 seconds
2. **Batch copy** - Click multiple "Copy" buttons to queue content
3. **Check history** - See when last generation ran
4. **Sort by date** - Newest blogs appear first
5. **Filter by status** - Quickly find drafts to publish

---

## 🎓 Learn More

See **README.md** for:
- Full architecture details
- Database schema
- Configuration options
- Extending the platform
- Production deployment

---

**You're all set! Start generating blogs:** http://localhost:5000
