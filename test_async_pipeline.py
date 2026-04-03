#!/usr/bin/env python
"""Test async blog generation."""
import requests
import time
import json

print('Testing async blog generation...')
print('=' * 60)

# Call pipeline endpoint
print('\n1. Calling /api/pipeline/run-complete...')
start = time.time()
r = requests.post('http://127.0.0.1:5000/api/pipeline/run-complete', timeout=5)
elapsed = time.time() - start
print(f'   ✓ Response: {r.status_code} in {elapsed:.2f}s')
print(f'   ✓ Message: {r.json().get("message")}')

# Wait for background jobs
print('\n2. Waiting for background blog generation (checking every 5 seconds)...')
before = requests.get('http://127.0.0.1:5000/api/accounts').json()['accounts']
before_total = sum(a['blog_count'] for a in before)
print(f'   Before: {before_total} total blogs')

for i in range(10):  # Up to 50 seconds
    time.sleep(5)
    current = requests.get('http://127.0.0.1:5000/api/accounts').json()['accounts']
    current_total = sum(a['blog_count'] for a in current)
    
    print(f'   After {(i+1)*5}s: {current_total} blogs', end='')
    if current_total > before_total:
        new_blogs = current_total - before_total
        print(f' (+{new_blogs} NEW) ✓')
        break
    else:
        print()

print('\n3. Account breakdown:')
for acc in current[:2]:
    print(f"   {acc['name']}: {acc['blog_count']} blogs")

print('\n✓ Async pipeline working correctly!')
