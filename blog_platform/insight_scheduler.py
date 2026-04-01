"""
INSIGHT-DRIVEN SCHEDULER
Generates blog posts for 5 accounts from WF1 content insights.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from bson import ObjectId
from pymongo import MongoClient

from config import Config
from database import Database
from blog_generator import BlogGenerator

logger = logging.getLogger(__name__)


class InsightDrivenBlogScheduler:
    """Generate blogs for 5 accounts from WF1 insights."""
    
    def __init__(self, db: Database, generator: BlogGenerator, mongodb_uri: str, mongodb_db: str):
        self.db = db
        self.generator = generator
        self.mongodb_uri = mongodb_uri
        self.mongodb_db = mongodb_db
        self._client = None
        self._mongo_db = None
    
    def connect_mongo(self):
        """Connect to MongoDB for insights."""
        if not self._client:
            self._client = MongoClient(self.mongodb_uri)
            self._mongo_db = self._client[self.mongodb_db]
            logger.info(f"Connected to MongoDB: {self.mongodb_db}")
    
    def close_mongo(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._mongo_db = None
            logger.info("Closed MongoDB connection")
    
    def get_pending_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get insights pending blog generation."""
        self.connect_mongo()
        
        try:
            insights = list(self._mongo_db.content_insights.find(
                {"status": {"$in": ["pending_generation", "new"]}},
                limit=limit
            ))
            logger.info(f"Found {len(insights)} pending insights")
            return insights
        except Exception as e:
            logger.error(f"Error fetching insights: {e}")
            return []
    
    def generate_blogs_from_insight(
        self,
        insight: Dict[str, Any],
        account_id: str
    ) -> Dict[str, str] | None:
        """
        Generate a blog post from a single insight for a specific account.
        
        insight structure:
        {
            "_id": ObjectId,
            "hook_sentence": "...",
            "core_claim": "...",
            "megallm_tie_in": "...",
            "infra_data_point": "...",
            "angle_type": "outage|pricing|benchmark|compliance|model_launch",
            ...
        }
        """
        try:
            insight_id = str(insight.get("_id", "unknown"))
            
            # Extract content from insight
            hook = insight.get("hook_sentence", "Infrastructure update")
            core_claim = insight.get("core_claim", "New development")
            megallm_tie_in = insight.get("megallm_tie_in", "")
            infra_data_point = insight.get("infra_data_point", "")
            angle_type = insight.get("angle_type", "infrastructure")
            
            # Map angle_type to blog topic
            topic_map = {
                'outage': 'Reliability & Uptime',
                'pricing': 'Cost Optimization',
                'benchmark': 'Performance Metrics',
                'compliance': 'Infrastructure Security',
                'model_launch': 'AI/ML Performance',
            }
            topic = topic_map.get(angle_type, 'Infrastructure Updates')
            
            # Prepare blog content
            topic_description = hook  # Use hook as description
            keywords = [word.strip() for word in infra_data_point.split(',')[:3] if word.strip()]
            
            logger.info(f"Generating blog from insight {insight_id[:8]}... for {account_id}")
            logger.info(f"  Topic: {topic}")
            logger.info(f"  Hook: {hook[:60]}...")
            
            # Generate blog using OpenRouter API
            blog_data = self.generator.generate_blog(
                topic=topic,
                topic_description=topic_description,
                keywords=keywords,
                word_count_min=600,
                word_count_max=900
            )
            
            if blog_data:
                # Add metadata
                blog_data["account_id"] = account_id
                blog_data["topic"] = topic
                blog_data["insight_id"] = insight_id
                blog_data["angle_type"] = angle_type
                blog_data["hook"] = hook
                blog_data["core_claim"] = core_claim
                blog_data["status"] = "draft"
                blog_data["created_at"] = datetime.now(timezone.utc).isoformat()
                blog_data["views"] = 0
                
                logger.info(f"✓ Generated blog: {blog_data['title'][:50]}...")
                return blog_data
            else:
                logger.error(f"Blog generator returned None for insight {insight_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error generating blog from insight: {e}")
            return None
    
    def generate_blogs_for_all_accounts(self, insights: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate blogs for all 5 accounts from insights.
        
        For each account:
        - Take pending insights
        - Generate a blog variant for each insight
        - Store with account_id
        
        Returns: Summary of generation
        """
        self.connect_mongo()
        
        # Get insights if not provided
        if insights is None:
            insights = self.get_pending_insights(limit=20)
        
        if not insights:
            logger.warning("No pending insights available")
            return {
                "success": True,
                "total_blogs": 0,
                "accounts": {},
                "message": "No pending insights"
            }
        
        accounts = Config.ACCOUNTS
        total_blogs_generated = 0
        account_results = {}
        
        logger.info(f"\nGenerating blogs for {len(accounts)} accounts from {len(insights)} insights")
        logger.info("=" * 80)
        
        # For each account
        for account in accounts:
            account_id = account["id"]
            account_blogs = 0
            
            logger.info(f"\n📝 Processing {account_id}...")
            
            # For each insight
            for idx, insight in enumerate(insights[:15], 1):  # Limit to 15 insights per account
                blog_data = self.generate_blogs_from_insight(insight, account_id)
                
                if blog_data:
                    # Insert into blogs collection
                    try:
                        blog_id = self.db.insert_blog(blog_data)
                        account_blogs += 1
                        total_blogs_generated += 1
                        logger.info(f"  [{idx}] ✓ Inserted blog {blog_id}")
                    except Exception as e:
                        logger.error(f"  [{idx}] Error inserting blog: {e}")
                else:
                    logger.warning(f"  [{idx}] Failed to generate blog")
            
            account_results[account_id] = {"blogs_generated": account_blogs}
            logger.info(f"✓ {account_id}: Generated {account_blogs} blogs")
        
        # Mark insights as processed
        try:
            if insights:
                insight_ids = [ObjectId(str(i['_id'])) for i in insights[:15]]
                result = self._mongo_db.content_insights.update_many(
                    {"_id": {"$in": insight_ids}},
                    {
                        "$set": {
                            "status": "blogs_generated",
                            "blog_generation_done_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                logger.info(f"Updated {result.modified_count} insights to blogs_generated status")
        except Exception as e:
            logger.error(f"Error updating insight status: {e}")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"Blog generation complete: {total_blogs_generated} blogs across {len(account_results)} accounts")
        
        return {
            "success": True,
            "total_blogs": total_blogs_generated,
            "accounts": account_results,
            "insights_processed": len(insights[:15])
        }
    
    def run_once(self) -> Dict[str, Any]:
        """Run insight-driven blog generation once."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING INSIGHT-DRIVEN BLOG GENERATION")
        logger.info("=" * 80)
        
        try:
            result = self.generate_blogs_for_all_accounts()
            self.close_mongo()
            return result
        except Exception as e:
            logger.error(f"Error in insight-driven generation: {e}", exc_info=True)
            self.close_mongo()
            return {
                "success": False,
                "error": str(e),
                "total_blogs": 0,
                "accounts": {}
            }


def generate_blogs_from_insights_now(
    db: Database,
    generator: BlogGenerator,
    mongodb_uri: str,
    mongodb_db: str
) -> Dict[str, Any]:
    """
    Quick function to generate blogs from insights.
    Used for manual triggering from API endpoints.
    """
    scheduler = InsightDrivenBlogScheduler(db, generator, mongodb_uri, mongodb_db)
    return scheduler.run_once()
