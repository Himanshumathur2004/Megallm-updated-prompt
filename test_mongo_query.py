#!/usr/bin/env python
"""Test MongoDB query"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB')]

# Same query as in debug script
insight = db.content_insights.find_one({'status': {'$in': ['pending_generation', 'new']}})
print(f'Query with $in: {insight is not None}')
if insight:
    print(f'Found: {insight.get("_id")}')

# Direct query
insight2 = db.content_insights.find_one({'status': 'pending_generation'})
print(f'Direct query: {insight2 is not None}')
if insight2:
    print(f'Found: {insight2.get("_id")}')

# Count
count = db.content_insights.count_documents({'status': 'pending_generation'})
print(f'Count with pending_generation: {count}')

client.close()
