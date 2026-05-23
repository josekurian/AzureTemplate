from fastapi import APIRouter

from app.orchestrators.nlp_router import NLPRouter
from app.schemas_nlp import (
    IntentRequest,
    IntentResponse,
    MultilingualChatRequest,
    MultilingualChatResponse,
    NLPAnalysisRequest,
    NLPAnalysisResponse,
    PiiRedactionRequest,
    QARequest,
    QAResponse,
)
from app.services.clu_client import CLUClient
from app.services.custom_language_client import CustomLanguageClient
from app.services.language_client import LanguageClient
from app.services.question_answering_client import QuestionAnsweringClient
from app.services.telemetry_helper import safe_telemetry

router = APIRouter(prefix="/nlp", tags=["nlp"])

language_client = LanguageClient()
clu_client = CLUClient()
custom_language_client = CustomLanguageClient()
qa_client = QuestionAnsweringClient()
nlp_router = NLPRouter()


@router.post("/analyze", response_model=NLPAnalysisResponse)
async def analyze_text(request: NLPAnalysisRequest):
    result = await language_client.analyze_text(request.text, include_opinion_mining=request.include_opinion_mining)
    return NLPAnalysisResponse(
        language=result["language"],
        sentiment=result["sentiment"],
        key_phrases=result["key_phrases"],
        entities=result["entities"],
        pii_redacted=result["pii_redacted"],
        redaction_count=result["redaction_count"],
        opinion_mining=result.get("opinion_mining"),
        telemetry=safe_telemetry(
            feature="nlp_analyze",
            detected_language=result["language"],
            redaction_count=result["redaction_count"],
        ),
    )


@router.post("/pii/redact")
async def redact_pii(request: PiiRedactionRequest):
    result = await language_client.redact_pii(request.text)
    return {
        "pii_redacted": result["pii_redacted"],
        "redaction_count": result["redaction_count"],
        "telemetry": safe_telemetry(feature="pii_redact", redaction_count=result["redaction_count"]),
    }


@router.post("/detect-language")
async def detect_language(request: PiiRedactionRequest):
    result = await language_client.detect_language(request.text)
    return {
        "language": result["language"],
        "confidence": result["confidence"],
        "telemetry": safe_telemetry(feature="detect_language", detected_language=result["language"], confidence=result["confidence"]),
    }


@router.post("/intent", response_model=IntentResponse)
async def classify_intent(request: IntentRequest):
    result = await clu_client.classify_intent(request.text, language=request.language)
    return IntentResponse(
        intent=result["intent"],
        confidence=result["confidence"],
        entities=result["entities"],
        recommended_route=result["recommended_route"],
        clarification_required=result["clarification_required"],
        telemetry=safe_telemetry(
            feature="intent_classification",
            detected_language=request.language,
            confidence=result["confidence"],
            fallback_reason="low_intent_confidence" if result["clarification_required"] else None,
        ),
    )


@router.post("/qa", response_model=QAResponse)
async def answer_qa(request: QARequest):
    result = await qa_client.answer_question(request.question, language=request.language)
    return QAResponse(
        answer=result["answer"],
        source_id=result["source_id"],
        confidence=result["confidence"],
        escalation_required=result["escalation_required"],
        telemetry=safe_telemetry(
            feature="faq_qa",
            detected_language=request.language,
            confidence=result["confidence"],
            fallback_reason="low_qa_confidence" if result["escalation_required"] else None,
        ),
    )


@router.post("/custom/classify")
async def custom_classify(request: IntentRequest):
    result = await custom_language_client.custom_text_classification(request.text)
    return {
        **result,
        "telemetry": safe_telemetry(feature="custom_text_classification", detected_language=request.language, confidence=result["confidence"]),
    }


@router.post("/custom/entities")
async def custom_entities(request: IntentRequest):
    result = await custom_language_client.custom_ner(request.text)
    return {
        **result,
        "telemetry": safe_telemetry(feature="custom_ner", detected_language=request.language),
    }


@router.post("/multilingual-chat", response_model=MultilingualChatResponse)
async def multilingual_chat(request: MultilingualChatRequest):
    result = await nlp_router.multilingual_chat(
        message=request.message,
        source_language=request.source_language,
        response_language=request.response_language,
        synthesize_audio=request.synthesize_audio,
    )
    return MultilingualChatResponse(
        route=result["route"],
        detected_language=result["detected_language"],
        normalized_message=result["normalized_message"],
        answer=result["answer"],
        response_language=result["response_language"],
        audio_base64=result.get("audio_base64"),
        sources=result.get("sources", []),
        telemetry=safe_telemetry(
            feature="multilingual_chat",
            detected_language=result["detected_language"],
            target_language=result["response_language"],
            confidence=result["intent"]["confidence"],
            redaction_count=result["analysis"]["redaction_count"],
            fallback_reason=result.get("fallback_reason"),
        ),
    )
