#!/usr/bin/env python3
"""Display all generated posts from MongoDB in a readable format."""
from pymongo import MongoClient
import json

db = MongoClient('mongodb://localhost:27017')['megallm']

posts = list(db.generated_posts.find({}).sort('_id', -1))

print("\n" + "="*80)
print("ALL GENERATED POSTS IN YOUR DATABASE")
print("="*80)
print(f"\nTotal: {len(posts)} posts\n")

for i, post in enumerate(posts, 1):
    print(f"\n{i}. {post['_id']}")
    print(f"   Platform: {post.get('platform')} | Variant: {post.get('variant')} | Status: {post.get('status')}")
    content = post.get('content', '')
    if post.get('platform') == 'twitter':
        # Twitter is stored as JSON array
        try:
            tweets = json.loads(content)
            print(f"   Tweets ({len(tweets)} in thread):")
            for j, tweet in enumerate(tweets[:2], 1):  # Show first 2
                print(f"     Tweet {j}: {tweet[:80]}...")
        except:
            print(f"   Content: {content[:100]}...")
    else:
        preview = content[:120].replace('\n', ' ')
        print(f"   Content: {preview}...")
    print()

print("="*80)
print("To see full content of a post, run:")
print('  python show_post_detail.py <post_id>')
print("="*80)
