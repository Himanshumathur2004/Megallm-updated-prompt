#!/usr/bin/env python
"""
Direct test of the insight-driven blog generation pipeline
Tests each step with detailed error reporting
"""

import sys
sys.path.insert(0, 'blog_platform')

from config import Config
from database import Database
from blog_generator import BlogGenerator
from insight_scheduler import InsightDrivenBlogScheduler
from dotenv import load_dotenv
import os
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s:%(levelname)s: %(message)s'
)

load_dotenv()

print("\n" + "="*80)
print("FULL PIPELINE TEST - Direct Blog Generation")
print("="*80)

# Step 1: Initialize components
print("\n[Step 1] Initializing components...")
try:
    db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
    generator = BlogGenerator(
        Config.OPENROUTER_API_KEY,
        Config.OPENROUTER_BASE_URL,
        Config.OPENROUTER_MODEL
    )
    scheduler = InsightDrivenBlogScheduler(
        db, generator,
        Config.MONGODB_URI,
        Config.MONGODB_DB
    )
    print("  ✓ All components initialized")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 2: Get pending insights
print("\n[Step 2] Getting pending insights...")
try:
    insights = scheduler.get_pending_insights(limit=2)
    print(f"  Found {len(insights)} pending insights")
    if not insights:
        print("  No insights available")
        exit(0)
    
    insight = insights[0]
    print(f"  First insight: {insight.get('_id')}")
    print(f"    hook: {insight.get('hook_sentence', 'N/A')[:60]}...")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Try to generate a blog from insight
print("\n[Step 3] Generating blog from insight...")
try:
    blog_data = scheduler.generate_blogs_from_insight(insight, "account_test")
    
    if blog_data:
        print(f"  ✓ Blog generated!")
        print(f"    - Title: {blog_data['title'][:70]}...")
        print(f"    - Body length: {len(blog_data['body'])} chars")
    else:
        print(f"  ERROR: generate_blogs_from_insight returned None!")
        print(f"  This is the root cause of the problem!")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
