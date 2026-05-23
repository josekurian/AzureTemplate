from __future__ import annotations

from pydantic import BaseModel, Field

from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.schemas import ReservationRequest

concierge = RestaurantConcierge()


class ReservationDraftInput(BaseModel):
    guest_name: str
    date: str
    time: str
    party_size: int = Field(..., ge=1, le=30)
    dietary_notes: str | None = None
    occasion: str | None = None
    language: str = "en"


async def draft_reservation_tool(data: ReservationDraftInput) -> dict:
    result = await concierge.create_reservation_draft(
        ReservationRequest(
            guest_name=data.guest_name,
            date=data.date,
            time=data.time,
            party_size=data.party_size,
            dietary_notes=data.dietary_notes,
            occasion=data.occasion,
            language=data.language,
        )
    )
    return result.model_dump()
