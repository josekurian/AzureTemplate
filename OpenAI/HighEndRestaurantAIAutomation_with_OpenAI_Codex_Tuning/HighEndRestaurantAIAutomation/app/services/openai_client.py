from openai import AzureOpenAI
from app.core.config import settings
from app.core.auth import get_credential

class AzureOpenAIClient:
    def _client(self):
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            azure_ad_token=token,
        )

    async def chat(self, system_prompt: str, user_prompt: str, context: str = "") -> str:
        if settings.mock_mode:
            return (
                "Mock concierge response: I recommend the chef's tasting menu with a sommelier "
                "pairing. I used grounded restaurant policy context and safety checks."
            )
        client = self._client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nGuest request:\n{user_prompt}"},
        ]
        response = client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> list[float]:
        if settings.mock_mode:
            return [0.01] * 3072
        client = self._client()
        response = client.embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=text,
        )
        return response.data[0].embedding
