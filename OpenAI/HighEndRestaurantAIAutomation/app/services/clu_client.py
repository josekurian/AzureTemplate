import json
import re
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class CLUClient:
    def __init__(self) -> None:
        self._intents = self._load_json("restaurant_intents.json")
        self._entities = self._load_json("entities.json")

    def _load_json(self, filename: str):
        path = Path(__file__).resolve().parents[2] / "data" / "nlp" / filename
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def _detect_entities(self, text: str) -> dict:
        lowered = text.lower()
        found: dict[str, str | int] = {}
        patterns = {
            "date": r"\b(today|tonight|tomorrow|friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b",
            "time": r"\b(\d{1,2}(?::\d{2})?\s?(?:am|pm)?)\b",
            "party_size": r"\b(\d{1,2})\s?(?:guests|people|party)?\b",
            "allergen": r"\b(peanut|dairy|gluten|shellfish|soy|nut)\b",
            "occasion": r"\b(anniversary|birthday|proposal|business dinner)\b",
            "budget": r"\$(\d+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match:
                value = match.group(1)
                found[key] = int(value) if key == "party_size" and value.isdigit() else value
        return found

    async def classify_intent(self, text: str, language: str = "en") -> dict:
        correlation_id = str(uuid4())
        lowered = text.lower()
        best_intent = "HumanEscalation"
        best_score = 0.2
        for item in self._intents:
            score = sum(1 for utterance in item.get("utterances", []) if utterance.lower() in lowered)
            if score > best_score:
                best_intent = item["intent"]
                best_score = min(0.99, 0.5 + 0.15 * score)
        entities = self._detect_entities(text)
        route_map = {
            "ReserveTable": "reservation",
            "PrivateDining": "private_dining",
            "AskMenu": "menu",
            "AskAllergen": "allergy",
            "Complaint": "human_review",
            "WinePairing": "sommelier",
            "FaqPolicy": "faq",
            "HumanEscalation": "human_review",
        }
        if settings.mock_mode:
            return {
                "intent": best_intent,
                "confidence": best_score,
                "entities": entities,
                "recommended_route": route_map.get(best_intent, "concierge"),
                "clarification_required": best_score < 0.55,
                "correlation_id": correlation_id,
            }
        return {
            "intent": best_intent,
            "confidence": best_score,
            "entities": entities,
            "recommended_route": route_map.get(best_intent, "concierge"),
            "clarification_required": best_score < 0.55,
            "correlation_id": correlation_id,
        }
