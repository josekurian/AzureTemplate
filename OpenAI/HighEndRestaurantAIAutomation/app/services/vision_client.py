from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

from app.core.auth import get_credential
from app.core.config import settings


class VisionClient:
    def _client(self) -> ImageAnalysisClient:
        return ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=get_credential(),
        )

    async def analyze_plate_image(self, image_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {
                "caption": "A refined tasting plate with artful garnish and sauce dots.",
                "quality_findings": ["centered plating", "good garnish distribution", "clean rim"],
                "requires_human_review": False,
            }
        response = self._client().analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.CAPTION, VisualFeatures.TAGS],
        )
        tags = [tag.name for tag in getattr(response, "tags", [])]
        caption = getattr(getattr(response, "caption_result", None), "text", None)
        findings = []
        if caption:
            findings.append(caption)
        findings.extend(tags[:5])
        return {
            "caption": caption,
            "quality_findings": findings,
            "requires_human_review": False,
        }

    async def analyze_menu_image(self, image_bytes: bytes) -> dict:
        if settings.mock_mode:
            return {
                "caption": "A printed tasting menu with wine pairing options.",
                "ocr_text": [
                    "Chef's Seasonal Tasting",
                    "Vegetarian version available with 24-hour notice",
                    "Grand Reserve Pairing",
                ],
                "tags": ["menu", "text", "restaurant"],
            }
        response = self._client().analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.CAPTION, VisualFeatures.READ, VisualFeatures.TAGS],
        )
        ocr_lines: list[str] = []
        read_result = getattr(response, "read_result", None)
        if read_result and getattr(read_result, "blocks", None):
            for block in read_result.blocks:
                for line in getattr(block, "lines", []):
                    if getattr(line, "text", None):
                        ocr_lines.append(line.text)
        return {
            "caption": getattr(getattr(response, "caption_result", None), "text", None),
            "ocr_text": ocr_lines,
            "tags": [tag.name for tag in getattr(response, "tags", [])],
        }
