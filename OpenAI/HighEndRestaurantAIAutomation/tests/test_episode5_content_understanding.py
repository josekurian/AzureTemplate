from fastapi.testclient import TestClient

from app.main import app
from app.services.content_understanding_client import ContentUnderstandingClient


async def test_content_understanding_menu_analyzer():
    result = await ContentUnderstandingClient().analyze_content(
        analyzer_id="menu_pdf",
        content_bytes=b"fake",
        filename="menu.pdf",
        content_type="application/pdf",
    )
    assert result["status"] == "succeeded"
    assert "upsell_candidates" in result["fields"]


async def test_content_understanding_event_contract_analyzer():
    result = await ContentUnderstandingClient().analyze_content(
        analyzer_id="event_contract",
        content_bytes=b"fake",
        filename="contract.pdf",
        content_type="application/pdf",
    )
    assert result["fields"]["approval_required"] is True
    assert result["warnings"]


def test_content_understanding_endpoint():
    client = TestClient(app)
    response = client.post(
        "/content-understanding/analyze",
        data={"analyzer_id": "guest_call_audio"},
        files={"file": ("guest.wav", b"fake-audio", "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json()["analyzer_id"] == "guest_call_audio"
    assert response.json()["status"] == "succeeded"
