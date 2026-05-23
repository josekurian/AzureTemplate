import importlib.util
import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# load azure_openai_adapter
spec = importlib.util.spec_from_file_location('aopenai', os.path.join(root, 'app', 'services', 'azure_openai_adapter.py'))
aopenai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aopenai)
AzureOpenAIAdapter = getattr(aopenai, 'AzureOpenAIAdapter')

# load cognitive_search_adapter
spec2 = importlib.util.spec_from_file_location('csearch', os.path.join(root, 'app', 'services', 'cognitive_search_adapter.py'))
csearch = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(csearch)
CognitiveSearchAdapter = getattr(csearch, 'CognitiveSearchAdapter')

# load document_intelligence_adapter
spec3 = importlib.util.spec_from_file_location('docint', os.path.join(root, 'app', 'services', 'document_intelligence_adapter.py'))
docint = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(docint)
DocumentIntelligenceAdapter = getattr(docint, 'DocumentIntelligenceAdapter')

import asyncio

async def test_azure_openai_chat_and_embed():
    a = AzureOpenAIAdapter(mock_mode=True)
    r = await a.chat('hello')
    assert 'response' in r
    e = await a.embed(['a','bb'])
    assert isinstance(e, list) and len(e) == 2

async def test_cognitive_search_index_and_search():
    c = CognitiveSearchAdapter(mock_mode=True)
    res = await c.index_documents([{'id':'1','text':'hello'}])
    assert res.get('indexed') == 1
    s = await c.search('hello')
    assert isinstance(s, list)

async def test_document_extract():
    d = DocumentIntelligenceAdapter(mock_mode=True)
    x = await d.extract_invoice('/tmp/file.pdf')
    assert x.get('vendor') == 'Mock Vendor'

def run_all():
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(test_azure_openai_chat_and_embed())
        loop.run_until_complete(test_cognitive_search_index_and_search())
        loop.run_until_complete(test_document_extract())
    finally:
        loop.close()

if __name__ == '__main__':
    run_all()
