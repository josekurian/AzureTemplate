import json
import re
from pathlib import Path
from uuid import uuid4

from azure.ai.textanalytics import TextAnalyticsClient

from app.core.auth import get_credential
from app.core.config import settings


class LanguageClient:
    def __init__(self) -> None:
        self._intent_examples = self._load_intent_examples()
        self._entity_patterns = {
            "date": r"\b(?:today|tonight|tomorrow|friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b",
            "time": r"\b(?:\d{1,2}(?::\d{2})?\s?(?:am|pm)?)\b",
            "party_size": r"\b(\d{1,2})\s?(?:guests|people|party)?\b",
            "allergen": r"\b(peanut|dairy|gluten|shellfish|soy|nut)\b",
            "occasion": r"\b(anniversary|birthday|proposal|business dinner|private dining)\b",
            "language": r"\b(english|spanish|french|italian|german|japanese)\b",
        }

    def _client(self) -> TextAnalyticsClient:
        return TextAnalyticsClient(
            endpoint=settings.azure_language_endpoint,
            credential=get_credential(),
        )

    def _load_intent_examples(self) -> dict[str, list[str]]:
        path = Path(__file__).resolve().parents[2] / "data" / "customer_intents.json"
        if not path.exists():
            return {}
        raw = json.loads(path.read_text())
        return {item["intent"]: item.get("utterances", []) for item in raw}

    def detect_intent(self, text: str) -> str:
        lowered = text.lower()
        best_intent = "restaurant_concierge"
        best_score = 0
        for intent, utterances in self._intent_examples.items():
            score = sum(1 for utterance in utterances if utterance.lower() in lowered)
            if score > best_score:
                best_intent = intent
                best_score = score
        return best_intent

    def _mock_detect_language(self, text: str) -> tuple[str, float]:
        lowered = text.lower()
        if any(ch in text for ch in ["¿", "á", "é", "í", "ó", "ú"]) or re.search(r"\breserva\b", lowered):
            return "es", 0.98
        if any(word in lowered for word in ["bonjour", "annulation", "réservation"]):
            return "fr", 0.95
        return "en", 0.99

    def _mock_entities(self, text: str) -> list[dict]:
        entities = []
        for name, pattern in self._entity_patterns.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(1) if match.groups() else match.group(0)
                entities.append({"category": name, "text": value, "confidence_score": 0.9})
        return entities

    def _redaction_count(self, original: str, redacted: str) -> int:
        return 0 if original == redacted else max(1, original.count("*"))

    async def redact_pii(self, text: str) -> dict:
        analysis = await self.analyze_guest_message(text)
        return {
            "original_length": len(text),
            "pii_redacted": analysis["pii_redacted"],
            "redaction_count": analysis.get("redaction_count", 0),
            "correlation_id": analysis.get("correlation_id"),
        }

    async def detect_language(self, text: str) -> dict:
        if settings.mock_mode:
            language, confidence = self._mock_detect_language(text)
            return {"language": language, "confidence": confidence, "correlation_id": str(uuid4())}
        client = self._client()
        result = client.detect_language([text])[0]
        return {
            "language": result.primary_language.iso6391_name,
            "confidence": result.primary_language.confidence_score,
            "correlation_id": str(uuid4()),
        }

    async def analyze_text(self, text: str, include_opinion_mining: bool = False) -> dict:
        correlation_id = str(uuid4())
        if settings.mock_mode:
            language, language_confidence = self._mock_detect_language(text)
            entities = self._mock_entities(text)
            redacted = re.sub(r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b", "[REDACTED_PHONE]", text)
            redacted = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "[REDACTED_EMAIL]", redacted)
            result = {
                "language": language,
                "language_confidence": language_confidence,
                "sentiment": "positive" if "thank" in text.lower() else "neutral",
                "key_phrases": ["reservation", "tasting menu"] if "reservation" in text.lower() else ["restaurant"],
                "entities": entities,
                "pii_redacted": redacted,
                "redaction_count": self._redaction_count(text, redacted),
                "detected_intent": self.detect_intent(text),
                "correlation_id": correlation_id,
            }
            if include_opinion_mining:
                result["opinion_mining"] = [{"target": "service", "assessment": "positive", "confidence_score": 0.88}]
            return result

        client = self._client()
        language = client.detect_language([text])[0]
        sentiment = client.analyze_sentiment([text], show_opinion_mining=include_opinion_mining)[0]
        pii = client.recognize_pii_entities([text])[0]
        phrases = client.extract_key_phrases([text])[0]
        entities_result = client.recognize_entities([text])[0]
        payload = {
            "language": language.primary_language.iso6391_name,
            "language_confidence": language.primary_language.confidence_score,
            "sentiment": sentiment.sentiment,
            "key_phrases": list(phrases.key_phrases),
            "entities": [
                {
                    "category": entity.category,
                    "text": entity.text,
                    "confidence_score": entity.confidence_score,
                }
                for entity in entities_result.entities
            ],
            "pii_redacted": pii.redacted_text,
            "redaction_count": self._redaction_count(text, pii.redacted_text),
            "detected_intent": self.detect_intent(text),
            "correlation_id": correlation_id,
        }
        if include_opinion_mining:
            payload["opinion_mining"] = [
                {
                    "target": sentence.text,
                    "assessment": sentence.sentiment,
                    "confidence_score": max(sentence.confidence_scores.__dict__.values()),
                }
                for sentence in sentiment.sentences
            ]
        return payload

    async def analyze_guest_message(self, text: str) -> dict:
        return await self.analyze_text(text, include_opinion_mining=False)
