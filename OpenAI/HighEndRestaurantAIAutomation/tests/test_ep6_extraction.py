from fastapi.testclient import TestClient

from app.main import app
from app.services.content_understanding_client import ContentUnderstandingClient
from app.services.document_intelligence_client import DocumentIntelligenceClient


async def test_document_intelligence_v2_contains_grounding_and_markdown():
    result = await DocumentIntelligenceClient().analyze_invoice(b"fake")
    assert result["field_confidences"]
    assert result["markdown"]
    assert result["grounding_references"]


async def test_content_understanding_v2_contains_confidence_and_grounding():
    result = await ContentUnderstandingClient().analyze_content(
        analyzer_id="menu_pdf",
        content_bytes=b"fake",
        filename="menu.pdf",
        content_type="application/pdf",
    )
    assert result["confidence"] > 0
    assert result["grounding_references"]
    assert result["markdown"]


def test_document_contract_v2_endpoint():
    client = TestClient(app)
    response = client.post(
        "/document/contract/v2",
        files={"file": ("contract.pdf", b"fake-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["grounding_references"]


def test_content_understanding_analyzer_list_endpoint():
    client = TestClient(app)
    response = client.get("/content-understanding/analyzers")
    assert response.status_code == 200
    assert any(item["analyzer_id"] == "menu_pdf" for item in response.json())
