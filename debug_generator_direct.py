#!/usr/bin/env python
"""
Debug blog generation - test the blog_generator directly
"""

import sys
sys.path.insert(0, 'blog_platform')

from blog_platform.config import Config
from blog_platform.blog_generator import BlogGenerator
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

print("\n" + "="*80)
print("DIRECT BLOG GENERATOR TEST")
print("="*80)

# Step 1: Initialize blog generator
print("\n[Step 1] Initializing BlogGenerator...")
try:
    api_key = Config.OPENROUTER_API_KEY
    base_url = Config.OPENROUTER_BASE_URL
    model = Config.OPENROUTER_MODEL
    
    print(f"  API Key: {api_key[:30]}..." if api_key else "  API Key: NOT SET")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    
    if not api_key:
        print("  ERROR: OPENROUTER_API_KEY not set!")
        exit(1)
    
    generator = BlogGenerator(api_key, base_url, model)
    print("  ✓ BlogGenerator initialized")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Step 2: Get a pending insight from MongoDB
print("\n[Step 2] Fetching pending insights from MongoDB...")
try:
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB', 'megallm_blog_platform')]
    
    insight = db.content_insights.find_one({"status": {"$in": ["pending_generation", "new"]}})
    if not insight:
        print("  ERROR: No pending insights found!")
        exit(1)
    
    print(f"  ✓ Found insight: {insight.get('_id')}")
    print(f"    - hook: {insight.get('hook_sentence', 'N/A')[:60]}...")
    print(f"    - angle_type: {insight.get('angle_type', 'N/A')}")
    
    client.close()
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Step 3: Generate blog using the generator directly
print("\n[Step 3] Calling generate_blog with insight data...")
try:
    hook = insight.get("hook_sentence", "Infrastructure update")
    core_claim = insight.get("core_claim", "New development")
    infra_data_point = insight.get("infra_data_point", "")
    angle_type = insight.get("angle_type", "infrastructure")
    
    topic_map = {
        'outage': 'Reliability & Uptime',
        'pricing': 'Cost Optimization',
        'benchmark': 'Performance Metrics',
        'compliance': 'Infrastructure Security',
        'model_launch': 'AI/ML Performance',
        'infra_scaling': 'Infrastructure Scaling',
    }
    topic = topic_map.get(angle_type, 'Infrastructure Updates')
    keywords = [word.strip() for word in infra_data_point.split(',')[:3] if word.strip()]
    
    print(f"  Topic: {topic}")
    print(f"  Keywords: {keywords}")
    
    blog_data = generator.generate_blog(
        topic=topic,
        topic_description=hook,
        keywords=keywords,
        word_count_min=600,
        word_count_max=900
    )
    
    if blog_data:
        print(f"  ✓ Blog generated successfully!")
        print(f"    - Title: {blog_data['title'][:70]}...")
        print(f"    - Body length: {len(blog_data['body'])} chars")
    else:
        print(f"  ERROR: blog_generator.generate_blog returned None!")
        print(f"  This is the problem!")

except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
