from fastapi import APIRouter, File, Form, UploadFile

from app.schemas import TextToSpeechResponse
from app.schemas_nlp import AudioLanguageIdentificationResponse, PronunciationAssessmentResponse, SpeechSynthesizeSsmlRequest, SpeechTranslationResponse
from app.services.speech_client import SpeechClient
from app.services.telemetry_helper import safe_telemetry

router = APIRouter(prefix="/speech", tags=["speech"])
speech_client = SpeechClient()


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    data = await file.read()
    result = await speech_client.transcribe(data)
    result["telemetry"] = safe_telemetry(
        feature="speech_transcribe",
        detected_language=result.get("language"),
        confidence=result.get("confidence"),
        audio_duration_ms=result.get("duration_ms"),
    )
    return result


@router.post("/synthesize", response_model=TextToSpeechResponse)
async def synthesize_audio(text: str = Form(...), voice: str = Form("en-US-JennyNeural")):
    result = await speech_client.synthesize(text, voice=voice)
    return TextToSpeechResponse(audio_base64=result["audio_base64"], format=result["format"], voice=result["voice"])


@router.post("/synthesize-ssml")
async def synthesize_ssml(request: SpeechSynthesizeSsmlRequest):
    result = await speech_client.synthesize_ssml(
        request.text,
        voice=request.voice,
        style=request.style,
        speaking_rate=request.speaking_rate,
    )
    result["telemetry"] = safe_telemetry(feature="speech_synthesize_ssml")
    return result


@router.post("/translate", response_model=SpeechTranslationResponse)
async def translate_speech(
    target_language: str = Form("en"),
    source_language: str | None = Form(None),
    file: UploadFile = File(...),
):
    data = await file.read()
    result = await speech_client.translate_speech(
        data,
        target_language=target_language,
        source_language=source_language,
    )
    return SpeechTranslationResponse(
        transcript=result["transcript"],
        source_language=result["source_language"],
        translated_text=result["translated_text"],
        target_language=result["target_language"],
        telemetry=safe_telemetry(
            feature="speech_translate",
            detected_language=result["source_language"],
            target_language=result["target_language"],
            audio_duration_ms=result.get("duration_ms"),
        ),
    )


@router.post("/pronunciation", response_model=PronunciationAssessmentResponse)
async def pronunciation_assessment(
    reference_text: str = Form(...),
    language: str = Form("en-US"),
    grading_system: str = Form("HundredMark"),
    file: UploadFile = File(...),
):
    data = await file.read()
    result = await speech_client.assess_pronunciation(data, reference_text, language=language)
    return PronunciationAssessmentResponse(
        accuracy_score=result["accuracy_score"],
        fluency_score=result["fluency_score"],
        completeness_score=result["completeness_score"],
        pronunciation_score=result["pronunciation_score"],
        feedback=result["feedback"],
        telemetry=safe_telemetry(feature="speech_pronunciation", detected_language=language, fallback_reason=f"grading_system={grading_system}"),
    )


@router.post("/identify-language", response_model=AudioLanguageIdentificationResponse)
async def identify_audio_language(file: UploadFile = File(...)):
    data = await file.read()
    result = await speech_client.identify_language(data)
    return AudioLanguageIdentificationResponse(
        language=result["language"],
        confidence=result["confidence"],
        telemetry=safe_telemetry(feature="speech_identify_language", detected_language=result["language"], confidence=result["confidence"]),
    )
