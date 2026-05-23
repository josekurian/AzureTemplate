import httpx
from app.core.config import settings
from app.core.auth import get_credential
from pathlib import Path
import csv
from uuid import uuid4
import re

class TranslatorClient:
    def __init__(self) -> None:
        self._glossary = self._load_glossary()

    def _load_glossary(self) -> dict[str, dict[str, str]]:
        path = Path(__file__).resolve().parents[2] / "data" / "nlp" / "translator_dictionary.tsv"
        glossary: dict[str, dict[str, str]] = {}
        if not path.exists():
            return glossary
        with path.open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                glossary.setdefault(row["source"].lower(), {})[row["target_language"]] = row["target"]
        return glossary

    def _detect_language(self, text: str) -> str:
        lowered = text.lower()
        if any(ch in text for ch in ["¿", "á", "é", "í", "ó", "ú"]) or re.search(r"\breserva\b", lowered):
            return "es"
        if any(word in lowered for word in ["bonjour", "annulation", "réservation"]):
            return "fr"
        return "en"

    def _apply_glossary(self, text: str, to_language: str) -> tuple[str, bool]:
        applied = False
        translated = text
        for source, mapping in self._glossary.items():
            if source in translated.lower() and to_language in mapping:
                translated = re_sub_case_insensitive(translated, source, mapping[to_language])
                applied = True
        return translated, applied

    async def detect_language(self, text: str) -> dict:
        return {"language": self._detect_language(text), "confidence": 0.98, "correlation_id": str(uuid4())}

    async def translate(self, text: str, to_language: str = "en", use_glossary: bool = True) -> dict:
        if settings.mock_mode:
            detected_language = self._detect_language(text)
            translated_text = text
            glossary_applied = False
            if use_glossary:
                translated_text, glossary_applied = self._apply_glossary(text, to_language)
            return {
                "translated_text": translated_text,
                "to": to_language,
                "detected_language": detected_language,
                "glossary_applied": glossary_applied,
                "correlation_id": str(uuid4()),
            }
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        url = f"{settings.azure_translator_endpoint.rstrip('/')}/translate?api-version=3.0&to={to_language}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=[{"text": text}], headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            payload = response.json()[0]
            return {
                "translated_text": payload["translations"][0]["text"] if payload.get("translations") else text,
                "to": to_language,
                "detected_language": payload.get("detectedLanguage", {}).get("language", "unknown"),
                "glossary_applied": False,
                "correlation_id": str(uuid4()),
            }

    async def translate_many(self, text: str, to_languages: list[str], use_glossary: bool = True) -> dict:
        detected = await self.detect_language(text)
        translations = {}
        glossary_applied = False
        for language in to_languages:
            result = await self.translate(text, to_language=language, use_glossary=use_glossary)
            translations[language] = result["translated_text"]
            glossary_applied = glossary_applied or result.get("glossary_applied", False)
        return {
            "detected_language": detected["language"],
            "translations": translations,
            "glossary_applied": glossary_applied,
            "correlation_id": detected["correlation_id"],
        }

    async def translate_document(self, filename: str, content: bytes, target_language: str) -> dict:
        output_name = f"{Path(filename).stem}.{target_language}{Path(filename).suffix or '.txt'}"
        return {
            "status": "completed" if settings.mock_mode else "submitted",
            "filename": filename,
            "target_language": target_language,
            "translated_filename": output_name,
            "character_count": len(content.decode('utf-8', errors='ignore')),
            "correlation_id": str(uuid4()),
        }


def re_sub_case_insensitive(text: str, old: str, new: str) -> str:
    import re

    return re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
