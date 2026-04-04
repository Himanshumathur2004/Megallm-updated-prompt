#!/usr/bin/env python3
"""Check account structure and generate blogs."""

from pymongo import MongoClient
from workflow_common import bootstrap_env
import os
import json

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

accounts_coll = db.accounts
accounts = list(accounts_coll.find())
print(f"Total accounts: {len(accounts)}")

if accounts:
    print("\nFirst account structure:")
    first = accounts[0]
    for key, value in first.items():
        if key != "_id":
            print(f"  {key}: {value}")

# Try to use the first account
if accounts:
    first_account = accounts[0]
    # Get the actual ID to use
    account_id = first_account.get("id") or str(first_account.get("_id"))
    
    print(f"\nUsing account_id: {account_id}")
    
    # Make HTTP request to generate blogs from articles
    import requests
    endpoint = "http://localhost:5000/api/blogs/generate-from-articles"
    
    print(f"\n🚀 Generating blogs from 40 pending articles...")
    print(f"Calling: POST {endpoint}")
    
    payload = {"account_id": account_id, "num_blogs": 40}
    
    try:
        response = requests.post(endpoint, json=payload, timeout=600)
        result = response.json()
        print(f"\nResponse status: {response.status_code}")
        print(f"Articles processed: {result.get('articles_processed', 0)}")
        print(f"Blogs generated: {result.get('generated_count', 0)}")
        print(f"Message: {result.get('message', 'N/A')}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Flask at http://localhost:5000")
        print("Make sure Flask is running: python blog_platform/app.py")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
else:
    print("No accounts found!")
