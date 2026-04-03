#!/usr/bin/env python3
"""Display scraped articles."""

from pymongo import MongoClient

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB', 'megallm')]

# First, let's check the latest articles by date
articles = db.articles.find().sort('isoDate', -1).limit(5)

print('=' * 90)
print('LATEST 5 ARTICLES IN DATABASE')
print('=' * 90)

count = 0
for art in articles:
    count += 1
    print(f"\n{count}. {art.get('title', 'N/A')[:75]}")
    print(f"   Source: {art.get('source', 'N/A')}")
    print(f"   Link: {art.get('link', 'N/A')[:70]}")
    print(f"   Date: {art.get('isoDate', 'N/A')}")
    print(f"   Status: {art.get('status', 'N/A')}")

total = db.articles.count_documents({})
print(f"\n{'=' * 90}")
print(f"Total articles in database: {total}")
