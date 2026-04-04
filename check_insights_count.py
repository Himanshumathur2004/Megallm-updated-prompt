#!/usr/bin/env python
"""Check if there are insights in MongoDB."""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
uri = os.getenv('MONGODB_URI')
db_name = os.getenv('MONGODB_DB', 'megallm_blog_platform')

client = MongoClient(uri)
db = client[db_name]

# Check collections
print('Collections:', db.list_collection_names())

# Check insights count
insights_count = db.content_insights.count_documents({})
print(f'Content insights: {insights_count}')

# Check pending insights
pending_count = db.content_insights.count_documents({"status": {"$in": ["pending_generation", "new"]}})
print(f'Pending insights: {pending_count}')

# Check articles count
articles_count = db.articles.count_documents({}) if 'articles' in db.list_collection_names() else 0
print(f'Articles: {articles_count}')

# Sample insight
if insights_count > 0:
    sample = db.content_insights.find_one()
    status = sample.get("status")
    print(f'Sample insight status: {status}')

client.close()
print("\nTo generate blogs, you need insights with status='pending_generation' or 'new'")
