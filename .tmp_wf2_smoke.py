import wf2

cfg = wf2._build_config()
p = wf2.ContentGenerationPipeline(cfg)
try:
    iid = str(p.db.content_insights.find_one({'status':'pending_generation'},{'_id':1})['_id'])
    print('testing insight:', iid)
    out = p.run(iid)
    print('generated_post_ids:', out)
finally:
    p.close()
