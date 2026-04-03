#!/usr/bin/env python
"""Check MongoDB connection."""
import sys
sys.path.insert(0, '.')

from blog_platform.config import Config
from blog_platform.database import Database

print('Configuration:')
print(f'MONGODB_URI: {Config.MONGODB_URI[:60]}...')
print(f'MONGODB_DB: {Config.MONGODB_DB}')
print()

# Try to connect
print('Connecting to MongoDB...')
try:
    db = Database(uri=Config.MONGODB_URI, db_name=Config.MONGODB_DB)
    accounts = db.get_all_accounts()
    print(f'✓ Connected!')
    print(f'✓ Total accounts: {len(accounts)}')
    
    if accounts:
        total_blogs = sum(db.get_blogs_by_account(a['account_id']) for a in accounts)
        total_blogs = sum(len(blogs) for blogs in total_blogs.values())
        print(f'✓ Total blogs: {total_blogs}')
    else:
        print('✗ No accounts found!')
except Exception as e:
    print(f'✗ Connection failed: {e}')
