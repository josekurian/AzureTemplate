from fastapi.testclient import TestClient

from app.agent_runtime.agent_router import AgentRouter
from app.agent_runtime.approval_queue import approval_queue
from app.agent_runtime.runtime import agent_runtime
from app.agent_runtime.trace_context import get_trace
from app.evaluation.agent_eval_runner import AgentEvalRunner
from app.main import app
from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.orchestrators.nlp_router import NLPRouter
from app.schemas import ChatRequest
from app.services.clu_client import CLUClient
from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.language_client import LanguageClient
from app.services.question_answering_client import QuestionAnsweringClient
from app.services.speech_client import SpeechClient
from app.services.translator_client import TranslatorClient
from app.services.vision_client import VisionClient


async def test_document_intelligence_mock_invoice():
    result = await DocumentIntelligenceClient().analyze_invoice(b"fake")
    assert "invoice_number" in result
    assert result["document_type"] == "invoice"


async def test_document_intelligence_mock_contract():
    result = await DocumentIntelligenceClient().analyze_private_event_contract(b"fake")
    assert result["document_type"] == "private_event_contract"
    assert result["human_review_required"] is True


async def test_vision_mock_plate():
    result = await VisionClient().analyze_plate_image(b"fake")
    assert "quality_findings" in result


async def test_vision_mock_menu_ocr():
    result = await VisionClient().analyze_menu_image(b"fake")
    assert "ocr_text" in result
    assert result["ocr_text"]


async def test_speech_mock_synthesis():
    result = await SpeechClient().synthesize("Welcome to Maison Azure.")
    assert result["audio_base64"]
    assert result["format"] == "wav"


async def test_language_detect_intent():
    result = await LanguageClient().analyze_guest_message("Can I book a table for two tomorrow?")
    assert result["detected_intent"] == "make_reservation"


async def test_concierge_translated_response_metadata():
    result = await RestaurantConcierge().chat(
        ChatRequest(
            message="Necesito una reserva para dos.",
            language="es",
            channel="web",
            response_language="es",
        )
    )
    assert result.translated_from == "es"
    assert result.translated_to == "es"


def test_router_selects_private_dining_agent():
    assert AgentRouter().route("I need a private dining event for 14 guests") == "private_dining_agent"


async def test_agent_runtime_returns_trace_and_memory():
    response = await agent_runtime.run_agent_chat(
        {
            "message": "Please help me with a wine pairing.",
            "language": "en",
            "actor_role": "guest",
            "session_id": "session-1",
        }
    )
    assert response.trace_id
    assert response.selected_agent == "sommelier_agent"
    assert response.memory_snapshot["last_agent"] == "sommelier_agent"


def test_detailed_health_endpoint():
    client = TestClient(app)
    response = client.get("/health/detailed")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "agent_runtime" in body["features"]


def test_bot_handoff_endpoint():
    client = TestClient(app)
    response = client.post(
        "/bot/handoff",
        json={
            "conversation_id": "conv-123",
            "guest_name": "Avery",
            "issue_summary": "Guest requests manager callback about private dining terms",
            "priority": "high",
        },
    )
    assert response.status_code == 200
    assert response.json()["handoff_required"] is True


def test_menu_ocr_endpoint():
    client = TestClient(app)
    response = client.post(
        "/vision/menu-ocr",
        files={"file": ("menu.png", b"fake-image", "image/png")},
    )
    assert response.status_code == 200
    assert "ocr_text" in response.json()


def test_contract_analysis_endpoint():
    client = TestClient(app)
    response = client.post(
        "/document/private-event-contract",
        files={"file": ("contract.pdf", b"fake-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["document_type"] == "private_event_contract"


def test_agents_chat_and_trace_endpoint():
    client = TestClient(app)
    response = client.post(
        "/agents/chat",
        json={
            "message": "I want a private dining event for 12 guests.",
            "language": "en",
            "actor_role": "guest",
            "session_id": "trace-session",
        },
    )
    assert response.status_code == 200
    body = response.json()
    trace = client.get(f"/agents/trace/{body['trace_id']}")
    assert trace.status_code == 200
    assert trace.json()["events"]


def test_private_dining_workflow_creates_approval():
    client = TestClient(app)
    response = client.post(
        "/workflows/private-dining",
        json={
            "session_id": "wf-1",
            "guest_name": "Morgan",
            "message": "We need a private dining event for 18 guests with a vegan menu.",
            "language": "en",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["approvals_requested"]


def test_approval_endpoint_decision():
    approval = approval_queue.create(
        workflow_type="private_dining",
        required_role="manager",
        created_by="test",
        summary="Approval needed",
        payload={"party_size": 12},
    )
    client = TestClient(app)
    response = client.post(
        f"/approvals/{approval['approval_id']}",
        json={"actor": "manager@example.com", "decision": "approved", "notes": "Approved for follow-up"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


async def test_eval_runner_produces_summary():
    summary = await AgentEvalRunner().run()
    assert summary["scenario_count"] >= 0


async def test_trace_lookup_contains_events():
    response = await agent_runtime.run_agent_chat(
        {"message": "Please review this allergy question.", "language": "en", "actor_role": "guest"}
    )
    events = get_trace(response.trace_id)
    assert events


async def test_language_full_analysis_and_redaction():
    result = await LanguageClient().analyze_text("My phone is 312-555-0100 and I need a reservation tomorrow.")
    assert result["language"] == "en"
    assert result["redaction_count"] >= 1
    assert "correlation_id" in result


async def test_clu_intent_route_and_entities():
    result = await CLUClient().classify_intent("We need a private dining event for 12 guests tomorrow.")
    assert result["intent"] == "PrivateDining"
    assert result["recommended_route"] == "private_dining"
    assert result["entities"]["party_size"] == 12


async def test_question_answering_faq():
    result = await QuestionAnsweringClient().answer_question("What is your cancellation policy?")
    assert result["source_id"] == "faq:cancellation_policy"
    assert result["confidence"] >= 0.6


async def test_translator_many_with_glossary():
    result = await TranslatorClient().translate_many("Chef's Seasonal Tasting", ["es", "fr"])
    assert result["translations"]["es"]
    assert result["glossary_applied"] is True


async def test_speech_translation_and_pronunciation():
    speech = SpeechClient()
    translated = await speech.translate_speech(b"fake", target_language="fr")
    assert translated["target_language"] == "fr"
    assessment = await speech.assess_pronunciation(b"fake", "Grand Reserve Pairing")
    assert assessment["accuracy_score"] > 0


async def test_nlp_router_faq_and_clarification_paths():
    router = NLPRouter()
    faq = await router.route_message("What is your dress code?", language="en")
    assert faq["route"] == "faq"
    low_conf = await router.route_message("Help me.", language="en")
    assert low_conf["route"] == "clarification"


def test_nlp_analyze_endpoint():
    client = TestClient(app)
    response = client.post("/nlp/analyze", json={"text": "Call me at 312-555-0100 for dinner tomorrow."})
    assert response.status_code == 200
    assert response.json()["redaction_count"] >= 1


def test_nlp_intent_endpoint():
    client = TestClient(app)
    response = client.post("/nlp/intent", json={"text": "I need a wine pairing recommendation.", "language": "en"})
    assert response.status_code == 200
    assert response.json()["recommended_route"] == "sommelier"


def test_nlp_qa_endpoint():
    client = TestClient(app)
    response = client.post("/nlp/qa", json={"question": "What is the private dining minimum?", "language": "en"})
    assert response.status_code == 200
    assert response.json()["source_id"] == "faq:private_dining_minimum"


def test_translate_text_endpoint():
    client = TestClient(app)
    response = client.post("/translate/text", json={"text": "Chef's Seasonal Tasting", "to_languages": ["es", "fr"]})
    assert response.status_code == 200
    assert "es" in response.json()["translations"]


def test_translate_document_endpoint():
    client = TestClient(app)
    response = client.post(
        "/translate/document",
        data={"target_language": "fr"},
        files={"file": ("menu.txt", b"Chef's Seasonal Tasting", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["target_language"] == "fr"


def test_speech_ssml_and_translate_endpoints():
    client = TestClient(app)
    ssml = client.post("/speech/synthesize-ssml", json={"text": "Welcome to Maison Azure."})
    assert ssml.status_code == 200
    translated = client.post(
        "/speech/translate",
        data={"target_language": "es", "source_language": "en-US"},
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
    )
    assert translated.status_code == 200
    assert translated.json()["target_language"] == "es"


def test_speech_pronunciation_and_language_identification_endpoints():
    client = TestClient(app)
    pronunciation = client.post(
        "/speech/pronunciation",
        data={"reference_text": "Grand Reserve Pairing", "language": "en-US", "grading_system": "HundredMark"},
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
    )
    assert pronunciation.status_code == 200
    identification = client.post(
        "/speech/identify-language",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
    )
    assert identification.status_code == 200
    assert identification.json()["language"] == "en-US"


def test_multilingual_chat_endpoint():
    client = TestClient(app)
    response = client.post(
        "/nlp/multilingual-chat",
        json={
            "message": "Necesito una reserva para dos personas mañana.",
            "source_language": "es",
            "response_language": "es",
            "synthesize_audio": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detected_language"] == "es"
    assert body["response_language"] == "es"
