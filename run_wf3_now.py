#!/usr/bin/env python3
"""Quick WF3 runner for all draft posts."""

from wf3 import QualityControlPipeline, _build_config
from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['megallm']

# Get all draft post IDs
post_ids = [str(doc['_id']) for doc in db.generated_posts.find({'status': 'draft'}, {'_id': 1})]

print(f'Running WF3 Quality Control on {len(post_ids)} posts...')
print('=' * 60)

config = _build_config()
qc = QualityControlPipeline(config)
result = qc.run(post_ids)
qc.close()

print('\n' + '=' * 60)
print('WF3 Complete!')
print(f"Approved: {result['approved']}")
print(f"Shelved: {result['shelved']}")
print(f"Total Processed: {result['total']}")
