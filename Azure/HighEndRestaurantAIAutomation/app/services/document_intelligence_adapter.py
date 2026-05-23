class DocumentIntelligenceAdapter:
    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    async def extract_invoice(self, file_path: str):
        if self.mock_mode:
            return {"vendor": "Mock Vendor", "amount": 123.45, "currency": "USD", "confidence": 0.98}
        raise NotImplementedError

    async def analyze_layout(self, file_path: str):
        if self.mock_mode:
            return {"pages": 1, "blocks": []}
        raise NotImplementedError
