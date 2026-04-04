#!/usr/bin/env python3
"""Generate comprehensive status report on insight generation."""

from pymongo import MongoClient
from workflow_common import bootstrap_env
import os
from datetime import datetime, timezone

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

print("=" * 80)
print("INSIGHT GENERATION STATUS REPORT")
print("=" * 80)

# Check articles
articles = db.articles
total_articles = articles.count_documents({})
pending = articles.count_documents({"status": "pending"})
processed = articles.count_documents({"status": "processed"})

print(f"\n📰 ARTICLES COLLECTION")
print(f"  Total articles scraped: {total_articles}")
print(f"  Pending (not yet processed): {pending}")
print(f"  Processed (insights generated): {processed}")

# Breakdown by source
sources = ["medium", "techcrunch", "hn"]
for source in sources:
    count = articles.count_documents({"source": source})
    if count > 0:
        processed_count = articles.count_documents({"source": source, "status": "processed"})
        pct = (processed_count / count) * 100
        print(f"    {source.upper():<12}: {count:3d} articles ({processed_count:2d} processed, {pct:5.1f}%)")

# Check blogs generated from articles
blogs = db.blogs
total_blogs = blogs.count_documents({})
blogs_from_articles = blogs.count_documents({"source_type": "scraped_article"})
blogs_from_topics = total_blogs - blogs_from_articles

print(f"\n📝 BLOGS COLLECTION")
print(f"  Total blogs in system: {total_blogs}")
print(f"  Blogs from scraped articles: {blogs_from_articles}")
print(f"  Blogs from topic-based generation: {blogs_from_topics}")
print(f"  Blog status breakdown:")
print(f"    Draft blogs: {blogs.count_documents({'status': 'draft'})}")
print(f"    Posted blogs: {blogs.count_documents({'status': 'posted'})}")

# Check insights
insights = db.content_insights
insights_count = insights.count_documents({})

print(f"\n💡 CONTENT INSIGHTS")
print(f"  Total insights stored: {insights_count}")

# Check generation history
gen_hist = db.generation_history
gen_events = gen_hist.count_documents({})
successful_gen = gen_hist.count_documents({"error": None})
failed_gen = gen_hist.count_documents({"error": {"$ne": None}})

print(f"\n📊 GENERATION HISTORY")
print(f"  Total generation events: {gen_events}")
print(f"  Successful: {successful_gen}")
print(f"  Failed: {failed_gen}")

# Most recent generation
latest_gen = gen_hist.find_one(sort=[("_id", -1)])
if latest_gen:
    print(f"  Last generation:")
    print(f"    Blogs generated: {latest_gen.get('generated_count', 0)}")
    print(f"    Account: {latest_gen.get('account_id', 'N/A')}")
    if latest_gen.get('error'):
        print(f"    Error: {latest_gen.get('error')[:80]}")

# Get recent blog samples
print(f"\n📄 RECENT BLOGS FROM ARTICLES")
recent_blogs = blogs.find(
    {"source_type": "scraped_article"},
    {"title": 1, "created_at": 1, "topic": 1}
).sort("_id", -1).limit(5)

for i, blog in enumerate(recent_blogs, 1):
    title = blog.get("title", "N/A")
    print(f"  {i}. {title[:70]}")

# Summary analysis
print(f"\n{'='*80}")
print(f"ANALYSIS & INSIGHTS")
print(f"{'='*80}")

if processed > 0 and blogs_from_articles > 0:
    rate = (blogs_from_articles / processed) * 100
    print(f"✅ Insight Generation Working!")
    print(f"   - {processed} articles have been processed")
    print(f"   - {blogs_from_articles} blogs generated from those articles")
    print(f"   - Success rate: {rate:.1f}%")
    
    if rate < 50:
        print(f"   ⚠️  Low success rate - some articles may have insufficient content")
        
    if pending > 0:
        print(f"\n📌 Next Steps:")
        print(f"   - {pending} articles still pending")
        print(f"   - Run generation again to process remaining articles")
        print(f"   - Command: python gen_blogs_final.py")
else:
    print(f"⚠️  Insight Generation Has Issues:")
    if processed == 0:
        print(f"   - No articles have been processed yet")
        print(f"   - Run the generation script to start processing")
    if blogs_from_articles == 0:
        print(f"   - No blogs generated from articles yet")
        print(f"   - Check API configuration and Flask logs")

print()
