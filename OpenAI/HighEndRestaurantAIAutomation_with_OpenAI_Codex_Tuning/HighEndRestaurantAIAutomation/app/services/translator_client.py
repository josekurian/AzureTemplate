import httpx
from app.core.config import settings
from app.core.auth import get_credential

class TranslatorClient:
    async def translate(self, text: str, to_language: str = "en") -> dict:
        if settings.mock_mode:
            return {"translated_text": text, "to": to_language, "detected_language": "en"}
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        url = f"{settings.azure_translator_endpoint.rstrip('/')}/translate?api-version=3.0&to={to_language}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=[{"text": text}], headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            return response.json()[0]
