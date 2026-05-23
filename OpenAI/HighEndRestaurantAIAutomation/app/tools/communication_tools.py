from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.bot_adapter import BotAdapter
from app.services.translator_client import TranslatorClient

translator = TranslatorClient()
bot_adapter = BotAdapter()


class TranslateTextInput(BaseModel):
    text: str = Field(..., min_length=1)
    to_language: str = "en"


class ManagerPacketInput(BaseModel):
    conversation_id: str
    summary: str
    guest_name: str | None = None
    priority: str = "high"


async def translate_text_tool(data: TranslateTextInput) -> dict:
    return await translator.translate(data.text, to_language=data.to_language)


async def create_manager_packet_tool(data: ManagerPacketInput) -> dict:
    return await bot_adapter.build_handoff_payload(
        conversation_id=data.conversation_id,
        guest_name=data.guest_name,
        issue_summary=data.summary,
        priority=data.priority,
    )
