import os
from typing import List, Optional
import asyncio

try:
    from azure.identity import DefaultAzureCredential
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient
except Exception:
    DefaultAzureCredential = None
    AzureKeyCredential = None
    SearchClient = None

class CognitiveSearchAdapter:
    def __init__(self, service_name: Optional[str] = None, index_name: Optional[str] = None, api_key: Optional[str] = None, mock_mode: bool = True):
        env_mock = os.getenv('MOCK_MODE', 'true').lower() == 'true'
        self.mock_mode = env_mock if mock_mode is None else mock_mode
        self.service_name = service_name or os.getenv('SEARCH_SERVICE_NAME')
        self.index_name = index_name or os.getenv('SEARCH_INDEX_NAME')
        self.api_key = api_key or os.getenv('SEARCH_API_KEY')
        self._client = None

    async def _get_client(self):
        if self._client:
            return self._client
        if self.mock_mode or SearchClient is None:
            return None
        endpoint = f"https://{self.service_name}.search.windows.net"
        if self.api_key and AzureKeyCredential is not None:
            cred = AzureKeyCredential(self.api_key)
        elif DefaultAzureCredential is not None:
            cred = DefaultAzureCredential()
        else:
            raise RuntimeError('No credential available for Cognitive Search')
        self._client = SearchClient(endpoint=endpoint, index_name=self.index_name, credential=cred)
        return self._client

    async def index_documents(self, docs: List[dict]):
        if self.mock_mode:
            return {"indexed": len(docs)}
        client = await self._get_client()
        if client is None:
            raise RuntimeError('Search client not initialized')
        # upload is synchronous API; run in thread
        result = await asyncio.to_thread(client.upload_documents, docs)
        return result

    async def search(self, query: str, top_k: int = 5):
        if self.mock_mode:
            return [{"id": "doc1", "score": 0.95, "text": "Mock result"}]
        client = await self._get_client()
        if client is None:
            raise RuntimeError('Search client not initialized')
        results = []
        async with client:
            async for r in client.search(query, top=top_k):
                results.append({"id": r.get('id'), "score": getattr(r, 'score', None), "doc": r})
        return results
