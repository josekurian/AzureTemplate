from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.search_client import RestaurantSearchClient

search_client = RestaurantSearchClient()


class MenuLookupInput(BaseModel):
    query: str = Field(..., min_length=1)


class WinePairingInput(BaseModel):
    preference: str
    dish: str


async def lookup_menu_tool(data: MenuLookupInput) -> dict:
    result = await search_client.search_knowledge(data.query)
    return {"menu_context": result["context"], "sources": result["sources"]}


async def recommend_wine_pairing_tool(data: WinePairingInput) -> dict:
    recommendation = (
        f"For {data.dish}, a balanced pairing for preference '{data.preference}' is a sommelier-guided "
        "reserve pairing with a lighter-bodied first pour and a fuller-bodied main-course pairing."
    )
    return {"recommendation": recommendation, "sources": ["sample_menu.json"]}
