"""
WSGI entry point for Render deployment
This file allows Render to run the app with gunicorn
"""

import os
import sys
import logging
from pathlib import Path

# Load environment variables BEFORE any other imports
from dotenv import load_dotenv
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try parent directory
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

# Add current directory and blog_platform to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("WSGI STARTUP FOR RENDER")
logger.info("=" * 60)

try:
    # Import Flask app
    from app import app, db, blog_generator
    from scheduler import BlogScheduler
    from config import Config
    
    logger.info("✓ Flask app loaded successfully")
    
    # Start the scheduler if we have a valid generator
    scheduler = None
    if blog_generator and db:
        try:
            logger.info("Starting background scheduler...")
            scheduler = BlogScheduler(db, blog_generator)
            scheduler.start()
            logger.info(f"✓ Scheduler started - generates blogs every {Config.GENERATION_INTERVAL_MINUTES} minutes")
        except Exception as e:
            logger.warning(f"Could not start scheduler: {e}")
    else:
        logger.warning("Scheduler not started: blog_generator or db is None")
    
    # Ensure we can shutdown properly
    import atexit
    
    def shutdown():
        if scheduler:
            logger.info("Shutting down scheduler...")
            try:
                scheduler.stop()
            except:
                pass
        if db:
            logger.info("Closing database...")
            try:
                db.close()
            except:
                pass
    
    atexit.register(shutdown)
    
    logger.info("=" * 60)
    logger.info("WSGI APP READY FOR REQUESTS")
    logger.info("=" * 60)
    
except Exception as e:
    logger.error(f"Failed to initialize app: {e}", exc_info=True)
    logger.error("Creating minimal Flask app to show error...")
    
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return f"App initialization failed: {e}", 500

