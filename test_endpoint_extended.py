#!/usr/bin/env python
"""
Comprehensive test for blog generation endpoint with longer timeout.
Tests the /api/insights/generate-blogs endpoint with max timeout.
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
print("COMPREHENSIVE BLOG GENERATION TEST (WITH EXTENDED TIMEOUT)")
print("="*80)

# Step 1: Check database state
print("\n[Step 1] Checking database state BEFORE generation...")
try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    insights_total = db.content_insights.count_documents({})
    insights_pending = db.content_insights.count_documents({"status": {"$in": ["pending_generation", "new"]}})
    blogs_total_before = db.blogs.count_documents({})
    
    print(f"  Total insights: {insights_total}")
    print(f"  Pending insights: {insights_pending}")
    print(f"  Total blogs BEFORE: {blogs_total_before}")
    
    client.close()
except Exception as e:
    print(f"  ERROR checking database: {e}")
    exit(1)

# Step 2: Call the endpoint with 30-minute timeout
print("\n[Step 2] Calling /api/insights/generate-blogs endpoint...")
print("  (This may take 5-15 minutes - waiting for response...)")

start_time = time.time()
try:
    response = requests.post(
        f"{api_url}/api/insights/generate-blogs",
        json={"accounts": ["account_1", "account_2", "account_3"]},
        timeout=1800  # 30 minutes
    )
    elapsed = time.time() - start_time
    print(f"  ✓ Response received after {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"  Response status: {response.status_code}\n")
    
    result = response.json()
    print(f"  Response:")
    print(json.dumps(result, indent=2))
    
    # Check for errors
    if not result.get("success"):
        print(f"\n  ERROR: Endpoint returned success=False")
        print(f"  Error message: {result.get('error', 'N/A')}")
    else:
        print(f"\n  ✓ Success! Generated {result.get('total_blogs', 0)} blogs")
    
except requests.exceptions.Timeout:
    elapsed = time.time() - start_time
    print(f"  ⚠️  Request timed out after {elapsed/60:.1f} minutes")
    print(f"  (Generation may still be in progress)")
except requests.exceptions.ConnectionError:
    print(f"  ERROR: Could not connect to API at {api_url}")
    print(f"         Is the Flask app running? (python main.py)")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    exit(1)

# Step 3: Check database state after
print("\n[Step 3] Checking database state AFTER generation...")
try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    blogs_total_after = db.blogs.count_documents({})
    blogs_generated = blogs_total_after - blogs_total_before
    
    blogs_a1 = db.blogs.count_documents({"account_id": "account_1"})
    blogs_a2 = db.blogs.count_documents({"account_id": "account_2"})
    blogs_a3 = db.blogs.count_documents({"account_id": "account_3"})
    
    print(f"  Total blogs AFTER: {blogs_total_after}")
    print(f"  Blogs generated: {blogs_generated} ✓" if blogs_generated > 0 else f"  Blogs generated: {blogs_generated}")
    print(f"\n  Blogs by account:")
    print(f"    account_1: {blogs_a1}")
    print(f"    account_2: {blogs_a2}")
    print(f"    account_3: {blogs_a3}")
    
    # Show recent blogs
    recent = list(db.blogs.find({"status": "draft"}).sort("created_at", -1).limit(3))
    print(f"\n  Recent generated blogs:")
    for blog in recent:
        created_at = blog.get('created_at', 'N/A')[:10]
        print(f"    - {blog.get('title', 'Untitled')[:60]}... ({blog.get('account_id')}) [{created_at}]")
    
    client.close()
except Exception as e:
    print(f"  ERROR checking database: {e}")

print("\n" + "="*80)
print("TEST COMPLETE ✓")
print("="*80)
