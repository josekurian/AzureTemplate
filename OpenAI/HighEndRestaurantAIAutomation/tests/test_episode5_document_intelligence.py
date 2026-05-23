from fastapi.testclient import TestClient

from app.main import app
from app.services.document_intelligence_client import DocumentIntelligenceClient


async def test_receipt_analysis_mock_shape():
    result = await DocumentIntelligenceClient().analyze_receipt(b"fake")
    assert result["document_type"] == "receipt"
    assert result["total"] > 0
    assert result["line_items"]


async def test_layout_analysis_mock_shape():
    result = await DocumentIntelligenceClient().analyze_layout(b"fake")
    assert result["document_type"] == "layout"
    assert result["paragraphs"]
    assert result["tables"]


async def test_contract_alias_uses_custom_event_type():
    result = await DocumentIntelligenceClient().analyze_custom_event_document(b"fake")
    assert result["document_type"] == "custom_event_contract"
    assert result["human_review_required"] is True


def test_receipt_endpoint():
    client = TestClient(app)
    response = client.post(
        "/document/receipt",
        files={"file": ("receipt.png", b"fake-image", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["document_type"] == "receipt"


def test_layout_endpoint():
    client = TestClient(app)
    response = client.post(
        "/document/layout",
        files={"file": ("event-order.pdf", b"fake-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["document_type"] == "layout"


def test_contract_endpoint():
    client = TestClient(app)
    response = client.post(
        "/document/contract",
        files={"file": ("contract.pdf", b"fake-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["document_type"] == "custom_event_contract"
