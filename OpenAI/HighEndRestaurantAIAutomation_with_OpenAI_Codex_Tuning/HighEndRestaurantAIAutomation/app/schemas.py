from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str = Field(..., description="Guest or staff message")
    guest_id: Optional[str] = None
    language: Optional[str] = "en"
    channel: Optional[str] = "web"

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    safety_decision: str = "allow"
    detected_intent: Optional[str] = None

class ReservationRequest(BaseModel):
    guest_name: str
    date: str
    time: str
    party_size: int
    dietary_notes: Optional[str] = None
    occasion: Optional[str] = None
    language: Optional[str] = "en"
