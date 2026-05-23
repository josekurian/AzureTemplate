import httpx
from app.core.config import settings
from app.core.auth import get_credential

class ContentSafetyClient:
    async def analyze_text(self, text: str) -> dict:
        if settings.mock_mode:
            decision = "block" if "ignore previous instructions" in text.lower() else "allow"
            return {
                "decision": decision,
                "categories": {"hate": 0, "violence": 0, "sexual": 0, "self_harm": 0},
                "prompt_shield": decision == "block",
            }
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        url = f"{settings.azure_content_safety_endpoint.rstrip('/')}/contentsafety/text:analyze?api-version=2024-09-01"
        payload = {"text": text, "categories": ["Hate", "Violence", "Sexual", "SelfHarm"]}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            return response.json()
