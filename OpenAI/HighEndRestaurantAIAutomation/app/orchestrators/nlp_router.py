from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.schemas import ChatRequest
from app.services.clu_client import CLUClient
from app.services.custom_language_client import CustomLanguageClient
from app.services.language_client import LanguageClient
from app.services.question_answering_client import QuestionAnsweringClient
from app.services.search_client import RestaurantSearchClient
from app.services.speech_client import SpeechClient
from app.services.translator_client import TranslatorClient


class NLPRouter:
    def __init__(self) -> None:
        self.language = LanguageClient()
        self.translator = TranslatorClient()
        self.clu = CLUClient()
        self.custom_language = CustomLanguageClient()
        self.qa = QuestionAnsweringClient()
        self.concierge = RestaurantConcierge()
        self.search = RestaurantSearchClient()
        self.speech = SpeechClient()

    async def route_message(self, message: str, language: str = "en") -> dict:
        translated = message
        detected_language = language
        if not language or language == "auto":
            detected = await self.language.detect_language(message)
            detected_language = detected["language"]
        if detected_language != "en":
            translated_payload = await self.translator.translate(message, to_language="en")
            translated = translated_payload["translated_text"]
            detected_language = translated_payload["detected_language"]
        analysis = await self.language.analyze_text(translated)
        intent = await self.clu.classify_intent(analysis["pii_redacted"], language="en")
        if intent["confidence"] < 0.55:
            return {
                "route": "clarification",
                "detected_language": detected_language,
                "normalized_message": analysis["pii_redacted"],
                "analysis": analysis,
                "intent": intent,
                "answer": "I want to make sure I understand correctly. Are you asking about a reservation, menu guidance, private dining, or a policy question?",
                "sources": [],
                "fallback_reason": "low_intent_confidence",
            }
        if intent["recommended_route"] == "faq":
            qa = await self.qa.answer_question(analysis["pii_redacted"], language="en")
            return {
                "route": "faq",
                "detected_language": detected_language,
                "normalized_message": analysis["pii_redacted"],
                "analysis": analysis,
                "intent": intent,
                "answer": qa["answer"],
                "sources": [qa["source_id"]],
                "fallback_reason": None,
            }
        if intent["recommended_route"] == "human_review":
            return {
                "route": "human_review",
                "detected_language": detected_language,
                "normalized_message": analysis["pii_redacted"],
                "analysis": analysis,
                "intent": intent,
                "answer": "I’m routing this to a human team member for careful review.",
                "sources": [],
                "fallback_reason": "escalation_intent",
            }
        concierge_response = await self.concierge.chat(
            ChatRequest(
                message=analysis["pii_redacted"],
                guest_id=None,
                language="en",
                channel="web",
                response_language="en",
            )
        )
        return {
            "route": intent["recommended_route"],
            "detected_language": detected_language,
            "normalized_message": analysis["pii_redacted"],
            "analysis": analysis,
            "intent": intent,
            "answer": concierge_response.answer,
            "sources": concierge_response.sources,
            "fallback_reason": None,
        }

    async def multilingual_chat(self, message: str, source_language: str | None = None, response_language: str | None = None, synthesize_audio: bool = False) -> dict:
        route_result = await self.route_message(message, language=source_language or "auto")
        final_language = response_language or route_result["detected_language"] or "en"
        final_answer = route_result["answer"]
        audio_base64 = None
        if final_language != "en":
            translated = await self.translator.translate(final_answer, to_language=final_language)
            final_answer = translated["translated_text"]
        if synthesize_audio:
            audio = await self.speech.synthesize_ssml(final_answer)
            audio_base64 = audio["audio_base64"]
        return {
            **route_result,
            "answer": final_answer,
            "response_language": final_language,
            "audio_base64": audio_base64,
        }
