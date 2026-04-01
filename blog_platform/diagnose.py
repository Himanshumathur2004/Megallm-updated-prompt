#!/usr/bin/env python3
"""Quick diagnostic tool to identify startup issues."""

import sys
from pathlib import Path

def diagnose():
    """Check what's causing startup failures."""
    print("\n" + "="*60)
    print("  DIAGNOSTIC CHECK")
    print("="*60 + "\n")
    
    # 1. Check .env
    print("1. Checking .env file...")
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(f"   ✗ NOT FOUND: {env_path}")
        print("\n   CREATE THIS FILE WITH:")
        print("   MEGALLM_API_KEY=sk-mega-your-key-here")
        print("   MONGODB_URI=mongodb://localhost:27017")
        print("   MONGODB_DB=megallm_blog_platform")
        return False
    else:
        print(f"   ✓ Found at {env_path}")
    
    # 2. Load and verify env
    print("\n2. Checking .env contents...")
    with open(env_path) as f:
        env_content = f.read()
    
    if "MEGALLM_API_KEY" not in env_content:
        print("   ✗ Missing MEGALLM_API_KEY")
        return False
    else:
        # Check if it's not empty
        for line in env_content.split('\n'):
            if line.startswith('MEGALLM_API_KEY='):
                value = line.split('=', 1)[1].strip()
                if value and value != 'sk-mega':
                    print(f"   ✓ MEGALLM_API_KEY set")
                else:
                    print(f"   ✗ MEGALLM_API_KEY is empty or placeholder")
                    return False
    
    # 3. Check Python imports
    print("\n3. Checking Python packages...")
    required = ['flask', 'pymongo', 'apscheduler', 'requests', 'dotenv']
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"   ✓ {pkg}")
        except ImportError:
            print(f"   ✗ Missing: {pkg}")
            print(f"      Run: pip install {pkg}")
            return False
    
    # 4. Check MongoDB
    print("\n4. Checking MongoDB...")
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        client.close()
        print("   ✓ MongoDB is running")
    except Exception as e:
        print(f"   ✗ MongoDB not running: {e}")
        print("\n   START MONGODB WITH:")
        print("   mongod  (or docker run -d -p 27017:27017 mongo)")
        return False
    
    print("\n" + "="*60)
    print("  ALL CHECKS PASSED ✓")
    print("="*60)
    print("\nYou can now run: python main.py\n")
    return True

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
