#!/usr/bin/env python3
import requests

api_key = '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'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
payload = {
    'model': 'qwen/qwen3.6-plus-preview:free',
    'messages': [{'role': 'user', 'content': 'Write one short sentence.'}],
    'max_tokens': 50
}

print('Testing openrouter.ai domain...')
url = 'https://openrouter.ai/api/v1/chat/completions'

try:
    print(f'URL: {url}')
    print(f'API Key: ...{api_key[-20:]}')
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f'Status: {resp.status_code}')
    if resp.status_code == 200:
        print('✓✓✓ SUCCESS ✓✓✓')
        content = resp.json()['choices'][0]['message']['content']
        print(f'Response: {content}')
    else:
        print(f'Error: {resp.status_code} - {resp.reason}')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {e}')
