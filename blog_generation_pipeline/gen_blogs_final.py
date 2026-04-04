#!/usr/bin/env python3
"""Generate blogs from pending articles using correct account_id."""

from pymongo import MongoClient
from workflow_common import bootstrap_env
import os
import requests

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

first_account = db.accounts.find_one()
if first_account:
    account_id = first_account.get("account_id")
    account_name = first_account.get("name")
    print(f"Using account: {account_name} ({account_id})")
    
    endpoint = "http://localhost:5000/api/blogs/generate-from-articles"
    payload = {"account_id": account_id, "num_blogs": 40}
    
    print(f"\n🚀 Generating blogs from 40 pending articles...")
    print(f"This will take a while as each blog is generated via OpenRouter API...\n")
    
    try:
        response = requests.post(endpoint, json=payload, timeout=600)
        result = response.json()
        
        articles_processed = result.get("articles_processed", 0)
        blogs_generated = result.get("generated_count", 0)
        message = result.get("message", "N/A")
        error = result.get("error")
        
        print(f"📊 Results:")
        print(f"  Articles processed: {articles_processed}")
        print(f"  Blogs generated: {blogs_generated}")
        print(f"  Message: {message}")
        
        if error:
            print(f"  Error: {error}")
        elif blogs_generated > 0:
            print(f"\n✅ SUCCESS! Generated {blogs_generated} blog insights from articles")
        else:
            print(f"\n⚠️ No blogs were generated. Check Flask logs for details.")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Flask at http://localhost:5000")
        print("Make sure Flask is running: python blog_platform/app.py")
    except requests.exceptions.Timeout:
        print("ERROR: Request timeout - blog generation took too long")
        print("Processing may still be happening in the background")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
else:
    print("ERROR: No accounts found in database")
