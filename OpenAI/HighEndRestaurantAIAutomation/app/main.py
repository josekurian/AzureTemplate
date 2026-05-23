from fastapi import FastAPI, File, UploadFile

from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.knowledge import router as knowledge_router
from app.api.nlp import router as nlp_router
from app.api.speech import router as speech_router
from app.api.translation import router as translation_router
from app.api.workflows import router as workflows_router
from app.core.config import settings
from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.schemas import (
    BotHandoffRequest,
    ChatRequest,
    ChatResponse,
    DetailedHealthResponse,
    FeatureStatus,
    ReservationRequest,
    ReservationResponse,
    TextToSpeechRequest,
    TextToSpeechResponse,
    TranslationRequest,
)
from app.services.bot_adapter import BotAdapter
from app.services.content_safety_client import ContentSafetyClient
from app.services.custom_vision_client import CustomVisionClient
from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.face_client import FaceClient
from app.services.language_client import LanguageClient
from app.services.speech_client import SpeechClient
from app.services.translator_client import TranslatorClient
from app.services.vision_client import VisionClient
from app.orchestrators.nlp_router import NLPRouter

app = FastAPI(title="High-End Restaurant AI Automation", version="0.5.0")
app.include_router(agents_router)
app.include_router(workflows_router)
app.include_router(approvals_router)
app.include_router(nlp_router)
app.include_router(translation_router)
app.include_router(speech_router)
app.include_router(knowledge_router)

concierge = RestaurantConcierge()
content_safety = ContentSafetyClient()
doc_intel = DocumentIntelligenceClient()
vision = VisionClient()
language = LanguageClient()
translator = TranslatorClient()
speech = SpeechClient()
bot_adapter = BotAdapter()
face = FaceClient()
custom_vision = CustomVisionClient()
episode4_nlp = NLPRouter()


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}


@app.get("/health/detailed", response_model=DetailedHealthResponse)
def detailed_health():
    mode = "mock" if settings.mock_mode else "live"
    return DetailedHealthResponse(
        status="ok",
        mock_mode=settings.mock_mode,
        features={
            "concierge_chat": FeatureStatus(available=True, mode=mode, notes="Grounded concierge flow"),
            "reservation_draft": FeatureStatus(available=True, mode=mode, notes="Draft only; no booking confirmation"),
            "translation": FeatureStatus(available=True, mode=mode, notes="Translator-backed multilingual path"),
            "speech": FeatureStatus(available=True, mode=mode, notes="STT and TTS endpoints"),
            "document_intelligence": FeatureStatus(available=True, mode=mode, notes="Invoice and contract analysis"),
            "vision": FeatureStatus(available=True, mode=mode, notes="Plate analysis and menu OCR"),
            "vip_demo": FeatureStatus(available=True, mode="demo", notes="Consent-based optional Face demo"),
            "bot_handoff": FeatureStatus(available=True, mode="integration", notes="Safe Azure Bot handoff payload"),
            "agent_runtime": FeatureStatus(available=True, mode=mode, notes="Episode 3 typed agents and tool orchestration"),
            "workflow_engine": FeatureStatus(available=True, mode=mode, notes="Approval-gated private dining workflow"),
            "episode4_nlp": FeatureStatus(available=True, mode=mode, notes="Text analytics, CLU-style routing, FAQ QA, translation, and speech labs"),
            "episode5_search": FeatureStatus(available=True, mode=mode, notes="Hybrid, vector, and semantic search with citations and filters"),
            "episode5_documents": FeatureStatus(available=True, mode=mode, notes="Invoice, receipt, layout, and contract extraction flows"),
            "episode5_content_understanding": FeatureStatus(available=True, mode=mode, notes="Analyzer-driven multimodal extraction patterns"),
            "episode6_ingestion_pipeline": FeatureStatus(available=True, mode=mode, notes="Chunking, normalization, embedding, indexing, and query diagnostics"),
            "episode6_human_review": FeatureStatus(available=True, mode=mode, notes="Low-confidence extraction review and correction workflow"),
        },
    )


@app.post("/concierge/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await concierge.chat(request)


@app.post("/reservations/request", response_model=ReservationResponse)
async def reservation(request: ReservationRequest):
    return await concierge.create_reservation_draft(request)


@app.post("/safety/check")
async def safety_check(request: ChatRequest):
    return await content_safety.analyze_text(request.message)


@app.post("/language/analyze")
async def language_analyze(request: ChatRequest):
    return await language.analyze_guest_message(request.message)


@app.post("/translate")
async def translate(request: TranslationRequest):
    return await translator.translate(request.text, to_language=request.to_language)


@app.post("/document/invoice")
async def analyze_invoice(file: UploadFile = File(...)):
    data = await file.read()
    return await doc_intel.analyze_invoice(data)


@app.post("/document/private-event-contract")
async def analyze_private_event_contract(file: UploadFile = File(...)):
    data = await file.read()
    return await doc_intel.analyze_private_event_contract(data)


@app.post("/vision/plate-quality")
async def analyze_plate(file: UploadFile = File(...)):
    data = await file.read()
    return await vision.analyze_plate_image(data)


@app.post("/vision/menu-ocr")
async def analyze_menu_image(file: UploadFile = File(...)):
    data = await file.read()
    return await vision.analyze_menu_image(data)


@app.post("/vision/plate-style")
async def classify_plate_style(file: UploadFile = File(...)):
    data = await file.read()
    return await custom_vision.classify_plate_style(data)


@app.post("/vip/verify")
async def verify_vip(consent_id: str, file: UploadFile = File(...)):
    data = await file.read()
    return await face.verify_vip_guest(data, consent_id)


@app.post("/bot/handoff")
async def bot_handoff(request: BotHandoffRequest):
    return await bot_adapter.build_handoff_payload(
        conversation_id=request.conversation_id,
        guest_name=request.guest_name,
        issue_summary=request.issue_summary,
        priority=request.priority,
    )


@app.post("/concierge/multilingual-chat")
async def multilingual_chat(request: ChatRequest, synthesize_audio: bool = False):
    return await episode4_nlp.multilingual_chat(
        message=request.message,
        source_language=request.language,
        response_language=request.response_language,
        synthesize_audio=synthesize_audio,
    )
