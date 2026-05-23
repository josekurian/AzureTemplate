from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent_runtime.policies import contains_restricted_claim
from app.services.content_safety_client import ContentSafetyClient

safety_client = ContentSafetyClient()


class SafetyReviewInput(BaseModel):
    text: str = Field(..., min_length=1)


async def review_safety_tool(data: SafetyReviewInput) -> dict:
    result = await safety_client.analyze_text(data.text)
    result["restricted_claim"] = contains_restricted_claim(data.text)
    if result["restricted_claim"]:
        result["decision"] = "block"
    return result
