# Complete Content Generation Pipeline: Scrape → Analyze → Blog

## 🎯 Overview

This is a **fully integrated content generation pipeline** that:

1. **Scrapes** articles from RSS feeds (TechCrunch, Medium, HN)
2. **Analyzes** content with WF1 to create marketing insights
3. **Generates** blog posts for 5 accounts from those insights

It replaces the disconnected random blog generation with **insight-driven content** that's actually based on real articles and analysis.

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   RSS Feeds         │ TechCrunch, Medium, HackerNews
├─────────────────────┤
│   scrape_to_mongo   │ Extracts articles
├─────────────────────┤
│   articles          │ MongoDB collection with raw content
├─────────────────────┤
│   wf1.py            │ Content Intelligence Pipeline
│   (DeepSeek V3.1)   │ Creates marketing angles & insights
├─────────────────────┤
│ content_insights    │ MongoDB collection with analysis
├─────────────────────┤
│ insight_scheduler   │ Maps insights to 5 accounts
│ (OpenRouter API)    │ Generates blog variants
├─────────────────────┤
│   blogs             │ MongoDB collection (5 accounts)
├─────────────────────┤
│   Flask API         │ Dashboard & endpoints
└─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
```bash
# MongoDB running
mongod

# Python 3.8+ with required packages
pip install pymongo requests openai apscheduler flask flask-cors python-dotenv
```

### Setup .env
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm

# Blog Generation (OpenRouter - FREE Qwen model)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free
USE_OPENROUTER=true

# Insights Analysis (MegaLLM)
MEGALLM_API_KEY=sk-mega-...

# Flask
FLASK_ENV=development
DEBUG=true
```

### Run Full Pipeline
```bash
# Step 1: Complete pipeline (scrape → WF1 → blog generation)
python orchestrate_full_pipeline.py

# This runs:
# 1. Scrapes articles from RSS feeds
# 2. Runs WF1 to create insights
# 3. Generates blogs for 5 accounts from insights
```

### View Results

**Via API:**
```bash
# Get all accounts
curl http://localhost:5000/api/accounts

# Get blogs for account_1
curl "http://localhost:5000/api/blogs?account_id=account_1"

# Get dashboard for account_1
curl http://localhost:5000/api/dashboard/account_1
```

**Via MongoDB:**
```bash
mongosh
> use megallm
> db.blogs.find({account_id: "account_1"}).pretty()
> db.content_insights.find().count()
> db.articles.find().count()
```

**Via Web Browser:**
```
http://localhost:5000
```

---

## 📊 Components

### 1. orchestrate_full_pipeline.py
**Full end-to-end orchestration**

```bash
python orchestrate_full_pipeline.py
```

Runs in sequence:
1. `step_1_scrape_articles()` - Scrapes RSS feeds
2. `step_2_create_insights()` - Runs WF1 analysis
3. `step_3_generate_blogs_for_accounts()` - Creates blogs for 5 accounts

Output: Complete pipeline execution with detailed logging

### 2. blog_platform/insight_scheduler.py
**Blog generation engine that consumes insights**

Key class: `InsightDrivenBlogScheduler`
- Fetches pending insights from MongoDB
- For each insight, generates 5 blog variants (one per account)
- Calls OpenRouter API for content generation
- Stores blogs with account_id in MongoDB

Used by:
- Flask API `/api/insights/generate-blogs` endpoint
- Direct Python imports for programmatic use

### 3. blog_platform/app.py
**Flask API with new endpoint**

New endpoint:
```
POST /api/insights/generate-blogs
```

Example:
```bash
curl -X POST http://localhost:5000/api/insights/generate-blogs
```

Response:
```json
{
  "success": true,
  "total_blogs": 75,
  "insights_processed": 15,
  "accounts": {
    "account_1": {"blogs_generated": 15},
    "account_2": {"blogs_generated": 15},
    ...
  }
}
```

### 4. Existing Components (Unchanged)
- `wf1.py` - WF1 Content Intelligence Pipeline
- `scrape_to_mongo.py` - RSS feed scraper
- `blog_platform/blog_generator.py` - OpenRouter API wrapper
- `workflow_common.py` - Shared utilities

---

## 📈 Data Flow

### Before (Old System)
```
[Random Topics] → [Blog Generator] → [5 Accounts] → [Blogs Collection]
(Disconnected from analysis)
```

### After (New System)
```
[RSS Feeds] → [Scraper] → [Articles] 
                              ↓
                         [WF1 Analysis] → [Insights]
                                            ↓
              [Blog Generator] ← [Per-Account Variants] ← [5 Accounts]
                                            ↓
                                   [Blogs Collection]
```

---

## 🔄 Workflow Details

### Step 1: Scraping
- Fetches from: TechCrunch, Medium, HackerNews RSS feeds
- Inserts to: `articles` collection
- Output fields: title, link, description, source, pub_date, guid

### Step 2: WF1 Analysis (Content Intelligence)
- Input: Articles from `articles` collection
- Model: DeepSeek V3.1 via MegaLLM API
- Output to: `content_insights` collection
- Analysis fields:
  - `hook_sentence` - Compelling opening
  - `core_claim` - Main takeaway
  - `megallm_tie_in` - Relevance to MegaLLM
  - `infra_data_point` - Technical detail
  - `angle_type` - Category (outage, pricing, benchmark, compliance, model_launch)
  - `status` - pending_generation → blogs_generated

### Step 3: Blog Generation (5 Account Distribution)
- Input: Insights from `content_insights` collection
- For each insight:
  - For each account (1-5):
    - Extract: hook_sentence, core_claim, infra_data_point
    - Call OpenRouter API with Qwen model (FREE)
    - Generate blog: title + body (600-900 words)
    - Store in `blogs` with account_id
    - Mark insight status = "blogs_generated"

**Example: 15 insights → 75 blogs (15 insights × 5 accounts)**

---

## 🎮 Usage Patterns

### Pattern 1: Full Pipeline (Recommended)
For a complete fresh run:
```bash
python orchestrate_full_pipeline.py
```
Time: 20-30 minutes (includes API calls)

### Pattern 2: Blog Generation Only
If insights already exist:
```bash
curl -X POST http://localhost:5000/api/insights/generate-blogs
```

### Pattern 3: Programmatic
```python
from orchestrate_full_pipeline import *
from blog_platform.app import db, blog_generator

# Run just blog generation step
results = step_3_generate_blogs_for_accounts()
print(f"Generated {results['total_blogs']} blogs")
```

### Pattern 4: Scheduled Task
```python
# In a cron job or scheduler
from blog_platform.insight_scheduler import generate_blogs_from_insights_now
from blog_platform.config import Config
from blog_platform.app import db, blog_generator

# Runs every 6 hours
result = generate_blogs_from_insights_now(
    db=db,
    generator=blog_generator,
    mongodb_uri=Config.MONGODB_URI,
    mongodb_db=Config.MONGODB_DB
)
```

---

## 📊 Monitoring

### Check Article Count
```bash
curl http://localhost:5000/api/dashboard/account_1 | jq .articles
```

### Check Insights
```bash
mongosh
> use megallm
> db.content_insights.find({status: "pending_generation"}).count()
> db.content_insights.find({status: "blogs_generated"}).count()
```

### Check Blogs
```bash
curl "http://localhost:5000/api/blogs?account_id=account_1&limit=5"
```

### View Logs
```bash
# Full pipeline logs
tail -f orchestration.log

# Flask logs
tail -f blog_platform.log
```

---

## ⚙️ Configuration

### Accounts (Hardcoded in config.py)
```python
ACCOUNTS = [
    {"id": "account_1", "name": "Account 1"},
    {"id": "account_2", "name": "Account 2"},
    {"id": "account_3", "name": "Account 3"},
    {"id": "account_4", "name": "Account 4"},
    {"id": "account_5", "name": "Account 5"},
]
```

### Blog Generation Settings
```python
BLOG_WORD_COUNT_MIN = 600
BLOG_WORD_COUNT_MAX = 900
BLOG_TEMPERATURE = 0.65
BLOG_MAX_TOKENS = 2000
```

### Topics (For Random Generation - Not Used Anymore)
```python
TOPICS = {
    "cost_optimization": {...},
    "performance": {...},
    "reliability": {...},
    "infrastructure": {...},
}
```

---

## 🔧 Troubleshooting

### Issue: "No pending insights found"
**Solution:**
1. Run scraping: `python orchestrate_full_pipeline.py`
2. Or check MongoDB: `db.content_insights.find().count()`

### Issue: "Blog generator not initialized"
**Solution:**
1. Check `.env` has `OPENROUTER_API_KEY`
2. Check `USE_OPENROUTER=true`
3. Restart Flask app

### Issue: "MongoDB connection refused"
**Solution:**
1. Start MongoDB: `mongod`
2. Check `MONGODB_URI` in `.env`
3. Verify database name: `MONGODB_DB=megallm`

### Issue: Slow Generation
**Normal:** 15 seconds per blog (API latency)
- 75 blogs = 1250 seconds = ~20 minutes
- No optimization yet (could add batching/parallelization)

---

## 📈 Performance

### Timeline (15 insights → 75 blogs)
- Step 1 (Scraping): 1-2 minutes
- Step 2 (WF1): 5-10 minutes (15 articles × 30-40 seconds each)
- Step 3 (Blog Gen): 15-20 minutes (75 API calls × 12-16 seconds each)
- **Total: 20-30 minutes**

### API Call Metrics
- Scraping: 3 RSS feeds
- WF1 Insights: 1 API call per article
- Blog Generation: 1 API call per (insight × account)

---

## 🔐 Security Notes

- API keys stored in `.env` (never commit!)
- MongoDB should have authentication in production
- OpenRouter API key = FREE tier (rate limited)
- MegaLLM API key = quota limited

---

## 📝 Files Structure

```
project_root/
├── orchestrate_full_pipeline.py        ← Main orchestration (NEW)
├── INTEGRATED_PIPELINE_GUIDE.py        ← Usage guide (NEW)
├── README_INTEGRATED.md                ← This file (NEW)
├── scrape_to_mongo.py                  ← RSS scraper (existing)
├── wf1.py                              ← WF1 analysis (existing)
├── wf2.py                              ← WF2 generation (existing)
├── wf3.py                              ← WF3 quality control (existing)
├── workflow_common.py                  ← Shared utils (existing)
└── blog_platform/
    ├── app.py                          ← Flask API (MODIFIED: added endpoint)
    ├── config.py                       ← Configuration (existing)
    ├── blog_generator.py               ← OpenRouter wrapper (existing)
    ├── insight_scheduler.py            ← Blog from insights (NEW)
    ├── database.py                     ← MongoDB wrapper (existing)
    ├── scheduler.py                    ← (original scheduler, not used)
    └── templates/
        └── index.html                  ← Dashboard (existing)
```

---

## 🚀 Next Steps

1. **Verify Setup**
   ```bash
   mongosh
   > db.version()  # Should print version
   ```

2. **Test Configuration**
   ```bash
   python -c "from blog_platform.config import Config; print(f'OpenRouter: {Config.MEGALLM_BASE_URL}')"
   ```

3. **Run Full Pipeline**
   ```bash
   python orchestrate_full_pipeline.py
   ```

4. **Monitor Progress**
   ```bash
   mongosh
   > use megallm
   > db.content_insights.find({status: "blogs_generated"}).count()
   ```

5. **View Results**
   ```
   http://localhost:5000
   ```

---

## 📞 Support

Check logs for detailed information:
- `orchestration.log` - Pipeline execution
- Flask console output - API requests
- MongoDB shell - Direct data inspection

All components log with timestamps and error details.

---

**Status: ✅ Ready for Testing**

The integrated pipeline is complete and ready to run. Execute `python orchestrate_full_pipeline.py` to see the full workflow in action!
