#!/usr/bin/env python3
"""
COMPLETE PIPELINE ORCHESTRATION
Scrape → WF1 Insights → Blog Generation for 5 Accounts

Flow:
1. Scrape articles from RSS feeds → articles collection
2. Run WF1 to analyze articles → content_insights collection
3. For each account (1-5): Generate blogs from insights → blogs collection

This is the main entry point that ties everything together.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import required modules
from workflow_common import bootstrap_env
bootstrap_env(__file__)

from pymongo import MongoClient
from bson import ObjectId
import scrape_to_mongo
import wf1

logger.info("=" * 80)
logger.info("COMPLETE PIPELINE: SCRAPE → WF1 INSIGHTS → BLOG GENERATION")
logger.info("=" * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "megallm")
ACCOUNTS = [
    {"id": "account_1", "name": "Account 1"},
    {"id": "account_2", "name": "Account 2"},
    {"id": "account_3", "name": "Account 3"},
    {"id": "account_4", "name": "Account 4"},
    {"id": "account_5", "name": "Account 5"},
]

# ============================================================================
# STEP 1: SCRAPE ARTICLES FROM RSS FEEDS
# ============================================================================

def step_1_scrape_articles() -> Dict[str, Any]:
    """Scrape articles from RSS feeds into MongoDB."""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: SCRAPING ARTICLES FROM RSS FEEDS")
    logger.info("=" * 80)
    
    try:
        summary = scrape_to_mongo.scrape_new_articles()
        
        inserted = summary.get('inserted', 0)
        skipped = summary.get('skipped', 0)
        total = inserted + skipped
        
        logger.info(f"✓ Scraping complete!")
        logger.info(f"  Inserted: {inserted} new articles")
        logger.info(f"  Skipped: {skipped} duplicates")
        logger.info(f"  Total processed: {total}")
        
        return {
            "success": True,
            "inserted": inserted,
            "skipped": skipped,
            "scrape_run_id": summary.get('scrape_run_id', '')
        }
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# STEP 2: RUN WF1 TO CREATE INSIGHTS FROM ARTICLES
# ============================================================================

def step_2_create_insights() -> Dict[str, Any]:
    """Run WF1 to analyze articles and create content insights."""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: CREATING CONTENT INSIGHTS (WF1)")
    logger.info("=" * 80)
    
    try:
        # Initialize WF1
        config = wf1.Config()
        pipeline = wf1.ContentIntelligencePipeline(config)
        
        logger.info(f"✓ WF1 initialized with model: {config.openai_model}")
        
        # Run WF1 pipeline
        results = pipeline.run()
        
        # Handle case where run() returns None
        if results is None:
            logger.warning("WF1 run() returned None - checking database for insights...")
            client = MongoClient(MONGODB_URI)
            mongo_db = client[MONGODB_DB]
            insights_count = mongo_db.content_insights.count_documents({})
            client.close()
            
            return {
                "success": True,
                "insights_created": 0,
                "insights_available": insights_count,
                "message": f"WF1 quota exhausted, but {insights_count} existing insights available"
            }
        
        logger.info(f"✓ WF1 complete!")
        logger.info(f"  Insights created: {results.get('insights_created', 0)}")
        logger.info(f"  Errors: {results.get('errors', 0)}")
        
        # Close pipeline
        pipeline.close()
        
        return {
            "success": True,
            "insights_created": results.get('insights_created', 0),
            "errors": results.get('errors', 0)
        }
    except Exception as e:
        logger.error(f"✗ WF1 failed: {e}", exc_info=True)
        
        # Check if we have existing insights
        try:
            client = MongoClient(MONGODB_URI)
            mongo_db = client[MONGODB_DB]
            insights_count = mongo_db.content_insights.count_documents({})
            client.close()
            
            if insights_count > 0:
                logger.warning(f"WF1 failed, but {insights_count} existing insights available - proceeding with blog generation")
                return {
                    "success": True,
                    "insights_created": 0,
                    "insights_available": insights_count,
                    "message": f"WF1 failed, using {insights_count} existing insights"
                }
        except:
            pass
        
        return {"success": False, "error": str(e)}


# ============================================================================
# STEP 3: GENERATE BLOGS FOR 5 ACCOUNTS FROM INSIGHTS
# ============================================================================

def step_3_generate_blogs_for_accounts() -> Dict[str, Any]:
    """Generate blog posts for each account from insights."""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: GENERATING BLOGS FOR 5 ACCOUNTS")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))
        
        from app import blog_generator, db
        from config import Config
        
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        mongo_db = client[MONGODB_DB]
        
        # Get pending insights
        insights = list(mongo_db.content_insights.find(
            {"status": "pending_generation"},
            limit=100
        ))
        
        logger.info(f"Found {len(insights)} insights pending generation")
        
        if not insights:
            logger.warning("No pending insights found!")
            return {
                "success": True,
                "total_blogs_generated": 0,
                "accounts_processed": 0,
                "message": "No pending insights"
            }
        
        total_blogs_generated = 0
        accounts_with_blogs = {}
        
        # For each account
        for account in ACCOUNTS:
            account_id = account["id"]
            account_blogs = 0
            
            logger.info(f"\nGenerating blogs for {account_id}...")
            
            # For each insight
            for idx, insight in enumerate(insights[:10], 1):  # Limit to 10 insights per account
                try:
                    insight_id = str(insight['_id'])
                    
                    # Extract topic from insight (if available)
                    angle_type = insight.get('angle_type', 'infrastructure')
                    topic_map = {
                        'outage': 'reliability',
                        'pricing': 'cost_optimization',
                        'benchmark': 'performance',
                        'compliance': 'infrastructure',
                        'model_launch': 'performance',
                    }
                    topic = topic_map.get(angle_type, 'infrastructure')
                    
                    # Generate blog using insight
                    blog_data = blog_generator.generate_blog(
                        topic=insight.get('core_claim', topic),
                        topic_description=insight.get('hook_sentence', ''),
                        keywords=[insight.get('infra_data_point', topic)]
                    )
                    
                    if blog_data:
                        # Add metadata
                        blog_data["account_id"] = account_id
                        blog_data["topic"] = topic
                        blog_data["insight_id"] = insight_id
                        blog_data["status"] = "draft"
                        blog_data["created_at"] = datetime.now(timezone.utc).isoformat()
                        blog_data["views"] = 0
                        
                        # Insert into blogs collection
                        result = mongo_db.blogs.insert_one(blog_data)
                        
                        logger.info(f"  [{idx}/10] Generated blog for {account_id}: {blog_data['title'][:50]}...")
                        account_blogs += 1
                        total_blogs_generated += 1
                    else:
                        logger.warning(f"  Failed to generate blog from insight {insight_id}")
                
                except Exception as e:
                    logger.error(f"  Error processing insight {insight_id}: {e}")
                    continue
            
            accounts_with_blogs[account_id] = account_blogs
            logger.info(f"✓ {account_id}: Generated {account_blogs} blogs")
        
        # Mark insights as processed
        insight_ids = [ObjectId(str(i['_id'])) for i in insights[:10]]
        mongo_db.content_insights.update_many(
            {"_id": {"$in": insight_ids}},
            {"$set": {"status": "blogs_generated"}}
        )
        
        logger.info(f"\n✓ Blog generation complete!")
        logger.info(f"  Total blogs generated: {total_blogs_generated}")
        logger.info(f"  Blogs per account: {accounts_with_blogs}")
        
        client.close()
        
        return {
            "success": True,
            "total_blogs_generated": total_blogs_generated,
            "accounts_processed": len(accounts_with_blogs),
            "blogs_per_account": accounts_with_blogs
        }
    
    except Exception as e:
        logger.error(f"✗ Blog generation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def run_complete_pipeline() -> None:
    """Run the complete pipeline: Scrape → WF1 → Blog Generation."""
    
    results = {
        "start_time": datetime.now(timezone.utc).isoformat(),
        "steps": {}
    }
    
    # Step 1: Scrape
    logger.info("\n\n🔄 Starting STEP 1: SCRAPE ARTICLES...")
    step1_result = step_1_scrape_articles()
    results["steps"]["scrape"] = step1_result
    
    if not step1_result.get("success"):
        logger.error("Scraping failed, stopping pipeline")
        results["status"] = "failed"
        results["end_time"] = datetime.now(timezone.utc).isoformat()
        print_summary(results)
        return
    
    # Step 2: WF1
    logger.info("\n\n🔄 Starting STEP 2: CREATE INSIGHTS (WF1)...")
    time.sleep(2)
    step2_result = step_2_create_insights()
    results["steps"]["wf1_insights"] = step2_result
    
    if not step2_result.get("success"):
        # Check if we have existing insights to use
        try:
            client = MongoClient(MONGODB_URI)
            mongo_db = client[MONGODB_DB]
            insights_count = mongo_db.content_insights.count_documents({})
            client.close()
            if insights_count == 0:
                logger.error("WF1 failed and no existing insights found - stopping pipeline")
                results["status"] = "failed"
                results["end_time"] = datetime.now(timezone.utc).isoformat()
                print_summary(results)
                return
            else:
                logger.warning(f"WF1 failed but using {insights_count} existing insights - continuing to blog generation")
        except Exception as e:
            logger.error(f"Error checking for existing insights: {e}")
            results["status"] = "failed"
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            print_summary(results)
            return
    
    # Step 3: Blog Generation
    logger.info("\n\n🔄 Starting STEP 3: GENERATE BLOGS FOR 5 ACCOUNTS...")
    time.sleep(2)
    step3_result = step_3_generate_blogs_for_accounts()
    results["steps"]["blog_generation"] = step3_result
    
    if not step3_result.get("success"):
        logger.error("Blog generation failed")
        results["status"] = "partial"
    else:
        results["status"] = "success"
    
    results["end_time"] = datetime.now(timezone.utc).isoformat()
    
    # Print final summary
    print_summary(results)


def print_summary(results: Dict[str, Any]) -> None:
    """Print pipeline execution summary."""
    logger.info("\n\n" + "=" * 80)
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("=" * 80)
    
    logger.info(f"Status: {results.get('status', 'unknown').upper()}")
    logger.info(f"Start: {results.get('start_time')}")
    logger.info(f"End: {results.get('end_time')}")
    
    logger.info("\nStep Results:")
    
    for step_name, step_result in results.get("steps", {}).items():
        success = step_result.get("success", False)
        status_icon = "✓" if success else "✗"
        logger.info(f"\n{status_icon} {step_name.upper()}")
        
        for key, value in step_result.items():
            if key != "success":
                if isinstance(value, dict):
                    logger.info(f"    {key}: {json.dumps(value, indent=6)}")
                else:
                    logger.info(f"    {key}: {value}")
    
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        run_complete_pipeline()
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
