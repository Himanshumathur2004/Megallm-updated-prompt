# Local Testing Before Deployment

Before deploying to Heroku, follow these steps to test locally.

## Step 1: Set Up Local Environment

```bash
# Navigate to project
cd e:\prompt_megallm

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies (if not done)
pip install -r requirements.txt
```

## Step 2: Configure .env (Already should exist)

Verify your `.env` file has (for local MongoDB):

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm_blog_platform
USE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free
FLASK_ENV=development
```

## Step 3: Start Flask API

```bash
cd blog_platform
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
* WARNING in app.run()
```

## Step 4: Test Dashboard

Open browser: **http://localhost:5000/**

You should see the dashboard with stats.

## Step 5: Generate Test Blogs

1. Click "Generate Blogs" tab
2. Click "Generate Blogs" button
3. Wait 1-2 minutes
4. Refresh dashboard to see new blogs

## Step 6: Verify in MongoDB Compass

1. Open MongoDB Compass
2. Connect to `mongodb://localhost:27017`
3. Check collections:
   - blogs (should have new documents)
   - articles (252+)
   - content_insights (36+)

## Step 7: Ready to Deploy?

If all works locally, you're ready for Heroku!

Next: Follow [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
