#!/usr/bin/env python3
"""
USAGE GUIDE: INTEGRATED PIPELINE
Scrape → WF1 Insights → Blog Generation for 5 Accounts

This script shows how to use the complete integrated pipeline.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workflow_common import bootstrap_env
bootstrap_env(__file__)

print("\n" + "=" * 80)
print("INTEGRATED PIPELINE GUIDE")
print("=" * 80)

print("""
OVERVIEW:
--------
This pipeline connects content scraping, intelligence analysis, and blog creation:
  1. SCRAPE: RSS feeds → articles collection
  2. ANALYZE (WF1): articles → content_insights collection  
  3. GENERATE: insights → blogs (5 account variants)

COMPONENTS:
-----------
1. orchestrate_full_pipeline.py
   - Main orchestration script
   - Runs: Scrape → WF1 → Blog Generation
   - Usage: python orchestrate_full_pipeline.py

2. blog_platform/insight_scheduler.py
   - InsightDrivenBlogScheduler class
   - Generates blogs from WF1 insights for 5 accounts
   - Used by Flask API and orchestration

3. blog_platform/app.py - New Endpoint
   - POST /api/insights/generate-blogs
   - Triggers blog generation from pending insights
   - Returns: blogs_by_account summary

WORKFLOW:
---------

OPTION 1: Run Full Pipeline (Recommended for First Time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ python orchestrate_full_pipeline.py
  
  This will:
  ✓ Scrape articles from RSS feeds (TechCrunch, Medium, HN)
  ✓ Run WF1 to create insights
  ✓ Generate blogs for 5 accounts from insights
  ✓ Store blogs in blogs collection with account_id
  ✓ Update insight status to blogs_generated
  

OPTION 2: Trigger Blog Generation from Random Insights
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
While Flask API is running:
  $ curl -X POST http://localhost:5000/api/insights/generate-blogs
  
  Response:
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


OPTION 3: Generate Blogs Only (Skip Scrape + WF1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If insights already exist in content_insights collection:
  
  from pymongo import MongoClient
  from blog_platform.insight_scheduler import InsightDrivenBlogScheduler
  from blog_platform.app import blog_generator, db
  from blog_platform.config import Config
  
  scheduler = InsightDrivenBlogScheduler(
      db=db,
      generator=blog_generator,
      mongodb_uri=Config.MONGODB_URI,
      mongodb_db=Config.MONGODB_DB
  )
  result = scheduler.run_once()
  print(result)


DATABASE COLLECTIONS:
─────────────────────
Before Pipeline:
  - articles: Raw scraped content from RSS feeds
  - content_insights: Empty (to be filled by WF1)
  
After Pipeline:
  - articles: ✓ Filled with scraped content
  - content_insights: ✓ Filled with WF1 analysis
  - blogs: ✓ Filled with 5 account variants per insight


KEY CHANGES FROM BEFORE:
────────────────────────
Before:
  - Blog platform generated on a 2-hour schedule with random topics
  - Disconnected from WF1 analysis
  - No insight-based content generation

After:
  - Blog platform generates from actual WF1 insights
  - Each insight creates 5 blog variants (one per account)
  - Fully integrated pipeline: Scrape → Analyze → Generate
  - Can be triggered manually via API or orchestration script


CONFIGURATION:
──────────────
The following .env settings are important:

  # MongoDB
  MONGODB_URI=mongodb://localhost:27017
  MONGODB_DB=megallm
  
  # OpenRouter API (for blog generation)
  OPENROUTER_API_KEY=sk-or-v1-...
  OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free
  USE_OPENROUTER=true
  
  # MegaLLM API (for WF1 insights)
  MEGALLM_API_KEY=sk-mega-...
  
  # Flask
  FLASK_ENV=development


MONITORING:
──────────
Check blog generation progress:
  $ curl http://localhost:5000/api/accounts -s | jq .
  $ curl "http://localhost:5000/api/blogs?account_id=account_1" -s | jq .

Check insights in MongoDB:
  $ mongosh
  > use megallm
  > db.content_insights.find({status: "blogs_generated"}).count()
  > db.blogs.find({account_id: "account_1"}).count()


TROUBLESHOOTING:
────────────────
1. No insights found
   - Ensure scraping and WF1 have been run first
   - Check: db.content_insights.countDocuments()

2. API Key errors
   - For blogs: Check OPENROUTER_API_KEY in .env
   - For WF1: Check MEGALLM_API_KEY in .env

3. MongoDB connection failed
   - Ensure MongoDB is running: mongod
   - Check MONGODB_URI and MONGODB_DB in config

4. Slow generation
   - API calls take 10-30 seconds per blog
   - 15 insights × 5 accounts = ~75 API calls = 20-30 minutes
  

NEXT STEPS:
───────────
1. Verify MongoDB is running (localhost:27017)
2. Verify .env file has valid API keys
3. Run full pipeline: python orchestrate_full_pipeline.py
4. Monitor Flask dashboard: http://localhost:5000
5. Query MongoDB for blogs: db.blogs.find()

""")

print("=" * 80)
print("Ready to run the integrated pipeline!")
print("=" * 80)
