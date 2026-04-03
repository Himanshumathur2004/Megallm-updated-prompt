#!/usr/bin/env python3
"""
VERIFICATION SCRIPT
Checks if the integrated pipeline is ready to run.
"""

import os
import sys
from pathlib import Path

print("\n" + "=" * 80)
print("INTEGRATED PIPELINE VERIFICATION")
print("=" * 80 + "\n")

errors = []
warnings = []
success_checks = []

# ============================================================================
# 1. Check Python Version
# ============================================================================
print("✓ Checking Python version...")
if sys.version_info >= (3, 8):
    success_checks.append(f"Python {sys.version_info.major}.{sys.version_info.minor} ✓")
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
else:
    errors.append("Python 3.8+ required")
    print(f"  ✗ Python {sys.version_info.major}.{sys.version_info.minor} (need 3.8+)")

# ============================================================================
# 2. Check Required Files Exist
# ============================================================================
print("\n✓ Checking required files...")
required_files = [
    "orchestrate_full_pipeline.py",
    "scrape_to_mongo.py",
    "wf1.py",
    "workflow_common.py",
    "blog_platform/app.py",
    "blog_platform/config.py",
    "blog_platform/blog_generator.py",
    "blog_platform/insight_scheduler.py",
]

for file in required_files:
    path = Path(__file__).parent / file
    if path.exists():
        print(f"  ✓ {file}")
        success_checks.append(f"File {file}")
    else:
        # Try to find it
        if Path(file).exists():
            print(f"  ✓ {file}")
            success_checks.append(f"File {file}")
        else:
            errors.append(f"Missing: {file}")
            print(f"  ✗ {file} - NOT FOUND")

# ============================================================================
# 3. Check Python Dependencies
# ============================================================================
print("\n✓ Checking Python dependencies...")
required_packages = {
    "pymongo": "MongoDB driver",
    "requests": "HTTP requests",
    "flask": "Flask web framework",
    "apscheduler": "Scheduling",
    "dotenv": "Environment variables",
}

for package, desc in required_packages.items():
    try:
        __import__(package)
        print(f"  ✓ {package}: {desc}")
        success_checks.append(f"Package {package}")
    except ImportError:
        errors.append(f"Missing package: {package} ({desc})")
        print(f"  ✗ {package}: {desc} - NOT INSTALLED")

# ============================================================================
# 4. Check .env File
# ============================================================================
print("\n✓ Checking .env file...")
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"  ✓ .env file found")
    success_checks.append(".env file exists")
    
    # Check for required keys
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    required_keys = [
        "MONGODB_URI",
        "MONGODB_DB",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "MEGALLM_API_KEY",
    ]
    
    for key in required_keys:
        if key in env_content:
            # Check if value is set (not placeholder)
            if f"{key}=" in env_content:
                value_line = [line for line in env_content.split('\n') if f"{key}=" in line]
                if value_line and len(value_line[0].split('=')) > 1:
                    value = value_line[0].split('=', 1)[1].strip()
                    if value and value != "your_" and value != "sk-":
                        print(f"  ✓ {key}: Set (✓)")
                        success_checks.append(f".env {key}")
                    else:
                        warnings.append(f"{key} appears to be placeholder (value: {value[:20]}...)")
                        print(f"  ⚠ {key}: May be placeholder")
                else:
                    errors.append(f"{key} not properly set")
                    print(f"  ✗ {key}: Not set")
            else:
                errors.append(f"{key} not found")
                print(f"  ✗ {key}: Not found")
        else:
            errors.append(f"{key} missing from .env")
            print(f"  ✗ {key}: Not in .env")
else:
    errors.append(".env file not found")
    print(f"  ✗ .env file - NOT FOUND at {env_file}")

# ============================================================================
# 5. Check MongoDB Connection
# ============================================================================
print("\n✓ Checking MongoDB connection...")
try:
    from pymongo import MongoClient
    
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db = os.getenv("MONGODB_DB", "megallm")
    
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        client.close()
        
        print(f"  ✓ MongoDB connected: {mongodb_uri}")
        print(f"  ✓ Database: {mongodb_db}")
        success_checks.append("MongoDB connection")
    except Exception as e:
        errors.append(f"MongoDB connection failed: {e}")
        print(f"  ✗ MongoDB: {e}")
        print(f"    Make sure MongoDB is running: mongod")
        
except ImportError:
    errors.append("pymongo not installed")

# ============================================================================
# 6. Test API Key Validity (Basic Check)
# ============================================================================
print("\n✓ Checking API keys...")
openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
megallm_key = os.getenv("MEGALLM_API_KEY", "")

if openrouter_key and openrouter_key.startswith("sk-or-v1-"):
    print(f"  ✓ OpenRouter key format: Valid")
    success_checks.append("OpenRouter API key format")
else:
    warnings.append("OpenRouter key may be invalid (should start with sk-or-v1-)")
    print(f"  ⚠ OpenRouter key: May be invalid")

if megallm_key and megallm_key.startswith("sk-"):
    print(f"  ✓ MegaLLM key format: Valid")
    success_checks.append("MegaLLM API key format")
else:
    warnings.append("MegaLLM key may be invalid")
    print(f"  ⚠ MegaLLM key: May be invalid")

# ============================================================================
# 7. Check MongoDB Collections
# ============================================================================
print("\n✓ Checking MongoDB collections...")
try:
    from pymongo import MongoClient
    
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db = os.getenv("MONGODB_DB", "megallm")
    
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[mongodb_db]
    
    collections = {
        "articles": "Raw scraped articles",
        "content_insights": "WF1 analysis output",
        "blogs": "Final blog posts",
        "generated_posts": "WF2 output (LinkedIn, Twitter, etc.)",
    }
    
    for collection_name, description in collections.items():
        try:
            count = db[collection_name].count_documents({})
            print(f"  ✓ {collection_name}: {count} documents ({description})")
            success_checks.append(f"Collection {collection_name}")
        except Exception as e:
            print(f"  ℹ {collection_name}: Not yet created ({description})")
    
    client.close()
except Exception as e:
    print(f"  ✗ Could not check collections: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

print(f"\n✓ Success checks: {len(success_checks)}")
for check in success_checks[:5]:
    print(f"  ✓ {check}")
if len(success_checks) > 5:
    print(f"  ... and {len(success_checks) - 5} more")

if warnings:
    print(f"\n⚠ Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  ⚠ {warning}")

if errors:
    print(f"\n✗ Errors: {len(errors)}")
    for error in errors:
        print(f"  ✗ {error}")

print("\n" + "=" * 80)

if not errors:
    print("✓ READY TO RUN")
    print("\nNext steps:")
    print("  1. Ensure MongoDB is running: mongod")
    print("  2. Run the full pipeline:")
    print("     python orchestrate_full_pipeline.py")
    print("  3. Monitor progress:")
    print("     tail -f orchestration.log")
    print("\n✓ System check PASSED")
    sys.exit(0)
else:
    print("✗ ISSUES FOUND")
    print("\nFix the above errors before running the pipeline.")
    print("\nCommon fixes:")
    print("  - MongoDB: Start with 'mongod'")
    print("  - Missing packages: pip install pymongo flask requests apscheduler python-dotenv")
    print("  - .env file: Copy from .env.example or create with required keys")
    print("\n✗ System check FAILED")
    sys.exit(1)

print("\n" + "=" * 80)
