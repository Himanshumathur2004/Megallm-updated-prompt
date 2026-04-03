#!/usr/bin/env python3
"""Test OpenRouter API key and model connectivity."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENROUTER_API_KEY')
BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
MODEL = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3.6-plus:free')

print("=" * 80)
print("OPENROUTER API KEY TEST")
print("=" * 80)
print(f"\n📍 Configuration:")
print(f"  API Key: {API_KEY[:20]}..." if API_KEY else "  API Key: NOT SET")
print(f"  Base URL: {BASE_URL}")
print(f"  Model: {MODEL}")

if not API_KEY:
    print("\n❌ ERROR: OPENROUTER_API_KEY not set in .env")
    exit(1)

print("\n🔄 Testing API connectivity...")

try:
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "MegaLLM Blog Platform"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Say 'API KEY WORKS' and nothing else"}
            ],
            "max_tokens": 10
        },
        timeout=30
    )
    
    print(f"  Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"  ✅ SUCCESS: API returned response")
        print(f"  Response: {message}")
        print(f"\n{'='*80}")
        print(f"✅ API KEY IS WORKING - Ready to run WF1")
        print(f"{'='*80}")
    elif response.status_code == 429:
        data = response.json()
        error_msg = data.get("error", {}).get("message", "Rate limited")
        print(f"  ⏱️  RATE LIMIT: {error_msg}")
        print(f"\n  → Model is temporarily rate-limited")
        print(f"  → Try again in a few minutes or use a different model")
    elif response.status_code == 404:
        data = response.json()
        error_msg = data.get("error", {}).get("message", "Model not found")
        print(f"  ❌ MODEL NOT FOUND: {error_msg}")
        print(f"\n  → {MODEL} doesn't exist on OpenRouter")
        print(f"  → Check: https://openrouter.ai/docs/models")
    else:
        print(f"  ❌ ERROR {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        
except requests.exceptions.Timeout:
    print(f"  ❌ TIMEOUT: Request took too long")
except requests.exceptions.ConnectionError as e:
    print(f"  ❌ CONNECTION ERROR: {e}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print(f"\n{'='*80}")
