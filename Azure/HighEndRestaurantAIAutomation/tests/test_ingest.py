import importlib.util
import os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# load orchestrator
spec = importlib.util.spec_from_file_location('orch', os.path.join(root, 'app', 'ingestion', 'orchestrator.py'))
orchm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orchm)
IngestionOrchestrator = getattr(orchm, 'IngestionOrchestrator')

# load mock embedder and indexer from services
spec2 = importlib.util.spec_from_file_location('aopenai', os.path.join(root, 'app', 'services', 'azure_openai_adapter.py'))
aopenai = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(aopenai)
AzureOpenAIAdapter = getattr(aopenai, 'AzureOpenAIAdapter')

spec3 = importlib.util.spec_from_file_location('csearch', os.path.join(root, 'app', 'services', 'cognitive_search_adapter.py'))
csearch = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(csearch)
CognitiveSearchAdapter = getattr(csearch, 'CognitiveSearchAdapter')

import asyncio

async def test_ingest_flow():
    embedder = AzureOpenAIAdapter(mock_mode=True)
    indexer = CognitiveSearchAdapter(mock_mode=True)
    orch = IngestionOrchestrator(embedder=embedder, indexer=indexer)
    res = await orch.ingest([{'id':'1','text':'hello world'}])
    assert res.get('ingested') == 1

if __name__ == '__main__':
    asyncio.run(test_ingest_flow())
