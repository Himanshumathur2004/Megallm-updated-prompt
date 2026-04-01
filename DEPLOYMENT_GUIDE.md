# 🚀 MegaLLM Blog Platform - Heroku Deployment Guide

## **Overview**

This guide will help you deploy the MegaLLM Blog Platform to Heroku with:
- ✓ Flask API backend
- ✓ Web dashboard frontend
- ✓ MongoDB Atlas cloud database
- ✓ OpenRouter LLM integration
- ✓ Full production pipeline (Scrape → Insights → Blogs)

**Timeline:** ~30 minutes total

---

## **Phase 1: Prerequisites (5 minutes)**

### 1.1 Create Accounts (Free)

**Heroku Free Tier:**
- Go to [heroku.com](https://heroku.com)
- Sign up for free account
- Verify email
- Install Heroku CLI: [https://devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)

**MongoDB Atlas Free Tier:**
- Go to [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
- Sign up for free account
- Create "Free" tier cluster (M0)
- Location: Choose closest to you

**OpenRouter API (Free):**
- Go to [openrouter.ai](https://openrouter.ai)
- Sign up
- Generate API key

### 1.2 Verify Local Setup

```bash
# Check Heroku CLI installed
heroku --version

# Check Git installed
git --version

# Check Python version
python --version  # Should be 3.8+
```

---

## **Phase 2: MongoDB Atlas Setup (8 minutes)**

### 2.1 Create Cluster

1. Go to **MongoDB Atlas** → **Clusters** → **+ Create**
2. Choose **Free Tier (M0)**
3. Select your region (closest to your location)
4. Click **Create Cluster** (wait 2-3 minutes)

### 2.2 Set Up Network Access

1. Click **Network Access**
2. Click **+ Add IP Address**
3. Select **Allow access from anywhere** (toggle)
4. Confirm with **0.0.0.0/0**

### 2.3 Create Database User

1. Click **Database Access**
2. Click **+ Add New Database User**
3. Username: `megallm_user`
4. Password: Create strong password (save it!)
5. Role: **Atlas admin** (for this user)
6. Click **Add User**

### 2.4 Get Connection String

1. Click **Databases** → Your Cluster
2. Click **Connect** → **Drivers**
3. Copy the connection string:

```
mongodb+srv://megallm_user:<password>@cluster-name.mongodb.net/megallm_blog_platform?retryWrites=true&w=majority
```

**Replace:**
- `<password>` with your database password
- Database name is optional in connection string (or use `/megallm_blog_platform`)

**Save this string** - you'll need it for Heroku

---

## **Phase 3: Prepare Project for Deployment (5 minutes)**

### 3.1 Verify Files Exist

Check these files are in your project root (`e:\prompt_megallm\`):

```
✓ requirements.txt       (dependencies)
✓ Procfile              (entry point for Heroku)
✓ blog_platform/wsgi.py (WSGI app)
✓ blog_platform/app.py  (Flask app)
✓ .env                  (environment variables - local only)
```

### 3.2 Create .env.example (for documentation)

Create file: `e:\prompt_megallm\.env.example`

```env
# MongoDB Atlas Connection String
MONGODB_URI=mongodb+srv://megallm_user:PASSWORD@cluster-name.mongodb.net/megallm_blog_platform?retryWrites=true&w=majority

# OpenRouter API
USE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free

# Flask
FLASK_ENV=production
```

### 3.3 Initialize Git (if not already done)

```bash
cd e:\prompt_megallm
git init
git add .
git commit -m "Initial commit for Heroku deployment"
```

---

## **Phase 4: Deploy to Heroku (10 minutes)**

### 4.1 Create Heroku App

```bash
cd e:\prompt_megallm

# Login to Heroku
heroku login

# Create app (name must be globally unique, lowercase, no spaces)
heroku create your-unique-app-name
# Example: heroku create megallm-blog-platform-v1
```

**Save your app name** - you'll see something like:
```
https://your-unique-app-name.herokuapp.com
```

### 4.2 Set Environment Variables on Heroku

```bash
# Using Heroku CLI
heroku config:set MONGODB_URI="mongodb+srv://megallm_user:PASSWORD@cluster-name.mongodb.net/megallm_blog_platform?retryWrites=true&w=majority"

heroku config:set USE_OPENROUTER=true

heroku config:set OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"

heroku config:set OPENROUTER_MODEL="qwen/qwen3.6-plus-preview:free"

heroku config:set FLASK_ENV=production
```

**Or via Dashboard:**
1. Go to your Heroku app
2. **Settings** → **Config Vars**
3. Click **Reveal Config Vars**
4. Add each variable above

### 4.3 Deploy to Heroku

```bash
cd e:\prompt_megallm

# Push to Heroku
git push heroku main

# Watch logs during deployment
heroku logs --tail

# When you see "Procfile declares types", deployment is starting
# Wait 2-3 minutes for Heroku to build and start the app
```

### 4.4 Verify Deployment

```bash
# Check if app is running
heroku ps

# You should see:
# Free dyno hours remaining this month: XXX
# dyno_type=web count=1 state=up

# View app logs
heroku logs

# Access your app
heroku open

# Or visit in browser
https://your-unique-app-name.herokuapp.com
```

---

## **Phase 5: Test the Deployment (5 minutes)**

### 5.1 Access Dashboard

**Open:** `https://your-unique-app-name.herokuapp.com/`

You should see:
- ✓ Dashboard with 5 stat cards (Blogs, Insights, Articles, Accounts)
- ✓ Tabs for Dashboard, Generate, Blogs, Insights, Accounts
- ✓ Green "Connected" indicator in navbar

### 5.2 Generate Blogs

1. Click **Generate Blogs** tab
2. Accounts should be checked (all 5)
3. Click **Generate Blogs** button
4. Wait 1-2 minutes (you'll see "Generating blogs..." spinner)
5. Should see success message

### 5.3 View Generated Blogs

1. Click **View Blogs** tab
2. You should see your generated blogs
3. Filter by account
4. Check the blog content and metadata

### 5.4 Monitor Logs

While testing, monitor Heroku logs:

```bash
heroku logs --tail
```

Watch for:
- ✓ "Initializing database..."
- ✓ "Database initialized"
- ✓ "LLM client: OpenRouter API"
- ✓ "API requests returning blogs"

---

## **Phase 6: Performance Notes**

### API Response Times on Heroku Free Tier

- **Cold start:** 5-10 seconds (first request after deploy)
- **Dashboard load:** 1-2 seconds
- **Blog generation:** 1-2 minutes (depends on OpenRouter)
- **Blog listing:** 500ms

### Heroku Free Tier Limits

- ⏰ **30 minute sleep:** App sleeps after 30 min of no traffic
- 🔄 **First request wake-up:** Takes 5-10 seconds
- 🕐 **550 free dyno hours/month:** ~23 hours/day
- 💾 **Database connections:** Limited (OK for 1-10 users)

### To Keep App Awake

Install **Kaffeine** (free):
1. Go to [kaffeine.herokuapp.com](https://kaffeine.herokuapp.com)
2. Enter your app URL
3. It will ping your app every 30 minutes

---

## **Phase 7: Upgrade (Optional)**

### Move to Paid Dyno (Optional)

For better performance without sleep:

```bash
# Upgrade to paid dyno (starts at $7/month)
heroku dyno:type --app your-unique-app-name

# Or via dashboard:
# Settings → Dyno Type → Choose "Standard" ($7/mo) or "Performance" ($50/mo)
```

### Scale Workers

For scheduled background jobs:

```bash
# Current free setup runs everything on web dyno
# If you need background jobs, add a worker dyno:
heroku dynos:create --type worker
```

---

## **Phase 8: Troubleshooting**

### 4.3 "Build failed" or "Slug too large"

```bash
# Check what's being uploaded
heroku config:set BUILDPACK_URL=heroku/python

# Make sure .gitignore excludes:
cat .gitignore

# Should exclude:
# __pycache__/
# .venv/
# *.pyc
# .env (but NOT .env.example)
```

### App Shows "Application Error"

```bash
# Check real error
heroku logs --tail

# Common issues:
# 1. Missing environment variables (check heroku config)
# 2. MongoDB connection string wrong
# 3. API key invalid
```

### Slow Blog Generation

This is normal! OpenRouter API calls take 10-15 seconds each. For 5 blogs (5 insights × 5 accounts ÷ 5 = 5 calls), expect 1-2 minutes.

### Database Quota Exceeded

If you exceed MongoDB Atlas M0 (512MB) limits:
1. Upgrade to M2 tier (starts at $9/month)
2. Or delete old blogs/generation_history

---

## **Phase 9: Post-Deployment Checklist**

After successful deployment:

```bash
# ✓ Set up automated backups (MongoDB Atlas)
# ✓ Enable 2FA on Heroku account
# ✓ Set up custom domain (optional, paid)
# ✓ Create production .env file
# ✓ Test all endpoints
# ✓ Monitor logs for errors
# ✓ Schedule regular backups
```

---

## **Phase 10: Accessing via Custom Domain (Optional)**

If you want custom domain like `blog.yourdomain.com`:

### 10.1 In Heroku Dashboard

1. **Settings** → **Domains and certificates**
2. **Add domain**
3. Enter `blog.yourdomain.com`
4. Note the DNS target (looks like `xxx.heroku-dns.com`)

### 10.2 In Your Domain Registrar

Add CNAME record:
- **Host:** blog
- **Points to:** (from Heroku)

---

## **Phase 11: Monitoring & Maintenance**

### Weekly Tasks

```bash
# Check app status
heroku status --app your-unique-app-name

# Review logs for errors
heroku logs --tail --num 100

# Check database size
# In MongoDB Atlas Dashboard → Collections → Metrics
```

### Set Up Metrics

In Heroku Dashboard:
1. **Metrics** tab
2. Monitor:
   - Response time
   - Error rate
   - Dyno load
   - Database connections

---

## **API Endpoints Available After Deployment**

Your app will have these endpoints live:

```
GET  https://your-app.herokuapp.com/
     → Dashboard web UI

GET  https://your-app.herokuapp.com/api/health
     → Returns {"status": "ok"}

GET  https://your-app.herokuapp.com/api/blogs
     → List all blogs

GET  https://your-app.herokuapp.com/api/insights
     → List all insights

GET  https://your-app.herokuapp.com/api/accounts
     → List all accounts

POST https://your-app.herokuapp.com/api/insights/generate-blogs
     → Trigger blog generation
```

---

## **Success Indicators**

You'll know everything works when:

✅ Dashboard loads and shows stats
✅ Can click "Generate Blogs" and see success message
✅ "View Blogs" tab shows your generated content
✅ No errors in `heroku logs`
✅ MongoDB Atlas shows documents in collections
✅ OpenRouter API key works (check costs dashboard)

---

## **Quick Reference: Useful Commands**

```bash
# View live logs (real-time)
heroku logs --tail

# View last 100 lines
heroku logs --num 100

# Check running processes
heroku ps

# Restart app
heroku restart

# View environment variables
heroku config

# View app URL
heroku info

# Open app in browser
heroku open

# Check MySQL/Database
heroku addons

# See releases and rollback
heroku releases
heroku releases:rollback

# Scale dynos
heroku scale web=1

# View cost estimation
heroku billing
```

---

## **Support & Troubleshooting**

**Heroku Documentation:** https://devcenter.heroku.com
**MongoDB Atlas Docs:** https://docs.mongodb.com/atlas
**OpenRouter API Docs:** https://openrouter.ai/docs

---

**Your app is now LIVE! 🎉** Share the URL with users and they can access the dashboard and generate blogs automatically.
