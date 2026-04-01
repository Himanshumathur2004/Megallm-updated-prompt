#!/usr/bin/env python3
"""Test all MegaLLM models to find one with available credits."""

import subprocess
import os
import shutil
from pathlib import Path

models = [
    'deepseek-ai/deepseek-v3.1',
    'claude-haiku-4.5', 
    'claude-sonnet-4.8',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-4',
    'gpt-5',
    'gpt-4.5-turbo',
    'gpt-6-mini',
    'gemini-2.5-pro'
]

results = []
api_key = 'sk-mega-6c309f77db9167850e784c25d8f8f93b672b2173b4dd791aa5c31a5ff6bd4329'

for model in models:
    print(f'\n[{models.index(model)+1}/{len(models)}] Testing {model}...')
    
    # Update .env
    env_content = f'''MEGALLM_API_KEY={api_key}
OPENAI_API_KEY={api_key}
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm
WF2_MODEL={model}
OPENAI_MODEL={model}'''
    
    Path('.env').write_text(env_content)
    
    # Clear cache
    for p in ['__pycache__', '.pytest_cache']:
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)
    
    try:
        result = subprocess.run(['python', 'gen_newsletter_only.py'], 
                              capture_output=True, text=True, timeout=20)
        output = result.stderr + result.stdout
        
        if '402' in output:
            status = '✗ Insufficient credits'
        elif '403' in output:
            status = '✗ Tier restriction'
        elif '404' in output:
            status = '✗ Model not found'
        elif 'ERROR' in output.upper() or 'Error' in output:
            status = '✗ Error'
        elif 'Total posts' in output and 'Newsletter posts' in output:
            status = '✓ WORKING - Generated posts!'
        else:
            status = '? Unknown response'
        
        results.append((model, status))
        print(f'  → {status}')
    except subprocess.TimeoutExpired:
        results.append((model, '✗ Timeout'))
        print(f'  → ✗ Timeout')
    except Exception as e:
        results.append((model, f'✗ Exception: {str(e)[:50]}'))
        print(f'  → ✗ Exception')

print('\n' + '='*70)
print('FINAL RESULTS:')
print('='*70)
for i, (model, status) in enumerate(results, 1):
    print(f'{i:2}. {model:30} {status}')

# Highlight working models
working = [m for m, s in results if '✓' in s]
if working:
    print(f'\n✓ WORKING MODELS: {working}')
else:
    print('\n✗ No working models found with current API key')
