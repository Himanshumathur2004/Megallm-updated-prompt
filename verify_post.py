#!/usr/bin/env python3
"""Verify generated post exists and show how to query it."""
from pymongo import MongoClient
from bson import ObjectId

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB', 'megallm')]

# Check if the post exists
post_id = ObjectId('69c2b21ac5134aa57c2009b6')
post = db.generated_posts.find_one({'_id': post_id})

if post:
    print('\n✓ POST FOUND IN DATABASE\n')
    print(f'  MongoDB ID: {post["_id"]}')
    print(f'  Platform: {post.get("platform")}')
    print(f'  Status: {post.get("status")}')
    print(f'  Insight ID: {post.get("insight_id")}')
    print(f'  Created: {post.get("created_at")}')
    print('\n--- QUERY TO FIND THIS POST ---\n')
    print('In MongoDB Compass or Studio 3T, use this query:')
    print('  { "_id": ObjectId("69c2b21ac5134aa57c2009b6") }')
    print('\nIn mongo shell:')
    print('  db.generated_posts.findOne({ _id: ObjectId("69c2b21ac5134aa57c2009b6") })')
else:
    print('\n✗ POST NOT FOUND\n')

# Show all posts
all_count = db.generated_posts.count_documents({})
print(f'\n--- DATABASE STATUS ---')
print(f'Total posts in generated_posts collection: {all_count}')

# List all post IDs
all_posts = list(db.generated_posts.find({}, {'_id': 1, 'platform': 1, 'status': 1}).sort('_id', -1).limit(5))
print('\nMost recent 5 posts:')
for p in all_posts:
    print(f'  {p["_id"]} - {p.get("platform")} ({p.get("status")})')
