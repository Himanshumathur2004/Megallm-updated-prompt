from pymongo import MongoClient
import os

client = MongoClient(os.environ['MONGODB_URI'])
db = client['n8n']
col = db['content_insights']
q = {'status':'pending_generation'}
all_count = col.count_documents(q)
with_id = col.count_documents({'status':'pending_generation','raw_content_id': {'$exists': True, '$ne': None}})
print('pending_generation_total:', all_count)
print('pending_generation_with_raw_content_id:', with_id)
print('pending_generation_missing_raw_content_id:', all_count - with_id)
client.close()
