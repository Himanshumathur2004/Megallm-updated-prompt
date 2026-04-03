#!/usr/bin/env python3
"""Quick setup script for Blog Generation Platform."""

import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_requirements():
    """Check if all requirements are installed."""
    print_header("Checking Requirements")
    
    required = [
        'flask',
        'flask_cors',
        'pymongo',
        'requests',
        'apscheduler',
        'python-dotenv'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✓ All requirements satisfied!")
    return True

def check_mongodb():
    """Check if MongoDB is accessible."""
    print_header("Checking MongoDB")
    
    try:
        from pymongo import MongoClient
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not set in .env")
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        client.close()
        print(f"✓ MongoDB connected: {mongodb_uri.split('@')[-1] if '@' in mongodb_uri else 'Atlas'}")
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        print("\nStart MongoDB:")
        print("  Windows: mongod")
        print("  Docker: docker run -d -p 27017:27017 mongo")
        return False

def check_env_file():
    """Check if .env file exists and has required keys."""
    print_header("Checking .env File")
    
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print(f"✗ .env file not found at {env_path}")
        print("\nCreate a .env file with:")
        print("""
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/?appName=Cluster0
MONGODB_DB=megallm_blog_platform
FLASK_ENV=development
DEBUG=True
        """)
        return False
    
    # Check required keys
    with open(env_path) as f:
        env_content = f.read()
    
    required_keys = ['OPENROUTER_API_KEY', 'MONGODB_URI']
    missing_keys = []
    
    for key in required_keys:
        if key not in env_content:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"✗ Missing keys in .env: {', '.join(missing_keys)}")
        return False
    
    # Check if API key is set
    if 'MEGALLM_API_KEY=' in env_content or 'OPENAI_API_KEY=' in env_content:
        has_key = False
        for line in env_content.split('\n'):
            if ('MEGALLM_API_KEY=' in line or 'OPENAI_API_KEY=' in line) and '=' in line:
                key_part = line.split('=')[1].strip()
                if key_part and not key_part.startswith('sk-'):
                    continue
                if key_part:
                    has_key = True
                    break
        
        if not has_key:
            print("⚠ API key appears to be empty or placeholder")
            return False
    
    print(f"✓ .env file found at {env_path}")
    print("✓ Required keys present")
    return True

def test_api_key():
    """Test OpenRouter API key."""
    print_header("Testing OpenRouter API Key")
    
    import os
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3.6-plus-preview:free')
    
    if not api_key:
        print("✗ OPENROUTER_API_KEY not found in .env")
        return False
    
    print(f"Testing OpenRouter API key: {api_key[:20]}...")
    print(f"Using model: {model}")
    
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': 'ping'}],
                'max_tokens': 10
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("✓ API key is valid and has credits")
            return True
        elif response.status_code == 429:
            print("⚠ API key valid but rate limited - try again in a moment")
            return True
        else:
            print(f"✗ API error ({response.status_code}): {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

def main():
    print_header("OpenRouter Blog Generation Platform - Setup Check")
    
    checks = [
        ("Requirements", check_requirements),
        ("MongoDB", check_mongodb),
        (".env Configuration", check_env_file),
        ("API Key", test_api_key),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"✗ Error during {check_name}: {e}")
            results.append((check_name, False))
    
    print_header("Setup Summary")
    
    all_passed = True
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print_header("Ready to Start!")
        print("Run this to start the platform:")
        print("\n  python main.py\n")
        print("Then open: http://localhost:5000")
        return 0
    else:
        print_header("Setup Issues Detected")
        print("Fix the issues above and run this script again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
