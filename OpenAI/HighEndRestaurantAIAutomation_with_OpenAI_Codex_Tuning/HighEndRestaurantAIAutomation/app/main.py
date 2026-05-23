from fastapi import FastAPI, UploadFile, File
from app.core.config import settings
from app.schemas import ChatRequest, ChatResponse, ReservationRequest
from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.services.content_safety_client import ContentSafetyClient
from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.vision_client import VisionClient
from app.services.language_client import LanguageClient
from app.services.translator_client import TranslatorClient
from app.services.speech_client import SpeechClient

app = FastAPI(title="High-End Restaurant AI Automation", version="0.1.0")
concierge = RestaurantConcierge()
content_safety = ContentSafetyClient()
doc_intel = DocumentIntelligenceClient()
vision = VisionClient()
language = LanguageClient()
translator = TranslatorClient()
speech = SpeechClient()

@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}

@app.post("/concierge/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await concierge.chat(request)

@app.post("/reservations/request")
async def reservation(request: ReservationRequest):
    return await concierge.create_reservation_draft(request)

@app.post("/safety/check")
async def safety_check(request: ChatRequest):
    return await content_safety.analyze_text(request.message)

@app.post("/language/analyze")
async def language_analyze(request: ChatRequest):
    return await language.analyze_guest_message(request.message)

@app.post("/translate")
async def translate(request: ChatRequest, to: str = "en"):
    return await translator.translate(request.message, to_language=to)

@app.post("/document/invoice")
async def analyze_invoice(file: UploadFile = File(...)):
    data = await file.read()
    return await doc_intel.analyze_invoice(data)

@app.post("/vision/plate-quality")
async def analyze_plate(file: UploadFile = File(...)):
    data = await file.read()
    return await vision.analyze_plate_image(data)

@app.post("/speech/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    data = await file.read()
    return await speech.transcribe(data)
