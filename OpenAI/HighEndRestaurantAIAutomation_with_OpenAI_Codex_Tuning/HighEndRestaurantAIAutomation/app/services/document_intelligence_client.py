from app.core.config import settings

class DocumentIntelligenceClient:
    async def analyze_invoice(self, document_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {
                "vendor": "Contoso Fine Foods",
                "invoice_number": "INV-2026-0422",
                "total": 1842.75,
                "fields": {"due_date": "2026-06-01", "purchase_order": "PO-PRIVATE-DINING"},
            }
        # TODO Codex: implement with azure.ai.documentintelligence.DocumentIntelligenceClient
        # Use prebuilt-invoice for invoices and custom model IDs for restaurant-specific contracts.
        raise NotImplementedError("Implement Azure Document Intelligence prebuilt-invoice call")
