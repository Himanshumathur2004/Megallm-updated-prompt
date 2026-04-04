#!/usr/bin/env python
"""Quick test of blog generation with valid API key"""

import requests
import json
import time
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB')]

print('\nQUICK GENERATION TEST')
print('='*60)

# Reset insights
result = db.content_insights.update_many({}, {'$set': {'status': 'pending_generation'}})
print(f'✓ Reset insights: {result.modified_count}')

# Check before
blogs_before = db.blogs.count_documents({})
pending = db.content_insights.count_documents({'status': 'pending_generation'})
print(f'📊 Blogs before: {blogs_before}')
print(f'📋 Pending insights: {pending}')

client.close()

# Call endpoint
print('\n🚀 Generating for account_1...')
print('   (waiting for response...)\n')

start = time.time()
try:
    r = requests.post(
        'http://localhost:5000/api/insights/generate-blogs',
        json={'accounts': ['account_1']},
        timeout=300
    )
    elapsed = time.time() - start

    print(f'✓ Status: {r.status_code} ({elapsed:.1f}s)')
    data = r.json()
    print(f'\nEndpoint Response:')
    print(f'  success: {data.get("success")}')
    print(f'  total_blogs: {data.get("total_blogs")}')
    print(f'  articles_scraped: {data.get("articles_scraped")}')
    
except requests.exceptions.Timeout:
    elapsed = time.time() - start
    print(f'⏱️  Timeout after {elapsed:.1f}s (generation still running)')
except Exception as e:
    print(f'❌ Error: {e}')

# Check after
print('\n📊 Checking results...')
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB')]
blogs_after = db.blogs.count_documents({})
new_blogs = blogs_after - blogs_before

print(f'  Blogs before: {blogs_before}')
print(f'  Blogs after: {blogs_after}')
print(f'  Generated: {new_blogs} new blogs')

if new_blogs > 0:
    print(f'\n✅ SUCCESS! Blogs are being generated!')
    # Show sample
    sample = list(db.blogs.find({'account_id': 'account_1'}).sort('created_at', -1).limit(1))
    if sample:
        print(f'\n📝 Sample generated blog:')
        print(f'   Title: {sample[0].get("title", "")[:70]}...')
        print(f'   Account: {sample[0].get("account_id")}')
        print(f'   Status: {sample[0].get("status")}')
else:
    print(f'\n⚠️  No new blogs generated')

client.close()
print('\n' + '='*60)
