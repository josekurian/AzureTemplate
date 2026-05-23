from typing import List
from app.services.provider_interface import ProviderInterface

class AzureOpenAIAdapter(ProviderInterface):
    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    async def chat(self, prompt: str, **kwargs):
        if self.mock_mode:
            return {"response": f"MOCK reply to: {prompt}"}
        # Real implementation would call azure ai openai SDK
        raise NotImplementedError

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if self.mock_mode:
            return [[0.1 * len(t) for _ in range(8)] for t in texts]
        raise NotImplementedError

    async def search(self, query: str, **kwargs):
        if self.mock_mode:
            return [{"id": "doc1", "score": 0.9, "snippet": "Mocked snippet"}]
        raise NotImplementedError
