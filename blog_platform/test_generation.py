#!/usr/bin/env python3
import requests
import json

url = 'http://localhost:5000/api/blogs/generate'
payload = {
    'account_id': 'account_1',
    'topics': {
        'cost_optimization': 1,
        'infrastructure': 1
    }
}

print('Testing blog generation with real OpenRouter API...')
try:
    resp = requests.post(url, json=payload, timeout=120)
    print(f'Status Code: {resp.status_code}')
    data = resp.json()
    generated = data.get('generated_count', 0)
    error = data.get('error')
    message = data.get('message')
    
    print(f'Generated: {generated} blogs')
    if error:
        print(f'Error: {error}')
    print(f'Message: {message}')
    
    if generated > 0:
        print('\n✓✓✓ SUCCESS - BLOGS GENERATED WITH REAL API! ✓✓✓')
    
except Exception as e:
    print(f'Exception: {type(e).__name__}: {e}')
