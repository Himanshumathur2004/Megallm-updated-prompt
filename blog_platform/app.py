"""Flask backend API for blog platform."""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from functools import wraps
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys
from threading import Thread

from config import Config
from database import Database
from blog_generator import BlogGenerator
from mock_blog_generator import MockBlogGenerator
from insight_scheduler import generate_blogs_from_insights_now
from render_pipeline import create_render_pipeline

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
    if not Config.OPENROUTER_API_KEY:
        logger.error("ERROR: OPENROUTER_API_KEY not set in .env file!")
        logger.error("Set OPENROUTER_API_KEY=sk-or-v1-... in .env")
        return False
    return True

# Initialize database and generator
db = None
blog_generator = None

try:
    if not validate_config():
        raise ValueError("Configuration validation failed")
    
    db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
    
    # Use OpenRouter API
    blog_generator = BlogGenerator(Config.OPENROUTER_API_KEY, Config.OPENROUTER_BASE_URL, Config.OPENROUTER_MODEL)
    logger.info("✓ App initialized")
    
except Exception as e:
    logger.error(f"Initialization error: {e}")
    
# Ensure we have a database instance (either MongoDB or in-memory)
if db is None:
    try:
        from database import InMemoryDatabase
        db = InMemoryDatabase()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

# Ensure we have a blog generator (with fallback error handling)
if blog_generator is None:
    logger.warning("Blog generator not initialized - using fallback mode")

# Initialize accounts on startup
def init_accounts():
    """Create accounts if they don't exist, or update if names changed."""
    created = 0
    updated = 0
    
    for account in Config.ACCOUNTS:
        existing_account = db.get_account(account["id"])
        if existing_account:
            # Check if name or description changed
            if existing_account.get("name") != account["name"] or existing_account.get("description") != account["description"]:
                # Update the account with new name/description
                db.update_account(account["id"], account["name"], account["description"])
                updated += 1
        else:
            # Create new account
            if db.create_account(account["id"], account["name"], account["description"]):
                created += 1
    
    if created > 0 or updated > 0:
        logger.info(f"Accounts: {created} created, {updated} updated")

init_accounts()


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


@app.route("/api/diagnostic", methods=["GET"])
def diagnostic():
    """Diagnostic endpoint to check database and config status."""
    # IMPORTANT: Never expose MongoDB URI or credentials!
    return jsonify({
        "database": {
            "type": "in-memory" if db.is_memory else "MongoDB",
            "is_connected": not db.is_memory,
            "is_memory_fallback": db.is_memory,
            "warning": "USING IN-MEMORY DATABASE - DATA WILL BE LOST ON RESTART!" if db.is_memory else "✓ MongoDB connected"
        },
        "config": {
            "openrouter_configured": bool(Config.OPENROUTER_API_KEY),
            "accounts_count": len(Config.ACCOUNTS),
            "topics_count": len(Config.TOPICS)
        },
        "data": {
            "total_accounts": len(db.get_all_accounts()),
            "total_blogs": sum(len(db.get_blogs_by_account(a['account_id'])) for a in db.get_all_accounts())
        }
    }), 200


@app.route("/api/blogs/generate", methods=["POST"])
@validate_account
def generate_blogs():
    """Generate new blogs for an account."""
    
    if not blog_generator:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration and API key"
        }), 500
    
    account_id = request.json.get("account_id")
    topics_to_generate = request.json.get("topics")
    
    if not topics_to_generate:
        topics_to_generate = {topic_id: 3 for topic_id in Config.TOPICS.keys()}
    
    generated_count = 0
    error = None
    
    try:
        for topic_id, count in topics_to_generate.items():
            if topic_id not in Config.TOPICS:
                continue
            
            topic_info = Config.TOPICS[topic_id]
            
            for i in range(count):
                try:
                    blog_data = blog_generator.generate_blog(
                        topic=topic_info["name"],
                        topic_description=topic_info["description"],
                        keywords=topic_info["keywords"]
                    )
                except Exception as ex:
                    raise
                
                if blog_data:
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = topic_id
                    blog_id = db.insert_blog(blog_data)
                    generated_count += 1
        
    except Exception as e:
        error = str(e)
        logger.error(f"Generation error: {error}")
    
    # Log generation event
    db.log_generation(account_id, generated_count, error)
    
    return jsonify({
        "account_id": account_id,
        "generated_count": generated_count,
        "error": error,
        "message": f"Successfully generated {generated_count} blogs"
    }), 200 if not error else 500


def _generate_blogs_background():
    """
    Background task: Generate 1 blog per account.
    Runs in separate thread to avoid blocking client.
    """
    try:
        logger.info("Starting background blog generation...")
        all_accounts = db.get_all_accounts()
        total_generated = 0
        
        for account in all_accounts:
            account_id = account.get("account_id")
            account_name = account.get("name", account_id)
            
            # Pick first topic
            first_topic_id = list(Config.TOPICS.keys())[0]
            topic_info = Config.TOPICS[first_topic_id]
            
            try:
                logger.info(f"Generating blog for {account_name}...")
                blog_data = blog_generator.generate_blog(
                    topic=topic_info["name"],
                    topic_description=topic_info["description"],
                    keywords=topic_info["keywords"]
                )
                
                if blog_data:
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = first_topic_id
                    db.insert_blog(blog_data)
                    total_generated += 1
                    logger.info(f"✓ Generated blog for {account_name}")
            except Exception as e:
                logger.error(f"Error generating blog for {account_id}: {e}")
        
        logger.info(f"Background generation complete: {total_generated} blogs created")
    except Exception as e:
        logger.error(f"Background generation failed: {e}")


@app.route("/api/pipeline/run-complete", methods=["POST"])
def run_complete_pipeline():
    """
    Pipeline endpoint: Start background blog generation and return immediately.
    Prevents timeout errors by not waiting for API calls.
    """
    if not blog_generator or not db:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration"
        }), 500
    
    try:
        # Start background generation thread
        bg_thread = Thread(target=_generate_blogs_background, daemon=True)
        bg_thread.start()
        logger.info("Background blog generation started")
        
        # Return success immediately (blogs will appear as they're generated)
        return jsonify({
            "success": True,
            "message": "Blog generation started in background",
            "status": "pending",
            "info": "Blogs will appear in the dashboard as they're generated",
            "steps": {
                "scrape": {"success": True, "inserted": 0},
                "insights": {"success": True, "insights_created": 0},
                "generation": {"total_blogs": 0, "accounts": {}}
            }
        }), 200
        
    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        logger.error(error_msg)
        
        return jsonify({
            "success": False,
            "error": error_msg,
            "status": "failed"
        }), 500


@app.route("/api/pipeline/status", methods=["GET"])
def pipeline_status():
    """Get current pipeline status."""
    return jsonify({
        "status": "ready",
        "message": "Pipeline ready for execution",
        "last_run": None,
        "next_scheduled": None
    }), 200


@app.route("/api/pipeline/webhook", methods=["POST", "OPTIONS"])
def handle_pipeline_webhook():
    """
    Webhook endpoint for receiving pipeline completion notifications.
    
    Expected POST payload:
    {
        "workflow_id": "string",
        "account_id": "string",
        "status": "completed" | "failed",
        "result": {
            "blogs": [list of blog IDs],
            "error": "error message if status is failed"
        }
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        workflow_id = data.get('workflow_id')
        account_id = data.get('account_id')
        status = data.get('status')
        result = data.get('result', {})
        
        if not all([workflow_id, account_id, status]):
            return jsonify({"error": "Missing required fields: workflow_id, account_id, status"}), 400
        
        if status == 'completed':
            blogs = result.get('blogs', [])
            return jsonify({
                "success": True,
                "message": f"Pipeline {workflow_id} processed successfully",
                "blogs_count": len(blogs)
            }), 200
        
        elif status == 'failed':
            error = result.get('error', 'Unknown error')
            return jsonify({
                "success": False,
                "message": f"Pipeline {workflow_id} failed",
                "error": error
            }), 200
        
        else:
            return jsonify({"error": f"Invalid status: {status}"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
# INSIGHTS & ARTICLES ROUTES (Frontend Dependencies)
# ============================================================================

@app.route("/api/insights", methods=["GET"])
def get_insights():
    """Get insights (currently just returns empty for frontend compatibility)."""
    return jsonify({
        "insights": [],
        "count": 0,
        "message": "No insights available"
    }), 200


@app.route("/api/insights/generate-blogs", methods=["POST"])
def generate_blogs_from_insights():
    """
    Generate blog posts from insights for selected accounts.
    
    Request body:
    {
        "accounts": ["account_1", "account_2", ...]  // accounts to generate for (optional)
    }
    
    Response:
    {
        "success": true,
        "total_blogs": 45,
        "articles_scraped": 15,
        "accounts": {
            "account_1": 15,
            "account_2": 15,
            ...
        }
    }
    """
    if not blog_generator:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration and API key",
            "success": False,
            "total_blogs": 0,
            "articles_scraped": 0
        }), 500
    
    try:
        data = request.get_json() or {}
        accounts = data.get("accounts")
        
        # Call insight-driven generation
        result = generate_blogs_from_insights_now(
            db=db,
            generator=blog_generator,
            mongodb_uri=Config.MONGODB_URI,
            mongodb_db=Config.MONGODB_DB,
            accounts=accounts
        )
        
        return jsonify(result), 200 if result.get("success") else 500
    
    except Exception as e:
        logger.error(f"Error generating blogs from insights: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "total_blogs": 0,
            "articles_scraped": 0,
            "accounts": {}
        }), 500


@app.route("/api/articles", methods=["GET"])
def get_articles():
    """Get articles (currently just returns empty for frontend compatibility)."""
    return jsonify({
        "articles": [],
        "count": 0,
        "message": "No articles available"
    }), 200


@app.route("/api/blogs", methods=["GET"])
def get_all_blogs():
    """Get all blogs across all accounts."""
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    
    if account_id:
        # If account specified, get blogs for that account
        blogs = db.get_blogs_by_account(account_id, status=status, limit=limit, offset=offset)
    else:
        # Otherwise get all blogs
        blogs = []
    
    # Convert ObjectId to string for JSON serialization
    for blog in blogs:
        if "_id" in blog:
            blog["_id"] = str(blog["_id"])
    
    return jsonify({
        "blogs": blogs,
        "count": len(blogs)
    }), 200


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
# BLOG GENERATION FROM SCRAPED ARTICLES (via insights)
# ============================================================================

@app.route("/api/pipeline/generate-from-articles", methods=["POST"])
def generate_blogs_from_articles():
    """
    Generate blog posts directly from scraped articles.
    
    This endpoint:
    1. Scrapes articles from RSS feeds
    2. Generates insights from articles (WF1)
    3. Generates blog posts for all 5 accounts from those insights
    4. Stores blogs with account_id
    
    Request body (optional):
    {
        "limit": 20  // max articles to process (default: all)
    }
    
    Response:
    {
        "success": true,
        "total_blogs": 45,
        "articles_processed": 15,
        "accounts": {
            "account_1": 15,
            "account_2": 15,
            "account_3": 15,
            ...
        }
    }
    """
    if not blog_generator:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration and API key"
        }), 500
    
    try:
        # Call insight-driven generation
        result = generate_blogs_from_insights_now(
            db=db,
            generator=blog_generator,
            mongodb_uri=Config.MONGODB_URI,
            mongodb_db=Config.MONGODB_DB
        )
        
        return jsonify(result), 200 if result.get("success") else 500
    
    except Exception as e:
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
    pass


if __name__ == "__main__":
    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=Config.DEBUG
        )
    except KeyboardInterrupt:
        if db:
            db.close()
