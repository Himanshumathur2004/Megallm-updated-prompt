"""Background scheduler for automatic blog generation."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime, timezone

from config import Config
from database import Database
from blog_generator import BlogGenerator

logger = logging.getLogger(__name__)


class BlogScheduler:
    """Manage scheduled blog generation."""
    
    def __init__(self, db: Database, generator: BlogGenerator):
        self.db = db
        self.generator = generator
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Start the scheduler."""
        accounts = Config.ACCOUNTS
        
        for account in accounts:
            account_id = account["id"]
            
            # Schedule generation every GENERATION_INTERVAL_MINUTES
            self.scheduler.add_job(
                func=self._generate_blogs_for_account,
                args=[account_id],
                trigger=IntervalTrigger(minutes=Config.GENERATION_INTERVAL_MINUTES),
                id=f"generate_blogs_{account_id}",
                name=f"Generate blogs for {account_id}",
                misfire_grace_time=60
            )
            
            logger.info(
                f"Scheduled blog generation for {account_id} "
                f"every {Config.GENERATION_INTERVAL_MINUTES} minutes"
            )
        
        self.scheduler.start()
        logger.info("Blog generation scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Blog generation scheduler stopped")
    
    def _generate_blogs_for_account(self, account_id: str):
        """Generate blogs for a specific account."""
        logger.info(f"Starting blog generation for {account_id}")
        
        try:
            # Define topics for this generation cycle
            # We generate 3 blogs per topic (12 total per 24 hours)
            topics_to_generate = {}
            for topic_id, topic_info in Config.TOPICS.items():
                topics_to_generate[topic_id] = topic_info.get("blogs_per_cycle", 3)
            
            # Generate blogs
            generated_blogs = self.generator.batch_generate(
                topics={
                    topic_id: Config.TOPICS[topic_id]
                    for topic_id in topics_to_generate.keys()
                },
                blogs_per_topic=1  # Generate one at a time
            )
            
            # Insert into database
            total_generated = 0
            for topic_id, blogs in generated_blogs.items():
                for blog_data in blogs:
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = topic_id
                    blog_id = self.db.insert_blog(blog_data)
                    total_generated += 1
                    logger.info(f"Inserted blog {blog_id} for {account_id}/{topic_id}")
            
            # Log generation event
            self.db.log_generation(account_id, total_generated, error=None)
            
            logger.info(f"✓ Generated {total_generated} blogs for {account_id}")
            
        except Exception as e:
            error_msg = f"Error generating blogs for {account_id}: {str(e)}"
            logger.error(error_msg)
            self.db.log_generation(account_id, 0, error=error_msg)
    
    def trigger_generation_now(self, account_id: str) -> bool:
        """Manually trigger generation for an account."""
        logger.info(f"Manually triggering blog generation for {account_id}")
        try:
            self._generate_blogs_for_account(account_id)
            return True
        except Exception as e:
            logger.error(f"Error manually triggering generation: {e}")
            return False
    
    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()
