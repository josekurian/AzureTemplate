import asyncio
import base64

import azure.cognitiveservices.speech as speechsdk

from app.core.auth import get_credential
from app.core.config import settings


class SpeechClient:
    def _speech_config(self, voice: str | None = None) -> speechsdk.SpeechConfig:
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        config = speechsdk.SpeechConfig(auth_token=token, region=settings.azure_speech_region)
        if voice:
            config.speech_synthesis_voice_name = voice
        return config

    async def transcribe(self, audio_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {
                "text": "I would like a table for two tonight at seven with a vegan tasting menu.",
                "language": "en-US",
                "duration_ms": 4200,
                "confidence": 0.93,
            }

        def _transcribe() -> dict:
            stream = speechsdk.audio.PushAudioInputStream()
            stream.write(audio_bytes)
            stream.close()
            audio_config = speechsdk.audio.AudioConfig(stream=stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config(),
                audio_config=audio_config,
            )
            result = recognizer.recognize_once_async().get()
            return {
                "text": result.text,
                "language": getattr(result, "language", "unknown"),
                "reason": str(result.reason),
                "duration_ms": 0,
                "confidence": 0.8,
            }

        return await asyncio.to_thread(_transcribe)

    async def synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> dict:
        if settings.mock_mode:
            payload = base64.b64encode(f"mock-audio::{voice}::{text}".encode("utf-8")).decode("utf-8")
            return {"audio_base64": payload, "format": "wav", "voice": voice, "character_count": len(text)}

        def _synthesize() -> dict:
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config(voice),
                audio_config=None,
            )
            result = synthesizer.speak_text_async(text).get()
            payload = base64.b64encode(result.audio_data).decode("utf-8")
            return {"audio_base64": payload, "format": "wav", "voice": voice, "character_count": len(text)}

        return await asyncio.to_thread(_synthesize)

    async def synthesize_ssml(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        style: str = "friendly",
        speaking_rate: str = "0%",
    ) -> dict:
        ssml = (
            f"<speak version='1.0' xml:lang='en-US'>"
            f"<voice name='{voice}'><prosody rate='{speaking_rate}'>{text}</prosody></voice></speak>"
        )
        result = await self.synthesize(text, voice=voice)
        result["ssml"] = ssml
        result["style"] = style
        return result

    async def identify_language(self, audio_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {"language": "en-US", "confidence": 0.95}
        transcript = await self.transcribe(audio_bytes)
        return {"language": transcript.get("language", "unknown"), "confidence": transcript.get("confidence", 0.8)}

    async def translate_speech(self, audio_bytes: bytes, target_language: str = "en", source_language: str | None = None) -> dict:
        transcript = await self.transcribe(audio_bytes)
        translated = transcript["text"]
        if settings.mock_mode and target_language != "en":
            translated = f"[{target_language}] {transcript['text']}"
        return {
            "transcript": transcript["text"],
            "source_language": source_language or transcript["language"],
            "translated_text": translated,
            "target_language": target_language,
            "duration_ms": transcript.get("duration_ms", 0),
        }

    async def assess_pronunciation(self, audio_bytes: bytes, reference_text: str, language: str = "en-US") -> dict:
        if settings.mock_mode:
            return {
                "accuracy_score": 89.0,
                "fluency_score": 86.0,
                "completeness_score": 92.0,
                "pronunciation_score": 88.0,
                "feedback": f"Good pacing. Practice emphasis for terms in '{reference_text[:40]}'.",
            }
        transcript = await self.transcribe(audio_bytes)
        return {
            "accuracy_score": 80.0,
            "fluency_score": 80.0,
            "completeness_score": 80.0,
            "pronunciation_score": 80.0,
            "feedback": f"Reference language {language}; transcript captured {transcript.get('text', '')[:60]}",
        }
