#!/usr/bin/env python
"""
Fix: Reset insights to pending_generation status so they can be used for blog generation
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB', 'megallm_blog_platform')]

print("\n" + "="*80)
print("RESETTING INSIGHTS STATUS")
print("="*80)

# Find all insights
all_insights = db.content_insights.find()
insight_ids = []
for insight in all_insights:
    insight_ids.append(insight['_id'])

if not insight_ids:
    print("No insights found in database!")
    exit(1)

print(f"\nFound {len(insight_ids)} insights")
print(f"Resetting status from 'blogs_generated'/'blog_generated' to 'pending_generation'...")

# Reset status
result = db.content_insights.update_many(
    {"_id": {"$in": insight_ids}},
    {"$set": {"status": "pending_generation"}}
)

print(f"✓ Updated {result.modified_count} insights")

# Verify
statuses = {}
for i in db.content_insights.find():
    status = i.get('status')
    statuses[status] = statuses.get(status, 0) + 1

print(f"\nNew statuses:")
for status, count in statuses.items():
    print(f"  - {status}: {count}")

client.close()

print("\n" + "="*80)
print("RESET COMPLETE - Insights are now ready for blog generation!")
print("="*80)
