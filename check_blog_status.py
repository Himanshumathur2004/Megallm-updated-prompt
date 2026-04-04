#!/usr/bin/env python
"""Check blog generation status"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB')]

print("\n" + "="*70)
print("BLOG GENERATION STATUS CHECK")
print("="*70)

# Total blog count
total = db.blogs.count_documents({})
print(f'\nTotal blogs in DB: {total}')

# Count by status
statuses = {}
for doc in db.blogs.find({}, {'status': 1}):
    status = doc.get('status', 'unknown')
    statuses[status] = statuses.get(status, 0) + 1

print(f'Status breakdown: {statuses}')

# Recently generated (last 1 hour)
one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
recent = db.blogs.count_documents({
    'created_at': {'$gte': one_hour_ago}
})
print(f'Blogs created in last hour: {recent}')

# Show 5 most recent
print('\nMost recent 5 blogs:')
for blog in db.blogs.find().sort('created_at', -1).limit(5):
    created = blog.get('created_at', 'unknown')
    title = blog.get('title', 'Untitled')[:50]
    status = blog.get('status', 'unknown')
    account = blog.get('account_id', 'unknown')
    print(f'  [{status:6}] {title}... ({account})')

# Blogs per account
print('\nBlogs per account:')
for account_id in ['account_1', 'account_2', 'account_3', 'account_4', 'account_5']:
    count = db.blogs.count_documents({'account_id': account_id})
    print(f'  {account_id}: {count}')

# Check insight status
insights_pending = db.content_insights.count_documents({'status': 'pending_generation'})
insights_generated = db.content_insights.count_documents({'status': 'blogs_generated'})
print(f'\nInsight status:')
print(f'  Pending generation: {insights_pending}')
print(f'  Blogs generated: {insights_generated}')

client.close()

print("="*70)
