from app.core.config import settings

class SpeechClient:
    async def transcribe(self, audio_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {"text": "I would like a table for two tonight at seven with a vegan tasting menu.", "language": "en-US"}
        # TODO Codex: implement Azure Speech SDK STT. For TTS add synthesize endpoint.
        raise NotImplementedError("Implement Azure AI Speech STT/TTS")
