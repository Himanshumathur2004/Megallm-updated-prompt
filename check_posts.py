#!/usr/bin/env python3
from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['megallm']

# Count posts by type
pipeline = [{'$group': {'_id': '$type', 'count': {'$sum': 1}}}]
results = list(db.generated_posts.aggregate(pipeline))

print("\n=== GENERATION SUMMARY ===")
print(f"Total posts in DB: {db.generated_posts.count_documents({})}")
print("\nBreakdown by type:")
for result in results:
    print(f"  {result['_id'] or 'unknown'}: {result['count']}")

insights = db.content_insights.count_documents({})
pending = db.content_insights.count_documents({'status': 'pending_generation'})
done = db.content_insights.count_documents({'status': 'generation_done'})

print(f"\nInsights:")
print(f"  Total: {insights}")
print(f"  Pending: {pending}")
print(f"  Done: {done}")
