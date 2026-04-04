#!/usr/bin/env python3
"""Check insight generation status and history."""

import os
from pymongo import MongoClient
from workflow_common import bootstrap_env

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

print("=== CONTENT INSIGHTS COLLECTION ===")
insights = db.content_insights
total_insights = insights.count_documents({})
print(f"Total insights in collection: {total_insights}")

print("\nMost recent insights (by creation date):")
recent = insights.find().sort("_id", -1).limit(5)
for i, insight in enumerate(recent, 1):
    created = insight.get("created_at", insight.get("_id"))
    article = insight.get("article_id", "N/A")
    topic = insight.get("topic", "N/A")
    summary = insight.get("summary", "")[:50]
    print(f"  {i}. Created: {created}")
    print(f"     Topic: {topic}, Article: {str(article)[:20]}...")
    print(f"     Summary: {summary}...")

print("\n=== GENERATION HISTORY ===")
gen_hist = db.generation_history
total_events = gen_hist.count_documents({})
print(f"Total generation events: {total_events}")

print("\nLast 10 generation attempts:")
recent_gen = gen_hist.find().sort("_id", -1).limit(10)
for i, event in enumerate(recent_gen, 1):
    date = event.get("date", "N/A")
    account = event.get("account_id", "N/A")
    count = event.get("generated_count", 0)
    error = event.get("error", None)
    status = "ERROR" if error else "OK  "
    print(f"  {i}. [{status}] {date}: Account={account:<15} Generated={count}")
    if error:
        print(f"       Error: {error[:70]}")

print("\n=== ARTICLE STATUS BREAKDOWN ===")
articles = db.articles
by_source = {}
for source in ["techcrunch", "medium", "hn"]:
    pending = articles.count_documents({"status": "pending", "source": source})
    processed = articles.count_documents({"status": "processed", "source": source})
    by_source[source] = {"pending": pending, "processed": processed}

for source, counts in by_source.items():
    total = counts["pending"] + counts["processed"]
    if total > 0:
        pct = (counts["processed"] / total) * 100
        print(f"  {source.upper():<12}: {counts['pending']:3d} pending, {counts['processed']:3d} processed ({pct:5.1f}% done)")

print("\n=== KEY FINDINGS ===")
pending = articles.count_documents({"status": "pending"})
processed = articles.count_documents({"status": "processed"})
blogs_from_articles = db.blogs.count_documents({"source_type": "scraped_article"})

print(f"📊 Status: {processed} articles processed, {pending} pending")
print(f"📝 Blogs generated from articles: {blogs_from_articles}")

if processed > 0 and pending > 0:
    rate = (processed / (processed + pending)) * 100
    print(f"⏳ Processing rate: {rate:.1f}% complete")
    print(f"⚠️  Only {blogs_from_articles} out of {processed} processed articles have generated blogs!")
    print(f"    This suggests the insight generation might be failing or incomplete.")
