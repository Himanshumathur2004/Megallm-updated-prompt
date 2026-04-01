"""Main entry point for Blog Generation Platform."""

import os
import sys
import logging
from pathlib import Path

# Load environment variables BEFORE any other imports
from dotenv import load_dotenv
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠ Warning: .env not found at {env_file}")
    print("  Create it with: MEGALLM_API_KEY=sk-mega-...")

# Add parent directory to path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

from app import app, db, blog_generator
from scheduler import BlogScheduler
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_platform.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Start the blog generation platform."""
    logger.info("=" * 60)
    logger.info("BLOG GENERATION PLATFORM - STARTUP")
    logger.info("=" * 60)
    
    # Initialize scheduler
    scheduler = BlogScheduler(db, blog_generator)
    
    try:
        # Start scheduler
        logger.info("Starting background scheduler...")
        scheduler.start()
        
        # Log configuration
        logger.info(f"MegaLLM Model: {Config.MEGALLM_MODEL}")
        logger.info(f"Blogs per 24h: {Config.BLOGS_PER_24_HOURS}")
        logger.info(f"Generation interval: {Config.GENERATION_INTERVAL_MINUTES} minutes")
        logger.info(f"Blog length: {Config.BLOG_WORD_COUNT_MIN}-{Config.BLOG_WORD_COUNT_MAX} words")
        logger.info(f"Number of accounts: {len(Config.ACCOUNTS)}")
        logger.info(f"Number of topics: {len(Config.TOPICS)}")
        
        logger.info("=" * 60)
        logger.info("Platform initialized successfully!")
        logger.info("Web UI: http://localhost:5000")
        logger.info("API: http://localhost:5000/api")
        logger.info("=" * 60)
        
        # Start Flask app (blocking)
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=Config.DEBUG,
            use_reloader=False  # Prevent scheduler from running twice
        )
        
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Stopping scheduler...")
        scheduler.stop()
        logger.info("Closing database connection...")
        db.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
