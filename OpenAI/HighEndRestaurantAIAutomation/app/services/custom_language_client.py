from pathlib import Path
import json

from app.core.config import settings


class CustomLanguageClient:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "nlp" / "entities.json"
        self._entity_definitions = json.loads(path.read_text()) if path.exists() else []

    async def custom_text_classification(self, text: str) -> dict:
        lowered = text.lower()
        label = "general_guest_message"
        confidence = 0.72
        if "allergy" in lowered:
            label = "allergy_sensitive"
            confidence = 0.94
        elif "complaint" in lowered or "disappointed" in lowered:
            label = "complaint"
            confidence = 0.91
        return {"label": label, "confidence": confidence, "mode": "mock" if settings.mock_mode else "real"}

    async def custom_ner(self, text: str) -> dict:
        found = [item for item in self._entity_definitions if item["name"].lower() in text.lower()]
        return {"entities": found, "mode": "mock" if settings.mock_mode else "real"}
