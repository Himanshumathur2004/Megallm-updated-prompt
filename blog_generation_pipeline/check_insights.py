#!/usr/bin/env python3
"""Check if insights are being generated from scraped articles."""

import os
from pathlib import Path
from pymongo import MongoClient
from workflow_common import bootstrap_env

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

# Check articles collection
articles = db.articles
pending = articles.count_documents({"status": "pending"})
processed = articles.count_documents({"status": "processed"})
total = articles.count_documents({})

print("=== ARTICLES COLLECTION ===")
print(f"Total articles: {total}")
print(f"Pending (not yet processed): {pending}")
print(f"Processed: {processed}")
print()

if pending > 0:
    print("First 3 pending articles:")
    for i, article in enumerate(articles.find({"status": "pending"}).limit(3), 1):
        print(f"\n{i}. Title: {article.get('title', 'N/A')[:60]}")
        print(f"   Source: {article.get('source', 'N/A')}")
        print(f"   Content length: {len(article.get('content', ''))} chars")
        print(f"   Categories: {article.get('categories', [])}")

# Check blogs collection
blogs = db.blogs
blogs_count = blogs.count_documents({})
drafts = blogs.count_documents({"status": "draft"})
posted = blogs.count_documents({"status": "posted"})
scraped_source = blogs.count_documents({"source_type": "scraped_article"})

print("\n=== BLOGS COLLECTION ===")
print(f"Total blogs: {blogs_count}")
print(f"Draft blogs: {drafts}")
print(f"Posted blogs: {posted}")
print(f"Blogs from scraped articles: {scraped_source}")

# Check all collections
collections = db.list_collection_names()
print("\n=== ALL COLLECTIONS ===")
for col in collections:
    count = db[col].count_documents({})
    print(f"  {col}: {count} documents")

# Analysis
print("\n=== ANALYSIS ===")
if pending > 0 and scraped_source == 0:
    print("⚠️  ISSUE: Articles have been scraped and are pending, but NO blogs have been generated from them!")
    print("   The insight generation pipeline is NOT running.")
elif pending > 0 and scraped_source > 0:
    print("✅ GOOD: Insights are being generated from articles")
    print(f"   {scraped_source} blogs created from {total} articles")
elif pending == 0:
    print("⚠️  WARNING: No pending articles found!")
    print("   Either articles haven't been scraped, or all have been processed")
