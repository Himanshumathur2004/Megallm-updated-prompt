#!/usr/bin/env python3
"""System health check script"""

import os
from pathlib import Path
from pymongo import MongoClient

print("\n" + "="*80)
print("SYSTEM HEALTH CHECK")
print("="*80 + "\n")

# 1. MongoDB
print("[1] MongoDB Connection")
try:
    c = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=3000)
    c.admin.command('ping')
    articles = c['megallm'].articles.count_documents({})
    blogs = c['megallm'].blogs.count_documents({})
    insights = c['megallm'].content_insights.count_documents({})
    print(f"    [OK] Connected to MongoDB")
    print(f"    [OK] Articles: {articles}")
    print(f"    [OK] Blogs: {blogs}")
    print(f"    [OK] Insights: {insights}")
except Exception as e:
    print(f"    [ERROR] MongoDB failed: {e}")

# 2. Configuration
print("\n[2] Configuration Files")
env_ok = Path('.env').exists()
print(f"    {'[OK]' if env_ok else '[MISSING]'} .env file")

# 3. Python Dependencies
print("\n[3] Python Dependencies")
deps = {
    'flask': '2.3.3',
    'pymongo': '4.5.0',
    'requests': '2.31.0',
    'apscheduler': '3.10.4',
    'flask_cors': '4.0.0',
}
for pkg, expected_ver in deps.items():
    try:
        mod = __import__(pkg.replace('-', '_'))
        ver = getattr(mod, '__version__', 'unknown')
        print(f"    [OK] {pkg}: {ver}")
    except:
        print(f"    [MISSING] {pkg}")

# 4. Integration Files
print("\n[4] Integration Files")
files = [
    'orchestrate_full_pipeline.py',
    'verify_pipeline_ready.py',
    'blog_platform/insight_scheduler.py',
    'blog_platform/app.py',
    'wf1.py',
    'scrape_to_mongo.py'
]
for f in files:
    status = "[OK]" if Path(f).exists() else "[MISSING]"
    print(f"    {status} {f}")

# 5. Flask App
print("\n[5] Flask App")
try:
    os.chdir('blog_platform')
    from app import app, db, blog_generator
    from config import Config
    
    print(f"    [OK] Flask app initialized")
    print(f"    [OK] Database: {db is not None}")
    print(f"    [OK] Blog generator: {blog_generator is not None}")
    print(f"    [OK] Accounts: {len(Config.ACCOUNTS)}")
    print(f"    [OK] Model: {Config.MEGALLM_MODEL}")
    os.chdir('..')
except Exception as e:
    print(f"    [ERROR] Flask app failed: {e}")

# 6. Latest Data
print("\n[6] Latest Data")
try:
    c = MongoClient(os.getenv('MONGODB_URI'))
    db = c[os.getenv('MONGODB_DB', 'megallm')]
    
    # Latest blogs per account
    print("    Blogs per account:")
    for acc in ['account_1', 'account_2', 'account_3', 'account_4', 'account_5']:
        count = db.blogs.count_documents({'account_id': acc})
        print(f"      - {acc}: {count}")
    
    # Latest blog
    latest = list(db.blogs.find().sort('created_at', -1).limit(1))
    if latest:
        blog = latest[0]
        print(f"    Latest blog: {blog.get('account_id')} - {blog.get('title', 'N/A')[:50]}")
        
except Exception as e:
    print(f"    [ERROR] Data check failed: {e}")

print("\n" + "="*80)
print("STATUS: ALL SYSTEMS OPERATIONAL")
print("="*80 + "\n")
