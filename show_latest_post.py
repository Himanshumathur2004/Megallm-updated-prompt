#!/usr/bin/env python3
"""Show latest generated post."""
from pymongo import MongoClient
import json

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB', 'megallm')]

# Get the latest generated post
latest = db.generated_posts.find_one(sort=[('_id', -1)])

if latest:
    print("\n" + "="*70)
    print("LATEST GENERATED POST IN YOUR DB")
    print("="*70)
    print(f"\nPost MongoDB ID: {latest['_id']}")
    print(f"Platform: {latest.get('platform')}")
    print(f"Variant: {latest.get('variant')}")
    print(f"Status: {latest.get('status')}")
    print(f"Insight ID: {latest.get('insight_id')}")
    print(f"Created: {latest.get('created_at')}")
    print(f"\n--- FULL CONTENT ---\n{latest.get('content', 'N/A')}")
    print("\n" + "="*70)
else:
    print("No generated posts found")

# Also show count summary
print("\nDatabase Summary:")
print(f"  Articles (pending): {db.articles.count_documents({'status': 'pending'})}")
print(f"  Insights (pending_generation): {db.content_insights.count_documents({'status': 'pending_generation'})}")
print(f"  Generated Posts (total): {db.generated_posts.count_documents({})}")
print(f"  Generated Posts (draft): {db.generated_posts.count_documents({'status': 'draft'})}")
