#!/usr/bin/env python3
import os
import requests
from workflow_common import bootstrap_env

# Load environment first
bootstrap_env(__file__)

api_key = os.getenv('MEGALLM_API_KEY')
print(f"API Key loaded: {api_key[:20]}..." if api_key else "API Key NOT loaded")

# Test API connectivity
headers = {'Authorization': f'Bearer {api_key}'}
try:
    # Try to get models list
    r = requests.get('https://ai.megallm.io/v1/models', headers=headers, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:300]}")
except Exception as e:
    print(f"Error: {e}")
