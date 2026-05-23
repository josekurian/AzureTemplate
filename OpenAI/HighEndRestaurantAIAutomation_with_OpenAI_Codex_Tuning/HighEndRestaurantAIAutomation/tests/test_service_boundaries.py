from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.vision_client import VisionClient

async def test_document_intelligence_mock_invoice():
    result = await DocumentIntelligenceClient().analyze_invoice(b"fake")
    assert "invoice_number" in result

async def test_vision_mock_plate():
    result = await VisionClient().analyze_plate_image(b"fake")
    assert "quality_findings" in result
