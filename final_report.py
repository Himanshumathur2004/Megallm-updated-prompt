from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['megallm']

# Get platform breakdown
platforms = list(db.generated_posts.aggregate([{'$group': {'_id': '$platform', 'count': {'$sum': 1}}}]))

print("\n=== FINAL GENERATION REPORT ===\n")
print("Posts by platform:")
for p in platforms:
    print(f"  {p['_id']}: {p['count']}")

# Check blog specifically
blogs = db.generated_posts.count_documents({'platform': 'blog'})
print(f"\nBlog posts specifically: {blogs}")

# Insights status
print(f"\nInsights Status:")
total = db.content_insights.count_documents({})
pending = db.content_insights.count_documents({'status': 'pending_generation'})
done = db.content_insights.count_documents({'status': 'generation_done'})
print(f"  Total insights: {total}")
print(f"  Pending generation: {pending}")
print(f"  Generation done: {done}")
