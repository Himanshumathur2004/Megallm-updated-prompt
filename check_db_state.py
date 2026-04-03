#!/usr/bin/env python3
"""Check current database state before running WF2."""

import os
from pymongo import MongoClient
from workflow_common import bootstrap_env

bootstrap_env(__file__)

client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB', 'megallm')]

print("=" * 60)
print("DATABASE STATE CHECK")
print("=" * 60)

# Articles
articles_count = db.articles.count_documents({})
print(f"\nTotal articles: {articles_count}")

# Insights by status
statuses = {}
for doc in db.content_insights.find({}, {"status": 1}):
    s = doc.get("status", "unknown")
    statuses[s] = statuses.get(s, 0) + 1

print("\nInsights by status:")
for status, count in sorted(statuses.items()):
    print(f"  {status}: {count}")

# Show pending_generation insights
pending = list(db.content_insights.find({"status": "pending_generation"}, {"_id": 1, "hook_sentence": 1}).limit(5))
print(f"\nPending generation insights ({len(pending)}):")
for p in pending:
    hook = p.get('hook_sentence', '')[:60]
    print(f"  {p['_id']}: {hook}")

# Show generated_posts
generated_count = db.generated_posts.count_documents({})
generated_by_status = {}
for doc in db.generated_posts.find({}, {"status": 1}):
    s = doc.get("status", "unknown")
    generated_by_status[s] = generated_by_status.get(s, 0) + 1

print(f"\nGenerated posts by status:")
for status, count in sorted(generated_by_status.items()):
    print(f"  {status}: {count}")

client.close()
