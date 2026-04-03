# Render Deployment Quick Start

## **📋 Checklist: 5 Minutes to Live**

### ✓ Done (Already Prepared)
- [x] MongoDB Atlas account set up
- [x] MongoDB URI: `mongodb+srv://himanshu123:himanshu123@cluster0.ecqcp1z.mongodb.net/?appName=Cluster0`
- [x] OpenRouter API Key: `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`
- [x] All code ready for deployment
- [x] Environment variables configured locally

### ⏳ Do Now (5 minutes)

#### Step 1: Create Render Account (2 min)
```
1. Go to https://render.com
2. Click "Sign Up"
3. Use GitHub or email
4. Verify email
5. Done!
```

#### Step 2: Connect GitHub Repository (2 min)

**Option A: If your repo is already on GitHub**
```bash
# Just make sure latest code is pushed
cd e:\prompt_megallm
git status
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

**Option B: If not on GitHub yet**
```bash
cd e:\prompt_megallm

# Configure git
git config user.email "your-email@gmail.com"
git config user.name "Your Name"

# Add all files
git add .
git commit -m "Initial commit - MegaLLM Blog Platform"

# Create repo on github.com/new named "Megallm-updated-prompt"

# Push to GitHub
git remote add origin https://github.com/YOUR-USERNAME/Megallm-updated-prompt.git
git branch -M main
git push -u origin main
```

#### Step 3: Deploy on Render (1 min)

1. Go to **https://render.com/dashboard**
2. Click **+ New** → **Web Service**
3. Connect GitHub → Select your repo
4. Fill settings:
   - **Name:** `megallm-blog-platform`
   - **Runtime:** `Python 3.9`
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `cd blog_platform && gunicorn wsgi:app --bind 0.0.0.0:$PORT`
5. Click **Advanced**
6. Add environment variables (copy-paste from table below)
7. Click **Create Web Service**

### Environment Variables to Add in Render

Copy these exactly:

```
MONGODB_URI=mongodb+srv://himanshu123:himanshu123@cluster0.ecqcp1z.mongodb.net/?appName=Cluster0

MONGODB_DB=megallm_blog_platform

OPENROUTER_API_KEY=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

USE_OPENROUTER=true

OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free

FLASK_ENV=production
```

---

## **✅ Your App is Live!**

After ~3 minutes, you'll see:
```
✓ Build succeeded
✓ Service live at: https://megallm-blog-platform.onrender.com
```

**Test it:**
1. Open the URL in browser
2. Click "Generate Blogs" tab
3. Click button
4. See magic happen! ✨

---

## **📚 Detailed Guide**

Full step-by-step with screenshots: [RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md)

---

## **Key Points**

- ✅ **Completely FREE** (Render free tier forever)
- ✅ **Always On** (no sleep like Heroku)
- ✅ **Auto-Deploy** (just `git push` and it redeploys)
- ✅ **All Data** (352 articles, 36 insights, 84 blogs included)
- ✅ **Ready to Use** (users can generate blogs immediately)

---

**Questions? Check [RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md) for detailed instructions.**
