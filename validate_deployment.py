"""Pre-Deployment Validation Script"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("🚀 PRE-DEPLOYMENT VALIDATION CHECKLIST")
print("=" * 60)

errors = []
warnings = []
success = []

# Check 1: Files exist
print("\n[1] Checking required files...")
required_files = [
    "requirements.txt",
    "Procfile",
    "blog_platform/wsgi.py",
    "blog_platform/app.py",
    "blog_platform/templates/dashboard.html",
    ".env",
]

for file in required_files:
    if Path(file).exists():
        success.append(f"✓ {file}")
        print(f"  ✓ {file}")
    else:
        errors.append(f"✗ Missing: {file}")
        print(f"  ✗ Missing: {file}")

# Check 2: Environment variables
print("\n[2] Checking environment variables...")
required_env = [
    "MONGODB_URI",
    "OPENROUTER_API_KEY",
]

from dotenv import load_dotenv
load_dotenv()

for var in required_env:
    value = os.getenv(var, "").strip()
    if value and not value.startswith("your_"):
        success.append(f"✓ {var} is set")
        print(f"  ✓ {var} is set")
    else:
        errors.append(f"✗ {var} not set or placeholder value")
        print(f"  ✗ {var} not set or placeholder value")

# Check 3: Python dependencies
print("\n[3] Checking Python dependencies...")
required_packages = [
    "flask",
    "flask_cors",
    "pymongo",
    "requests",
    "apscheduler",
    "dotenv",
]

try:
    import importlib
    for package in required_packages:
        try:
            # Special handling for flask_cors which is installed as Flask-CORS
            if package == "flask_cors":
                mod = importlib.import_module("flask_cors")
            else:
                mod = importlib.import_module(package.replace("_", "-"))
            success.append(f"✓ {package} installed")
            print(f"  ✓ {package} installed")
        except ImportError:
            errors.append(f"✗ {package} not installed - run: pip install {package}")
            print(f"  ✗ {package} not installed")
except Exception as e:
    warnings.append(f"Could not check all packages: {e}")

# Check 4: Flask app can be imported
print("\n[4] Checking Flask app...")
try:
    sys.path.insert(0, "blog_platform")
    from app import app
    success.append("✓ Flask app imports successfully")
    print("  ✓ Flask app imports successfully")
except Exception as e:
    errors.append(f"✗ Flask app import error: {e}")
    print(f"  ✗ Flask app import error: {e}")

# Check 5: Database connection
print("\n[5] Checking MongoDB connection...")
try:
    from pymongo import MongoClient
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    db_name = os.getenv("MONGODB_DB", "megallm_blog_platform")
    db = client[db_name]
    collection_count = len(db.list_collection_names())
    success.append(f"✓ MongoDB connected ({collection_count} collections)")
    print(f"  ✓ MongoDB connected ({collection_count} collections)")
except Exception as e:
    if "localhost" in str(mongo_uri):
        warnings.append(f"⚠ Local MongoDB not reachable (OK for production)")
        print(f"  ⚠ Local MongoDB not reachable (OK for production)")
    else:
        errors.append(f"✗ MongoDB connection failed: {e}")
        print(f"  ✗ MongoDB connection failed: {e}")

# Check 6: Git setup
print("\n[6] Checking Git repository...")
try:
    git_dir = Path(".git")
    if git_dir.exists():
        success.append("✓ Git repository initialized")
        print("  ✓ Git repository initialized")
    else:
        warnings.append("⚠ Git repository not initialized (you'll need to init before git push heroku main)")
        print("  ⚠ Git repository not initialized")
except Exception as e:
    warnings.append(f"⚠ Could not check git: {e}")

# Summary
print("\n" + "=" * 60)
print("📊 SUMMARY")
print("=" * 60)

if success:
    print(f"\n✓ Passed: {len(success)}")
    for s in success:
        print(f"  {s}")

if warnings:
    print(f"\n⚠ Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  {w}")

if errors:
    print(f"\n✗ Errors: {len(errors)}")
    for e in errors:
        print(f"  {e}")
    print("\n❌ Some checks failed. Fix errors above before deploying.")
    sys.exit(1)
else:
    print("\n✅ ALL CHECKS PASSED! Ready for deployment.")
    print("\nNext steps:")
    print("1. Initialize git: git init (if not done)")
    print("2. Commit code: git add . && git commit -m 'Ready for Heroku'")
    print("3. Create Heroku app: heroku create your-app-name")
    print("4. Set config vars: heroku config:set MONGODB_URI='...' OPENROUTER_API_KEY='...'")
    print("5. Deploy: git push heroku main")
    print("6. Check logs: heroku logs --tail")
    print("7. Open app: heroku open")
    print("\nSee DEPLOYMENT_GUIDE.md for detailed instructions.")
    sys.exit(0)
