#!/usr/bin/env python3
"""Show generated posts in MongoDB."""
from pymongo import MongoClient
import json

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB', 'megallm')]
posts = list(db.generated_posts.find().sort('_id', -1).limit(3))

print("=== GENERATED POSTS IN YOUR DB ===\n")
for p in posts:
    print(f"Post ID: {p['_id']}")
    print(f"Platform: {p.get('platform')}")
    print(f"Variant: {p.get('variant')}")
    print(f"Status: {p.get('status')}")
    content = p.get('content', '')[:200].replace('\n', ' ')
    print(f"Content Preview: {content}...\n")
