import asyncio

from app.services.openai_client import AzureOpenAIClient


class RestaurantEmbedder:
    def __init__(self) -> None:
        self._client = AzureOpenAIClient()

    async def embed_text(self, text: str, *, retries: int = 2) -> list[float]:
        attempt = 0
        while True:
            try:
                return await self._client.embed(text)
            except Exception:
                attempt += 1
                if attempt > retries:
                    raise
                await asyncio.sleep(0.2 * attempt)
