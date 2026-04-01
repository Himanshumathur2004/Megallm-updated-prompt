import traceback
import wf2

cfg = wf2._build_config()
p = wf2.ContentGenerationPipeline(cfg)
try:
    iid = str(p.db.content_insights.find_one({'status':'pending_generation'},{'_id':1})['_id'])
    print('testing insight:', iid)
    p.run(iid)
except Exception as e:
    print('EXC:', e)
    traceback.print_exc()
finally:
    p.close()
