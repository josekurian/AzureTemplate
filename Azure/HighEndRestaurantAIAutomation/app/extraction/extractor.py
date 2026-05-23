class Extractor:
    def __init__(self, docint):
        self.docint = docint

    async def extract(self, path: str):
        return await self.docint.extract_invoice(path)
