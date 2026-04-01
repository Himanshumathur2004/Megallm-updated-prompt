#!/usr/bin/env python3
"""Show final newsletter generation results."""
from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['megallm']

nl_count = db.generated_posts.count_documents({'platform': 'newsletter'})
pending = db.content_insights.count_documents({'status': 'pending_generation'})

print("=" * 70)
print("NEWSLETTER GENERATION COMPLETE")
print("=" * 70)
print(f"\n✅ Newsletter posts created: {nl_count}")
print(f"⏳ Insights still pending: {pending}")

print("\n📰 Sample Newsletter Posts:")
posts = list(db.generated_posts.find({'platform': 'newsletter'}).limit(3))
for i, post in enumerate(posts, 1):
    content = post.get('content', '')
    preview = content[:150].replace('\n', ' ') + '...'
    print(f"\n   {i}. {preview}")

print("\n" + "=" * 70)
