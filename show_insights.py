#!/usr/bin/env python3
"""Display insights created by WF1."""

from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['megallm']

print('=' * 90)
print('CONTENT INSIGHTS CREATED BY WF1')
print('=' * 90)

insights = db.content_insights.find({'status': {'$ne': 'low_icp'}}).sort('_id', -1).limit(5)
count = 0
for i in insights:
    count += 1
    print(f'\n{count}. Insight ID: {str(i["_id"])}')
    print(f'   Hook: {i.get("hook_sentence", "N/A")[:75]}')
    print(f'   Claim: {i.get("core_claim", "N/A")[:75]}')
    print(f'   Angle: {i.get("angle_type", "N/A")}')
    print(f'   ICP Score: {i.get("icp_score", "N/A")}')
    print(f'   Status: {i.get("status", "N/A")}')
    print(f'   Infra Point: {i.get("infra_data_point", "N/A")[:60]}')

total_insights = db.content_insights.count_documents({})
pending = db.content_insights.count_documents({'status': 'pending_generation'})
low_icp = db.content_insights.count_documents({'status': 'low_icp'})

print(f'\n' + '=' * 90)
print(f'Total Insights: {total_insights}')
print(f'Pending Generation (Ready for WF2): {pending}')
print(f'Low ICP (Rejected): {low_icp}')
print('=' * 90)
