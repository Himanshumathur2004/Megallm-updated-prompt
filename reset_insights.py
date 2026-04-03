#!/usr/bin/env python3
"""Reset insights to pending_generation so they can be generated for blog only."""

from pymongo import MongoClient
from bson import ObjectId

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB', 'megallm')]

# Check current statuses
print("Current insight statuses:")
statuses = db.content_insights.aggregate([
    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for result in statuses:
    print(f"  {result['_id']}: {result['count']}")

# Reset all generation_done insights back to pending_generation
print("\nResetting insights to pending_generation...")
result = db.content_insights.update_many(
    {"status": "generation_done"},
    {"$set": {"status": "pending_generation"}}
)
print(f"Updated {result.modified_count} insights")

# Verify
print("\nNew insight statuses:")
statuses = db.content_insights.aggregate([
    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for result in statuses:
    print(f"  {result['_id']}: {result['count']}")
