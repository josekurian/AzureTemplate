from typing import List

class CognitiveSearchAdapter:
    def __init__(self, service_name: str = None, api_key: str = None, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.service_name = service_name
        self.api_key = api_key

    async def index_documents(self, docs: List[dict]):
        if self.mock_mode:
            return {"indexed": len(docs)}
        raise NotImplementedError

    async def search(self, query: str, top_k: int = 5):
        if self.mock_mode:
            return [{"id": "doc1", "score": 0.95, "text": "Mock result"} for _ in range(min(top_k,1))]
        raise NotImplementedError
