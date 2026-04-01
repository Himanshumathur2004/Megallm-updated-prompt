"""
Complete Blog Generation Pipeline for Render
Integrates: Scrape → WF1 Analysis → Blog Generation
All steps run on demand for real-time user access.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Make sure parent directory is in path for imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)


class RenderPipeline:
    """Complete pipeline orchestration for Render platform."""
    
    def __init__(self, db, blog_generator, config):
        """
        Initialize pipeline with database and generator.
        
        Args:
            db: Database instance
            blog_generator: BlogGenerator instance
            config: Config instance with API keys and settings
        """
        self.db = db
        self.blog_generator = blog_generator
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def run_complete_pipeline(self) -> Dict[str, Any]:
        """
        Run complete pipeline: Scrape → Analyze → Generate
        
        Returns:
            Dictionary with results from all pipeline steps
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING COMPLETE PIPELINE ON RENDER")
        self.logger.info("=" * 80)
        
        results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "steps": {},
            "total_blogs_generated": 0,
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Scrape articles
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 1: SCRAPING ARTICLES FROM RSS FEEDS")
            self.logger.info("=" * 80)
            
            scrape_result = self._scrape_articles()
            results["steps"]["scrape"] = scrape_result
            
            if not scrape_result.get("success"):
                self.logger.warning("Scraping failed, but continuing with existing articles...")
            
            # Step 2: Analyze with WF1
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 2: ANALYZING ARTICLES WITH WF1")
            self.logger.info("=" * 80)
            
            insights_result = self._create_insights()
            results["steps"]["insights"] = insights_result
            
            if not insights_result.get("success"):
                self.logger.warning("WF1 analysis failed, but continuing with existing insights...")
            
            # Step 3: Generate blogs from insights
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 3: GENERATING BLOGS FROM INSIGHTS")
            self.logger.info("=" * 80)
            
            generation_result = self._generate_blogs_from_insights()
            results["steps"]["generation"] = generation_result
            
            results["total_blogs_generated"] = generation_result.get("total_blogs", 0)
            results["success"] = True
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results["error"] = error_msg
            results["success"] = False
        
        results["end_time"] = datetime.now(timezone.utc).isoformat()
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PIPELINE COMPLETE")
        self.logger.info(f"Total blogs generated: {results['total_blogs_generated']}")
        self.logger.info("=" * 80)
        
        return results
    
    def _scrape_articles(self) -> Dict[str, Any]:
        """Scrape articles from RSS feeds into MongoDB."""
        try:
            # Import scraping module
            try:
                import scrape_to_mongo
            except ImportError:
                # If direct import fails, try with parent directory
                sys.path.insert(0, str(Path(__file__).parent.parent))
                import scrape_to_mongo
            
            self.logger.info("Starting article scraping...")
            summary = scrape_to_mongo.scrape_new_articles()
            
            inserted = summary.get('inserted', 0)
            skipped = summary.get('skipped', 0)
            
            self.logger.info(f"✓ Scraping complete")
            self.logger.info(f"  Inserted: {inserted} new articles")
            self.logger.info(f"  Skipped: {skipped} duplicates")
            
            return {
                "success": True,
                "inserted": inserted,
                "skipped": skipped,
                "total": inserted + skipped
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"✗ Scraping failed: {error_msg}", exc_info=True)
            
            # Check how many articles we have
            try:
                from pymongo import MongoClient
                client = MongoClient(self.config.MONGODB_URI)
                mongo_db = client[self.config.MONGODB_DB]
                article_count = mongo_db.articles.count_documents({})
                client.close()
                
                return {
                    "success": False,
                    "error": error_msg,
                    "existing_articles": article_count,
                    "message": f"Scraping failed but {article_count} existing articles available"
                }
            except:
                return {"success": False, "error": error_msg}
    
    def _create_insights(self) -> Dict[str, Any]:
        """Run WF1 to analyze articles and create insights."""
        try:
            # Import WF1 module
            try:
                import wf1
            except ImportError:
                sys.path.insert(0, str(Path(__file__).parent.parent))
                import wf1
            
            self.logger.info("Initializing WF1 analysis...")
            config = wf1.Config()
            pipeline = wf1.ContentIntelligencePipeline(config)
            
            self.logger.info(f"WF1 initialized with model: {config.openai_model}")
            self.logger.info("Running WF1 analysis on scraped articles...")
            
            results = pipeline.run()
            pipeline.close()
            
            # Handle None response (quota or errors)
            if results is None:
                self.logger.warning("WF1 returned None - checking existing insights...")
                from pymongo import MongoClient
                client = MongoClient(self.config.MONGODB_URI)
                mongo_db = client[self.config.MONGODB_DB]
                insights_count = mongo_db.content_insights.count_documents({})
                client.close()
                
                return {
                    "success": True,
                    "insights_created": 0,
                    "existing_insights": insights_count,
                    "message": f"WF1 quota reached, using {insights_count} existing insights"
                }
            
            insights_created = results.get('insights_created', 0)
            errors = results.get('errors', 0)
            
            self.logger.info(f"✓ WF1 analysis complete")
            self.logger.info(f"  Created: {insights_created} insights")
            self.logger.info(f"  Errors: {errors}")
            
            return {
                "success": True,
                "insights_created": insights_created,
                "errors": errors
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"✗ WF1 analysis failed: {error_msg}", exc_info=True)
            
            # Check how many insights we have
            try:
                from pymongo import MongoClient
                client = MongoClient(self.config.MONGODB_URI)
                mongo_db = client[self.config.MONGODB_DB]
                insights_count = mongo_db.content_insights.count_documents({})
                client.close()
                
                return {
                    "success": False,
                    "error": error_msg,
                    "existing_insights": insights_count,
                    "message": f"WF1 failed but {insights_count} existing insights available"
                }
            except:
                return {"success": False, "error": error_msg}
    
    def _generate_blogs_from_insights(self) -> Dict[str, Any]:
        """Generate blogs for all accounts from insights."""
        try:
            from pymongo import MongoClient
            
            self.logger.info("Connecting to MongoDB for insights...")
            client = MongoClient(self.config.MONGODB_URI)
            mongo_db = client[self.config.MONGODB_DB]
            
            # Get all pending insights
            pending_insights = list(mongo_db.content_insights.find(
                {"status": "pending_generation"},
                limit=500
            ))
            
            self.logger.info(f"Found {len(pending_insights)} insights pending generation")
            
            if not pending_insights:
                self.logger.warning("No pending insights found for blog generation")
                return {
                    "success": True,
                    "total_blogs": 0,
                    "message": "No pending insights to generate blogs from"
                }
            
            total_blogs = 0
            errors = []
            
            # Generate blogs for each account
            for account in self.config.ACCOUNTS:
                account_id = account["id"]
                account_blogs = 0
                
                self.logger.info(f"\nGenerating blogs for {account_id}...")
                
                # Generate 3 blogs per account from insights
                for i, insight in enumerate(pending_insights[:3]):
                    try:
                        self.logger.info(f"  Generating blog {i+1}/3 from insight: {insight.get('_id')}")
                        
                        # Generate blog using insight data
                        blog_data = self._generate_blog_from_insight(insight)
                        
                        if blog_data:
                            # Add metadata
                            blog_data["account_id"] = account_id
                            blog_data["insight_id"] = str(insight.get("_id"))
                            blog_data["created_at"] = datetime.now(timezone.utc).isoformat()
                            
                            # Insert into database
                            blog_id = self.db.insert_blog(blog_data)
                            self.logger.info(f"    ✓ Created blog: {blog_id}")
                            
                            account_blogs += 1
                            total_blogs += 1
                        else:
                            self.logger.warning(f"    ✗ Failed to generate blog from insight")
                            errors.append(f"Failed to generate from insight {insight.get('_id')}")
                    
                    except Exception as e:
                        error_msg = f"Error generating blog: {str(e)}"
                        self.logger.error(f"    ✗ {error_msg}", exc_info=True)
                        errors.append(error_msg)
                
                # Mark insights as generated
                try:
                    mongo_db.content_insights.update_many(
                        {"_id": {"$in": [i["_id"] for i in pending_insights[:3]]}},
                        {"$set": {"status": "blog_generated"}}
                    )
                    self.logger.info(f"  Marked {min(3, len(pending_insights))} insights as generated")
                except Exception as e:
                    self.logger.warning(f"  Could not mark insights as generated: {e}")
                
                self.logger.info(f"  ✓ Generated {account_blogs} blogs for {account_id}")
            
            client.close()
            
            self.logger.info(f"\n✓ Blog generation complete")
            self.logger.info(f"  Total blogs: {total_blogs}")
            self.logger.info(f"  Errors: {len(errors)}")
            
            return {
                "success": True,
                "total_blogs": total_blogs,
                "accounts": len(self.config.ACCOUNTS),
                "errors": errors,
                "message": f"Generated {total_blogs} blogs across {len(self.config.ACCOUNTS)} accounts"
            }
        
        except Exception as e:
            error_msg = f"Blog generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
    
    def _generate_blog_from_insight(self, insight: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a single blog post from an insight.
        
        Args:
            insight: Content insight document from MongoDB
        
        Returns:
            Blog data dict with title and body, or None on error
        """
        try:
            # Extract key data from insight
            topic = insight.get("content_topic", "Technology")
            keywords = insight.get("key_insights", [])[:5]  # Top 5 insights
            summary = insight.get("summary", "")
            content = insight.get("extracted_content", "")
            
            # Build prompt from insight data
            topic_description = summary or f"Technical insights about {topic}"
            
            self.logger.info(f"    Generating blog: topic={topic}")
            
            # Generate blog using the blog generator
            blog_data = self.blog_generator.generate_blog(
                topic=topic,
                topic_description=topic_description,
                keywords=keywords,
                word_count_min=500,
                word_count_max=800
            )
            
            return blog_data
        
        except Exception as e:
            self.logger.error(f"    Error generating blog from insight: {e}", exc_info=True)
            return None


def create_render_pipeline(db, blog_generator, config) -> RenderPipeline:
    """Factory function to create a pipeline instance."""
    return RenderPipeline(db, blog_generator, config)
