from app.core.config import settings

class VisionClient:
    async def analyze_plate_image(self, image_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {
                "caption": "A refined tasting plate with artful garnish and sauce dots.",
                "quality_findings": ["centered plating", "good garnish distribution", "clean rim"],
                "requires_human_review": False,
            }
        # TODO Codex: implement Azure AI Vision Image Analysis client for captions/tags/OCR.
        raise NotImplementedError("Implement Azure AI Vision image analysis")
