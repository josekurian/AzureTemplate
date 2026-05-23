import importlib.util
import os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

spec = importlib.util.spec_from_file_location('extractor', os.path.join(root, 'app', 'extraction', 'extractor.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Extractor = getattr(mod, 'Extractor')

spec2 = importlib.util.spec_from_file_location('docint', os.path.join(root, 'app', 'services', 'document_intelligence_adapter.py'))
dmod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(dmod)
DocumentIntelligenceAdapter = getattr(dmod, 'DocumentIntelligenceAdapter')

spec3 = importlib.util.spec_from_file_location('hrq', os.path.join(root, 'app', 'review', 'human_review_queue.py'))
hr = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(hr)
HumanReviewQueue = getattr(hr, 'HumanReviewQueue')

import asyncio

async def test_extract_and_queue():
    docint = DocumentIntelligenceAdapter(mock_mode=True)
    extractor = Extractor(docint)
    res = await extractor.extract('/tmp/file.pdf')
    assert res.get('vendor') == 'Mock Vendor'
    q = HumanReviewQueue()
    r = await q.enqueue({'id':'1','reason':'low_confidence'})
    assert r.get('queued')

if __name__ == '__main__':
    asyncio.run(test_extract_and_queue())
