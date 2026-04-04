#!/usr/bin/env python
"""
Comprehensive test for blog generation endpoint.
Tests the /api/insights/generate-blogs endpoint step by step.
"""

import requests
import json
import time
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()
api_url = "http://localhost:5000"
mongodb_uri = os.getenv('MONGODB_URI')
mongodb_db = os.getenv('MONGODB_DB', 'megallm_blog_platform')

print("\n" + "="*80)
print("BLOG GENERATION ENDPOINT TEST")
print("="*80)

# Step 1: Check database state
print("\n[Step 1] Checking database state...")
try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    insights_total = db.content_insights.count_documents({})
    insights_pending = db.content_insights.count_documents({"status": {"$in": ["pending_generation", "new"]}})
    blogs_total = db.blogs.count_documents({})
    
    print(f"  Total insights: {insights_total}")
    print(f"  Pending insights: {insights_pending}")
    print(f"  Total blogs: {blogs_total}")
    
    # Show sample pending insights
    if insights_pending > 0:
        samples = list(db.content_insights.find({"status": {"$in": ["pending_generation", "new"]}}).limit(2))
        for sample in samples:
            print(f"\n  Sample pending insight:")
            print(f"    - _id: {sample.get('_id')}")
            print(f"    - status: {sample.get('status')}")
            print(f"    - hook_sentence: {sample.get('hook_sentence', 'N/A')[:80]}...")
            print(f"    - angle_type: {sample.get('angle_type', 'N/A')}")
    
    client.close()
except Exception as e:
    print(f"  ERROR checking database: {e}")
    exit(1)

# Step 2: Call the endpoint
print("\n[Step 2] Calling /api/insights/generate-blogs endpoint...")
try:
    response = requests.post(
        f"{api_url}/api/insights/generate-blogs",
        json={"accounts": ["account_1", "account_2"]},
        timeout=300
    )
    print(f"  Response status: {response.status_code}")
    
    result = response.json()
    print(f"\n  Response:")
    print(json.dumps(result, indent=2))
    
    # Check for errors
    if not result.get("success"):
        print(f"\n  ERROR: Endpoint returned success=False")
        print(f"  Error message: {result.get('error', 'N/A')}")
    
except requests.exceptions.Timeout:
    print(f"  ERROR: Request timed out (300 seconds)")
except requests.exceptions.ConnectionError:
    print(f"  ERROR: Could not connect to API at {api_url}")
    print(f"         Is the Flask app running? (python main.py)")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    exit(1)

# Step 3: Check database state after
print("\n[Step 3] Checking database state after generation...")
try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    blogs_total_after = db.blogs.count_documents({})
    blogs_for_account1 = db.blogs.count_documents({"account_id": "account_1"})
    blogs_for_account2 = db.blogs.count_documents({"account_id": "account_2"})
    
    print(f"  Total blogs now: {blogs_total_after} (was {blogs_total})")
    print(f"  Blogs for account_1: {blogs_for_account1}")
    print(f"  Blogs for account_2: {blogs_for_account2}")
    
    # Show recent blogs
    recent = list(db.blogs.find({"status": "draft"}).sort("created_at", -1).limit(2))
    print(f"\n  Recent blogs:")
    for blog in recent:
        print(f"    - {blog.get('title', 'Untitled')[:60]}... ({blog.get('account_id')})")
    
    client.close()
except Exception as e:
    print(f"  ERROR checking database: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
