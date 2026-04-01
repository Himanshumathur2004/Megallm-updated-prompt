"""Flask backend API for blog platform."""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from functools import wraps
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys

from config import Config
from database import Database
from blog_generator import BlogGenerator
from mock_blog_generator import MockBlogGenerator
from insight_scheduler import generate_blogs_from_insights_now
from scheduler import BlogScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get template folder path
template_dir = Path(__file__).parent / "templates"

# Initialize Flask app
app = Flask(__name__, template_folder=str(template_dir))
app.config.from_object(Config)
CORS(app)

# Validate configuration
def validate_config():
    """Validate required configuration."""
    if Config.USE_OPENROUTER:
        if not Config.MEGALLM_API_KEY or Config.MEGALLM_API_KEY == "your_openrouter_api_key_here":
            logger.error("ERROR: OPENROUTER_API_KEY not set in .env file!")
            logger.error("Set OPENROUTER_API_KEY=sk-or-v1-... in .env")
            return False
    else:
        if not Config.MEGALLM_API_KEY:
            logger.error("ERROR: MEGALLM_API_KEY not set in .env file!")
            logger.error("Set MEGALLM_API_KEY=sk-mega-... in .env")
            return False
    return True

# Initialize database and generator
db = None
blog_generator = None

try:
    if not validate_config():
        raise ValueError("Configuration validation failed")
    
    logger.info("Initializing database...")
    db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
    logger.info("✓ Database initialized")
    
    logger.info("Initializing LLM client...")
    
    # Use real OpenRouter API
    logger.info("Using BlogGenerator with OpenRouter API")
    blog_generator = BlogGenerator(Config.MEGALLM_API_KEY, Config.MEGALLM_BASE_URL, Config.MEGALLM_MODEL)
    logger.info("✓ LLM client initialized (OpenRouter)")
    
except Exception as e:
    logger.error(f"✗ Initialization error: {e}")
    logger.error("App will start in limited mode. Configure .env properly to enable full features.")
    
# Ensure we have a database instance (either MongoDB or in-memory)
if db is None:
    try:
        logger.warning("Creating fallback in-memory database...")
        from database import InMemoryDatabase
        db = InMemoryDatabase()
        logger.info("✓ In-memory database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize even fallback database: {e}")
        sys.exit(1)

# Ensure we have a blog generator (with fallback error handling)
if blog_generator is None:
    logger.warning("Blog generator not initialized - generation will fail until configured")
    logger.warning(f"USE_OPENROUTER: {Config.USE_OPENROUTER}")
    logger.warning(f"API_KEY: {Config.MEGALLM_API_KEY[:20] if Config.MEGALLM_API_KEY else 'NOT SET'}...")
    logger.warning(f"BASE_URL: {Config.MEGALLM_BASE_URL}")
    logger.warning(f"MODEL: {Config.MEGALLM_MODEL}")

# Initialize accounts on startup
def init_accounts():
    """Create accounts if they don't exist."""
    logger.info("Initializing accounts...")
    created = 0
    existing = 0
    
    for account in Config.ACCOUNTS:
        if db.get_account(account["id"]):
            existing += 1
            logger.info(f"  ✓ Account exists: {account['id']}")
        else:
            if db.create_account(account["id"], account["name"], account["description"]):
                created += 1
                logger.info(f"  ✓ Created account: {account['id']}")
            else:
                logger.warning(f"  ✗ Failed to create account: {account['id']}")
    
    logger.info(f"Accounts initialized: {created} created, {existing} existing")

init_accounts()

# Initialize and start automatic blog scheduler
scheduler = None
try:
    logger.info("Initializing automatic blog generation scheduler...")
    scheduler = BlogScheduler(db, blog_generator)
    scheduler.start()
    logger.info(f"✓ Blog scheduler started - will generate blogs every {Config.GENERATION_INTERVAL_MINUTES} minutes")
except Exception as e:
    logger.error(f"✗ Failed to start scheduler: {e}")
    logger.warning("Scheduled blog generation will be disabled - use manual generation via API")


# ============================================================================
# STATIC & TEMPLATE ROUTES
# ============================================================================

@app.route("/", methods=["GET"])
def index():
    """Serve the main dashboard HTML."""
    return render_template("index.html")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_account(f):
    """Decorator to validate account_id parameter."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to get account_id from query params first (for GET requests)
        account_id = request.args.get("account_id")
        
        # If not found in query params, try JSON body (for POST/PUT requests)
        if not account_id and request.is_json:
            account_id = request.json.get("account_id")
        
        if not account_id:
            return jsonify({"error": "Missing account_id"}), 400
        
        account = db.get_account(account_id)
        if not account:
            return jsonify({"error": f"Account {account_id} not found"}), 404
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ACCOUNT ROUTES
# ============================================================================

@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """Get all accounts."""
    print("🔴 GET /api/accounts - ENDPOINT CALLED", flush=True)
    accounts = db.get_all_accounts()
    return jsonify({"accounts": accounts}), 200


@app.route("/api/accounts/<account_id>", methods=["GET"])
def get_account(account_id):
    """Get single account details."""
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    return jsonify(account), 200


# ============================================================================
# BLOG ROUTES
# ============================================================================

@app.route("/api/blogs", methods=["GET"])
@validate_account
def get_blogs():
    """Get blogs for an account."""
    account_id = request.args.get("account_id")
    status = request.args.get("status")  # optional: draft, posted
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    
    blogs = db.get_blogs_by_account(account_id, status=status, limit=limit, offset=offset)
    
    # Convert ObjectId to string for JSON serialization
    for blog in blogs:
        if "_id" in blog:
            blog["_id"] = str(blog["_id"])
    
    return jsonify({
        "account_id": account_id,
        "blogs": blogs,
        "count": len(blogs)
    }), 200


@app.route("/api/blogs/<blog_id>", methods=["GET"])
def get_blog(blog_id):
    """Get single blog details."""
    blog = db.get_blog_by_id(blog_id)
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    return jsonify(blog), 200


@app.route("/api/test/endpoint", methods=["GET"])
def test_endpoint():
    """Test endpoint to verify Flask code reloading."""
    msg = "TEST ENDPOINT CALLED - Flask is reloading code!"
    print(msg, flush=True)
    logger.info(msg)
    return jsonify({
        "status": "ok",
        "message": msg,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/api/blogs/generate", methods=["POST"])
@validate_account
def generate_blogs():
    """Generate new blogs for an account."""
    # Debug to file since print()/logger aren't showing
    with open("endpoint_debug.log", "a") as f:
        f.write(f"\n=== ENDPOINT CALLED at {datetime.now().isoformat()} ===\n")
    
    logger.info("[ENDPOINT CALLED] /api/blogs/generate")
    
    if not blog_generator:
        logger.error("[ERROR] Blog generator is None!")
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration and API key"
        }), 500
    
    account_id = request.json.get("account_id")
    topics_to_generate = request.json.get("topics")
    
    with open("endpoint_debug.log", "a") as f:
        f.write(f"account_id: {account_id}\n")
        f.write(f"topics_to_generate: {topics_to_generate}\n")
        f.write(f"blog_generator type: {type(blog_generator)}\n")
    
    logger.info(f"  account_id: {account_id}")
    logger.info(f"  topics_to_generate: {topics_to_generate}")
    
    if not topics_to_generate:
        topics_to_generate = {topic_id: 3 for topic_id in Config.TOPICS.keys()}
        logger.info(f"  Using default topics: {topics_to_generate}")
    
    generated_count = 0
    error = None
    
    try:
        for topic_id, count in topics_to_generate.items():
            if topic_id not in Config.TOPICS:
                logger.warning(f"Unknown topic: {topic_id}")
                continue
            
            topic_info = Config.TOPICS[topic_id]
            logger.info(f"  Generating {count} blogs for topic: {topic_id}")
            with open("endpoint_debug.log", "a") as f:
                f.write(f"  Processing topic: {topic_id}\n")
            
            for i in range(count):
                logger.info(f"    Calling blog_generator.generate_blog()...")
                try:
                    blog_data = blog_generator.generate_blog(
                        topic=topic_info["name"],
                        topic_description=topic_info["description"],
                        keywords=topic_info["keywords"]
                    )
                    with open("endpoint_debug.log", "a") as f:
                        f.write(f"      generate_blog() returned OK: {blog_data is not None}\n")
                        if blog_data:
                            f.write(f"      keys: {list(blog_data.keys()) if isinstance(blog_data, dict) else 'NOT_DICT'}\n")
                except Exception as ex:
                    with open("endpoint_debug.log", "a") as f:
                        f.write(f"      generate_blog() EXCEPTION: {type(ex).__name__}: {ex}\n")
                    raise
                    
                logger.info(f"    Result: {blog_data is not None}")
                
                if blog_data:
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = topic_id
                    blog_id = db.insert_blog(blog_data)
                    logger.info(f"[SUCCESS] Generated blog {i+1}/{count} for {account_id}/{topic_id}: {blog_id}")
                    generated_count += 1
                else:
                    logger.error(f"[FAIL] Failed to generate blog {i+1}/{count} for {account_id}/{topic_id}")
        
    except Exception as e:
        error = str(e)
        logger.error(f"[ERROR] Generation error for {account_id}: {error}", exc_info=True)
        with open("endpoint_debug.log", "a") as f:
            f.write(f"EXCEPTION: {error}\n")
    
    with open("endpoint_debug.log", "a") as f:
        f.write(f"Generated {generated_count} blogs, error: {error}\n")
        f.write(f"=== END ENDPOINT ===\n")
    
    logger.info(f"[COMPLETE] Generation: {generated_count} blogs generated, error: {error}")
    
    # Log generation event
    db.log_generation(account_id, generated_count, error)
    
    return jsonify({
        "account_id": account_id,
        "generated_count": generated_count,
        "error": error,
        "message": f"Successfully generated {generated_count} blogs"
    }), 200 if not error else 500


@app.route("/api/blogs/<blog_id>/mark-posted", methods=["PUT"])
def mark_blog_posted(blog_id):
    """Mark a blog as posted."""
    success = db.mark_blog_posted(blog_id)
    
    if not success:
        return jsonify({"error": "Blog not found or could not be updated"}), 404
    
    blog = db.get_blog_by_id(blog_id)
    return jsonify({
        "message": "Blog marked as posted",
        "blog": blog
    }), 200


@app.route("/api/blogs/<blog_id>/copy", methods=["GET"])
def copy_blog_content(blog_id):
    """Get blog content for copying (title and body separate)."""
    blog = db.get_blog_by_id(blog_id)
    
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    
    return jsonify({
        "blog_id": blog_id,
        "title": blog.get("title", ""),
        "body": blog.get("body", ""),
        "topic": blog.get("topic", ""),
        "copy_text_title": blog.get("title", ""),
        "copy_text_body": blog.get("body", "")
    }), 200


@app.route("/api/blogs/<blog_id>", methods=["DELETE"])
def delete_blog(blog_id):
    """Delete a blog (draft only)."""
    blog = db.get_blog_by_id(blog_id)
    
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    
    if blog.get("status") != "draft":
        return jsonify({"error": "Can only delete draft blogs"}), 400
    
    success = db.delete_blog(blog_id)
    
    if not success:
        return jsonify({"error": "Could not delete blog"}), 500
    
    return jsonify({"message": "Blog deleted successfully"}), 200


# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@app.route("/api/dashboard/<account_id>", methods=["GET"])
def get_dashboard(account_id):
    """Get dashboard summary for an account."""
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    summary = db.get_dashboard_summary(account_id)
    return jsonify(summary), 200


@app.route("/api/generation-history/<account_id>", methods=["GET"])
def get_generation_history(account_id):
    """Get generation history for an account."""
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    limit = int(request.args.get("limit", 10))
    history = db.get_generation_history(account_id, limit=limit)
    
    return jsonify({
        "account_id": account_id,
        "history": history
    }), 200


# ============================================================================
# INSIGHT-DRIVEN BLOG GENERATION
# ============================================================================

@app.route("/api/insights/generate-blogs", methods=["POST"])
def generate_blogs_from_insights():
    """
    Generate blog posts for all 5 accounts from WF1 content insights.
    
    This endpoint:
    1. Fetches pending insights from content_insights collection
    2. For each account (1-5): Generates a blog post variant from each insight
    3. Stores blogs in the blogs collection with account_id
    4. Updates insight status to blogs_generated
    
    Request body (optional):
    {
        "limit": 20  // max insights to process (default 20)
    }
    
    Response:
    {
        "success": true,
        "total_blogs": 45,  // e.g., 15 insights * 3 accounts
        "accounts": {
            "account_1": {"blogs_generated": 15},
            "account_2": {"blogs_generated": 15},
            ...
        },
        "insights_processed": 15
    }
    """
    logger.info("\n" + "=" * 80)
    logger.info("[API] POST /api/insights/generate-blogs - TRIGGERED")
    logger.info("=" * 80)
    
    if not blog_generator:
        logger.error("Blog generator not initialized")
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration and API key"
        }), 500
    
    try:
        # Get insights limit from request (default 20)
        insights_limit = 20
        if request.is_json:
            insights_limit = request.json.get("limit", 20)
        
        logger.info(f"Generating blogs from insights (limit: {insights_limit})")
        
        # Call insight-driven generation
        result = generate_blogs_from_insights_now(
            db=db,
            generator=blog_generator,
            mongodb_uri=Config.MONGODB_URI,
            mongodb_db=Config.MONGODB_DB
        )
        
        logger.info(f"Blog generation from insights: {result}")
        
        return jsonify(result), 200 if result.get("success") else 500
    
    except Exception as e:
        logger.error(f"Error generating blogs from insights: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "total_blogs": 0,
            "accounts": {}
        }), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Blog Generation Platform"
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.before_request
def before_request():
    """Setup before request."""
    pass


@app.teardown_appcontext
def teardown_db(exception=None):
    """Cleanup on shutdown."""
    global scheduler
    if scheduler:
        try:
            logger.info("Stopping blog generation scheduler...")
            scheduler.stop()
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")


if __name__ == "__main__":
    try:
        logger.info("Starting Blog Generation Platform API...")
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=Config.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        db.close()
