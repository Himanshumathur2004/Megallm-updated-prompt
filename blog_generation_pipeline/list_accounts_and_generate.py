#!/usr/bin/env python3
"""List existing accounts."""

from pymongo import MongoClient
from workflow_common import bootstrap_env
import os

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

accounts = list(db.accounts.find())
print(f"Total accounts: {len(accounts)}")
for acc in accounts:
    acc_id = acc.get("id")
    acc_name = acc.get("name")
    print(f"  {acc_id}: {acc_name}")

# Now generate blogs using the first account
if accounts:
    account_id = accounts[0].get("id")
    print(f"\nUsing account: {account_id}")
    
    # Make HTTP request to generate blogs from articles
    import requests
    endpoint = "http://localhost:5000/api/blogs/generate-from-articles"
    
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
    except Exception as e:
        print(f"ERROR: {e}")
else:
    print("No accounts found!")
