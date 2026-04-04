#!/usr/bin/env python3
"""Generate insights from pending articles."""

import os
import requests
from pymongo import MongoClient
from workflow_common import bootstrap_env

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")
flask_url = "http://localhost:5000"

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

print("=" * 70)
print("BLOG GENERATION FROM SCRAPED ARTICLES")
print("=" * 70)

articles = db.articles
pending = articles.count_documents({"status": "pending"})
print(f"\n📰 Pending articles to process: {pending}")

if pending == 0:
    print("✅ No pending articles!")
    exit(0)

# Check for account
account = db.accounts.find_one({"id": "account_1"})
if not account:
    print("❌ Account 'account_1' not found")
    exit(1)

print(f"👤 Account: {account.get('name', 'Default Account')}")

# Try to call the Flask endpoint to generate blogs from articles
print(f"\n🚀 Calling {flask_url}/api/blogs/generate-from-articles...")
try:
    response = requests.post(
        f"{flask_url}/api/blogs/generate-from-articles",
        json={
            "account_id": "account_1",
            "num_blogs": pending  # Process all pending articles
        },
        timeout=600  # 10 minute timeout since this can take a while
    )
    
    print(f"Response status: {response.status_code}")
    data = response.json()
    
    print(f"\n📊 Results:")
    print(f"  Articles processed: {data.get('articles_processed', 0)}")
    print(f"  Blogs generated: {data.get('generated_count', 0)}")
    
    if data.get('error'):
        print(f"  ❌ Error: {data.get('error')}")
    else:
        print(f"  ✅ Success: {data.get('message')}")
        
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to Flask server at http://localhost:5000")
    print("   Make sure you run: python blog_platform/app.py")
except Exception as e:
    print(f"❌ Error: {e}")
