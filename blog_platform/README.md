# MegaLLM Blog Generation Platform

A streamlined, account-based blog generation system for MegaLLM targeting CTOs at AI startups.

## Features

✅ **Blog-Only Generation** - No multi-platform complexity
✅ **5 Managed Accounts** - Account 1 through Account 5  
✅ **Automatic Scheduling** - 12 blogs every 24 hours per account (3 per topic)
✅ **4 CTO Topics** - Cost Optimization, Performance, Reliability, Infrastructure/Compliance
✅ **Web-Based Dashboard** - Intuitive UI for managing blogs
✅ **Copy Functionality** - Separate title and body copy buttons
✅ **Mark Posted** - Track published vs draft blogs
✅ **Generation History** - View past generation events
✅ **MongoDB Integration** - Persistent storage

---

## Architecture

```
blog_platform/
├── config.py              # Configuration & settings
├── database.py            # MongoDB models & utilities
├── blog_generator.py      # MegaLLM API integration
├── app.py                 # Flask API backend
├── scheduler.py           # APScheduler for auto-generation
├── main.py                # Entry point (starts Flask + Scheduler)
├── templates/
│   └── index.html         # Web dashboard UI
└── requirements.txt       # Python dependencies
```

---

## Setup

### 1. Install Dependencies

```bash
cd blog_platform
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create or update your `.env` file in the parent directory:

```env
# MegaLLM API
MEGALLM_API_KEY=sk-mega-xxxxx
OPENAI_API_KEY=sk-mega-xxxxx  # Falls back if MEGALLM_API_KEY not set
MEGALLM_MODEL=deepseek-ai/deepseek-v3.1

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm_blog_platform

# Flask
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 3. Ensure MongoDB is Running

```bash
# On Windows with MongoDB installed
mongod

# Or with Docker
docker run -d -p 27017:27017 mongo
```

### 4. Start the Platform

```bash
python main.py
```

The platform will:
- Initialize 5 accounts in MongoDB
- Start the background scheduler
- Listen on `http://localhost:5000`

---

## Usage

### Web Dashboard

Open `http://localhost:5000` to access the dashboard:

1. **Select an account** - Choose from 5 accounts (Account 1-5)
2. **View statistics** - See total blogs, draft/posted counts, breakdown by topic
3. **Generate blogs** - Click "🚀 Generate Blogs Now" to manually trigger generation
4. **Filter blogs** - View All, Draft, or Posted blogs
5. **Copy content** - Click "📋 Copy" button to copy title and body separately
6. **Mark as posted** - Click "✅ Mark Posted" to update blog status
7. **View history** - See generation events and statistics

---

## Configuration

### Blog Generation Settings (`config.py`)

```python
BLOG_WORD_COUNT_MIN = 500
BLOG_WORD_COUNT_MAX = 800
BLOG_TEMPERATURE = 0.65
BLOG_MAX_TOKENS = 2000

BLOGS_PER_24_HOURS = 12  # Total across all accounts
GENERATION_INTERVAL_MINUTES = 120  # Every 2 hours
```

### Topics

Four CTO-focused topics (12 blogs/24h = 3 per topic):

1. **Cost Optimization** - Reducing inference costs
2. **Performance & Speed** - Latency reduction, throughput
3. **Reliability & Uptime** - Production stability, failover
4. **Infrastructure & Compliance** - Data residency, GDPR, security

Each blog is 500-800 words, targeting startup CTOs in UK/SG/AU/NZ.

---

## API Endpoints

### Accounts
- `GET /api/accounts` - Get all accounts
- `GET /api/accounts/<account_id>` - Get single account

### Blogs
- `GET /api/blogs?account_id=xxx` - List blogs (with optional `status` filter)
- `GET /api/blogs/<blog_id>` - Get single blog
- `GET /api/blogs/<blog_id>/copy` - Get copy-ready content (title + body)
- `POST /api/blogs/generate` - Generate new blogs
- `PUT /api/blogs/<blog_id>/mark-posted` - Mark blog as posted
- `DELETE /api/blogs/<blog_id>` - Delete draft blog

### Dashboard
- `GET /api/dashboard/<account_id>` - Dashboard summary
- `GET /api/generation-history/<account_id>` - Generation history

### Health
- `GET /api/health` - Health check

---

## Database Schema

### Collections

#### `accounts`
```json
{
  "_id": ObjectId,
  "account_id": "account_1",
  "name": "Account 1",
  "description": "Main content account",
  "created_at": "2024-01-15T10:30:00Z",
  "blog_count": 45,
  "posted_count": 30,
  "last_generation": "2024-01-15T10:30:00Z"
}
```

#### `blogs`
```json
{
  "_id": ObjectId,
  "account_id": "account_1",
  "topic": "cost_optimization",
  "title": "5 Ways to Cut LLM Inference Costs by 40%",
  "body": "Full blog content...",
  "status": "draft" | "posted",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "posted_at": "2024-01-15T11:00:00Z" | null,
  "views": 0
}
```

#### `generation_history`
```json
{
  "_id": ObjectId,
  "account_id": "account_1",
  "generated_count": 4,
  "error": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Automatic Generation

The scheduler runs every **2 hours** per account:

1. Selects 4 topics (Cost, Performance, Reliability, Infrastructure)
2. Generates 3 blogs per topic (12 total/24h)
3. Inserts blogs with status `draft`
4. Logs generation event in `generation_history`

To manually trigger: **Click "🚀 Generate Blogs Now"** in the dashboard.

---

## Dashboard Features

### Statistics Card
- Total blogs for the account
- Draft blogs count
- Posted blogs count
- Blogs breakdown by topic

### Blog List
- Title, topic, status badge
- Content preview (truncated)
- Creation date
- Copy button (separate title/body)
- Mark Posted button (if draft)

### Actions
- Filter by status (All/Draft/Posted)
- Generate new blogs
- View generation history
- Sort by creation date (newest first)

---

## Copy & Paste Workflow

1. Open blog from list
2. Click **"📋 Copy"** button
3. Modal opens with:
   - **Title** section - Click "Copy Title" to copy headline only
   - **Body** section - Click "Copy Body" to copy the full article
4. Paste into your CMS or platform
5. After publishing, return to dashboard and click **"✅ Mark Posted"**

---

## Troubleshooting

### No blogs generating
1. Check API key in `.env` has credits
2. Verify MongoDB is running: `mongo --eval "db.adminCommand('ping')"`
3. Check logs in `blog_platform.log`
4. Try manually generating: Click "🚀 Generate Blogs Now"

### API connection errors
1. Verify Flask is running: Check console output
2. Ensure port 5000 is not in use
3. Check firewall settings

### MongoDB connection failed
1. Start MongoDB: `mongod` (Windows: Services > MongoDB)
2. Test connection: `mongo` in terminal
3. Verify URI in `.env`: `mongodb://localhost:27017`

### LLM generation failures
1. Check API key is valid
2. Verify account has credits
3. Test with `python -c "from blog_generator import BlogGenerator; bg = BlogGenerator('key', 'url', 'model'); bg.generate_blog(...)"`

---

## Performance Tips

1. **Batch generation** - Generate multiple accounts simultaneously via API
2. **Database indexing** - Already optimized with indexes on account_id, topic, status, created_at
3. **Caching** - Dashboard auto-refreshes every 30 seconds
4. **Rate limiting** - Add Flask-Limiter for API rate limits if needed

---

## Extending the Platform

### Add More Accounts
Edit `config.py`:
```python
ACCOUNTS = [
    {"id": "account_1", "name": "Account 1", ...},
    {"id": "account_6", "name": "Account 6", ...},  # Add new
]
```

### Add New Topics
Edit `config.py` `TOPICS` dict:
```python
TOPICS = {
    "new_topic": {
        "name": "New Topic Name",
        "description": "Description",
        "keywords": ["keyword1", "keyword2"],
        "blogs_per_cycle": 3
    }
}
```

### Change Generation Schedule
Edit `config.py`:
```python
GENERATION_INTERVAL_MINUTES = 60  # Generate every hour instead of 2
```

---

## API Examples

### Get all blogs for Account 1
```bash
curl http://localhost:5000/api/blogs?account_id=account_1
```

### Generate 12 blogs now
```bash
curl -X POST http://localhost:5000/api/blogs/generate \
  -H "Content-Type: application/json" \
  -d '{"account_id": "account_1"}'
```

### Copy blog content
```bash
curl http://localhost:5000/api/blogs/<blog_id>/copy
```

### Mark blog as posted
```bash
curl -X PUT http://localhost:5000/api/blogs/<blog_id>/mark-posted
```

---

## Logs

All events logged to `blog_platform.log`:

```
2024-01-15 10:30:00 - INFO - Starting Blog Generation Platform API...
2024-01-15 10:30:01 - INFO - Created account: account_1
2024-01-15 10:30:05 - INFO - Blog generation scheduler started
2024-01-15 11:00:00 - INFO - Starting blog generation for account_1
2024-01-15 11:00:45 - INFO - ✓ Generated 12 blogs for account_1
```

---

## License

Commercial use. MegaLLM platform only.

---

## Support

For issues or questions, check:
1. `.log` files for error messages
2. MongoDB connection: `mongo` shell
3. API health: `http://localhost:5000/api/health`
4. Flask console output for startup errors
