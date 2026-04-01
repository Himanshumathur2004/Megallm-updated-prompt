#!/usr/bin/env python3
"""Generate NEWSLETTER variant posts only from pending insights."""

import argparse
import logging
import os
from datetime import datetime, timezone
from workflow_common import bootstrap_env

# Bootstrap environment BEFORE importing wf2
bootstrap_env(__file__)

from bson import ObjectId
from wf2 import (
    _build_config, LLMClient, fetch_insight, generate_newsletter,
    write_posts
)
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Generate newsletter-only posts from pending insights")
parser.add_argument(
    "--model",
    default="",
    help="Override WF2 model for this run (example: openai/gpt-4o-mini)",
)
args = parser.parse_args()

if args.model:
    os.environ["WF2_MODEL"] = args.model

db = MongoClient('mongodb://localhost:27017')['megallm']
collection = db.generated_posts

# Get ALL pending insights
insights = list(db.content_insights.find({'status': 'pending_generation'}))

print(f"Generating NEWSLETTER posts for {len(insights)} insights...")
print("=" * 60)

config = _build_config()
print(f"Using model: {config.model}")
llm = LLMClient(config.api_key, config.api_base_url, config.model)

for insight in insights:
    insight_id = str(insight['_id'])
    print(f"\nProcessing insight: {insight_id}")
    
    try:
        # Generate only newsletter
        newsletter_text = generate_newsletter(insight, llm, config)
        logger.info(f"Newsletter generated: {len(newsletter_text)} chars")
        
        # Build insert payload
        now = datetime.now(timezone.utc).isoformat()
        try:
            content_insight_id = ObjectId(insight_id)
        except Exception:
            content_insight_id = insight_id
        
        post = {
            "insight_id": insight_id,
            "content_insight_id": content_insight_id,
            "platform": "newsletter",
            "variant": "A",
            "content": newsletter_text,
            "meta": {},
            "status": "draft",
            "created_at": now,
        }
        
        # Write to DB
        result = collection.insert_one(post)
        print(f"✓ Newsletter post inserted: {result.inserted_id}")
        
        # Update insight status
        db.content_insights.update_one(
            {"_id": ObjectId(insight_id)},
            {"$set": {"status": "generation_done"}},
        )
        
    except Exception as e:
        logger.error(f"Error for {insight_id}: {e}")

# Check final count
total_posts = db.generated_posts.count_documents({})
newsletter_posts = db.generated_posts.count_documents({'platform': 'newsletter'})

print("\n" + "=" * 60)
print(f"Total posts: {total_posts}")
print(f"Newsletter posts: {newsletter_posts}")
