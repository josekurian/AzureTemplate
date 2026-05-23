from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.search_client import RestaurantSearchClient

search_client = RestaurantSearchClient()


class SearchKnowledgeInput(BaseModel):
    query: str = Field(..., min_length=1)
    query_type: str = "hybrid"
    document_type: str | None = None


class PrivateDiningPolicyInput(BaseModel):
    query: str = Field(..., min_length=1)


async def search_knowledge_tool(data: SearchKnowledgeInput) -> dict:
    return await search_client.search_knowledge(
        data.query,
        query_type=data.query_type,
        document_type=data.document_type,
    )


async def private_dining_policy_tool(data: PrivateDiningPolicyInput) -> dict:
    result = await search_client.search_knowledge(data.query)
    return {
        "summary": result["context"],
        "sources": result["sources"],
    }
