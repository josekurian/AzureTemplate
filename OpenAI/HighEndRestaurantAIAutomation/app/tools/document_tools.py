from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.document_intelligence_client import DocumentIntelligenceClient

document_client = DocumentIntelligenceClient()


class ContractSummaryInput(BaseModel):
    document_text: str = Field(..., min_length=1)


async def summarize_contract_tool(data: ContractSummaryInput) -> dict:
    return {
        "document_type": "private_event_contract",
        "summary": data.document_text[:400],
        "human_review_required": True,
    }
