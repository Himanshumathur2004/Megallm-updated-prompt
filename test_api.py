import os
import requests
import json

# Read .env file manually
with open('.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

api_key = os.getenv('MEGALLM_API_KEY')
print(f'Testing API key: {api_key[:20]}...')
print()

headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
payload = {'model': 'deepseek-ai/deepseek-v3.1', 'messages': [{'role': 'user', 'content': 'hello'}], 'max_tokens': 10}

try:
    resp = requests.post('https://ai.megallm.io/v1/chat/completions', json=payload, headers=headers, timeout=15)
    print(f'Status: {resp.status_code}')
    
    if resp.status_code == 200:
        print('\n✓ SUCCESS - API Key VALID & HAS CREDITS')
        print(f'Ready to process articles!')
    else:
        data = resp.json()
        if 'error' in data:
            msg = data['error'].get('message', 'Unknown error')
            print(f'\n✗ API Error ({resp.status_code}): {msg}')
except Exception as e:
    print(f'✗ Connection error: {e}')
