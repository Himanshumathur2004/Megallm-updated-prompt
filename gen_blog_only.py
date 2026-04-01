#!/usr/bin/env python3
"""Generate BLOG variant posts only from pending insights."""

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from workflow_common import bootstrap_env, LLMQuotaExceededError

# Bootstrap environment BEFORE importing wf2
bootstrap_env(__file__)

from bson import ObjectId
from wf2 import (
    _build_config, LLMClient, fetch_insight, fetch_seo_brief, generate_blog,
    write_posts
)
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Generate blog-only posts from pending insights")
parser.add_argument(
    "--model",
    default="",
    help="Override WF2 model for this run (example: openai/gpt-4o-mini)",
)
parser.add_argument(
    "--limit",
    type=int,
    default=0,
    help="Limit number of insights to process (0=all)",
)
parser.add_argument(
    "--retry",
    type=int,
    default=3,
    help="Number of retries per insight on timeout/errors",
)
args = parser.parse_args()

if args.model:
    os.environ["WF2_MODEL"] = args.model

db = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))[os.getenv('MONGODB_DB', 'megallm')]
collection = db.generated_posts

# Get ALL pending insights
query = {'status': 'pending_generation'}
cursor = db.content_insights.find(query)
if args.limit > 0:
    cursor = cursor.limit(args.limit)
insights = list(cursor)

print(f"Generating BLOG posts for {len(insights)} insights...")
print("=" * 60)

config = _build_config()
print(f"Using model: {config.model}")
print(f"Serper API Key set: {'Yes' if config.serper_api_key else 'No (SEO briefs will be empty)'}")
llm = LLMClient(config.api_key, config.api_base_url, config.model)

generated_count = 0
failed_count = 0

for idx, insight in enumerate(insights, 1):
    insight_id = str(insight['_id'])
    print(f"\n[{idx}/{len(insights)}] Processing insight: {insight_id}")
    
    for attempt in range(1, args.retry + 1):
        try:
            # Fetch SEO brief for gap analysis
            keyword = insight.get('infra_data_point', insight.get('core_claim', 'LLM infrastructure'))
            seo_brief = fetch_seo_brief(keyword, config)
            
            # Generate only blog post
            print(f"Generating blog post (attempt {attempt}/{args.retry})...")
            blog_text = generate_blog(insight, seo_brief, llm, config)
            logger.info(f"Blog post generated: {len(blog_text)} chars")
            
            # Build insert payload
            now = datetime.now(timezone.utc).isoformat()
            try:
                content_insight_id = ObjectId(insight_id)
            except Exception:
                content_insight_id = insight_id
            
            post = {
                "insight_id": insight_id,
                "content_insight_id": content_insight_id,
                "platform": "blog",
                "variant": "A",
                "content": blog_text,
                "meta": {"seo_keyword": keyword},
                "status": "draft",
                "created_at": now,
            }
            
            # Write to DB
            result = collection.insert_one(post)
            print(f"✓ Blog post inserted: {result.inserted_id}")
            
            # Update insight status
            db.content_insights.update_one(
                {"_id": ObjectId(insight_id)},
                {"$set": {"status": "generation_done"}},
            )
            
            generated_count += 1
            break  # Success, move to next insight
            
        except LLMQuotaExceededError as e:
            logger.error(f"LLM quota exceeded: {e}")
            print(f"Rate limit hit. Stopping to avoid further quotas. {generated_count} posts generated so far.")
            break
        except (OSError, TimeoutError) as e:
            # Network/timeout error - retry
            if attempt < args.retry:
                wait_time = 10 * attempt
                logger.warning(f"Timeout/network error, retrying in {wait_time}s: {e}")
                print(f"Network timeout, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                failed_count += 1
                logger.error(f"Failed after {args.retry} attempts for {insight_id}: {e}")
                print(f"Failed after {args.retry} retries")
                break
        except Exception as e:
            if attempt < args.retry:
                wait_time = 5 * attempt
                logger.warning(f"Error (attempt {attempt}), retrying in {wait_time}s: {e}")
                print(f"Error, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                failed_count += 1
                logger.error(f"Final error for {insight_id}: {e}")
                break
    
    # Small delay between insights to avoid hammering API
    if generated_count + failed_count < len(insights):
        time.sleep(2)

# Check final count
total_posts = db.generated_posts.count_documents({})
blog_posts = db.generated_posts.count_documents({'platform': 'blog'})

print("\n" + "=" * 60)
print(f"Blog posts generated in this run: {generated_count}")
print(f"Failed: {failed_count}")
print(f"Total posts in DB: {total_posts}")
print(f"Total blog posts in DB: {blog_posts}")
