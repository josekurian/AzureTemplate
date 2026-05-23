import os
from typing import List, Optional
import httpx
import asyncio
from app.services.provider_interface import ProviderInterface

try:
    from azure.identity import DefaultAzureCredential
except Exception:
    DefaultAzureCredential = None

class AzureOpenAIAdapter(ProviderInterface):
    """Adapter that talks to Azure OpenAI REST endpoints or falls back to mock.

    Requirements for real mode:
      - MOCK_MODE=false
      - OPENAI_ENDPOINT and OPENAI_DEPLOYMENT_CHAT/EMBED set in env or passed
      - Either OPENAI_API_KEY (api-key header) or enable DefaultAzureCredential
    """
    def __init__(self, mock_mode: Optional[bool] = None):
        env_mock = os.getenv('MOCK_MODE', 'true').lower() == 'true'
        self.mock_mode = env_mock if mock_mode is None else mock_mode
        self.endpoint = os.getenv('OPENAI_ENDPOINT')
        self.deployment_chat = os.getenv('OPENAI_DEPLOYMENT_CHAT')
        self.deployment_embed = os.getenv('OPENAI_DEPLOYMENT_EMBED')
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.credential = None
        if not self.mock_mode and DefaultAzureCredential is not None:
            try:
                self.credential = DefaultAzureCredential()
            except Exception:
                self.credential = None

    async def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers['api-key'] = self.api_key
            return headers
        if self.credential is not None:
            # request a token for cognitive services scope
            try:
                token = await asyncio.to_thread(self.credential.get_token, 'https://cognitiveservices.azure.com/.default')
                headers['Authorization'] = f'Bearer {token.token}'
                return headers
            except Exception:
                pass
        return headers

    async def chat(self, prompt: str, max_tokens: int = 512):
        if self.mock_mode:
            return {"response": f"MOCK reply to: {prompt}"}
        if not self.endpoint or not self.deployment_chat:
            raise RuntimeError('OPENAI_ENDPOINT and OPENAI_DEPLOYMENT_CHAT must be set in non-mock mode')
        url = self.endpoint.rstrip('/') + f"/openai/deployments/{self.deployment_chat}/chat/completions?api-version=2023-05-15"
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            j = r.json()
            # Try common shapes
            try:
                return {"response": j['choices'][0]['message']['content']}
            except Exception:
                return {"response": j}

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if self.mock_mode:
            return [[0.1 * len(t) for _ in range(8)] for t in texts]
        if not self.endpoint or not self.deployment_embed:
            raise RuntimeError('OPENAI_ENDPOINT and OPENAI_DEPLOYMENT_EMBED must be set in non-mock mode')
        url = self.endpoint.rstrip('/') + f"/openai/deployments/{self.deployment_embed}/embeddings?api-version=2023-05-15"
        payload = {"input": texts}
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            j = r.json()
            # extract embeddings
            if 'data' in j:
                return [d.get('embedding') for d in j['data']]
            # fallback
            return []

    async def search(self, query: str, **kwargs):
        # Higher-level search is provided by cognitive search adapter. Keep a simple fallback.
        if self.mock_mode:
            return [{"id": "doc1", "score": 0.9, "snippet": "Mocked snippet"}]
        raise NotImplementedError('Use CognitiveSearchAdapter for search operations')
