from pymongo import MongoClient

import os
db = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))[os.getenv('MONGODB_DB', 'megallm')]

total_articles = db.articles.count_documents({})
total_insights = db.content_insights.count_documents({})
pending_insights = db.content_insights.count_documents({'status': 'pending_generation'})

print(f'Total articles: {total_articles}')
print(f'Total insights: {total_insights}')
print(f'Pending generation insights: {pending_insights}')
print()

# Get status breakdown
statuses = {}
for article in db.articles.find():
    status = article.get('status', 'unknown')
    statuses[status] = statuses.get(status, 0) + 1

print('Article statuses:')
for status, count in statuses.items():
    print(f'  {status}: {count}')
