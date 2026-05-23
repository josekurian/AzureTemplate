from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from app.core.config import settings
from app.core.auth import get_credential

class RestaurantSearchClient:
    def _client(self):
        # Prefer DefaultAzureCredential + RBAC. AzureKeyCredential is kept only for external fallback.
        return SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index,
            credential=get_credential(),
        )

    async def search_knowledge(self, query: str) -> dict:
        if settings.mock_mode:
            return {
                "context": "Sample policy: jackets recommended after 6 PM; vegan tasting menu requires 24-hour notice; cancellation fee applies within 24 hours.",
                "sources": ["sample_menu.json", "private_dining_policy.md"],
            }
        client = self._client()
        results = client.search(search_text=query, top=5)
        chunks, sources = [], []
        for r in results:
            chunks.append(r.get("content", ""))
            sources.append(r.get("source", "unknown"))
        return {"context": "\n".join(chunks), "sources": sources}
