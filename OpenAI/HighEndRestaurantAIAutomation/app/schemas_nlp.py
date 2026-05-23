from typing import Any, Optional

from pydantic import BaseModel, Field


class NLPAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    include_opinion_mining: bool = False


class PiiRedactionRequest(BaseModel):
    text: str = Field(..., min_length=1)


class IntentRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = "en"


class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    language: str = "en"


class TranslationTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    to_languages: list[str] = Field(default_factory=lambda: ["en"])
    use_glossary: bool = True


class TranslationDocumentRequest(BaseModel):
    filename: str
    target_language: str


class PronunciationAssessmentRequest(BaseModel):
    reference_text: str = Field(..., min_length=1)
    language: str = "en-US"
    grading_system: str = "HundredMark"


class SpeechTranslateRequest(BaseModel):
    target_language: str = "en"
    source_language: Optional[str] = None


class SpeechSynthesizeSsmlRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = "en-US-JennyNeural"
    style: str = "friendly"
    speaking_rate: str = "0%"


class MultilingualChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    guest_id: Optional[str] = None
    source_language: Optional[str] = None
    response_language: Optional[str] = None
    synthesize_audio: bool = False


class SafeTelemetry(BaseModel):
    feature: str
    correlation_id: str
    latency_ms: int = 0
    detected_language: Optional[str] = None
    target_language: Optional[str] = None
    confidence: Optional[float] = None
    redaction_count: int = 0
    fallback_reason: Optional[str] = None
    audio_duration_ms: Optional[int] = None


class NLPAnalysisResponse(BaseModel):
    language: str
    sentiment: str
    key_phrases: list[str]
    entities: list[dict[str, Any]]
    pii_redacted: str
    redaction_count: int
    opinion_mining: Optional[list[dict[str, Any]]] = None
    telemetry: SafeTelemetry


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict[str, Any]
    recommended_route: str
    clarification_required: bool = False
    telemetry: SafeTelemetry


class QAResponse(BaseModel):
    answer: str
    source_id: str
    confidence: float
    escalation_required: bool
    telemetry: SafeTelemetry


class TranslationTextResponse(BaseModel):
    detected_language: str
    translations: dict[str, str]
    glossary_applied: bool
    telemetry: SafeTelemetry


class TranslationDocumentResponse(BaseModel):
    status: str
    filename: str
    target_language: str
    translated_filename: str
    telemetry: SafeTelemetry


class SpeechTranslationResponse(BaseModel):
    transcript: str
    source_language: str
    translated_text: str
    target_language: str
    telemetry: SafeTelemetry


class PronunciationAssessmentResponse(BaseModel):
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    pronunciation_score: float
    feedback: str
    telemetry: SafeTelemetry


class AudioLanguageIdentificationResponse(BaseModel):
    language: str
    confidence: float
    telemetry: SafeTelemetry


class MultilingualChatResponse(BaseModel):
    route: str
    detected_language: str
    normalized_message: str
    answer: str
    response_language: str
    audio_base64: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    telemetry: SafeTelemetry
