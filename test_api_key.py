#!/usr/bin/env python3
"""Test API key is loaded correctly."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load from current directory
cwd_env = Path.cwd() / ".env"
print(f"Loading .env from: {cwd_env}")
print(f"File exists: {cwd_env.exists()}")

if cwd_env.exists():
    load_dotenv(cwd_env)

api_key = os.getenv("MEGALLM_API_KEY")
print(f"\nAPI Key loaded: {api_key[:20]}...{api_key[-20:] if api_key else 'NOT FOUND'}")
print(f"API Key starts with sk-mega: {api_key.startswith('sk-mega') if api_key else False}")

# Test a simple API call
import requests
import json

url = "https://ai.megallm.io/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": "deepseek-ai/deepseek-v3.1",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 50,
}

print("\nTesting API call...")
try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
