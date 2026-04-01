#!/usr/bin/env python3
"""Generate BLOG posts using Claude AI (via MegaLLM) from pending insights."""

import argparse
import logging
import os
import time
import requests
import json
from datetime import datetime, timezone
from workflow_common import bootstrap_env

# Bootstrap environment BEFORE importing
bootstrap_env(__file__)

from bson import ObjectId
from pymongo import MongoClient
from wf2 import fetch_seo_brief, _build_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Generate blog-only posts using Claude AI (via MegaLLM) from pending insights")
parser.add_argument(
    "--limit",
    type=int,
    default=0,
    help="Limit number of insights to process (0=all)",
)
parser.add_argument(
    "--model",
    default="claude-3-5-sonnet-20241022",
    help="Claude model to use (default: claude-3-5-sonnet-20241022)",
)
args = parser.parse_args()

db = MongoClient('mongodb://localhost:27017')['megallm']
collection = db.generated_posts

# Get MegaLLM config
megallm_config = _build_config()

# Get pending insights
query = {'status': 'pending_generation'}
cursor = db.content_insights.find(query)
if args.limit > 0:
    cursor = cursor.limit(args.limit)
insights = list(cursor)

print(f"Generating BLOG posts for {len(insights)} insights using Claude AI (via MegaLLM)...")
print(f"Model: {args.model}")
print("=" * 70)

generated_count = 0
failed_count = 0

for idx, insight in enumerate(insights, 1):
    insight_id = str(insight['_id'])
    print(f"\n[{idx}/{len(insights)}] Processing insight: {insight_id}")
    
    try:
        # Get SEO brief
        keyword = insight.get('infra_data_point', insight.get('core_claim', 'LLM infrastructure'))
        seo_brief = fetch_seo_brief(keyword, _build_config())
        
        # Build SEO context
        seo_context = ""
        if seo_brief.get("results"):
            top = seo_brief["results"][:3]
            seo_context = "\n\nSEO gap analysis — top 3 ranking articles on this keyword:\n"
            for i, r in enumerate(top, 1):
                seo_context += f"{i}. {r['title']}: {r['snippet']}\n"
            seo_context += "\nYour post must cover angles these articles miss."
        
        # Build prompt for Claude
        user_prompt = f"""Target keyword: {keyword}

Insight data:
Hook: {insight.get('hook_sentence', '')}
Core claim: {insight.get('core_claim', '')}
Angle type: {insight.get('angle_type', '')}
MegaLLM tie-in: {insight.get('megallm_tie_in', '')}
Infra data point: {insight.get('infra_data_point', '')}{seo_context}

Write a comprehensive, SEO-optimized blog post (2000-3000 words) that:
1. Opens with the hook and core claim
2. Provides technical depth on the infrastructure challenge
3. Includes the MegaLLM tie-in naturally
4. Covers angles missing from the top-ranking articles
5. Uses proper markdown formatting with headers, lists, and code blocks
6. Ends with actionable recommendations"""
        
        # Call MegaLLM Claude API
        print(f"Calling MegaLLM Claude ({args.model})...")
        
        headers = {
            "Authorization": f"Bearer {megallm_config.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": args.model,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "max_tokens": 3000,
            "temperature": 0.7,
        }
        
        response = requests.post(
            f"{megallm_config.api_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        blog_text = result['choices'][0]['message']['content']
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
            "meta": {"seo_keyword": keyword, "generator": f"claude-{args.model}"},
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
        
        # Small delay to avoid rate limiting
        time.sleep(1)
        
    except requests.exceptions.HTTPError as e:
        failed_count += 1
        logger.error(f"HTTP Error for {insight_id}: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        failed_count += 1
        logger.error(f"Error for {insight_id}: {e}")

# Check final count
total_posts = db.generated_posts.count_documents({})
blog_posts = db.generated_posts.count_documents({'platform': 'blog'})

print("\n" + "=" * 70)
print(f"Blog posts generated in this run: {generated_count}")
print(f"Failed: {failed_count}")
print(f"Total posts in DB: {total_posts}")
print(f"Total blog posts in DB: {blog_posts}")
