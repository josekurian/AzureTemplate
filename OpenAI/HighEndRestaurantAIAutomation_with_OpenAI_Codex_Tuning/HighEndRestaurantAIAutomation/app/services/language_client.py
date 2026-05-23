from azure.ai.textanalytics import TextAnalyticsClient
from app.core.auth import get_credential
from app.core.config import settings

class LanguageClient:
    def _client(self):
        return TextAnalyticsClient(endpoint=settings.azure_language_endpoint, credential=get_credential())

    async def analyze_guest_message(self, text: str) -> dict:
        if settings.mock_mode:
            return {"sentiment": "positive", "pii_redacted": text, "key_phrases": ["reservation", "tasting menu"]}
        client = self._client()
        sentiment = client.analyze_sentiment([text])[0]
        pii = client.recognize_pii_entities([text])[0]
        phrases = client.extract_key_phrases([text])[0]
        return {
            "sentiment": sentiment.sentiment,
            "pii_redacted": pii.redacted_text,
            "key_phrases": list(phrases.key_phrases),
        }
