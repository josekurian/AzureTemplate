import os
import asyncio

try:
    from azure.identity import DefaultAzureCredential
    from azure.ai.documentanalysis.aio import DocumentAnalysisClient
except Exception:
    DefaultAzureCredential = None
    DocumentAnalysisClient = None

class DocumentIntelligenceAdapter:
    def __init__(self, mock_mode: bool = True):
        env_mock = os.getenv('MOCK_MODE', 'true').lower() == 'true'
        self.mock_mode = env_mock if mock_mode is None else mock_mode
        self.endpoint = os.getenv('DOCINT_ENDPOINT')
        self.credential = None
        if not self.mock_mode and DefaultAzureCredential is not None:
            try:
                self.credential = DefaultAzureCredential()
            except Exception:
                self.credential = None

    async def extract_invoice(self, file_path: str):
        if self.mock_mode:
            return {"vendor": "Mock Vendor", "amount": 123.45, "currency": "USD", "confidence": 0.98}
        if DocumentAnalysisClient is None or not self.endpoint:
            raise RuntimeError('DocumentAnalysisClient not configured or endpoint missing')
        client = DocumentAnalysisClient(self.endpoint, self.credential)
        with open(file_path, 'rb') as f:
            data = f.read()
        poller = await client.begin_analyze_document('prebuilt-invoice', document=data)
        result = await poller.result()
        # Simplified extraction - map fields
        out = {}
        for field, val in result.documents[0].fields.items():
            out[field] = val.value if hasattr(val, 'value') else None
        return out

    async def analyze_layout(self, file_path: str):
        if self.mock_mode:
            return {"pages": 1, "blocks": []}
        if DocumentAnalysisClient is None or not self.endpoint:
            raise RuntimeError('DocumentAnalysisClient not configured or endpoint missing')
        client = DocumentAnalysisClient(self.endpoint, self.credential)
        with open(file_path, 'rb') as f:
            data = f.read()
        poller = await client.begin_analyze_document('prebuilt-layout', document=data)
        result = await poller.result()
        return {"pages": len(result.pages), "blocks": []}
