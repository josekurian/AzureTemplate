from abc import ABC, abstractmethod

class ProviderInterface(ABC):
    @abstractmethod
    async def chat(self, prompt: str, **kwargs):
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    async def search(self, query: str, **kwargs):
        pass
